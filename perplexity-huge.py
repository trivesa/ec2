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
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

if GOOGLE_APPLICATION_CREDENTIALS_JSON:
    credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=SCOPES)
else:
    logging.error("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")
    exit(1)

sheets_service = build('sheets', 'v4', credentials=credentials)

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
Use the provided Brand, Product Type, Style number, Additional Information, and Size Information to search for product details and complete the eBay product listing as per the below requirements:

Create Title (Titolo), Subtitle (Sottotitolo), Short Description (Breve Descrizione), and Description (Descrizione).
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
- Size: Add the size information to the end of the title if available.

Instructions for the subtitle (Sottotitolo)
Complementary: It should add value beyond what the main title already says.
Concise: Keep it short and clear, under 55 characters.

Instructions for the Description (Descrizione):
Create a comprehensive product description using bullet points for better readability. Include the following elements:

• Product Overview:
  - Brief, engaging statement highlighting key features or benefits
  - Explanation of what makes this product stand out

• Key Features:
  - Focus on the most important features (technology, materials, design)
  - Explain how these features benefit the user
  - Provide specific details about product characteristics and proprietary technologies

• Size and Fit:
  - Detailed information about fit, including size options
  - Comparison to standard sizing

• Materials and Construction:
  - Description of materials used in different parts of the product
  - Information on special manufacturing processes

• Intended Use:
  - Explanation of activities or occasions the product is best suited for

• Care Instructions:
  - Guidance on how to clean and maintain the product

• After-Sales:
  - Mention of warranty information and return policy within 14 days according to the European regulations.

• Purchase Encouragement:
  - Conclusion encouraging the buyer to make a purchase
  - Highlight any limited availability or special offers

Combine all these elements into a cohesive, flowing description using bullet points, without separate headings or sections. Ensure the description is easy to read, informative, and engaging.
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

def get_size_info(row):
    for cell in row:
        if cell.strip():
            return f"Size {cell.strip()}"
    return ""

def generate_prompt(template, brand, product_type, style_number, additional_info, size_info):
    prompt = f"""
    Brand: {brand}
    Product Type: {product_type}
    Style Number: {style_number}
    Additional Information: {additional_info}
    Size Information: {size_info}

    Please generate a detailed eBay listing using the following format:

    **Title (Titolo):** [Generate a concise, descriptive title]
    **Subtitle (Sottotitolo):** [Generate a brief, catchy subtitle]
    **Short Description (Breve Descrizione):** [Generate a brief summary of the product, about 2-3 sentences]
    **Description (Descrizione):** [Generate a detailed, multi-paragraph description]
    
    **Mandatory Fields:**
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
            {'role': 'system', 'content': 'You are a luxury consumer goods industry expert, specializing in high-end fashion and luxury brand product descriptions and market positioning.'},
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
    
    fields_to_extract = ['Title (Titolo)', 'Subtitle (Sottotitolo)', 'Short Description (Breve Descrizione)', 'Description (Descrizione)']
    
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
        Generate a detailed product description for {brand} {product_type}.
        Additional Information: {additional_info}
        Please format your response exactly as follows:

        **Title (Titolo):** [Your title here, do not include style number]
        **Subtitle (Sottotitolo):** [Your subtitle here]
        **Short Description (Breve Descrizione):** [Your brief summary here, about 2-3 sentences]
        **Description (Descrizione):**
        [Your multi-line description here]

        Use bullet points for better readability in the description.
        """
        description_response = call_perplexity_api(description_prompt, 0.7)  # 使用较高的温度以获得有创意的描述
        
        if not description_response:
            logging.warning(f"Failed to generate description on attempt {attempt + 1}")
            continue

        # 第二次API调用：生成Mandatory和Optional字段
        fields_prompt = f"""
        For the {brand} {product_type} with style number {style_number}, 
        Additional Information: {additional_info}
        Size Information: {size_info}
        provide information for the following fields. Use 'N/A' if the information is not available or not applicable.

        Mandatory Fields:
        {', '.join(template['mandatory_fields'])}

        Optional Fields:
        {', '.join(template['optional_fields'])}

        Please provide the information in a structured format, with each field on a new line.
        """
        fields_response = call_perplexity_api(fields_prompt, 0.3)  # 使用较低的温度以获得更精确的字段信息
        
        if not fields_response:
            logging.warning(f"Failed to generate fields on attempt {attempt + 1}")
            continue

        # 处理描述和字段分别
        description_data = extract_fields_from_response(description_response, template)
        fields_data = extract_fields_from_response(fields_response, template)
        extracted_data = {**description_data, **fields_data}
        
        # 添加尺寸信息到标题（如果可用）
        if 'Title (Titolo)' in extracted_data and size_info:
            extracted_data['Title (Titolo)'] += f" {size_info}"
        
        validate_fields(extracted_data)  # 验证字段
        
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

def prepare_data_for_write(data):
    return [[str(cell) if cell is not None else '' for cell in row] for row in data]

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

def validate_fields(data):
    if '**Subtitle' in data.get('Title (Titolo)', ''):
        logging.warning("Title contains Subtitle content")
        # 尝试修复问题
        data['Title (Titolo)'] = data['Title (Titolo)'].split('**Subtitle')[0].strip()
    
    if '**Short Description' in data.get('Title (Titolo)', ''):
        logging.warning("Title contains Short Description content")
        # 尝试修复问题
        data['Title (Titolo)'] = data['Title (Titolo)'].split('**Short Description')[0].strip()
    
    if '**Short Description' in data.get('Subtitle (Sottotitolo)', ''):
        logging.warning("Subtitle contains Short Description content")
        # 尝试修复问题
        data['Subtitle (Sottotitolo)'] = data['Subtitle (Sottotitolo)'].split('**Short Description')[0].strip()
    
    # 检查字段长度
    if len(data.get('Title (Titolo)', '')) > 80:
        logging.warning(f"Title is too long: {len(data['Title (Titolo)'])} characters")
    if len(data.get('Subtitle (Sottotitolo)', '')) > 55:
        logging.warning(f"Subtitle is too long: {len(data['Subtitle (Sottotitolo)'])} characters")
    
    # 可以添加更多的验证...

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
        try:
            if ensure_sheet_exists(sheet_name):
                # Get field names (first row) of the sheet
                field_names = sheets_service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID, range=f"'{sheet_name}'!A1:ZZ1").execute().get('values', [[]])[0]

                logging.info(f"Sheet field names: {field_names}")
                logging.info(f"Extracted data keys: {list(data[0].keys())}")

                # Ensure all required fields are present
                required_fields = ['Internal Reference', 'Title (Titolo)', 'Subtitle (Sottotitolo)', 'Short Description (Breve Descrizione)', 'Description (Descrizione)']
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

