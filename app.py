from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import vision
import os
import subprocess
import logging
import openai
import json  # Make sure this is imported for handling JSON

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

# Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# API clients setup
vision_client = vision.ImageAnnotatorClient()
drive_service = build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))
sheets_service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))
# Constants
SPREADSHEET_ID = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
SHEET_NAME = 'Sheet1'
SHEET_ID = 2114301033
PARENT_FOLDER_ID = '1A9k4cBKuiplG5XJpkzmN_6bl2Ighz-bf'

# Helper function to load template based on product type
def load_template(product_type):
    """Loads the appropriate product listing template based on product type."""
    try:
        with open(f'/home/ec2-user/templates/{product_type}_template.json', 'r') as file:
            template = json.load(file)
        return template
    except FileNotFoundError:
        logging.error(f"Template for {product_type} not found!")
        return None

# Helper function to sort files by the last 5 digits
def sort_by_last_5_digits(file):
    last_5_digits = file['name'][-9:-4]
    return int(last_5_digits)

# Google Sheets Integration
def update_google_sheet(sheet_name, row_data):
    """
    Updates the target sheet with the response data.
    """
    try:
        # Fetch the sheet by name
        sheet = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name + "!A1:AY1"
        ).execute()

        # Get the headers from the first row
        headers = sheet.get('values', [])[0]

        # Find the next empty row
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name
        ).execute()

        # Find the next available row for insertion
        rows = result.get('values', [])
        next_empty_row = len(rows) + 1

        # Prepare the row data
        new_row = []
        for header in headers:
            if header in row_data:
                new_row.append(row_data[header])
            else:
                new_row.append("")  # Empty if field is not present

        # Insert the new row into the sheet
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A{next_empty_row}:AY{next_empty_row}",
            valueInputOption="RAW",
            body={"values": [new_row]}
        ).execute()

        logging.info(f"Row inserted successfully into sheet: {sheet_name} at row {next_empty_row}")

    except Exception as e:
        logging.error(f"Error updating Google Sheet: {str(e)}")

# Route handler: Home route
@app.route('/')
def home():
    return "Flask application is running!"

# Route handler: Trigger script (related to Google Drive processing)
@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    try:
        logging.info("Triggering the script...")
        
        # Find the latest added subfolder
        query = f"'{PARENT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id)").execute()
        latest_subfolder = results.get('files', [])[0]
        logging.debug(f"Found latest subfolder: {latest_subfolder['id']}")

        # Fetch and sort image files
        results = drive_service.files().list(
            q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])
        files_sorted = sorted(files, key=sort_by_last_5_digits)
        logging.debug(f"Sorted files: {files_sorted}")

        # Process the files (implement your logic here)
        return jsonify({"message": "Processing completed successfully"}), 200
    except Exception as e:
        logging.error(f"Error triggering script: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Route handler: Run photo processing script
@app.route('/run-photo-processing', methods=['POST'])
def run_photo_processing():
    try:
        script_path = "/home/ec2-user/photo_processing.py"
        logging.info(f"Running photo processing script: {script_path}")
        
        result = subprocess.run(['python3', script_path], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logging.info(f"Script executed successfully: {result.stdout}")
            return jsonify({"message": "Script executed successfully", "output": result.stdout}), 200
        else:
            logging.error(f"Script execution failed: {result.stderr}")
            return jsonify({"error": "Script execution failed", "details": result.stderr}), 500
    except subprocess.TimeoutExpired:
        logging.error("Script execution timed out")
        return jsonify({"error": "Script execution timed out"}), 500
    except Exception as e:
        logging.error(f"Error during script execution: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Route handler: Generate product listing and send to Google Sheets
@app.route('/generate-listing', methods=['POST'])
def generate_listing():
    try:
        data = request.json
        # Ensure that the required fields are provided
        if not data or 'product_type' not in data or 'brand' not in data or 'style_number' not in data:
            logging.warning("Required fields (product_type, brand, style_number) are missing")
            return jsonify({'error': 'Required fields are missing'}), 400

        # Load the appropriate template based on product type
        product_type = data['product_type']
        brand = data['brand']
        style_number = data['style_number']

        template = load_template(product_type)
        if not template:
            return jsonify({'error': f'Template for product type {product_type} not found'}), 400

        # Fill in the template with the provided brand, product type, and style number
        title = template['title'].replace("[Brand]", brand).replace("[Product Type]", product_type)
        description = template['description'].replace("[Brand]", brand).replace("[Product Type]", product_type).replace("[Style Number]", style_number)

        prompt = f"{title}\n{description}\nMandatory Fields: {', '.join(template['mandatory_fields'])}\nOptional Fields: {', '.join(template['optional_fields'])}"

        logging.info(f"Generated prompt: {prompt}")

        # Send the filled-in prompt to OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an eBay fashion product listing expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        if 'choices' in response and len(response['choices']) > 0:
            listing_text = response['choices'][0]['message']['content'].strip()
            logging.info(f"Generated listing: {listing_text}")

            # Prepare row data for Google Sheets
            row_data = {
                "Title": listing_text,
                "Description": listing_text,
                "Brand": brand,
                "Style Number": style_number,
                "Product Type": product_type
            }

            # Determine which sheet to update
            sheet_name = determine_sheet_name(product_type)

            # Update Google Sheet with the response
            update_google_sheet(sheet_name, row_data)

            return jsonify({'listing': listing_text}), 200

        else:
            logging.error("No valid response from OpenAI")
            return jsonify({'error': 'No valid response from OpenAI'}), 500

    except Exception as e:
        logging.error(f"Error generating listing: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Helper function to determine the correct sheet based on product type
def determine_sheet_name(product_type):
    """
    Determines which sheet to update based on product type.
    """
    sheet_map = {
        'shoes': 'shoes',
        'bag': 'bag',
        'clothing': 'clothing',
        'belt': 'belt',
        'scarf': 'scarf',
        'watch': 'watch'
    }
    return sheet_map.get(product_type, 'other accessories')

# Flask app runner
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
