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
    return build('sheets', 'v4', credentials=credentials)

def read_spreadsheet(service, range_name):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    if not values:
        logging.warning("No data found in spreadsheet")
    return values

def call_perplexity_api(prompt, temperature=0.5):
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
    try:
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
    Generate an eBay product description in HTML format for a {brand} {product_type} with style number {style_number}.
    Additional Information: {additional_info}
    Find the most important or unique feature of this product on the internet and use it to write an appealing description.
    
    Requirements:
    - Use HTML tags for formatting
    - Include a catchy title and subtitle
    - Provide a detailed description focusing on the unique feature
    - Use bullet points for key features
    - End with a call to action
    """
    return call_perplexity_api(prompt)

def write_description_to_sheet(service, sheet_name, row_index, description):
    try:
        # 写入描述到工作表的"Description"列
        range_name = f"'{sheet_name}'!D{row_index}"  # 假设"D"列是描述列
        body = {
            'values': [[description]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        logging.info(f"Description written to sheet '{sheet_name}' at row {row_index}.")
    except Exception as e:
        logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

def main():
    service = get_sheets_service()
    product_data = read_spreadsheet(service, 'Sheet1!E2:H')  # 假设E列是品牌，F列是产品类型，G列是样式编号，H列是附加信息

    for index, row in enumerate(product_data, start=2):
        if len(row) < 4:
            continue
        brand, product_type, style_number, additional_info = row[0], row[1], row[2], row[3]
        description = generate_ebay_description(brand, product_type, style_number, additional_info)
        if description:
            write_description_to_sheet(service, product_type, index, description)

if __name__ == '__main__':
    main()
