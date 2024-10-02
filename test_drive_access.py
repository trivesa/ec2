from googleapiclient.discovery import build
from google.oauth2 import service_account

# Path to your service account key file
SERVICE_ACCOUNT_FILE = '/home/ec2-user/google-credentials/product-information-automation-image-text.json'

# Define the scope for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

# Create credentials using the service account file
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Drive API client
drive_service = build('drive', 'v3', credentials=creds)

# Folder ID for 'folder1' in the shared drive (Replace with actual ID)
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'

# Try to access the folder metadata
try:
    folder_metadata = drive_service.files().get(fileId=folder_id, fields='id, name').execute()
    print(f"Access granted to folder: '{folder_metadata['name']}' (ID: {folder_metadata['id']})")
except Exception as e:
    print(f"Access error: {e}")

# List the files in the folder
try:
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        pageSize=10,
        fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found in the folder.')
    else:
        print('Files found in folder:')
        for item in items:
            print(f" - {item['name']} (ID: {item['id']})")
except Exception as e:
    print(f"Error listing files: {e}")
