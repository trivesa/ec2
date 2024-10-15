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
Structure of the title: brand name + product name + key features + style number + shoe size or clothing size or belt size or sizes if it is other products.
Requirements of each section of the title:
 1) Brand Name: Include the brand for recognition (e.g., 'PRADA').
 2) Product Name: Clearly state what the item is (e.g., 'America's Cup T-Shirt').
 3) Key Features: Include important features such as model name, style name, or technology (e.g., 'Luna Rossa Collection').
 4) Style Number: ALWAYS include the style number.
 5) Size: Always include the shoe size or clothing size or belt size or sizes if there are other products, separated from other parts of the title with a comma.
 6) Keep the title within 80 characters if possible.

Example: "PRADA America's Cup T-Shirt Luna Rossa Collection ABC123, 12Y"

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

def extract_fields_from_response(raw_response, template, brand, style_number, size_info):
    extracted_data = {}
    
    # 使用更宽松的正则表达式来匹配字段
    field_pattern = r'\*\*(.*?):\*\*(.*?)(?=\*\*|$)'
    matches = re.findall(field_pattern, raw_response, re.DOTALL)
    
    for field, value in matches:
        extracted_data[field.strip()] = value.strip()
    
    # 处理标题
    if 'Title (Titolo)' in extracted_data:
        title = extracted_data['Title (Titolo)']
        if brand not in title:
            title = f"{brand} {title}"
        if style_number not in title:
            title = f"{title} {style_number}"
        if size_info and size_info not in title:
            title = f"{title}, {size_info}"
        extracted_data['Title (Titolo)'] = title[:80]  # 限制标题长度为80个字符
    
    # 为所有模板中的字段设置默认值
    for field in template:
        if field not in extracted_data:
            extracted_data[field] = 'N/A'
    
    return extracted_data

