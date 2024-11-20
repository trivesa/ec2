# verify_listings.py
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
GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
SOURCE_SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')  # 原始表格
VERIFICATION_SPREADSHEET_ID = '1rJvO5QpRChKFS3NrhQgforpPKCx3OhVGeaV72nUdGLw'  # 验证表格

def verify_objective_fields(listing_data):
    """验证客观字段（颜色、材质等）"""
    objective_checks = {
        'Color': {
            'is_valid': bool(listing_data.get('Color')),
            'message': 'Color is missing' if not listing_data.get('Color') else 'Valid'
        },
        'Style': {
            'is_valid': bool(listing_data.get('Style')),
            'message': 'Style is missing' if not listing_data.get('Style') else 'Valid'
        },
        'Type': {
            'is_valid': bool(listing_data.get('Type')),
            'message': 'Type is missing' if not listing_data.get('Type') else 'Valid'
        },
        'Upper Material': {
            'is_valid': bool(listing_data.get('Upper Material')),
            'message': 'Material is missing' if not listing_data.get('Upper Material') else 'Valid'
        }
    }
    return objective_checks

def verify_title_and_description(brand, style_number, listing_data):
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
            "appropriate_length": boolean,
            "keyword_optimization": boolean
        }},
        "description_check": {{
            "is_valid": boolean,
            "issues": [list of issues],
            "completeness": boolean,
            "accuracy": boolean,
            "formatting": boolean
        }}
    }}

    Check for:
    1. Title (80 characters max):
       - Brand name accuracy
       - Key features included
       - No style number included
       - SEO optimization

    2. Description:
       - Product details accuracy
       - Complete specifications
       - Proper formatting
       - Required policies included
    """

    try:
        response = call_perplexity_api(verification_prompt)
        return json.loads(response)
    except Exception as e:
        logging.error(f"Title/Description verification error: {str(e)}")
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
        ],
        'max_tokens': 1000,
        'temperature': 0.1
    }

    response = requests.post(
        'https://api.perplexity.ai/chat/completions',
        headers=headers,
        json=data
    )
    return response.json()['choices'][0]['message']['content']

def get_listing_data(sheets_service, product_type):
    """从原始表格获取listing数据"""
    try:
        sheet_name = product_type.lower().strip()
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SOURCE_SPREADSHEET_ID,
            range=f"'{sheet_name}'!A:Z"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None
            
        headers = values[0]
        required_fields = ['Title', 'Description', 'Color', 'Style', 'Type', 'Upper Material']
        indices = {field: headers.index(field) if field in headers else -1 for field in required_fields}
        
        if len(values) > 1:
            latest_row = values[-1]
            return {
                field: latest_row[index] if index >= 0 and index < len(latest_row) else 'N/A'
                for field, index in indices.items()
            }
            
        return None
    except Exception as e:
        logging.error(f"Error getting listing data: {str(e)}")
        return None

def write_verification_results(sheets_service, results):
    """写入验证结果到验证表格"""
    try:
        # 写入表头
        headers = [
            ['Internal Reference', 'Brand', 'Style Number', 'Product Type', 
             'Overall Status', 'Title Check', 'Description Check', 
             'Objective Fields Check', 'Issues Found', 'Suggestions']
        ]
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=VERIFICATION_SPREADSHEET_ID,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body={'values': headers}
        ).execute()

        # 写入验证结果
        sheets_service.spreadsheets().values().update(
            spreadsheetId=VERIFICATION_SPREADSHEET_ID,
            range='Sheet1!A2',
            valueInputOption='RAW',
            body={'values': results}
        ).execute()

    except Exception as e:
        logging.error(f"Error writing verification results: {str(e)}")

def main():
    try:
        # 设置 Google Sheets 服务
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        sheets_service = build('sheets', 'v4', credentials=credentials)

        # 读取源数据
        source_data = sheets_service.spreadsheets().values().get(
            spreadsheetId=SOURCE_SPREADSHEET_ID,
            range='Sheet1!C2:I'  # 调整范围以匹配您的数据
        ).execute().get('values', [])

        verification_results = []
        for row in source_data:
            if len(row) >= 5:
                internal_ref = row[0]
                brand = row[3]  # 根据实际列调整
                style_number = row[6]  # 根据实际列调整
                product_type = row[2]  # 根据实际列调整

                # 获取listing数据
                listing_data = get_listing_data(sheets_service, product_type)
                
                if listing_data:
                    # 验证客观字段
                    objective_checks = verify_objective_fields(listing_data)
                    
                    # 验证标题和描述
                    content_verification = verify_title_and_description(brand, style_number, listing_data)
                    
                    # 汇总验证结果
                    overall_status = "Pass" if (
                        all(check['is_valid'] for check in objective_checks.values()) and
                        content_verification['title_check']['is_valid'] and
                        content_verification['description_check']['is_valid']
                    ) else "Fail"

                    # 准备结果行
                    result_row = [
                        internal_ref,
                        brand,
                        style_number,
                        product_type,
                        overall_status,
                        json.dumps(content_verification['title_check']),
                        json.dumps(content_verification['description_check']),
                        json.dumps(objective_checks),
                        json.dumps(content_verification['title_check'].get('issues', []) + 
                                 content_verification['description_check'].get('issues', [])),
                        json.dumps(content_verification.get('suggestions', []))
                    ]
                    
                    verification_results.append(result_row)
                    
                    # 避免超过API限制
                    time.sleep(1)

        # 写入验证结果
        if verification_results:
            write_verification_results(sheets_service, verification_results)
            logging.info(f"Successfully verified {len(verification_results)} listings")

    except Exception as e:
        logging.error(f"Main process error: {str(e)}")

if __name__ == '__main__':
    main()
