import json
import os
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging
import re# 设置日志
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

# Perplexity API设置
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
if not PERPLEXITY_API_KEY:
    logging.error("PERPLEXITY_API_KEY environment variable not set")
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

def read_spreadsheet(range_name):
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    logging.info(f"Read {len(values)} rows from spreadsheet")
    if not values:
        logging.warning("No data found in spreadsheet")
    return values

def write_to_spreadsheet(range_name, values):
    body = {
        'values': values
    }
    logging.info(f"Attempting to write {len(values)} rows to range: {range_name}")
    logging.info(f"First row of data: {values[0] if values else 'No data'}")
    try:
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption='RAW', body=body).execute()
        logging.info(f"Write result: {result}")
        logging.info(f"Updated {result.get('updatedCells')} cells")
    except Exception as e:
        logging.error(f"Error writing to spreadsheet: {str(e)}")

def get_template(product_type):
    if not product_type:
        logging.error("Product type is empty")
        return None, None
    
    product_type = product_type.lower().replace(" ", "_")
    template_file = f'templates/{product_type}_template.json'
    
    try:
        with open(template_file, 'r') as file:
            template = json.load(file)
            template['product_type'] = product_type
            return template, product_type
    except Exception as e:
        logging.error(f"Error loading template: {str(e)}")
        return None, None

def get_size_info(row):
    for cell in row:
        if cell.strip():
            return f"Size {cell.strip()}"
    return ""

def generate_prompt(template, brand, product_type, style_number, additional_info, size_info):
    if product_type.lower() == 'shoes':
        prompt = f"""
        Please provide detailed information about these {brand} shoes...
        """
    else:
        prompt = f"""
        Please generate a detailed eBay listing using the following format:

        **Title:** [Generate a concise, descriptive title]
        **Subtitle:** [Generate a brief, catchy subtitle]
        **Short Description:** [Generate a brief summary of the product, about 2-3 sentences]
        **Description:** [Generate a detailed, multi-paragraph description]
        """
        
        for field in template['mandatory_fields']:
            prompt += f"\n**{field}:** [Generate appropriate content]"
        
        prompt += "\n\n**Optional Fields:**"
        
        for field in template['optional_fields']:
            prompt += f"\n**{field}:** [Generate appropriate content if available, or 'N/A' if not applicable]"
        
        prompt += "\n\n" + GENERAL_INSTRUCTIONS
    
    return prompt

def call_perplexity_api(prompt, temperature):
    logging.info(f"Calling Perplexity API with temperature {temperature}. Prompt: {prompt[:100]}...")  # 记录API调用
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
        
        # 记录完整的API响应
        logging.info(f"Full API response: {json.dumps(response_json, indent=2)}")
        
        # 保存API响应到文件
        with open(f'api_response_{int(time.time())}.json', 'w') as f:
            json.dump(response_json, f, indent=2)
        
        logging.info(f"API response saved to file. Content: {content[:200]}...")  # 只记录前200个字符
        return content
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        return None

def get_sheet_name(product_type):
    return product_type.lower().strip()

def ensure_sheet_exists(sheet_name):
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

def extract_fields_from_response(raw_response, template):
    logging.info(f"Raw response to extract: {raw_response[:500]}...")  # 只记录前500个字符
    extracted_data = {}

    # 特别处理鞋子的关键字段
    if template.get('product_type') == 'shoes':
        # 检查并提取 Type
        type_match = re.search(r'Type:\s*([^.\n]+)', raw_response)
        if type_match:
            shoe_type = type_match.group(1).strip()
            # 验证是否是有效的鞋子类型
            valid_men_types = ['Athletic Shoes', 'Sneakers', 'Boots', 'Casual Shoes', 'Dress Shoes', 'Sandals', 'Slippers']
            valid_women_types = ['Athletic Shoes', 'Sneakers', 'Boots', 'Comfort Shoes', 
                     'Flats', 'Heels', 'Sandals', 'Slippers']
            if any(valid_type in shoe_type for valid_type in valid_men_types + valid_women_types):
                extracted_data['Type'] = shoe_type
            else:
                logging.warning(f"Invalid shoe type detected: {shoe_type}")
                extracted_data['Type'] = 'N/A'
        
        # 检查并提取 Style
        style_match = re.search(r'Style:\s*([^.\n]+)', raw_response)
        if style_match:
            style = style_match.group(1).strip()
            extracted_data['Style'] = style
        
        # 检查并提取 Upper Material
        material_match = re.search(r'Upper Material:\s*([^.\n]+)', raw_response)
        if material_match:
            upper_material = material_match.group(1).strip()
            extracted_data['Upper Material'] = upper_material
    
    # 更新字段名称，移除意大利语
    fields_to_extract = ['Title', 'Subtitle', 'Short Description', 'Description']
    
    for field in fields_to_extract:
        pattern = rf'\*\*{re.escape(field)}:\*\*\s*(.*?)(?=\n\n\*\*|$)'
        match = re.search(pattern, raw_response, re.DOTALL)
        if match:
            extracted_data[field] = match.group(1).strip()
            logging.info(f"Successfully extracted {field}: {extracted_data[field][:100]}...")
        else:
            logging.warning(f"Failed to extract {field}")

    # Extract other fields
    all_fields = template['mandatory_fields'] + template['optional_fields']
    for field in all_fields:
        if field not in extracted_data:  # Avoid overwriting already extracted special fields
            field_match = re.search(rf'\*\*{re.escape(field)}:\*\*\s*(.+)', raw_response, re.IGNORECASE | re.MULTILINE)
            if field_match:
                extracted_data[field] = field_match.group(1).strip()
            else:
                extracted_data[field] = 'N/A'
                logging.warning(f"Field '{field}' not found in API response")

    logging.info(f"Extracted data: {json.dumps(extracted_data, indent=2)}")
    return extracted_data

