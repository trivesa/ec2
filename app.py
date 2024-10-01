from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import vision
import os
import subprocess
import logging
import openai

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

# Helper functions
def sort_by_last_5_digits(file):
    last_5_digits = file['name'][-9:-4]
    return int(last_5_digits)

# Route handlers
@app.route('/')
def home():
    return "Flask application is running!"

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

@app.route('/generate-listing', methods=['POST'])
def generate_listing():
    try:
        data = request.json
        if not data or 'prompt' not in data:
            logging.warning("No prompt provided")
            return jsonify({'error': 'No prompt provided'}), 400

        prompt = data['prompt']
        logging.info(f"Received prompt: {prompt}")

        response = openai.ChatCompletion.create(
            model="gpt-4o",
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
            return jsonify({'listing': listing_text})
        else:
            logging.error("No valid response from OpenAI")
            return jsonify({'error': 'No valid response from OpenAI'}), 500

    except Exception as e:
        logging.error(f"Error generating listing: {str(e)}")
        logging.error(f"Full error details: {repr(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
