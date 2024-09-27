from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
from PIL import Image, ImageStat
import io
import os
import subprocess  # For running shell commands

app = Flask(__name__)

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
    # Assuming the last 5 digits are part of the filename before the extension
    last_5_digits = file['name'][-9:-4]  # Adjust the slicing if your file naming is different
    return int(last_5_digits)

# Replace with the parent folder ID
parent_folder_id = '1A9k4cBKuiplG5XJpkzmN_6bl2Ighz-bf'

@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    try:
        # Find the latest added subfolder within the parent folder
        query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id)").execute()
        latest_subfolder = results.get('files', [])[0]

        # Fetch list of image files from the latest subfolder
        results = drive_service.files().list(
            q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])

        # Sort files based on the last 5 digits of their names
        files_sorted = sorted(files, key=sort_by_last_5_digits)

        # Process the files (your existing logic here)
        # ...

        return jsonify({"message": "Processing completed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-photo-processing', methods=['POST'])
def run_photo_processing():
    try:
        # Replace this path with the actual path to your script
        script_path = "/home/ec2-user/photo_processing.py"
        
        # Run the photo_processing.py script using subprocess
        result = subprocess.run(['python3', script_path], capture_output=True, text=True)
        
        if result.returncode == 0:
            # If the script runs successfully, return the output
            return jsonify({"message": "Script executed successfully", "output": result.stdout}), 200
        else:
            # If there was an error running the script, return the error message
            return jsonify({"error": "Script execution failed", "details": result.stderr}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