def process_product(product_type, brand, style_number, additional_info, size_info, index, max_retries=2):
    logging.info(f"Processing: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}', Additional Info: '{additional_info}', Size Info: '{size_info}'")

    if not product_type:
        logging.warning(f"Skipping row {index} due to empty product type")
        return None

    sheet_name = get_sheet_name(product_type)
    template, _ = get_template(product_type)
    if not template:
        logging.warning(f"Skipping row {index} due to missing template for product type: {product_type}")
        return None

    for attempt in range(max_retries):
        # 第一次API调用：生成产品描述
        description_prompt = f"""
            Generate a concise and professional product description for {brand} {product_type}.
            Additional Information: {additional_info}

            Format requirements:
            1. Title: Create a clear title under 80 characters
               - Include brand, product type, and key features
               - Do not include style number
               - Format: [Brand] [Product Type] [Key Feature] [Color/Material]

            2. Subtitle: Create a compelling subtitle under 55 characters
               - Highlight unique selling points
               - Focus on benefits or exclusive features

            3. Short Description: 
               - 2-3 concise sentences
               - Focus on main features and benefits
               - Avoid technical details

            4. Description:
               - Use simple paragraphs without bullet points or markdown
               - Focus on: Materials, Design, Comfort, Quality
               - Include care instructions and sizing information
               - End with a call to action

            Please format your response exactly as:
            **Title:** [title]
            **Subtitle:** [subtitle]
            **Short Description:** [short description]
            **Description:**
            [description]
            """

        description_response = call_perplexity_api(description_prompt, 0.3)
        
        if not description_response:
            logging.warning(f"Failed to generate description on attempt {attempt + 1}")
            continue

        # 第二次API调用：生成Mandatory和Optional字段
        fields_prompt = f"""
        For this {brand} {product_type} (Style: {style_number}):

        Product Details:
        - Additional Info: {additional_info}
        - Size Info: {size_info}

        Please provide accurate information for each field:

        Mandatory Fields:
        {', '.join(template['mandatory_fields'])}

        Optional Fields:
        {', '.join(template['optional_fields'])}

        Requirements:
        1. Use 'N/A' only if information is truly unavailable
        2. Be specific with measurements and materials
        3. Include actual market prices where available
        4. Format each field as: **Field Name:** [content]
        5. Keep technical specifications precise and verifiable
        """
        
        fields_response = call_perplexity_api(fields_prompt, 0.1)  # 使用较低的温度以获得更精确的字段信息
        
        if not fields_response:
            logging.warning(f"Failed to generate fields on attempt {attempt + 1}")
            continue

        # 处理描述和字段分别
        description_data = extract_fields_from_response(description_response, template)
        fields_data = extract_fields_from_response(fields_response, template)
        extracted_data = {**description_data, **fields_data}
        
        # 添加尺寸信息到标题（如果可用）
        if 'Title' in extracted_data and size_info:
            extracted_data['Title'] += f" {size_info}"
        
        validate_fields(extracted_data, product_type)  # 验证字段
        
        logging.info(f"Extracted data: {json.dumps(extracted_data, indent=2)}")
        return sheet_name, extracted_data

    logging.error(f"Failed to process product after {max_retries} attempts")
    return None

