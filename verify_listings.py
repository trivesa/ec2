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
API_RATE_LIMIT = 50
API_DELAY = 60.0 / API_RATE_LIMIT

def call_perplexity_api(prompt):
    """调用 Perplexity API"""
    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": API_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a luxury fashion expert specialized in verifying product information accuracy. Always respond with a valid JSON object containing your analysis."
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
        
        if response.status_code == 200:
            response_json = response.json()
            content = response_json['choices'][0]['message']['content']
            
            # 清理和解析JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            return result
            
        else:
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
        
        # 读取所有需要的列
        range_name = 'Sheet1!A:N'
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
        
        # 更新表头以反映新的验证结构
        headers = [
            ['Timestamp', 'Internal Reference', 'Brand', 'Style Number', 
             'Title Accuracy', 'Description Accuracy', 
             'Color Verification', 'Style Verification', 'Type Verification',
             'Material Verification', 'Heel Height Verification', 
             'Country Verification', 'Issues Found', 'Status']
        ]
        
        # 准备数据行
        data_rows = []
        for result in results:
            verification = result.get('verification', {})
            content_check = verification.get('content_check', {})
            attribute_check = verification.get('attribute_check', {})
            
            row = [
                time.strftime('%Y-%m-%d %H:%M:%S'),
                result.get('internal_ref', ''),
                result.get('brand', ''),
                result.get('style_number', ''),
                json.dumps(content_check.get('title', {})),
                json.dumps(content_check.get('description', {})),
                json.dumps(attribute_check.get('color', {})),
                json.dumps(attribute_check.get('style', {})),
                json.dumps(attribute_check.get('type', {})),
                json.dumps(attribute_check.get('upper_material', {})),
                json.dumps(attribute_check.get('heel_height', {})),
                json.dumps(attribute_check.get('country_of_manufacture', {})),
                json.dumps(result.get('issues', [])),
                'Pass' if all([
                    content_check.get('title', {}).get('is_accurate', False),
                    content_check.get('description', {}).get('is_accurate', False),
                    all(attr.get('is_correct', False) for attr in attribute_check.values())
                ]) else 'Fail'
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
    As a luxury fashion expert, verify this eBay listing data.
    
    Given correct data (DO NOT VERIFY THESE):
    Brand: {brand}
    Style Number: {style_number}
    Product Category: {listing_data.get('product_category', 'N/A')}
    Condition: {listing_data.get('condition', 'N/A')}

    Please verify these AI generated content for factual accuracy only:
    Title: {listing_data.get('Title', 'N/A')}
    Description: {listing_data.get('Description', 'N/A')}

    Please verify these specific attributes:
    Color: {listing_data.get('Color', 'N/A')}
    Style: {listing_data.get('Style', 'N/A')}
    Type: {listing_data.get('Type', 'N/A')}
    Upper Material: {listing_data.get('Upper Material', 'N/A')}
    Heel Height: {listing_data.get('Heel Height', 'N/A')}
    Country of Manufacture: {listing_data.get('Country of Manufacture', 'N/A')}

    Please verify and respond in strict JSON format:
    {{
        "content_check": {{
            "title": {{
                "is_accurate": boolean,
                "issues": [list of factual errors only]
            }},
            "description": {{
                "is_accurate": boolean,
                "issues": [list of factual errors only]
            }}
        }},
        "attribute_check": {{
            "color": {{
                "is_correct": boolean,
                "correct_value": "string"
            }},
            "style": {{
                "is_correct": boolean,
                "correct_value": "string"
            }},
            "type": {{
                "is_correct": boolean,
                "correct_value": "string"
            }},
            "upper_material": {{
                "is_correct": boolean,
                "correct_value": "string"
            }},
            "heel_height": {{
                "is_correct": boolean,
                "correct_value": "string"
            }},
            "country_of_manufacture": {{
                "is_correct": boolean,
                "correct_value": "string"
            }}
        }}
    }}

    Focus only on factual accuracy. Do not check formatting, SEO, or listing optimization.
    For attributes, provide the correct value if the current value is wrong.
    """

    try:
        # API 速率限制
        time.sleep(API_DELAY)
        
        # 调用 API
        response = call_perplexity_api(verification_prompt)
        
        # 验证响应格式
        if not isinstance(response, dict):
            raise ValueError("Invalid API response format")
        
        required_keys = ['content_check', 'attribute_check']
        if not all(key in response for key in required_keys):
            raise ValueError("Missing required fields in API response")
        
        logging.info(f"Verification completed for {brand} {style_number}")
        return response
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON response: {str(e)}")
        return create_error_response("Invalid JSON format in API response")
    except Exception as e:
        logging.error(f"Verification error: {str(e)}")
        return create_error_response(str(e))

def create_error_response(error_message):
    """创建错误响应的标准格式"""
    return {
        "content_check": {
            "title": {
                "is_accurate": False,
                "issues": [error_message]
            },
            "description": {
                "is_accurate": False,
                "issues": [error_message]
            }
        },
        "attribute_check": {
            "color": {"is_correct": False, "correct_value": "Unknown"},
            "style": {"is_correct": False, "correct_value": "Unknown"},
            "type": {"is_correct": False, "correct_value": "Unknown"},
            "upper_material": {"is_correct": False, "correct_value": "Unknown"},
            "heel_height": {"is_correct": False, "correct_value": "Unknown"},
            "country_of_manufacture": {"is_correct": False, "correct_value": "Unknown"}
        }
    }

def main():
    try:
        logging.info("Starting verification process...")
        
        # 获取 Sheet 数据
        data = get_sheet_data()
        if not data or len(data) < 2:
            logging.error("No data found or insufficient data")
            return
        
        headers = data[0]
        
        # 定义已知正确的列和需要验证的列
        known_correct_columns = [
            'internal reference', 
            'product category', 
            'brand', 
            'additional information',
            'condition', 
            'style number'
        ]
        
        verify_columns = [
            'Title', 
            'Description', 
            'Color', 
            'Style', 
            'Type', 
            'Upper Material', 
            'Heel Height', 
            'Country of Manufacture'
        ]
        
        # 获取列索引
        column_indices = {}
        for col in known_correct_columns + verify_columns:
            try:
                column_indices[col] = headers.index(col)
            except ValueError:
                logging.error(f"Column '{col}' not found in headers: {headers}")
                return
        
        logging.info(f"Found all required columns: {column_indices}")
        
        verification_results = []
        batch_size = 10  # 设置批处理大小
        
        # 批量处理数据
        for batch_start in range(1, len(data), batch_size):
            batch_end = min(batch_start + batch_size, len(data))
            batch = data[batch_start:batch_end]
            batch_results = []
            
            for row in batch:
                try:
                    if len(row) <= max(column_indices.values()):
                        logging.warning(f"Row {batch_start + len(batch_results)} is incomplete, skipping...")
                        continue
                    
                    # 收集已知正确的数据
                    known_data = {
                        'product_category': row[column_indices['product category']],
                        'additional_information': row[column_indices['additional information']],
                        'condition': row[column_indices['condition']]
                    }
                    
                    # 收集需要验证的数据
                    verify_data = {
                        col: row[column_indices[col]]
                        for col in verify_columns
                        if column_indices[col] < len(row)
                    }
                    
                    # 合并数据
                    listing_data = {**known_data, **verify_data}
                    
                    brand = row[column_indices['brand']]
                    style_number = row[column_indices['style number']]
                    
                    logging.info(f"Processing: {brand} - {style_number}")
                    
                    # 验证列表
                    verification = verify_listing(brand, style_number, listing_data)
                    
                    if verification:
                        # 收集内容验证问题
                        content_issues = []
                        for check_type, check_data in verification['content_check'].items():
                            if not check_data['is_accurate']:
                                content_issues.extend(check_data['issues'])
                        
                        # 收集属性验证问题
                        attribute_issues = []
                        for attr, check_data in verification['attribute_check'].items():
                            if not check_data['is_correct']:
                                attribute_issues.append(
                                    f"{attr}: Current '{verify_data.get(attr, 'N/A')}' "
                                    f"should be '{check_data['correct_value']}'"
                                )
                        
                        result = {
                            'internal_ref': row[column_indices['internal reference']],
                            'brand': brand,
                            'style_number': style_number,
                            'verification': verification,
                            'content_issues': content_issues,
                            'attribute_issues': attribute_issues,
                            'all_issues': content_issues + attribute_issues
                        }
                        batch_results.append(result)
                        
                except Exception as e:
                    logging.error(f"Error processing row {batch_start + len(batch_results)}: {str(e)}")
                    continue
            
            # 将批次结果添加到总结果
            verification_results.extend(batch_results)
            
            # 每处理完一个批次就写入结果
            if batch_results:
                write_verification_results(batch_results)
                logging.info(f"Wrote batch results: {len(batch_results)} items")
        
        logging.info(f"Verification complete. Total processed: {len(verification_results)} listings")
        
    except Exception as e:
        logging.error(f"Main process error: {str(e)}")
        raise

if __name__ == '__main__':
    main()
