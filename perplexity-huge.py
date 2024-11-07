import json
import os
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging
import re
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

if GOOGLE_CREDENTIALS_PATH:
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        # 创建 sheets_service
        sheets_service = build('sheets', 'v4', credentials=credentials)  
    except Exception as e:
        logging.error(f"Error loading credentials from file: {str(e)}")
        exit(1)
else:
    logging.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    exit(1)

# API Keys 设置
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not PERPLEXITY_API_KEY:
    logging.error("PERPLEXITY_API_KEY environment variable not set")
    exit(1)
if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY environment variable not set")
    exit(1)

PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

# Google spreadsheet ID
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    logging.error("SPREADSHEET_ID environment variable not set")
    exit(1)

GENERAL_INSTRUCTIONS = """
Product Listing Guidelines for Luxury Fashion Items:

1. Basic Information Format:
   - Title: [Brand] [Product Type] [Key Feature] [Color] - Size [XX]
   - Subtitle: One compelling benefit under 55 characters
   - Short Description: 2-3 clear sentences
   - Description: Clear paragraphs without bullet points

2. Field Name Requirements:
   - Use exact format without translations
   - Example: 'Material', 'Color'
   - Use 'N/A' only when information is unavailable

3. Content Guidelines:
   Materials & Construction:
   - Specify primary materials and their quality
   - Detail manufacturing techniques
   - Include care instructions

   Sizing & Fit:
   - Provide exact measurements
   - Compare with standard sizes
   - Include fit recommendations

   Technical Details:
   - List key features and technologies
   - Explain practical benefits
   - Include relevant certifications

4. Description Structure:
   First Paragraph: Product overview and key features
   Second Paragraph: Materials and construction details
   Third Paragraph: Fit and sizing information
   Fourth Paragraph: Care instructions and warranty
   Final Paragraph: Brief call to action

5. Style Requirements:
   - Use professional, minimalist language
   - Avoid marketing hyperbole
   - Focus on factual information
   - Maintain EU/UK compliance
   - Include current market pricing when available

Note: All descriptions must be accurate, verifiable, and compliant with EU consumer protection laws.
"""