def verify_written_data(sheet_name, start_row, num_rows):
    range_name = f"'{sheet_name}'!A{start_row}:ZZ{start_row + num_rows - 1}"
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    logging.info(f"Verifying written data in {sheet_name} from row {start_row} to {start_row + num_rows - 1}")
    for row_index, row in enumerate(values):
        logging.info(f"Row {start_row + row_index}:")
        for col_index, value in enumerate(row):
            logging.info(f"  Column {col_index + 1}: {value[:100]}...")  # 只记录前100个字符

def prepare_data_for_write(data, sheet_name):
    if sheet_name == 'shoes':
        # 确保所有必需字段都存在
        required_fields = [
            'Title', 'Subtitle', 'Description', 
            'Type', 'Style', 'Upper Material'
        ]
        
        for field in required_fields:
            if field not in data:
                data[field] = 'N/A'
                logging.warning(f"Missing field {field} in shoes data")

def clear_range_format(sheet_name, start_row, end_row):
    range_name = f"'{sheet_name}'!A{start_row}:ZZ{end_row}"
    clear_request = {
        "requests": [
            {
                "updateCells": {
                    "range": {
                        "sheetId": get_sheet_id(sheet_name),
                        "startRowIndex": start_row - 1,
                        "endRowIndex": end_row
                    },
                    "fields": "userEnteredFormat"
                }
            }
        ]
    }
    sheets_service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=clear_request).execute()
    logging.info(f"Cleared format for range: {range_name}")

def get_sheet_id(sheet_name):
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in sheet_metadata.get('sheets', ''):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None

def validate_fields(data, product_type=None):
    if product_type == 'shoes':
        # 验证鞋子特定字段
        if 'Type' in data and len(data['Type']) > 0:
            logging.info(f"Shoe Type: {data['Type']}")
        else:
            logging.warning("Missing or invalid Shoe Type")
            
        if 'Style' in data and len(data['Style']) > 0:
            logging.info(f"Shoe Style: {data['Style']}")
        else:
            logging.warning("Missing or invalid Shoe Style")
            
        if 'Upper Material' in data and len(data['Upper Material']) > 0:
            logging.info(f"Upper Material: {data['Upper Material']}")
        else:
            logging.warning("Missing or invalid Upper Material")
    if '**Subtitle' in data.get('Title', ''):
        logging.warning("Title contains Subtitle content")
        # 尝试修复问题
        data['Title'] = data['Title'].split('**Subtitle')[0].strip()
    
    if '**Short Description' in data.get('Title', ''):
        logging.warning("Title contains Short Description content")
        # 尝试修复问题
        data['Title'] = data['Title'].split('**Short Description')[0].strip()
    
    if '**Short Description' in data.get('Subtitle', ''):
        logging.warning("Subtitle contains Short Description content")
        # 尝试修复问题
        data['Subtitle'] = data['Subtitle'].split('**Short Description')[0].strip()
    
    # 检查字段长度
    if len(data.get('Title', '')) > 80:
        logging.warning(f"Title is too long: {len(data['Title'])} characters")
    if len(data.get('Subtitle', '')) > 55:
        logging.warning(f"Subtitle is too long: {len(data['Subtitle'])} characters")
    # 可以添加更多的验证...