def process_product(product_type, brand, style_number, additional_info, size_info, internal_reference, max_retries=2):
    logging.info(f"Processing: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}', Additional Info: '{additional_info}', Size Info: '{size_info}'")

    if not product_type:
        logging.warning(f"Skipping row due to empty product type")
        return None

    sheet_name = get_sheet_name(product_type)
    template, _ = get_template(product_type)
    if not template:
        logging.warning(f"Skipping row due to missing template for product type: {product_type}")
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
        **Short Description (Breve Descrizione):** [Your brief summary here]
        **Description (Descrizione):** [Your detailed description here]

        Then, provide information for the following fields:

        **Object Category (Categoria Oggetto):**
        **Store Category (Categoria del Negozio):**
        **Brand (Marca):**
        **Cut (Taglia):**
        **Department (Reparto):**
        **Type (Tipo):**
        **Style (Stile):**
        **Condition of the Item (Condizione dell'oggetto):**
        **Price (Prezzo):**
        **Shipping Rule (Regola sulla spedizione):**
        **MPN (MPN):**
        **Custom Label (Etichetta personalizzata - SKU):**
        **EAN (EAN):**
        **Material (Materiale):**
        **Color (Colore):**
        **Tissue (Tessuto):**
        **Size Type (Tipo di taglia):**
        **Fit (Vestibilità):**
        **Sleeve Length (Lunghezza della manica):**
        **Unit of Measurement (Unità di misura):**
        **Character (Personaggio):**
        **Season (Stagione):**
        **Vintage (Vintage):**
        **Neckline (Scollatura):**
        **Theme (Tema):**
        **Activity (Attività):**
        **Decorative Elements (Elementi decorativi):**
        **Characteristics (Caratteristiche):**
        **Occasion (Occasione):**
        **Knitting Style (Stile lavorazione a maglia):**
        **Graphic Printing (Stampa grafica):**
        **Garment Care (Cura dell'indumento):**
        **Country of Manufacture (Paese di fabbricazione):**
        **Fabric Type (Tipo di tessuto):**
        **Personalized (Personalizzato):**
        **Year Manufactured (Anno di fabbricazione):**
        **Handmade (Fatto a mano):**
        **Pattern (Fantasia):**
        **Closure Type (Tipo di chiusura):**
        **Accents (Dettagli decorativi):**
        **Product Line (Linea di prodotto):**

        If you don't have information for a field, use 'N/A'.
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

        combined_response = f"{description_response}\n\n{fields_response}"
        template, _ = get_template(product_type)
        extracted_data = extract_fields_from_response(combined_response, template, brand, style_number, size_info)
        
        # 添加内部引用和样式编号
        extracted_data['Internal Reference'] = internal_reference
        extracted_data['Style Number'] = style_number
        
        return get_sheet_name(product_type), extracted_data

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

def get_sheet_id(sheet_name):
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in sheet_metadata.get('sheets', ''):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None

def get_column_indices(headers):
    column_indices = {}
    for index, header in enumerate(headers):
        clean_header = header.strip().lower()
        if 'internal reference' in clean_header:
            column_indices['Internal Reference'] = index
        elif 'product category' in clean_header:
            column_indices['Product Category'] = index
        elif 'product type' in clean_header:
            column_indices['Product Type'] = index
        elif 'brand' in clean_header:
            column_indices['Brand'] = index
        elif 'style number' in clean_header:
            column_indices['Style Number'] = index
        elif 'additional info' in clean_header:
            column_indices['Additional Info'] = index
        # 可以继续添加其他需要的列
    return column_indices

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # 读取表头
    headers = read_spreadsheet('Sheet1!A1:ZZ1')[0]
    logging.info(f"Headers: {headers}")
    
    # 动态获取列索引
    column_indices = get_column_indices(headers)
    logging.info(f"Column indices: {column_indices}")
    
    # 读取数据
    all_data = read_spreadsheet('Sheet1!A2:ZZ')
    
    logging.info(f"Read {len(all_data)} rows of data")
    
    if len(all_data) == 0:
        logging.error("No data found in spreadsheet.")
        return

    # Store data for each sheet
    sheet_data = {}
    
    for row in all_data:
        internal_reference = row[column_indices.get('Internal Reference', -1)].strip() if column_indices.get('Internal Reference', -1) < len(row) else ""
        product_category = row[column_indices.get('Product Category', -1)].strip() if column_indices.get('Product Category', -1) < len(row) else ""
        product_type = row[column_indices.get('Product Type', -1)].strip() if column_indices.get('Product Type', -1) < len(row) else ""
        brand = row[column_indices.get('Brand', -1)].strip() if column_indices.get('Brand', -1) < len(row) else ""
        style_number = row[column_indices.get('Style Number', -1)].strip() if column_indices.get('Style Number', -1) < len(row) else ""
        add_info = row[column_indices.get('Additional Info', -1)].strip() if column_indices.get('Additional Info', -1) < len(row) else ""
        
        # 假设尺寸信息在 'Additional Info' 列之后的所有列
        size_info = " ".join([cell.strip() for cell in row[column_indices.get('Additional Info', -1)+1:] if cell.strip()])
        
        if not all([product_type, brand, style_number]):
            logging.warning(f"Skipping row due to missing mandatory data: Product Type: '{product_type}', Brand: '{brand}', Style Number: '{style_number}'")
            continue
        
        result = process_product(product_type, brand, style_number, add_info, size_info, internal_reference)
        if result:
            sheet_name, raw_extracted_data = result
            template, _ = get_template(product_type)
            # 使用新的 extract_fields_from_response 函数
            extracted_data = extract_fields_from_response(raw_extracted_data, template, brand, style_number, size_info)
            if sheet_name not in sheet_data:
                sheet_data[sheet_name] = []
            sheet_data[sheet_name].append(extracted_data)

    # Write data to respective sheets
    for sheet_name, data in sheet_data.items():
        try:
            if ensure_sheet_exists(sheet_name):
                # 获取工作表的字段名（第一行）
                field_names = sheets_service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID, range=f"'{sheet_name}'!A1:ZZ1").execute().get('values', [[]])[0]

                logging.info(f"Sheet field names: {field_names}")
                logging.info(f"Extracted data keys: {list(data[0].keys())}")

                # 准备要写入的数据
                rows_to_write = []
                for item in data:
                    row = [''] * len(field_names)  # 初始化一个空行，长度与字段名数量相同
                    
                    # 填入所有字段
                    for i, field in enumerate(field_names):
                        if field == 'MPN (MPN)':
                            row[i] = item.get('Style Number', 'N/A')
                        elif field == 'Custom Label (Etichetta personalizzata - SKU)':
                            row[i] = item.get('Internal Reference', 'N/A')
                        else:
                            row[i] = item.get(field, 'N/A')
                    
                    rows_to_write.append(row)
                    logging.info(f"Prepared row: {row[:10]}...")  # 只记录前10个字段

                # 获取当前工作表的行数
                sheet_info = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=[f"'{sheet_name}'"], includeGridData=True).execute()
                current_row = len(sheet_info['sheets'][0]['data'][0]['rowData']) + 1

                # 清除要写入范围的格式
                clear_range_format(sheet_name, current_row, current_row + len(rows_to_write))

                # 写入数据
                range_name = f"'{sheet_name}'!A{current_row}"
                write_to_spreadsheet(range_name, rows_to_write)
                
                # 验证写入的数据
                verify_written_data(sheet_name, current_row, len(rows_to_write))
                
                logging.info(f"Successfully wrote and verified {len(rows_to_write)} rows to sheet '{sheet_name}'")
            else:
                logging.error(f"Unable to ensure '{sheet_name}' sheet exists. Skipping write operation.")
        except Exception as e:
            logging.error(f"Error writing to sheet '{sheet_name}': {str(e)}")

if __name__ == '__main__':
    main()
