import json
import os
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging
import re

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
- Size: If possible, include the size range (e.g., 'US 8-13').
- Style Number: ALWAYS include the style number at the end of the title.

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
        pattern = rf'\*\*{re.escape(field)}:\*\*\s*([\s\S]+?)(?=\n\n\*\*|$)'
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
        # Generate product description
        description_prompt = f"""
        Generate a detailed product description for {brand} {product_type} with style number {style_number}.
        Additional Information: {additional_info}
        Size Information: {size_info}
        Please format your response exactly as follows:

        **Title (Titolo):** [Your title here]
        **Subtitle (Sottotitolo):** [Your subtitle here]
        **Short Description (Breve Descrizione):** [Your brief summary here, about 2-3 sentences]
        **Description (Descrizione):**
        [Your multi-line description here]

        Use bullet points for better readability in the description.
        """
        description_response = call_perplexity_api(description_prompt, 0.3)
        
        if not description_response:
            logging.warning(f"Failed to generate description on attempt {attempt + 1}")
            continue

        # Generate Mandatory and Optional fields
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
        fields_response = call_perplexity_api(fields_prompt, 0.1)
        
        if not fields_response:
            logging.warning(f"Failed to generate fields on attempt {attempt + 1}")
            continue

        # Process description and fields separately
        description_data = extract_fields_from_response(description_response, template)
        fields_data = extract_fields_from_response(fields_response, template)
        extracted_data = {**description_data, **fields_data}
        
        # Add size information to the title
        if 'Title (Titolo)' in extracted_data and size_info:
            extracted_data['Title (Titolo)'] += f" {size_info}"
        
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

def find_column_index(sheet_data, column_name):
    if not sheet_data or not sheet_data[0]:
        return -1
    return next((i for i, cell in enumerate(sheet_data[0]) if cell.strip().lower() == column_name.lower()), -1)

def read_column_data(sheet_data, column_name):
    col_index = find_column_index(sheet_data, column_name)
    if col_index == -1:
        # 尝试模糊匹配
        for i, cell in enumerate(sheet_data[0]):
            if column_name.lower() in cell.strip().lower():
                col_index = i
                logging.info(f"Found similar column name: '{cell}' for '{column_name}'")
                break
        if col_index == -1:
            logging.warning(f"Column '{column_name}' not found in the sheet.")
            return []
    return [row[col_index] for row in sheet_data[1:] if len(row) > col_index]

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # 读取整个工作表的数据
    sheet_data = read_spreadsheet('Sheet1!A1:ZZ')
    
    if not sheet_data:
        logging.error("No data found in the spreadsheet.")
        return

    # 使用列标题读取数据，不区分大小写
    column_mappings = {
        "product_types": ["Product Type", "ProductType", "Type"],
        "brands": ["Brand", "BrandName"],
        "style_numbers": ["Style Number", "StyleNumber", "Style"],
        "additional_info": ["Additional Information", "AdditionalInfo", "Extra Info"],
        "size_info": ["Size", "Size Information", "Available Sizes", "SizeInfo"]
    }

    data = {}
    for key, possible_names in column_mappings.items():
        for name in possible_names:
            column_data = read_column_data(sheet_data, name)
            if column_data:
                data[key] = column_data
                logging.info(f"Found data for '{key}' using column name '{name}'")
                break
        if key not in data:
            logging.warning(f"No data found for '{key}' using any of the possible names: {possible_names}")

    # 检查必要的数据是否存在
    required_keys = ["product_types", "brands", "style_numbers"]
    if not all(key in data for key in required_keys):
        logging.error("One or more mandatory columns are missing. Please check the spreadsheet.")
        return

    min_length = min(len(data[key]) for key in required_keys)
    logging.info(f"Processing {min_length} rows with mandatory data")

    # 处理数据
    for index in range(min_length):
        product_type = data["product_types"][index] if index < len(data["product_types"]) else ""
        brand = data["brands"][index] if index < len(data["brands"]) else ""
        style_number = data["style_numbers"][index] if index < len(data["style_numbers"]) else ""
        add_info = data.get("additional_info", [])[index] if index < len(data.get("additional_info", [])) else ""
        size = data.get("size_info", [])[index] if index < len(data.get("size_info", [])) else ""
        
        if not all([product_type, brand, style_number]):
            logging.warning(f"Skipping row {index+2} due to missing mandatory data: "
                            f"Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")
            continue
        
        # 处理产品数据...
        result = process_product(product_type, brand, style_number, add_info, size, index+2)
        # ... 其余的处理逻辑 ...

    # ... 其余的主函数逻辑 ...

if __name__ == '__main__':
    main()
