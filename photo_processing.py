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
    # List files in the specified folder
    results = service.files().list(q=f"'{FOLDER_ID}' in parents", pageSize=10, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        print('No files found in the folder.')
    else:
        print('Files in the folder:')
        for item in items:
            print(f"{item['name']} ({item['id']})")
except Exception as e:
    print(f"Error accessing folder: {e}")
