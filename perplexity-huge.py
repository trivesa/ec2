import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Google Sheets API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = '/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=credentials)

# Perplexity API setup
PERPLEXITY_API_KEY = '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'
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

SPREADSHEET_ID = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
GENERAL_INSTRUCTIONS = """
Use the provided Brand, Product Type, Style number, Additional Information, and Size Information to search for product details and complete the eBay product listing as per the below requirements:

Create Title (Titolo), Subtitle (Sottotitolo), Short Description (Breve Descrizione), and Description (Descrizione).
Find the Mandatory and Optional product information listed under 'Mandatory Fields' and 'Optional Fields'.
IMPORTANT: You MUST use the EXACT field names as provided, including both English and Italian parts. Every field name should be in the format: 'English Name (Italian Name)'. Do not omit or change any part of the field names.
"""

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
        logging.info(f"Sending request to Perplexity API: {prompt[:100]}...")
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        content = response_json['choices'][0]['message']['content']
        logging.info(f"Received response from Perplexity API: {content[:100]}...")
        return content
    except requests.RequestException as e:
        logging.error(f"Error during API request: {str(e)}")
        return None
    except KeyError:
        logging.error("Unexpected response structure from Perplexity API")
        return None
def generate_prompt(template, brand, product_type, style_number, additional_info=None, size_info=None):
    prompt = f"""
    Brand: {brand}
    Product Type: {product_type}
    Style Number: {style_number}
    """

    if additional_info:
        prompt += f"Additional Information: {additional_info}\n"
    if size_info:
        prompt += f"Size Information: {size_info}\n"

    prompt += """
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

def extract_fields_from_response(raw_response, template):
    logging.info(f"Raw response to extract: {raw_response[:200]}...")

    extracted_data = {}
    title_match = re.search(r'\*\*Title \(Titolo\):\*\*\s*(.+)', raw_response)
    subtitle_match = re.search(r'\*\*Subtitle \(Sottotitolo\):\*\*\s*(.+)', raw_response)
    short_description_match = re.search(r'\*\*Short Description \(Breve Descrizione\):\*\*\s*(.+)', raw_response)
    description_match = re.search(r'\*\*Description \(Descrizione\):\*\*\s*\n([\s\S]+?)(?=\n\n\*\*|$)', raw_response)

    extracted_data['Title (Titolo)'] = title_match.group(1).strip() if title_match else 'N/A'
    extracted_data['Subtitle (Sottotitolo)'] = subtitle_match.group(1).strip() if subtitle_match else 'N/A'
    extracted_data['Short Description (Breve Descrizione)'] = short_description_match.group(1).strip() if short_description_match else 'N/A'
    extracted_data['Description (Descrizione)'] = description_match.group(1).strip() if description_match else 'N/A'

    all_fields = template['mandatory_fields'] + template['optional_fields']
    for field in all_fields:
        field_match = re.search(rf'\*\*{re.escape(field)}:\*\*\s*(.+)', raw_response, re.IGNORECASE)
        extracted_data[field] = field_match.group(1).strip() if field_match else 'N/A'

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
        description_prompt = generate_prompt(
            template, brand, product_type, style_number,
            additional_info if additional_info else None,
            size_info if size_info else None
        )

        description_response = call_perplexity_api(description_prompt, 0.3)
        
        if not description_response:
            logging.warning(f"Failed to generate description on attempt {attempt + 1}")
            continue

        description_data = extract_fields_from_response(description_response, template)

        if 'Title (Titolo)' in description_data and size_info:
            description_data['Title (Titolo)'] += f" {size_info}"

        logging.info(f"Extracted data: {json.dumps(description_data, indent=2)}")
        return sheet_name, description_data

    logging.error(f"Failed to process product after {max_retries} attempts")
    return None
def read_spreadsheet(range_name):
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    logging.info(f"Read {len(values)} rows from spreadsheet")
    if not values:
        logging.warning("No data found in spreadsheet")
    return values

def get_size_info(row):
    for cell in row:
        if cell.strip():
            return f"Size {cell.strip()}"
    return None  # Return None instead of empty string if no size info is found

def get_sheet_name(product_type):
    return product_type.lower().strip()

def write_to_spreadsheet(range_name, values):
    body = {'values': values}
    try:
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption='RAW', body=body).execute()
        logging.info(f"Written {result.get('updatedCells')} cells to spreadsheet")
    except Exception as e:
        logging.error(f"Failed to write to spreadsheet: {str(e)}")

def ensure_sheet_exists(sheet_name):
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', '')
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                logging.info(f"Sheet '{sheet_name}' already exists.")
                return True
        
        request_body = {'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body=request_body).execute()
        logging.info(f"Sheet '{sheet_name}' has been created.")
        return True
    except Exception as e:
        logging.error(f"Error ensuring sheet '{sheet_name}' exists: {str(e)}")
        return False

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    product_types = read_spreadsheet('Sheet1!E2:E')
    brands = read_spreadsheet('Sheet1!F2:F')
    style_numbers = read_spreadsheet('Sheet1!I2:I')
    additional_info = read_spreadsheet('Sheet1!J2:J')
    size_info = read_spreadsheet('Sheet1!K2:X')
    
    logging.info(f"Read {len(product_types)} product types, {len(brands)} brands, {len(style_numbers)} style numbers, {len(additional_info)} additional info entries, and {len(size_info)} size info entries")
    
    min_length = min(len(product_types), len(brands), len(style_numbers), len(additional_info), len(size_info))
    
    if min_length == 0:
        logging.error("One or more columns are empty. Please check the spreadsheet.")
        return

    logging.info(f"Processing {min_length} rows with complete data")

    sheet_data = {}
    
    for index in range(min_length):
        product_type = str(product_types[index][0]).strip() if product_types[index] else ""
        brand = str(brands[index][0]).strip() if brands[index] else ""
        style_number = str(style_numbers[index][0]).strip() if style_numbers[index] else ""
        add_info = str(additional_info[index][0]).strip() if additional_info[index] else None
        size = get_size_info(size_info[index]) if size_info[index] else None
        
        if not all([product_type, brand, style_number]):
            logging.warning(f"Skipping row {index+2} due to missing data: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")
            continue
        
        result = process_product(product_type, brand, style_number, add_info, size, index+2)
        if result:
            sheet_name, extracted_data = result
            if sheet_name not in sheet_data:
                sheet_data[sheet_name] = []
            sheet_data[sheet_name].append(extracted_data)

    for sheet_name, data in sheet_data.items():
        try:
            if ensure_sheet_exists(sheet_name):
                field_names = sheets_service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID, range=f"'{sheet_name}'!A1:ZZ1").execute().get('values', [[]])[0]

                rows_to_write = []
                for item in data:
                    row = [item.get(field, 'N/A') for field in field_names]
                    rows_to_write.append(row)

                sheet_info = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=[f"'{sheet_name}'"], includeGridData=True).execute()
                current_row = len(sheet_info['sheets'][0]['data'][0]['rowData']) + 1

                range_name = f"'{sheet_name}'!A{current_row}"
                write_to_spreadsheet(range_name, rows_to_write)
                logging.info(f"Successfully wrote {len(rows_to_write)} rows to sheet '{sheet_name}'")
            else:
                logging.error(f"Unable to ensure '{sheet_name}' sheet exists. Skipping write operation.")
        except Exception as e:
            logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

if __name__ == '__main__':
    main()
