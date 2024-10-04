import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests

# 设置Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = '/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=credentials)

# Perplexity API设置
PERPLEXITY_API_KEY = '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'
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

def read_spreadsheet(spreadsheet_id, range_name):
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    return result.get('values', [])

def write_to_spreadsheet(spreadsheet_id, range_name, values):
    body = {'values': values}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()

def get_template(product_type):
    template_file = f'templates/{product_type.lower()}_template.json'
    with open(template_file, 'r') as file:
        return json.load(file)

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

def parse_api_response(response):
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

def main(spreadsheet_id):
    # 读取产品信息
    products = read_spreadsheet(spreadsheet_id, 'Sheet1!A2:C')  # 假设数据从A2开始

    for index, product in enumerate(products, start=2):
        product_type, brand, style_number = product

        # 获取对应的模板
        template = get_template(product_type)

        # 生成提示
        prompt = generate_prompt(template, brand, product_type, style_number)

        # 调用Perplexity API
        api_response = call_perplexity_api(prompt)

        # 解析API返回的结果
        parsed_data = parse_api_response(api_response)

        # 准备写回spreadsheet的数据
        output_data = []
        for field in template['mandatory_fields'] + template['optional_fields']:
            output_data.append(parsed_data.get(field, 'N/A'))

        # 将结果写回spreadsheet
        write_to_spreadsheet(spreadsheet_id, f'Sheet1!D{index}:{chr(ord("D")+len(output_data)-1)}{index}', [output_data])

if __name__ == '__main__':
    spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
    main(spreadsheet_id)
