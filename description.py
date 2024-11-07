import os
import requests
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Google Sheets API设置
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')

# Perplexity API设置
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

def get_sheets_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    return build('sheets', 'v4', credentials=credentials, cache_discovery=False)

def read_spreadsheet(service, range_name):
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            logging.warning("No data found in spreadsheet")
        return values
    except Exception as e:
        logging.error(f"Error reading spreadsheet: {str(e)}")
        return []

def call_perplexity_api(prompt, temperature=0.5):
    try:
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'llama-3.1-sonar-huge-128k-online',
            'messages': [
                {
                    'role': 'system', 
                    'content': '''You are a luxury fashion expert specializing in high-end product descriptions.
                    Your responses should be:
                    1. Professional but accessible
                    2. Accurate and specific
                    3. Free of marketing hyperbole
                    4. Focused on materials, craftsmanship, and design
                    5. Compliant with EU/UK product description standards'''
                },
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1000,
            'temperature': temperature,
            'top_p': 0.9,
            'return_citations': True,
            'frequency_penalty': 1
        }
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        content = response_json['choices'][0]['message']['content']
        return content
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        return None

def generate_ebay_description(brand, product_type, style_number, additional_info):
    prompt = f"""
    Generate a concise product description in HTML format for a {brand} {product_type} with style number {style_number}.
    Additional Information: {additional_info}
    
    Requirements:
    1. Format:
        - Title: Brand + Product Type + Key Feature (max 80 characters)
        - Short description: 2-3 sentences about the product's unique features
        - 4-6 bullet points highlighting key features
    
    2. Content:
        - Focus on unique design elements, materials, and craftsmanship
        - Highlight what makes this product special
        - DO NOT include any shipping, payment, or return policy information
        - DO NOT include prices or promotional content
    
    3. Use this HTML structure:
        <h1>[Title]</h1>
        <p>[Short description]</p>
        <h3>Key Features:</h3>
        <ul>
            <li>[Feature 1]</li>
            <li>[Feature 2]</li>
            ...
        </ul>
    """
    
    response = call_perplexity_api(prompt)
    
    # 如果响应包含Markdown格式（**），则转换为HTML
    if response and '**' in response:
        # 转换标题
        response = response.replace('**Title:**', '<h1>')
        response = response.replace('**Subtitle:**', '</h1>\n<h2>')
        
        # 转换关键特性
        response = response.replace('**Key Features:**', '</h2>\n<h3>Key Features:</h3>\n<ul>')
        
        # 转换列表项
        lines = response.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            if line.strip().startswith('- **'):
                if not in_list:
                    in_list = True
                line = line.replace('- **', '<li><strong>').replace('**', '</strong>')
                line = f"{line}</li>"
            elif in_list and not line.strip().startswith('-'):
                in_list = False
                formatted_lines.append('</ul>')
            formatted_lines.append(line)
        
        response = '\n'.join(formatted_lines)
        
        # 清理其余的Markdown语法
        response = response.replace('**', '<strong>').replace('**', '</strong>')
        
        # 添加段落标签
        response = '<p>' + response + '</p>'
        response = response.replace('\n\n', '</p>\n<p>')
        
        # 清理多余的HTML标签
        response = response.replace('<p><h', '<h')
        response = response.replace('</h1></p>', '</h1>')
        response = response.replace('</h2></p>', '</h2>')
        response = response.replace('</h3></p>', '</h3>')
        response = response.replace('</ul></p>', '</ul>')
    
    return response

def write_description_to_sheet(service, sheet_name, row_index, internal_reference, description):
    try:
        # 写入描述和内部参考到工作表
        range_name = f"'{sheet_name}'!C{row_index}:D{row_index}"  # 假设"C"列是Internal Reference，"D"列是Description
        body = {
            'values': [[internal_reference, description]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        logging.info(f"Description and Internal Reference written to sheet '{sheet_name}' at row {row_index}.")
    except Exception as e:
        logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

def main():
    service = get_sheets_service()
    if not service:
        logging.error("Failed to create Sheets service.")
        return

    # 使用与perplexity-huge.py相同的范围
    product_types = read_spreadsheet(service, 'Sheet1!E2:E')
    brands = read_spreadsheet(service, 'Sheet1!F2:F')
    style_numbers = read_spreadsheet(service, 'Sheet1!I2:I')
    additional_info = read_spreadsheet(service, 'Sheet1!G2:G')
    size_info = read_spreadsheet(service, 'Sheet1!K2:X')
    internal_references = read_spreadsheet(service, 'Sheet1!C2:C')

    min_length = min(len(product_types), len(brands), len(style_numbers), len(internal_references))
    
    if min_length == 0:
        logging.error("One or more mandatory columns are empty. Please check the spreadsheet.")
        return

    logging.info(f"Processing {min_length} rows with mandatory data")

    for index in range(min_length):
        product_type = str(product_types[index][0]).strip() if product_types[index] else ""
        brand = str(brands[index][0]).strip() if brands[index] else ""
        style_number = str(style_numbers[index][0]).strip() if style_numbers[index] else ""
        add_info = str(additional_info[index][0]).strip() if index < len(additional_info) and additional_info[index] else ""
        size = get_size_info(size_info[index]) if index < len(size_info) and size_info[index] else ""
        internal_reference = str(internal_references[index][0]).strip() if internal_references[index] else ""

        description = generate_ebay_description(brand, product_type, style_number, add_info)
        if description:
            write_description_to_sheet(service, product_type, index + 2, internal_reference, description)
        else:
            logging.warning(f"Failed to generate description for row {index + 2}.")

if __name__ == '__main__':
    main()
