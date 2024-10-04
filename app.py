from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import logging
import openai
import json  # For handling JSON

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

# Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# API clients setup
credentials = service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
sheets_service = build('sheets', 'v4', credentials=credentials)

# Google Spreadsheet ID
SPREADSHEET_ID = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'

# Tab IDs based on product type
SHEET_MAP = {
    "shoes": "shoes",
    "bag": "bag",
    "clothing": "clothing",
    "scarf": "scarf",
    "belt": "belt",
    "watch": "watch",
    "other accessories": "other accessories"
}

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

# Helper function to determine the correct sheet name based on product type
def determine_sheet_name(product_type):
    """
    Determines which sheet name to update based on product type.
    """
    return SHEET_MAP.get(product_type, 'other accessories')
# Google Sheets Integration: Update the target tab with response data
def update_google_sheet(sheet_name, row_data):
    """
    Updates the target tab (by sheet name) with the product listing data.
    """
    try:
        # Get the headers from the first row of the target sheet by name
        sheet_range = f"'{sheet_name}'!A1:AY1"
        sheet = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range
        ).execute()

        headers = sheet.get('values', [])[0]
        logging.info(f"Headers found in the sheet: {headers}")

        # Fetch all rows to find the next empty row
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{sheet_name}'"
        ).execute()

        rows = result.get('values', [])
        next_empty_row = len(rows) + 1  # Find the next available row
        logging.info(f"Next empty row: {next_empty_row}")

        # Prepare row data based on headers
        new_row = []
        for header in headers:
            header_lower = header.strip().lower()  # Normalize for matching
            if header_lower in row_data:
                new_row.append(row_data[header_lower])
            else:
                new_row.append("")  # Leave blank if no matching field in response

        logging.info(f"Row data to be inserted: {new_row}")

        # Insert the new row into the sheet by name
        insert_range = f"'{sheet_name}'!A{next_empty_row}:AY{next_empty_row}"
        response = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=insert_range,
            valueInputOption="RAW",
            body={"values": [new_row]}
        ).execute()

        logging.info(f"Row inserted successfully into sheet: {sheet_name} at row {next_empty_row}")
        logging.info(f"Response from Sheets API: {response}")

    except Exception as e:
        logging.error(f"Error updating Google Sheet: {str(e)}")



@app.route('/generate-listing', methods=['POST'])
def generate_listing():
    try:  # Start the try block

        # Get the request data
        data = request.json
        if not data or 'product_type' not in data or 'brand' not in data or 'style_number' not in data:
            logging.warning("Required fields (product_type, brand, style_number) are missing")
            return jsonify({'error': 'Required fields are missing'}), 400

        # Extract product details from the request
        product_type = data['product_type'].strip().lower()
        brand = data['brand']
        style_number = data['style_number']

        # Load the appropriate template based on product type
        template = load_template(product_type)
        if not template:
            return jsonify({'error': f'Template for product type {product_type} not found'}), 400

        # Fill in the template with the provided brand, product type, and style number
        title = template['title'].replace("[Brand]", brand).replace("[Product Type]", product_type)
        description = template['description'].replace("[Brand]", brand).replace("[Product Type]", product_type).replace("[Style Number]", style_number)

        # Create the final prompt to send to OpenAI
        prompt = f"{title}\n{description}\nMandatory Fields: {', '.join(template['mandatory_fields'])}\nOptional Fields: {', '.join(template['optional_fields'])}"

        logging.info(f"Generated prompt: {prompt}")

        # Send the prompt to OpenAI API
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

            # Prepare the row data for Google Sheets
            row_data = {
                "title": listing_text,
                "description": listing_text,
                "brand": brand,
                "style_number": style_number,
                "product_type": product_type
            }

            # Determine which sheet to update based on product type
            sheet_name = determine_sheet_name(product_type)

            # Update Google Sheets with the generated listing
            update_google_sheet(sheet_name, row_data)

            return jsonify({'listing': listing_text}), 200

        else:
            logging.error("No valid response from OpenAI")
            return jsonify({'error': 'No valid response from OpenAI'}), 500

    except Exception as e:  # Add the exception handling block here
        logging.error(f"Error generating listing: {str(e)}")
        return jsonify({'error': str(e)}), 500  # Return a JSON error response
# Route handler: Trigger script (related to Google Drive processing)
@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    try:
        logging.info("Triggering the script...")

        # Find the latest added subfolder in Google Drive
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
        files_sorted = sorted(files, key=lambda file: file['name'][-9:-4])
        logging.debug(f"Sorted files: {files_sorted}")

        # Process the files (implement your logic here)
        return jsonify({"message": "Processing completed successfully"}), 200
    except Exception as e:
        logging.error(f"Error triggering script: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Route handler: Trigger script (related to Google Drive processing)
@app.route('/trigger-google-drive-script', methods=['POST'])  # Changed endpoint to avoid conflict
def trigger_google_drive_script():
    try:
        logging.info("Triggering the Google Drive script...")

        # Find the latest added subfolder in Google Drive
        query = f"'{PARENT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id, name)").execute()
        latest_subfolder = results.get('files', [])[0] if results.get('files') else None

        if not latest_subfolder:
            logging.error("No subfolder found in the Google Drive folder")
            return jsonify({"error": "No subfolder found"}), 404

        logging.debug(f"Found latest subfolder: {latest_subfolder['id']}")

        # Fetch and sort image files in the subfolder
        results = drive_service.files().list(
            q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])
        files_sorted = sorted(files, key=lambda file: file['name'][-9:-4])
        logging.debug(f"Sorted files: {files_sorted}")

        # Process the files (you can add your image processing logic here)
        return jsonify({"message": "Processing completed successfully", "files_processed": len(files_sorted)}), 200

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


# Flask app runner
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

