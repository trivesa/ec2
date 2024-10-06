import json
import os
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
Use the provided Brand, Product Type, and Style number to search for product details and complete the eBay product listing as per the below requirements:

Create Title (Titolo), Subtitle (Sottotitolo) and Description (Descrizione).
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

def write_to_sheet(sheet, data):
    try:
        title = data.get("Title (Titolo)", "")
        subtitle = data.get("Subtitle (Sottotitolo)", "")
        description = data.get("Description (Descrizione)", "")
        
        logging.info(f"Preparing to write data. Title: {title[:50]}...")
        logging.info(f"Subtitle length: {len(subtitle)}")
        logging.info(f"Description length: {len(description)}")
        
        row = [title, subtitle, description]  # 添加其他字段
        
        sheet.append_row(row)
        logging.info("Successfully wrote row to sheet")
        
        # 验证写入是否成功
        last_row = sheet.get_all_values()[-1]
        logging.info(f"Last row written: {last_row[:3]}")  # 只打印前三列
        
    except Exception as e:
        logging.error(f"Error writing to sheet: {str(e)}")
        logging.error(f"Data that failed to write: {data}")

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

def generate_prompt(template, brand, product_type, style_number):
    prompt = f"""
    Brand: {brand}
    Product Type: {product_type}
    Style Number: {style_number}

    Please generate a detailed eBay listing using the following format:

    **Title (Titolo):** [Generate a concise, descriptive title]
    **Subtitle (Sottotitolo):** [Generate a brief, catchy subtitle]
    **Description (Descrizione):**
    [Generate a detailed, multi-paragraph description]

    **Mandatory Fields:**
    """
    
    for field in template['mandatory_fields']:
        prompt += f"\n**{field}:** [Generate appropriate content]"
    
    prompt += "\n\n**Optional Fields:**"
    
    for field in template['optional_fields']:
        prompt += f"\n**{field}:** [Generate appropriate content if available, or 'N/A' if not applicable]"
    
    prompt += "\n\n" + GENERAL_INSTRUCTIONS
    
    return prompt

def call_perplexity_api(prompt):
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'llama-3.1-sonar-huge-128k-online',
        'messages': [
            {'role': 'system', 'content': 'You are an eBay fashion product listing expert.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 1000,
        'temperature': 0.2,
        'top_p': 0.9,
        'return_citations': True,
        'search_recency_filter': 'month',
        'frequency_penalty': 1
    }
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        content = response_json['choices'][0]['message']['content']
        logging.info(f"Raw API Response: {content}")
        return content
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {str(e)}")
        return None

def get_sheet_name(product_type):
    return product_type.lower().strip().replace(" ", "_")

def extract_fields_from_response(raw_response, template):
    extracted_data = {}
    
    # 提取 Title, Subtitle, 和 Description
    title_match = re.search(r'\*\*Title \(Titolo\):\*\* (.+)', raw_response)
    subtitle_match = re.search(r'\*\*Subtitle \(Sottotitolo\):\*\* (.+)', raw_response)
    description_match = re.search(r'\*\*Description \(Descrizione\):\*\*\n([\s\S]+?)(?=\n\n\*\*|$)', raw_response)
    
    if title_match:
        extracted_data['Title (Titolo)'] = title_match.group(1).strip()
    if subtitle_match:
        extracted_data['Subtitle (Sottotitolo)'] = subtitle_match.group(1).strip()
    if description_match:
        extracted_data['Description (Descrizione)'] = description_match.group(1).strip()
    
    # 提取其他字段
    all_fields = template['mandatory_fields'] + template['optional_fields']
    for field in all_fields:
        if field not in extracted_data:  # 避免覆盖已提取的特殊字段
            field_match = re.search(rf'\*\*{re.escape(field)}:\*\* (.+)', raw_response, re.IGNORECASE | re.MULTILINE)
            if field_match:
                extracted_data[field] = field_match.group(1).strip()
            else:
                extracted_data[field] = 'N/A'
                logging.warning(f"Field '{field}' not found in API response")
    
    return extracted_data

def process_product(product_type, brand, style_number, index, max_retries=2):
    logging.info(f"Processing: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")

    if not product_type:
        logging.warning(f"Skipping row {index} due to empty product type")
        return None

    sheet_name = get_sheet_name(product_type)
    template, _ = get_template(product_type)
    if not template:
        logging.warning(f"Skipping row {index} due to missing template for product type: {product_type}")
        return None

    for attempt in range(max_retries):
        prompt = generate_prompt(template, brand, product_type, style_number)
        raw_response = call_perplexity_api(prompt)
        
        if raw_response:
            logging.info(f"Raw API Response received for {product_type} - {brand} - {style_number}")
            extracted_data = extract_fields_from_response(raw_response, template)
            logging.info(f"Extracted data: {json.dumps(extracted_data, indent=2)}")
            return sheet_name, extracted_data
        else:
            logging.warning("API call failed or returned empty response")
        
        logging.warning(f"Attempt {attempt + 1} failed. Retrying...")

    logging.error(f"Failed to process product after {max_retries} attempts")
    return None

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # 读取产品信息
    product_types = read_spreadsheet('Sheet1!E2:E')
    brands = read_spreadsheet('Sheet1!F2:F')
    style_numbers = read_spreadsheet('Sheet1!I2:I')
    
    logging.info(f"Read {len(product_types)} product types, {len(brands)} brands, and {len(style_numbers)} style numbers")
    
    # 找出最短的列的长度
    min_length = min(len(product_types), len(brands), len(style_numbers))
    
    if min_length == 0:
        logging.error("One or more columns are empty. Please check the spreadsheet.")
        return

    logging.info(f"Processing {min_length} rows with complete data")

    # 用于存储每个sheet的数据
    sheet_data = {}
    
    for index in range(min_length):
        product_type = str(product_types[index][0]).strip() if product_types[index] else ""
        brand = str(brands[index][0]).strip() if brands[index] else ""
        style_number = str(style_numbers[index][0]).strip() if style_numbers[index] else ""
        
        if not all([product_type, brand, style_number]):
            logging.warning(f"Skipping row {index+2} due to missing data: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")
            continue
        
        result = process_product(product_type, brand, style_number, index+2)
        if result:
            sheet_name, extracted_data = result
            if sheet_name not in sheet_data:
                sheet_data[sheet_name] = []
            sheet_data[sheet_name].append(extracted_data)

    # 将数据写入相应的sheet
    for sheet_name, data in sheet_data.items():
        try:
            # 获取sheet的字段名（第一行）
            field_names = sheets_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A1:ZZ1").execute().get('values', [[]])[0]

            # 准备要写入的数据
            rows_to_write = []
            for item in data:
                row = [item.get(field, 'N/A') for field in field_names]
                rows_to_write.append(row)

            # 获取sheet的当前行数
            sheet_info = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=[sheet_name], includeGridData=True).execute()
            current_row = len(sheet_info['sheets'][0]['data'][0]['rowData']) + 1

            # 写入数据
            range_name = f"{sheet_name}!A{current_row}"
            write_to_spreadsheet(range_name, rows_to_write)
            logging.info(f"Successfully wrote {len(rows_to_write)} rows to sheet '{sheet_name}'")
        except Exception as e:
            logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

if __name__ == '__main__':
    main()
