from googleapiclient.discovery import build
from google.oauth2 import service_account
import os

# Set up Google Drive API credentials
SERVICE_ACCOUNT_FILE = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# Print a test message to ensure the script is running
print("Testing Google Drive access...")

# Authenticate and create the Google Drive API client
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

try:
    # List all files in the root of Google Drive
    results = service.files().list(pageSize=20, fields="files(id, name, mimeType, parents)").execute()
    items = results.get('files', [])
    print(f"Raw response: {results}")  # Print the raw response for debugging
    if not items:
        print('No files found in your Google Drive.')
    else:
        print('Files found in your Google Drive:')
        for item in items:
            print(f"{item['name']} ({item['id']}) - Type: {item['mimeType']} - Parent Folder ID: {item['parents']}")
except Exception as e:
    print(f"Error accessing Google Drive: {e}")
