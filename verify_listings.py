import json
import os
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 配置
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GOOGLE_CREDENTIALS_PATH = "/home/ec2-user/google-credentials/service-account.json"
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
SPREADSHEET_ID = "1rJvO5QpRChKFS3NrhQgforpPKCx3OhVGeaV72nUdGLw"

def verify_listing(brand, style_number, listing_data):
    """使用 Perplexity API 验证标题和描述"""
    verification_prompt = f"""
    As a luxury fashion expert, verify this eBay listing:

    Brand: {brand}
    Style Number: {style_number}

    Title: {listing_data.get('Title', 'N/A')}
    Description: {listing_data.get('Description', 'N/A')}

    Please verify and respond in JSON format:
    {{
        "title_check": {{
            "is_valid": boolean,
            "issues": [list of issues],
            "contains_brand": boolean,
            "appropriate_length": boolean
        }},
        "description_check": {{
            "is_valid": boolean,
            "issues": [list of issues],
            "completeness": boolean,
            "accuracy": boolean
        }}
    }}
    """

    try:
        response = call_perplexity_api(verification_prompt)
        return json.loads(response)
    except Exception as e:
        logging.error(f"Verification error: {str(e)}")
        return None

def call_perplexity_api(prompt):
    """调用 Perplexity API"""
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'llama-3.1-sonar-huge-128k-online',
        'messages': [
            {
                'role': 'system',
                'content': 'You are a luxury fashion expert specializing in product verification.'
            },
            {'role': 'user', 'content': prompt}
        ]
    }

    response = requests.post(
        'https://api.perplexity.ai/chat/completions',
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        raise Exception(f"API call failed with status {response.status_code}: {response.text}")

def get_sheet_data():
    """获取 Google Sheet 数据"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 读取 Sheet1 的数据
        range_name = 'Sheet1!A:N'  # A 到 N 列包含所有需要的数据
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        return result.get('values', [])
    except Exception as e:
        logging.error(f"Error reading sheet: {str(e)}")
        return None

def write_verification_results(results):
    """写入验证结果"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # 准备表头
        headers = [
            ['Internal Reference', 'Brand', 'Style Number', 
             'Title Check', 'Description Check', 'Issues Found']
        ]
        
        # 准备数据行
        data_rows = [[
            result['internal_ref'],
            result['brand'],
            result['style_number'],
            json.dumps(result['verification']['title_check']),
            json.dumps(result['verification']['description_check']),
            json.dumps(result.get('issues', []))
        ] for result in results]
        
        # 写入数据
        body = {
            'values': headers + data_rows
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='Verification!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
    except Exception as e:
        logging.error(f"Error writing verification results: {str(e)}")

def main():
    try:
        # 读取数据
        data = get_sheet_data()
        if not data:
            logging.error("No data found in sheet")
            return
        
        headers = data[0]
        required_columns = ['internal reference', 'brand', 'style number', 'Title', 'Description']
        column_indices = {col: headers.index(col) if col in headers else -1 for col in required_columns}
        
        verification_results = []
        
        # 处理每一行
        for row in data[1:]:
            if len(row) <= max(column_indices.values()):
                continue
                
            listing_data = {
                'Title': row[column_indices['Title']],
                'Description': row[column_indices['Description']]
            }
            
            verification = verify_listing(
                row[column_indices['brand']],
                row[column_indices['style number']],
                listing_data
            )
            
            if verification:
                result = {
                    'internal_ref': row[column_indices['internal reference']],
                    'brand': row[column_indices['brand']],
                    'style_number': row[column_indices['style number']],
                    'verification': verification
                }
                verification_results.append(result)
            
            # 避免 API 限制
            time.sleep(1)
        
        # 写入验证结果
        if verification_results:
            write_verification_results(verification_results)
            logging.info(f"Successfully verified {len(verification_results)} listings")
        
    except Exception as e:
        logging.error(f"Main process error: {str(e)}")

if __name__ == '__main__':
    main()