class OpenAIEnhancer:
    def __init__(self):
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            max_retries=3,
            timeout=30.0
        )
        self.model = "gpt-4"  # 使用最新的GPT-4模型
        self.temperature = 0.3  # 较低的temperature以保持输出的一致性和准确性

    def enhance_product_data(self, 
                           extracted_data: Dict[str, Any], 
                           product_type: str, 
                           brand: str, 
                           style_number: str) -> Dict[str, Any]:
        """使用 OpenAI 增强品数据"""
        try:
            messages = self._prepare_messages(extracted_data, product_type, brand, style_number)
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=1500,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            return self._process_response(completion, extracted_data)
            
        except Exception as e:
            logging.error(f"Error in enhance_product_data: {str(e)}")
            return extracted_data

    def _prepare_messages(self, data: Dict[str, Any], product_type: str, 
                         brand: str, style_number: str) -> list:
        """准备 OpenAI API 消息"""
        system_prompt = """
        You are a luxury fashion expert and e-commerce content optimizer. Your tasks:
        1. Verify product information accuracy
        2. Improve title and description appeal
        3. Ensure all required fields have meaningful content
        4. Maintain professionalism while enhancing marketing appeal
        
        Rules:
        - Title must include brand, product type, key feature, and color
        - Subtitle must highlight unique selling point
        - Description must be professional, accurate, and engaging
        - All technical specifications must be accurate
        - Keep original data structure and field names
        - Return response in valid JSON format
        - Maintain factual accuracy while making minimal creative improvements
        - Focus on clarity and precision in technical specifications
        """
        
        user_prompt = f"""
        Please review and enhance the following {brand} {product_type} product information:
        
        Current data:
        {json.dumps(data, indent=2)}
        
        Requirements:
        1. Verify accuracy of each field
        2. Improve title appeal (keep within 80 characters) while maintaining key product information
        3. Optimize subtitle (keep within 55 characters) to highlight main selling point
        4. Enhance description's professionalism and appeal while keeping all technical details accurate
        5. Ensure all technical specification fields have accurate information
        6. Focus on factual improvements rather than creative embellishments
        
        Return the enhanced data in the same JSON format.
        """
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _process_response(self, completion: Any, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理 OpenAI API 响应"""
        try:
            if hasattr(completion, 'usage'):
                logging.info(f"""
                    OpenAI API usage:
                    - Prompt tokens: {completion.usage.prompt_tokens}
                    - Completion tokens: {completion.usage.completion_tokens}
                    - Total tokens: {completion.usage.total_tokens}
                """)
            
            content = completion.choices[0].message.content
            
            try:
                enhanced_data = json.loads(content)
                
                if self._validate_enhanced_data(enhanced_data, original_data):
                    logging.info("Successfully enhanced data with OpenAI")
                    return enhanced_data
                else:
                    logging.warning("Validation failed, using original data")
                    return original_data
                    
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse OpenAI response as JSON: {e}")
                return original_data
                
        except Exception as e:
            logging.error(f"Error processing OpenAI response: {str(e)}")
            return original_data

    def _validate_enhanced_data(self, enhanced_data: Dict[str, Any], 
                              original_data: Dict[str, Any]) -> bool:
        """验证增强的数据"""
        try:
            required_fields = set(original_data.keys())
            if not all(field in enhanced_data for field in required_fields):
                logging.warning("Missing required fields in enhanced data")
                return False
            
            if len(enhanced_data.get('Title', '')) > 80:
                logging.warning("Title too long")
                return False
                
            if len(enhanced_data.get('Subtitle', '')) > 55:
                logging.warning("Subtitle too long")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating enhanced data: {str(e)}")
            return False

def read_spreadsheet(range_name):
    """从 Google Sheets 读取数据"""
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        return result.get('values', [])
    except Exception as e:
        logging.error(f"Error reading spreadsheet range {range_name}: {str(e)}")
        return []

def get_size_info(size_row):
    """处理尺寸信息"""
    if not size_row:
        return ""
    size_info = []
    for size in size_row:
        if size and str(size).strip():
            size_info.append(str(size).strip())
    return ", ".join(size_info) if size_info else ""

def get_template(product_type):
    """获取产品类型的模板"""
    product_type = product_type.lower()
    
    if product_type == 'shoes':
        template = {
            'mandatory_fields': [
                'Title', 'Subtitle', 'Short Description', 'Description',
                'Brand', 'Style', 'Color', 'Material', 'Condition',
                'Heel Height', 'Shoe Size', 'Country/Region of Manufacture'
            ],
            'optional_fields': [
                'Pattern', 'Features', 'Occasion', 'Season',
                'Style Code', 'Width', 'US Shoe Size', 'EUR Shoe Size',
                'UK Shoe Size', 'Heel Type', 'Sole Material'
            ]
        }
        sheet_name = 'Shoes'
    else:
        template = {
            'mandatory_fields': [
                'Title', 'Subtitle', 'Short Description', 'Description',
                'Brand', 'Style', 'Color', 'Material', 'Condition',
                'Size', 'Country/Region of Manufacture'
            ],
            'optional_fields': [
                'Pattern', 'Features', 'Occasion', 'Season',
                'Style Code', 'Department', 'Theme'
            ]
        }
        sheet_name = 'Other'
    
    return template, sheet_name

def validate_fields(data, product_type):
    """验证字段"""
    template, _ = get_template(product_type)
    missing_fields = []
    
    for field in template['mandatory_fields']:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        logging.warning(f"Missing mandatory fields: {', '.join(missing_fields)}")
        return False
    
    return True

def validate_shoe_fields(data):
    """验证鞋类特定字段"""
    errors = []
    
    # 验证鞋码
    if 'Shoe Size' in data:
        shoe_size = str(data['Shoe Size'])
        if not re.match(r'^\d+(\.\d+)?$', shoe_size):
            errors.append(f"Invalid shoe size format: {shoe_size}")
    
    # 验证跟高
    if 'Heel Height' in data:
        heel_height = str(data['Heel Height'])
        if not re.match(r'^\d+(\.\d+)?\s*(cm|in|mm)$', heel_height):
            errors.append(f"Invalid heel height format: {heel_height}")
    
    return errors

def generate_prompt(template, brand, product_type, style_number, additional_info, size_info):
    """生成API提示"""
    if product_type.lower() == 'shoes':
        prompt = f"""
        Please provide detailed information about these {brand} shoes.
        Style Number: {style_number}
        Additional Information: {additional_info}
        Available Sizes: {size_info}

        Required Fields:
        - Title: Create a clear title under 80 characters including brand, type, and key features
        - Subtitle: Create a compelling subtitle under 55 characters
        - Short Description: 2-3 sentences summarizing key features
        - Description: Detailed, professional description including:
          * Design and style details
          * Materials and construction
          * Comfort features
          * Sizing and fit information
          * Care instructions
        
        Technical Specifications:
        - Brand: {brand}
        - Style Number: {style_number}
        - Available Sizes: {size_info}
        - Include all available information about:
          * Color
          * Material
          * Heel Height
          * Sole Material
          * Country of Manufacture
          * Width (if applicable)
          * Pattern (if applicable)
          * Season (if applicable)
        
        Additional Notes:
        {additional_info}

        Please format the response as a structured JSON object with all the fields.
        """
    else:
        prompt = f"""
        Please generate a detailed product listing for this {brand} {product_type}.
        Style Number: {style_number}
        Additional Information: {additional_info}
        Size Information: {size_info}

        Required Fields:
        """
        
        for field in template['mandatory_fields']:
            prompt += f"\n- {field}"
        
        prompt += "\n\nOptional Fields (include if information is available):"
        for field in template['optional_fields']:
            prompt += f"\n- {field}"
        
        prompt += f"""

        Guidelines:
        1. Title must be under 80 characters
        2. Subtitle must be under 55 characters
        3. Include all available technical specifications
        4. Maintain professional tone
        5. Format response as JSON
        
        Additional Notes:
        {additional_info}
        """
    
    return prompt

def call_perplexity_api(prompt, temperature=0.3):
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
                'content': GENERAL_INSTRUCTIONS
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': temperature
    }
    
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
        
        if response.status_code != 200:
            logging.error(f"Perplexity API Error - Status Code: {response.status_code}")
            logging.error(f"Response Text: {response.text}")
            return None
            
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        return None

def extract_fields_from_response(response_text, template):
    """从API响应中提取字段"""
    try:
        # 尝试直接解析JSON
        try:
            data = json.loads(response_text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # 如果不是JSON，尝试从文本中提取字段
        data = {}
        current_field = None
        current_content = []
        
        # 分割响应文本为行
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新字段
            field_match = re.match(r'\*\*(.*?):\*\*\s*(.*)', line)
            if field_match:
                # 保存之前的字��（如果有）
                if current_field and current_content:
                    data[current_field] = '\n'.join(current_content).strip()
                    current_content = []
                
                # 置新字段
                current_field = field_match.group(1).strip()
                content = field_match.group(2).strip()
                if content:
                    current_content.append(content)
            elif current_field:
                current_content.append(line)
        
        # 保存最后一个字段
        if current_field and current_content:
            data[current_field] = '\n'.join(current_content).strip()
        
        # 验证必需字段
        for field in template['mandatory_fields']:
            if field not in data:
                logging.warning(f"Missing mandatory field in response: {field}")
                return None
        
        return data
        
    except Exception as e:
        logging.error(f"Error extracting fields from response: {str(e)}")
        return None

def ensure_sheet_exists(sheet_name):
    """确保工作表存在"""
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', '')
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                logging.info(f"Sheet '{sheet_name}' already exists.")
                return True
        
        # 如果工作表不存在，创建它
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=request_body
        ).execute()
        logging.info(f"Sheet '{sheet_name}' has been created.")
        return True
    except Exception as e:
        logging.error(f"Error ensuring sheet '{sheet_name}' exists: {str(e)}")
        return False

def process_product(product_type, brand, style_number, additional_info, size_info, index, max_retries=2):
    """处理产品信息，包括 Perplexity API 调用"""
    logging.info(f"Processing: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}', Additional Info: '{additional_info}', Size Info: '{size_info}'")
    
    template, sheet_name = get_template(product_type)
    if not template or not sheet_name:
        logging.error(f"Failed to get template for product type: {product_type}")
        return None
    
    prompt = generate_prompt(template, brand, product_type, style_number, additional_info, size_info)
    
    for attempt in range(max_retries):
        try:
            response = call_perplexity_api(prompt)
            
            if response and 'choices' in response:
                extracted_data = extract_fields_from_response(response['choices'][0]['message']['content'], template)
                
                if extracted_data:
                    logging.info(f"Successfully processed product for {brand} {product_type}")
                    return sheet_name, extracted_data
                else:
                    logging.error("Failed to extract fields from response")
            
            elif response and response.get('error'):
                logging.error(f"API error: {response['error']}")
            
            else:
                logging.error("Invalid response format from API")
                
        except Exception as e:
            logging.error(f"Error processing product (attempt {attempt + 1}): {str(e)}")
        
        logging.info(f"Retrying... ({attempt + 1}/{max_retries})")
        time.sleep(5)
    
    logging.error(f"Failed to process product after {max_retries} attempts")
    return None

def write_to_sheet(sheet_name, data_list):
    """将数据写入到指定的工作表"""
    if not data_list:
        logging.warning(f"No data to write to sheet {sheet_name}")
        return False
    
    try:
        # 确保工作表存在
        if not ensure_sheet_exists(sheet_name):
            return False
        
        # 准备表头和数据
        if sheet_name.lower() == 'shoes':
            headers = [
                'Internal Reference', 'Title', 'Subtitle', 'Short Description', 'Description',
                'Brand', 'Style', 'Color', 'Material', 'Condition',
                'Heel Height', 'Shoe Size', 'Country/Region of Manufacture',
                'Pattern', 'Features', 'Occasion', 'Season',
                'Style Code', 'Width', 'US Shoe Size', 'EUR Shoe Size',
                'UK Shoe Size', 'Heel Type', 'Sole Material'
            ]
        else:
            headers = [
                'Internal Reference', 'Title', 'Subtitle', 'Short Description', 'Description',
                'Brand', 'Style', 'Color', 'Material', 'Condition',
                'Size', 'Country/Region of Manufacture',
                'Pattern', 'Features', 'Occasion', 'Season',
                'Style Code', 'Department', 'Theme'
            ]
        
        # 准备数据行
        rows = []
        for item in data_list:
            row = []
            for header in headers:
                row.append(str(item.get(header, '')))
            rows.append(row)
        
        # 获取现有数据的范围
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1:Z"
        ).execute()
        
        existing_values = result.get('values', [])
        start_row = len(existing_values) + 1 if existing_values else 1
        
        # 如果是空表，先写入表头
        if not existing_values:
            header_range = f"{sheet_name}!A1:{chr(65 + len(headers) - 1)}1"
            header_body = {
                'values': [headers]
            }
            sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=header_range,
                valueInputOption='RAW',
                body=header_body
            ).execute()
            start_row = 2
        
        # 写入数据
        data_range = f"{sheet_name}!A{start_row}:{chr(65 + len(headers) - 1)}{start_row + len(rows) - 1}"
        data_body = {
            'values': rows
        }
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=data_range,
            valueInputOption='RAW',
            body=data_body
        ).execute()
        
        logging.info(f"Successfully wrote {len(rows)} rows to sheet {sheet_name}")
        return True
        
    except Exception as e:
        logging.error(f"Error writing to sheet {sheet_name}: {str(e)}")
        return False

def main():
    """主函数"""
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # 读取产品信息
    product_types = read_spreadsheet('Sheet1!E2:E')
    brands = read_spreadsheet('Sheet1!F2:F')
    style_numbers = read_spreadsheet('Sheet1!I2:I')
    additional_info = read_spreadsheet('Sheet1!G2:G')
    size_info = read_spreadsheet('Sheet1!K2:X')
    internal_references = read_spreadsheet('Sheet1!C2:C')
    
    logging.info(f"Read {len(product_types)} product types, {len(brands)} brands, "
                f"{len(style_numbers)} style numbers, {len(additional_info)} additional info entries, "
                f"{len(size_info)} size info entries, and {len(internal_references)} internal references")
    
    # 找到必需列的最小长度
    min_length = min(len(product_types), len(brands), len(style_numbers), len(internal_references))
    if min_length == 0:
        logging.error("One or more mandatory columns are empty. Please check the spreadsheet.")
        return
        
    logging.info(f"Processing {min_length} rows with mandatory data")
    
    # 存储每个工作表的数据
    sheet_data = {}
    
    # 处理每一行数据
    for index in range(min_length):
        product_type = str(product_types[index][0]).strip() if product_types[index] else ""
        brand = str(brands[index][0]).strip() if brands[index] else ""
        style_number = str(style_numbers[index][0]).strip() if style_numbers[index] else ""
        add_info = str(additional_info[index][0]).strip() if index < len(additional_info) and additional_info[index] else ""
        size = get_size_info(size_info[index]) if index < len(size_info) and size_info[index] else ""
        internal_reference = str(internal_references[index][0]).strip() if internal_references[index] else ""
        
        # 验证必需数据
        if not all([product_type, brand, style_number, internal_reference]):
            logging.warning(f"Skipping row {index+2} due to missing mandatory data: "
                          f"Product Type: '{product_type}', Brand: '{brand}', "
                          f"Style Number: '{style_number}', Internal Reference: '{internal_reference}'")
            continue
        
        # 处理产品数据
        result = process_product(product_type, brand, style_number, add_info, size, index+2)
        if result:
            sheet_name, extracted_data = result
            extracted_data['Internal Reference'] = internal_reference
            if sheet_name not in sheet_data:
                sheet_data[sheet_name] = []
            sheet_data[sheet_name].append(extracted_data)
    
    # 写入数据到相应的工作表
    for sheet_name, data_list in sheet_data.items():
        if not write_to_sheet(sheet_name, data_list):
            logging.error(f"Failed to write data to sheet {sheet_name}")
    
    logging.info("Processing completed")

if __name__ == "__main__":
    try:
        # 设置基本日志配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('product_processing.log'),
                logging.StreamHandler()
            ]
        )
        
        # 记录程序开始
        logging.info("Starting product processing script")
        
        # 验证环境变量
        required_env_vars = [
            'GOOGLE_APPLICATION_CREDENTIALS',
            'SPREADSHEET_ID',
            'PERPLEXITY_API_KEY',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            exit(1)
        
        # 运行主程序
        main()
        
        # 记录程序结束
        logging.info("Product processing script completed successfully")
        
    except Exception as e:
        logging.error(f"Unexpected error in main program: {str(e)}")
        logging.exception("Stack trace:")
        exit(1)