def validate_shoe_fields(data):
    """验证鞋子特定字段的有效性"""
    valid_fields = {
        'Type': {
            'men': ['Athletic Shoes', 'Sneakers', 'Boots', 'Casual Shoes', 
                   'Dress Shoes', 'Sandals', 'Slippers'],
            'women': ['Athletic Shoes', 'Sneakers', 'Boots', 'Comfort Shoes', 
                     'Flats', 'Heels', 'Sandals', 'Slippers']
        },
        'Style': {
            'boots': ['Knee-high', 'Mid-calf', 'Hiking', 'Chelsea', 'Winter', 
                     'Wellington', 'Ankle', 'Work Boots'],
            'casual': ['Sneakers', 'Loafers', 'Vans'],
            'formal': ['Oxfords', 'Smart Shoes', 'Dress Shoes'],
            'sandals': ['Classic', 'Platform', 'Flip Flops', 'Sports', 
                       'Beach Shoes', 'Birkenstock', 'Crocs', 'Teva', 
                       'Adidas Sliders']
        }
    }
    
    errors = []
    
    # 验证类型
    if data.get('Type') and not any(
        shoe_type in data['Type'] 
        for types in valid_fields['Type'].values() 
        for shoe_type in types
    ):
        errors.append(f"Invalid shoe type: {data['Type']}")
    
    # 验证风格
    if data.get('Style') and not any(
        style in data['Style'] 
        for styles in valid_fields['Style'].values() 
        for style in styles
    ):
        errors.append(f"Invalid shoe style: {data['Style']}")
    
    return errors

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # Read product information
    product_types = read_spreadsheet('Sheet1!E2:E')
    brands = read_spreadsheet('Sheet1!F2:F')
    style_numbers = read_spreadsheet('Sheet1!I2:I')
    additional_info = read_spreadsheet('Sheet1!G2:G')
    size_info = read_spreadsheet('Sheet1!K2:X')
    internal_references = read_spreadsheet('Sheet1!C2:C')  # 读取"internal reference"列
    
    logging.info(f"Read {len(product_types)} product types, {len(brands)} brands, {len(style_numbers)} style numbers, {len(additional_info)} additional info entries, {len(size_info)} size info entries, and {len(internal_references)} internal references")
    
    # Find the length of the mandatory columns
    min_length = min(len(product_types), len(brands), len(style_numbers), len(internal_references))
    
    if min_length == 0:
        logging.error("One or more mandatory columns are empty. Please check the spreadsheet.")
        return

    logging.info(f"Processing {min_length} rows with mandatory data")

    # Store data for each sheet
    sheet_data = {}
    
    for index in range(min_length):
        product_type = str(product_types[index][0]).strip() if product_types[index] else ""
        brand = str(brands[index][0]).strip() if brands[index] else ""
        style_number = str(style_numbers[index][0]).strip() if style_numbers[index] else ""
        add_info = str(additional_info[index][0]).strip() if index < len(additional_info) and additional_info[index] else ""
        size = get_size_info(size_info[index]) if index < len(size_info) and size_info[index] else ""
        internal_reference = str(internal_references[index][0]).strip() if internal_references[index] else ""
        
        if not all([product_type, brand, style_number, internal_reference]):
            logging.warning(f"Skipping row {index+2} due to missing mandatory data: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}', Internal Reference: '{internal_reference}'")
            continue
        
        result = process_product(product_type, brand, style_number, add_info, size, index+2)
        if result:
            sheet_name, extracted_data = result
            extracted_data['Internal Reference'] = internal_reference  # 添加内部参考号到提取的数据中
            if sheet_name not in sheet_data:
                sheet_data[sheet_name] = []
            sheet_data[sheet_name].append(extracted_data)

    # Write data to respective sheets
    for sheet_name, data in sheet_data.items():
        for item in data:
            prepare_data_for_write(item, sheet_name)
        try:
            if ensure_sheet_exists(sheet_name):
                # Get field names (first row) of the sheet
                field_names = sheets_service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID, range=f"'{sheet_name}'!A1:ZZ1").execute().get('values', [[]])[0]

                logging.info(f"Sheet field names: {field_names}")
                logging.info(f"Extracted data keys: {list(data[0].keys())}")

                # 在 main 函数中
                required_fields = ['Internal Reference', 'Title', 'Subtitle', 'Short Description', 'Description']
                for field in required_fields:
                    if field not in field_names:
                        field_names.insert(0, field)  # 将Internal Reference插入到字段列表的开头
                        logging.info(f"Added missing field to sheet: {field}")

                # Prepare data to write
                rows_to_write = []
                for item in data:
                    row = [item.get('Internal Reference', 'N/A')]  # 首先添加Internal Reference
                    for field in field_names[1:]:  # 跳过Internal Reference，因为我们已经添加了
                        value = item.get(field, 'N/A')
                        if isinstance(value, str) and len(value) > 50000:
                            value = value[:50000] + "... (truncated)"
                        row.append(value)
                    rows_to_write.append(row)
                    logging.info(f"Prepared row: {row[:5]}...")  # 只记录前5个字段

                # Get current row count of the sheet
                sheet_info = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=[f"'{sheet_name}'"], includeGridData=True).execute()
                current_row = len(sheet_info['sheets'][0]['data'][0]['rowData']) + 1

                # Clear format of the range to be written
                clear_range_format(sheet_name, current_row, current_row + len(rows_to_write))

                # Prepare data for write
                rows_to_write = prepare_data_for_write(rows_to_write)

                # Write data
                range_name = f"'{sheet_name}'!A{current_row}"
                write_to_spreadsheet(range_name, rows_to_write)
                
                # Verify written data
                verify_written_data(sheet_name, current_row, len(rows_to_write))
                
                logging.info(f"Successfully wrote and verified {len(rows_to_write)} rows to sheet '{sheet_name}'")
            else:
                logging.error(f"Unable to ensure '{sheet_name}' sheet exists. Skipping write operation.")
        except Exception as e:
            logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

if __name__ == '__main__':
    main()

