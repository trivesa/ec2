import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = '/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=credentials)

# Perplexity API设置
PERPLEXITY_API_KEY = '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'
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

# Google spreadsheet ID
SPREADSHEET_ID = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'

# 通用 prompt 指令
GENERAL_INSTRUCTIONS = """
Use the provided Brand, Product Type, and Style number to search for product details and complete the eBay product listing as per the below requirements:
Create Title (Titolo), Subtitle (Sottotitolo) and Description (Descrizione).
Find the Mandatory and Optional product information listed under 'Mandatory Fields' and 'Optional Fields'.
IMPORTANT: You MUST use the EXACT field names as provided, including both English and Italian parts. Every field name should be in the format: 'English Name (Italian Name)'. Do not omit or change any part of the field names.
If any fields have no information available on the internet, or you cannot find it, use 'N/A' as the value.
Provide specific price ranges based on current market data when possible.
Include detailed size information, including available sizes and fit recommendations.
Fill in as many optional fields as possible, especially technical specifications.
Provide detailed information about materials used and manufacturing processes.
The tone should be professional and follow a minimalist style.
Ensure all field names in your response follow the 'English (Italian)' format, even if you're only able to provide information for the English part.

Instructions for the Title (Titolo):
- Brand Name: Include the brand for recognition (e.g., 'Nike').
- Product Type: Clearly state what the item is (e.g., 'Men's Running Shoes').
- Key Features: Include important features such as model name, color, or technology (e.g., 'Air Max', 'Black/White', 'Flyknit').
- Size: If possible, include the size range (e.g., 'US 8-13').
- Style Number: ALWAYS include the style number at the end of the title.

Instructions for the subtitle (Sottotitolo)
Complementary: It should add value beyond what the main title already says.
Concise: Keep it short and clear, under 55 characters.

Instructions for the Description (Descrizione):
Create a comprehensive product description that includes the following elements, but do not use these as headings in the final description:
1. Start with a brief, engaging statement that highlights the product's key features or benefits.
2. Explain what makes this product stand out from similar items.
3. Focus on the most important features (technology, materials, design) and explain how they benefit the user.
4. Provide specific details about the product's characteristics and any proprietary technologies used.
5. Offer detailed information about the fit, including size options and how the product compares to standard sizing.
6. Describe the materials used in different parts of the product and any special manufacturing processes.
7. Explain what activities or occasions the product is best suited for.
8. Provide guidance on how to clean and maintain the product.
9. Mention any warranty information and your return policy.
10. Conclude with an encouragement for the buyer to make a purchase, highlighting any limited availability or special offers.

Combine all these elements into a cohesive, flowing description without using separate headings or sections.
...
"""

def read_spreadsheet(range_name):
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    logging.info(f"Read {len(values)} rows from spreadsheet")
    if not values:
        logging.warning("No data found in spreadsheet")
    return values

def write_to_spreadsheet(range_name, values):
    body = {'values': values}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    logging.info(f"Written {len(values)} rows to spreadsheet")

def get_template(product_type):
    if not product_type:
        logging.error("Product type is empty")
        return None, None
    
    product_type = product_type.lower().replace(" ", "_")
    template_file = f'templates/{product_type}_template.json'
    abs_template_file = os.path.abspath(template_file)
    logging.info(f"Attempting to open template file: {abs_template_file}")
    
    if not os.path.exists(abs_template_file):
        logging.error(f"Template file does not exist: {abs_template_file}")
        return None, None
    
    try:
        with open(abs_template_file, 'r') as file:
            return json.load(file), product_type
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {abs_template_file}")
        return None, None

def generate_prompt(template, brand, product_type, style_number):
    prompt = f"Brand: {brand}\nProduct Type: {product_type}\nStyle Number: {style_number}\n\n"
    prompt += GENERAL_INSTRUCTIONS
    prompt += "\nGenerate a detailed eBay listing based on the following template:\n\n"
    prompt += json.dumps(template, indent=2)
    return prompt

