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

    # 假设perplexity-huge.py中使用了类似的范围
    product_data = read_spreadsheet(service, 'Sheet1!C2:H')  # 确保范围与perplexity-huge.py一致

    for index, row in enumerate(product_data, start=2):
        if len(row) < 6:
            logging.warning(f"Skipping row {index} due to insufficient data.")
            continue
        internal_reference, brand, product_type, style_number, additional_info = row[0], row[2], row[3], row[4], row[5]
        description = generate_ebay_description(brand, product_type, style_number, additional_info)
        if description:
            write_description_to_sheet(service, product_type, index, internal_reference, description)
        else:
            logging.warning(f"Failed to generate description for row {index}.")

if __name__ == '__main__':
    main()
