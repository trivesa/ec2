from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import vision
from PIL import Image, ImageStat
import io
import os
import subprocess  # For running shell commands
import logging  # For logging
import openai  # For OpenAI API

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

# Set the OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Set the path to the Google service account credentials JSON file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# Set up the Google Cloud Vision API client
vision_client = vision.ImageAnnotatorClient()

# Set up Google Drive API client
drive_service = build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Set up Google Sheets API client
sheets_service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Define the Google Sheet ID and sheet name
spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
sheet_name = 'Sheet1'
sheet_id = 2114301033

def sort_by_last_5_digits(file):
    """
    Custom sorting function to extract and compare the last 5 digits of file names.
    """
    last_5_digits = file['name'][-9:-4]
    return int(last_5_digits)

# Replace with the parent folder ID
parent_folder_id = '1A9k4cBKuiplG5XJpkzmN_6bl2Ighz-bf'

@app.route('/')
def home():
    return "Flask application is running!"

@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    try:
        logging.info("Triggering the script...")
        
        # Find the latest added subfolder within the parent folder
        query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id)").execute()
        latest_subfolder = results.get('files', [])[0]
        logging.debug(f"Found latest subfolder: {latest_subfolder['id']}")

        # Fetch list of image files from the latest subfolder
        results = drive_service.files().list(
            q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])
        logging.debug(f"Found files: {files}")

        # Sort files based on the last 5 digits of their names
        files_sorted = sorted(files, key=sort_by_last_5_digits)
        logging.debug(f"Sorted files: {files_sorted}")

        # Process the files (your existing logic here)

        return jsonify({"message": "Processing completed successfully"}), 200
    except Exception as e:
        logging.error(f"Error triggering script: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/run-photo-processing', methods=['POST'])
def run_photo_processing():
    try:
        script_path = "/home/ec2-user/photo_processing.py"
        logging.info(f"Running photo processing script: {script_path}")
        
        # Run the photo_processing.py script using subprocess with a timeout
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

@app.route('/generate-listing', methods=['POST'])
def generate_listing():
    try:
        data = request.json  # Get the data sent from Google Sheets
        # Validate required fields
        if not data or not all(key in data for key in ['brand', 'product_category', 'product_type', 'style_number']):
            logging.warning("Insufficient product details provided")
            return jsonify({'error': 'Insufficient product details provided'}), 400

        # Extract product details from request
        brand = data.get("brand", "Unknown Brand")
        product_category = data.get("product_category", "Unknown Category")
        product_type = data.get("product_type", "Unknown Type")
        style_number = data.get("style_number", "Unknown Style Number")

        # Define the prompt for OpenAI
        prompt = f"""
        You are an eBay fashion product listing expert. Use the following details for the listing:
        Brand: "{brand}"
        Product Category: "{product_category}"
        Product Type: "{product_type}"
        Style Number: "{style_number}"

        Information Retrieval:
        Please search for the product's information using the brand's official website as the primary source. 
        If the required information is not available on the official website, use the following websites as secondary sources:
        1. Net-A-Porter
        2. Mytheresa
        3. Flannels
        4. Moda Operandi

        If you still cannot find the required information, use other reliable fashion retail websites or sources. 
        If any mandatory field information is unavailable after all attempts, indicate "N/A".

        Fashion Product Listing Part 1: Mandatory and Optional Fields

        Mandatory Fields:
        1. Object Category (Categoria Oggetto) 
        2. Store Category (Categoria del Negozio)
        3. Brand (Marca) 
        4. Size (Numero di scarpa EU) 
        5. Department (Reparto) 
        6. Color (Colore) 
        7. Type (Tipo) 
        8. Style (Stile) 
        9. Condition of the Item (Condizione dell'oggetto) 
        10. Price (Prezzo) 
        11. Shipping Rule (Regola sulla spedizione)

        Optional Fields:
        1. MPN (MPN) 
        2. Custom Label (Etichetta personalizzata - SKU) 
        3. EAN (EAN) 
        4. Material (Materiale della tomaia) 
        5. Sole Material (Materiale della suola) 
        6. Lining Material (Materiale della fodera)
        """

        # Send the prompt to the OpenAI API (using OpenAI Completion API)
        response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are an eBay fashion product listing expert."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=1000,
    temperature=0.7
)

        # Validate OpenAI response
        if 'choices' in response and len(response['choices']) > 0:
            listing_text = response['choices'][0]['text'].strip()
        else:
            logging.error("No valid response from OpenAI")
            return jsonify({'error': 'No valid response from OpenAI'}), 500

        logging.info(f"Generated listing: {listing_text}")
        return jsonify({'listing': listing_text})

    except Exception as e:
        logging.error(f"Error generating listing: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
