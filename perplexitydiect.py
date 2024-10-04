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
        return None
    
    product_type = product_type.lower().replace(" ", "_")
    template_file = f'templates/{product_type}_template.json'
    abs_template_file = os.path.abspath(template_file)
    logging.info(f"Attempting to open template file: {abs_template_file}")
    
    if not os.path.exists(abs_template_file):
        logging.error(f"Template file does not exist: {abs_template_file}")
        return None
    
    try:
        with open(abs_template_file, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {abs_template_file}")
        return None

def generate_prompt(template, brand, product_type, style_number):
    prompt = f"Brand: {brand}\nProduct Type: {product_type}\nStyle Number: {style_number}\n\n"
    prompt += json.dumps(template, indent=2)
    return prompt

def call_perplexity_api(prompt):
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'llama-3.1-sonar-large-128k-online',
        'messages': [
            {'role': 'system', 'content': 'You are an eBay fashion product listing expert.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500,
        'temperature': 0.7
    }
    response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

def parse_api_response(response, template):
    parsed_data = {}
    current_field = None
    for line in response.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key in template['mandatory_fields'] or key in template['optional_fields']:
                current_field = key
                parsed_data[current_field] = value
        elif current_field and line.strip():
            parsed_data[current_field] += ' ' + line.strip()
    return parsed_data

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

def process_product(product, index):
    if len(product) < 3:
        logging.warning(f"Skipping row {index} due to insufficient data: {product}")
        return None

    product_type, brand, style_number = product
    logging.info(f"Processing: Product type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")

    if not product_type:
        logging.warning(f"Skipping row {index} due to empty product type")
        return None

    sheet_name = get_sheet_name(product_type)
    if sheet_name == "unknown":
        logging.warning(f"Unknown product type: {product_type}")
        return None

    template = get_template(product_type)
    if not template:
        logging.warning(f"Skipping row {index} due to missing template for product type: {product_type}")
        return None

    prompt = generate_prompt(template, brand, product_type, style_number)

    try:
        api_response = call_perplexity_api(prompt)
        logging.info("Successfully called Perplexity API")
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        return None

    parsed_data = parse_api_response(api_response, template)

    output_data = []
    for field in template['mandatory_fields'] + template['optional_fields']:
        output_data.append(parsed_data.get(field, 'N/A'))

    return sheet_name, output_data

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # 读取产品信息
    products = read_spreadsheet('Sheet1!A2:C')
    logging.info(f"Read {len(products)} products from spreadsheet")
    
    # 用于存储每个sheet的数据
    sheet_data = {}
    
    for index, product in enumerate(products, start=2):
        result = process_product(product, index)
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
