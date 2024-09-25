from googleapiclient.discovery import build
from google.oauth2 import service_account
import os

# Set up Google Drive API credentials
SERVICE_ACCOUNT_FILE = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# Folder ID of the 'folder1' subfolder where the images are located
FOLDER_ID = "1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3"  # Your provided folder1 ID

# Print the folder ID to ensure it's correct
print(f"Using folder ID: {FOLDER_ID}")

# Authenticate and create the Google Drive API client
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

try:
    # List all files in the specified folder and any subfolders
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'image/'"
    results = service.files().list(q=query, fields="files(id, name, mimeType, parents)").execute()
    items = results.get('files', [])
    print(f"Raw response: {results}")  # Print the raw response for debugging
    if not items:
        print('No files found in the folder or its subfolders.')
    else:
        print('Files found in the folder or its subfolders:')
        for item in items:
            print(f"{item['name']} ({item['id']}) - Type: {item['mimeType']} - Parent Folder ID: {item['parents']}")
except Exception as e:
    print(f"Error accessing folder: {e}")
