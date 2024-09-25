print(f"Using folder ID: {FOLDER_ID}")
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up Google Drive API credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# Define the folder ID of the photo_processing folder
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'  # Replace with your actual folder ID

# Authenticate and create the Google Drive API client
try:
    service = build('drive', 'v3')
except Exception as e:
    print(f"Error creating Drive service: {e}")
    exit()

# Function to list files in the specified folder
def list_files_in_folder(folder_id):
    try:
        # Search for files in the specified folder
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name)"
        ).execute()
        items = results.get('files', [])
        if not items:
            print('No files found in the folder.')
        else:
            print('Files in the folder:')
            for item in items:
                print(f"{item['name']} ({item['id']})")
    except HttpError as error:
        print(f"Error accessing folder: {error}")
        print('No files found in the folder.')

# Run the function to list files in the specified folder
list_files_in_folder(folder_id)
