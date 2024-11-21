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

# API 配置
API_MODEL = "llama-3.1-sonar-huge-128k-online"
API_RATE_LIMIT = 50  # 每分钟请求数
API_DELAY = 60.0 / API_RATE_LIMIT  # 每次请求的延迟时间

def call_perplexity_api(prompt):
    """调用 Perplexity API"""
    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": API_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a luxury fashion expert. Always respond with a valid JSON object containing your analysis."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "top_p": 0.9
    }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        logging.info(f"Calling Perplexity API with model: {API_MODEL}")
        response = requests.post(url, json=payload, headers=headers)
        
        logging.info(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            # 获取实际的消息内容
            content = response_json['choices'][0]['message']['content']
            logging.info(f"API Response Content: {content[:200]}...")
            
            # 尝试解析内容为 JSON
            try:
                # 清理内容
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                # 解析 JSON
                result = json.loads(content)
                logging.info(f"Successfully parsed JSON response: {str(result)[:200]}...")
                return result
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse content as JSON: {str(e)}")
                logging.error(f"Content was: {content[:200]}...")
                return {
                    "title_check": {
                        "is_valid": False,
                        "issues": ["API response not in valid JSON format"],
                        "contains_brand": False,
                        "appropriate_length": False,
                        "keyword_optimization": False
                    },
                    "description_check": {
                        "is_valid": False,
                        "issues": ["API response not in valid JSON format"],
                        "completeness": False,
                        "accuracy": False,
                        "formatting": False
                    },
                    "is_valid": False,
                    "suggestions": ["API response format error"]
                }
        else:
            logging.error(f"API request failed: {response.text}")
            raise Exception(f"API request failed: {response.text}")
            
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        raise

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
        
        values = result.get('values', [])
        if not values:
            logging.info("No data found in sheet")
            return None
            
        logging.info(f"Found {len(values)} rows of data")
        return values
        
    except Exception as e:
        logging.error(f"Error reading sheet: {str(e)}")
        return None

def write_verification_results(results):
    """写入验证结果到新的工作表"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # 准备表头
        headers = [
            ['Timestamp', 'Internal Reference', 'Brand', 'Style Number', 
             'Title Check', 'Description Check', 'Issues Found', 'Overall Status']
        ]
        
        # 准备数据行
        data_rows = []
        for result in results:
            row = [
                time.strftime('%Y-%m-%d %H:%M:%S'),
                result.get('internal_ref', ''),
                result.get('brand', ''),
                result.get('style_number', ''),
                json.dumps(result.get('verification', {}).get('title_check', {})),
                json.dumps(result.get('verification', {}).get('description_check', {})),
                json.dumps(result.get('issues', [])),
                'Pass' if result.get('verification', {}).get('is_valid', False) else 'Fail'
            ]
            data_rows.append(row)
        
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
        
        logging.info(f"Successfully wrote {len(data_rows)} verification results")
        
    except Exception as e:
        logging.error(f"Error writing verification results: {str(e)}")

def verify_listing(brand, style_number, listing_data):
    """验证商品列表"""
    verification_prompt = f"""
    As a luxury fashion expert, verify this eBay listing:

    Brand: {brand}
    Style Number: {style_number}

    Title: {listing_data.get('Title', 'N/A')}
    Description: {listing_data.get('Description', 'N/A')}

    Please verify and respond in strict JSON format:
    {{
        "title_check": {{
            "is_valid": boolean,
            "issues": [list of specific issues found],
            "contains_brand": boolean,
            "appropriate_length": boolean,
            "keyword_optimization": boolean
        }},
        "description_check": {{
            "is_valid": boolean,
            "issues": [list of specific issues found],
            "completeness": boolean,
            "accuracy": boolean,
            "formatting": boolean
        }},
        "is_valid": boolean,
        "suggestions": [list of improvement suggestions]
    }}

    Focus on:
    1. Title verification:
       - Brand name accuracy
       - Key features included
       - No style number included
       - SEO optimization
       - Character limit (80 max)

    2. Description verification:
       - Product details accuracy
       - Complete specifications
       - Proper formatting
       - Required policies included
    """

    try:
        # 添加 API 速率限制延迟
        time.sleep(API_DELAY)
        
        response = call_perplexity_api(verification_prompt)
        verification_result = json.loads(response)
        
        logging.info(f"Verification completed for {brand} {style_number}")
        return verification_result
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON response: {str(e)}")
        return {
            "title_check": {"is_valid": False, "issues": ["Invalid API response format"]},
            "description_check": {"is_valid": False, "issues": ["Invalid API response format"]},
            "is_valid": False,
            "suggestions": ["API response format error"]
        }
    except Exception as e:
        logging.error(f"Verification error: {str(e)}")
        return None

def main():
    try:
        logging.info("Starting verification process...")
        
        # 获取 Sheet 数据
        data = get_sheet_data()
        if not data or len(data) < 2:  # 确保至少有表头和一行数据
            logging.error("No data found or insufficient data")
            return
        
        headers = data[0]
        required_columns = ['internal reference', 'brand', 'style number', 'Title', 'Description']
        
        # 获取列索引
        column_indices = {}
        for col in required_columns:
            try:
                column_indices[col] = headers.index(col)
            except ValueError:
                logging.error(f"Required column '{col}' not found in headers: {headers}")
                return
        
        logging.info(f"Found all required columns: {column_indices}")
        
        verification_results = []
        
        # 处理每一行数据
        for row_num, row in enumerate(data[1:], start=2):  # 从第二行开始，跳过表头
            if len(row) <= max(column_indices.values()):
                logging.warning(f"Row {row_num} is incomplete, skipping...")
                continue
                
            try:
                listing_data = {
                    'Title': row[column_indices['Title']],
                    'Description': row[column_indices['Description']]
                }
                
                brand = row[column_indices['brand']]
                style_number = row[column_indices['style number']]
                
                logging.info(f"Processing row {row_num}: {brand} - {style_number}")
                
                # 验证列表
                verification = verify_listing(brand, style_number, listing_data)
                
                if verification:
                    result = {
                        'internal_ref': row[column_indices['internal reference']],
                        'brand': brand,
                        'style_number': style_number,
                        'verification': verification,
                        'issues': (
                            verification.get('title_check', {}).get('issues', []) +
                            verification.get('description_check', {}).get('issues', [])
                        )
                    }
                    verification_results.append(result)
                    logging.info(f"Verification completed for row {row_num}")
                
            except Exception as e:
                logging.error(f"Error processing row {row_num}: {str(e)}")
                continue
        
        # 写入验证结果
        if verification_results:
            write_verification_results(verification_results)
            logging.info(f"Successfully verified {len(verification_results)} listings")
        else:
            logging.warning("No verification results to write")
        
    except Exception as e:
        logging.error(f"Main process error: {str(e)}")

if __name__ == '__main__':
    main()
    
