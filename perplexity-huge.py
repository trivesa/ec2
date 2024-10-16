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

# 其他常量和指令保持不变

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
    
    if isinstance(raw_response, dict):
        # 处理字典类型的响应
        extracted_data = raw_response
    else:
        # 使用正则表达式处理字符串响应
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

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # Read product information
    product_types = read_spreadsheet('Sheet1!E2:E')
    brands = read_spreadsheet('Sheet1!F2:F')
    style_numbers = read_spreadsheet('Sheet1!I2:I')
    additional_info = read_spreadsheet('Sheet1!J2:J')
    size_info = read_spreadsheet('Sheet1!K2:X')
    
    logging.info(f"Read {len(product_types)} product types, {len(brands)} brands, {len(style_numbers)} style numbers, {len(additional_info)} additional info entries, and {len(size_info)} size info entries")
    
    # Find the length of the mandatory columns
    min_length = min(len(product_types), len(brands), len(style_numbers))
    
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
        
        if not all([product_type, brand, style_number]):
            logging.warning(f"Skipping row {index+2} due to missing mandatory data: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")
            continue
        
        result = process_product(product_type, brand, style_number, add_info, size, index+2)
        if result:
            sheet_name, extracted_data = result
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
                required_fields = ['Title (Titolo)', 'Subtitle (Sottotitolo)', 'Short Description (Breve Descrizione)', 'Description (Descrizione)']
                for field in required_fields:
                    if field not in field_names:
                        field_names.append(field)
                        logging.info(f"Added missing field to sheet: {field}")

                # Prepare data to write
                rows_to_write = []
                for item in data:
                    row = []
                    for field in field_names:
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
