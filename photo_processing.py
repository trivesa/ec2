from googleapiclient.discovery import build
from google.oauth2 import service_account
import os

# Path to your service account key file
SERVICE_ACCOUNT_FILE = '/home/ec2-user/google-credentials/product-information-automation-image-text.json'

# Define the scope for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

# Create credentials using the service account file
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Drive API client
drive_service = build('drive', 'v3', credentials=creds)

# Folder ID for 'folder1' in the shared drive
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'

# Check if the folder is accessible and get its metadata
try:
    folder_metadata = drive_service.files().get(fileId=folder_id, fields='id, name, mimeType, owners, permissions').execute()
    print(f"Folder '{folder_metadata['name']}' found and accessible.")
    print("Folder Metadata:")
    print(folder_metadata)
except Exception as e:
    print(f"Error accessing folder: {e}")

# List the files in the folder
results = drive_service.files().list(
    q=f"'{folder_id}' in parents",
    pageSize=100,
    fields="files(id, name, mimeType)").execute()
items = results.get('files', [])

if not items:
    print('No files found in the folder.')
else:
    print(f"Files found in folder {folder_id}:")
    for item in items:
        print(f" - {item['name']} (ID: {item['id']}, Type: {item['mimeType']})")

    # Sort files by the last 5 digits of the name
    sorted_items = sorted(items, key=lambda x: int(x['name'].split()[-1].split('.')[0]))

    # Find the white photo (first pure white background photo)
    white_photo = None
    for item in sorted_items:
        if 'white' in item['name'].lower():  # This is just a simple check. Replace with your own logic.
            white_photo = item
            break

    if white_photo:
        print(f"White photo found: {white_photo['name']} (ID: {white_photo['id']})")

        # Find the label photo next to the white photo
        white_photo_index = sorted_items.index(white_photo)
        if white_photo_index + 1 < len(sorted_items):
            label_photo = sorted_items[white_photo_index + 1]
            print(f"Label photo found: {label_photo['name']} (ID: {label_photo['id']})")
        else:
            print('No label photo found after the white photo.')
    else:
        print('No white photo found.')