def call_perplexity_api(prompt):
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'llama-3.1-sonar-huge-128k-online',
        'messages': [
            {'role': 'system', 'content': 'You are an eBay fashion product listing expert.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 1000,
        'temperature': 0.2,
        'top_p': 0.9,
        'return_citations': True,
        'search_recency_filter': 'month',
        'frequency_penalty': 1
    }
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        content = response_json['choices'][0]['message']['content']
        logging.info(f"Raw API Response: {content}")
        return content  # 返回原始内容，而不是直接解析
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        return None
def parse_api_response(response, product_type, brand, style_number):
    logging.info(f"Parsing response")
    parsed_data = {}
    current_field = None

    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('### '):
            current_field = line.replace('### ', '').strip()
            parsed_data[current_field] = ''
        elif current_field and line:
            parsed_data[current_field] += line + ' '

    # 清理数据
    for key, value in parsed_data.items():
        parsed_data[key] = value.strip()

    # 清理描述中的子标题
    if 'Description (Descrizione)' in parsed_data:
        description_lines = parsed_data['Description (Descrizione)'].split('\n')
        cleaned_description = []
        for line in description_lines:
            if not any(subtitle in line.lower() for subtitle in ['catchy introduction:', 'unique selling point:', 'key features and benefits:', 'product specifications:', 'fit and sizing:', 'materials and construction:', 'performance and usage:', 'care instructions:', 'warranty and returns:', 'call to action:']):
                cleaned_description.append(line)
        parsed_data['Description (Descrizione)'] = ' '.join(cleaned_description).strip()

    logging.info(f"Parsed data: {json.dumps(parsed_data, indent=2)}")

    # 验证必填字段
    required_fields = ['Title (Titolo)', 'Subtitle (Sottotitolo)', 'Description (Descrizione)']
    for field in required_fields:
        if field not in parsed_data or not parsed_data[field]:
            logging.warning(f"Missing required field: {field}")
            return None

    # 添加关键词验证
    keywords = [product_type.lower(), brand.lower(), style_number.lower()]
    title = parsed_data.get('Title (Titolo)', '').lower()
    description = parsed_data.get('Description (Descrizione)', '').lower()

    if not all(keyword in title or keyword in description for keyword in keywords):
        logging.warning(f"Generated content may not match the product. Missing keywords: {product_type}, {brand}, or {style_number}")
        return None

    return parsed_data

def validate_product_type(parsed_data, expected_type):
    generated_type = parsed_data.get('Object Category (Categoria Oggetto)', '').lower()
    if expected_type.lower() not in generated_type:
        logging.warning(f"Generated product type '{generated_type}' does not match expected type '{expected_type}'")
        return False
    return True

def get_sheet_name(product_type):
    product_type = product_type.lower().strip()
    sheet_mapping = {
        "shoes": "shoes",
        "bag": "bag",
        "clothing": "clothing",
        "scarf": "scarf",
        "belt": "belt",
        "watch": "watch",
        "other accessories": "other accessories"
    }
    return sheet_mapping.get(product_type, "unknown")

def process_product(product_type, brand, style_number, index, max_retries=2):
    logging.info(f"Processing: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")

    if not product_type:
        logging.warning(f"Skipping row {index} due to empty product type")
        return None

    sheet_name = get_sheet_name(product_type)
    if sheet_name == "unknown":
        logging.warning(f"Unknown product type: {product_type}")
        return None

    template, validated_product_type = get_template(product_type)
    if not template:
        logging.warning(f"Skipping row {index} due to missing template for product type: {product_type}")
        return None

    for attempt in range(max_retries):
        prompt = generate_prompt(template, brand, validated_product_type, style_number)
        raw_response = call_perplexity_api(prompt)
        
        if raw_response:
            logging.info(f"Raw API Response received for {validated_product_type} - {brand} - {style_number}")
            parsed_data = parse_api_response(raw_response, product_type, brand, style_number)
            if parsed_data:
                if validate_product_type(parsed_data, product_type):
                    logging.info(f"Parsed data for {validated_product_type} - {brand} - {style_number}:\n{json.dumps(parsed_data, indent=2)}")

                    output_data = []
                    for field in template['mandatory_fields'] + template['optional_fields']:
                        output_data.append(parsed_data.get(field, 'N/A'))

                    return sheet_name, output_data
                else:
                    logging.warning(f"Product type validation failed. Generated type: {parsed_data.get('Object Category (Categoria Oggetto)', 'N/A')}, Expected type: {product_type}")
            else:
                logging.warning("Failed to parse API response")
        else:
            logging.warning("API call failed or returned empty response")
        
        logging.warning(f"Attempt {attempt + 1} failed. Retrying...")

    logging.error(f"Failed to process product after {max_retries} attempts")
    return None

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # 读取产品信息
    product_types = read_spreadsheet('Sheet1!E2:E')
    brands = read_spreadsheet('Sheet1!F2:F')
    style_numbers = read_spreadsheet('Sheet1!I2:I')
    
    logging.info(f"Read {len(product_types)} product types, {len(brands)} brands, and {len(style_numbers)} style numbers")
    
    # 找出最短的列的长度
    min_length = min(len(product_types), len(brands), len(style_numbers))
    
    if min_length == 0:
        logging.error("One or more columns are empty. Please check the spreadsheet.")
        return

    logging.info(f"Processing {min_length} rows with complete data")

    # 用于存储每个sheet的数据
    sheet_data = {}
    
    for index in range(min_length):
        # 确保每个值都是字符串，并去除首尾空白
        product_type = str(product_types[index][0]).strip() if product_types[index] else ""
        brand = str(brands[index][0]).strip() if brands[index] else ""
        style_number = str(style_numbers[index][0]).strip() if style_numbers[index] else ""
        
        if not all([product_type, brand, style_number]):
            logging.warning(f"Skipping row {index+2} due to missing data: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")
            continue
        
        result = process_product(product_type, brand, style_number, index+2)
        if result:
            sheet_name, output_data = result
            if sheet_name not in sheet_data:
                sheet_data[sheet_name] = []
            sheet_data[sheet_name].append(output_data)

    # 将数据写入相应的sheet
    for sheet_name, data in sheet_data.items():
        try:
            # 获取sheet的当前行数
            sheet_info = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=[sheet_name], includeGridData=True).execute()
            current_row = len(sheet_info['sheets'][0]['data'][0]['rowData']) + 1

            # 写入数据
            range_name = f"{sheet_name}!A{current_row}"
            write_to_spreadsheet(range_name, data)
            logging.info(f"Successfully wrote {len(data)} rows to sheet '{sheet_name}'")
        except Exception as e:
            logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

if __name__ == '__main__':
    main()
