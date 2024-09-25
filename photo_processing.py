from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
import io
import os

# Set the path to the Google service account credentials JSON file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# Set up the Google Cloud Vision API client
vision_client = vision.ImageAnnotatorClient()

# Set up Google Drive API client
drive_service = build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Replace with the folder ID of the Google Drive subfolder
folder_id = 'YOUR_SUBFOLDER_ID'  # Replace with the actual folder ID

# Function to check if a photo is white (placeholder logic)
def is_white_photo(image_file):
    # Simplified check for a white photo by analyzing brightness
    # This is a placeholder function. You should implement a more robust logic here.
    return True  # Assume all photos are white for this placeholder

# Get the list of files in the subfolder
results = drive_service.files().list(q=f"'{folder_id}' in parents and mimeType='image/jpeg'", fields="files(id, name)").execute()
files = results.get('files', [])

if not files:
    print("No files found in the folder.")
else:
    # Sort files by the last 5 digits of the filename (sequence number)
    files_sorted = sorted(files, key=lambda x: int(x['name'][-9:-4]))

    white_photo_found = False
    for i, file in enumerate(files_sorted):
        file_name = file['name']
        file_id = file['id']

        # Download the file content for analysis
        request = drive_service.files().get_media(fileId=file_id)
        image_file = io.BytesIO()
        downloader = MediaIoBaseDownload(image_file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}% complete.")

        # Move to the beginning of the BytesIO object to read the image
        image_file.seek(0)

        # Determine if it's a white photo
        if is_white_photo(image_file) and not white_photo_found:
            print(f"Identified white photo: {file_name} ({file_id})")
            white_photo_found = True
        elif white_photo_found:
            # Process this as the label photo
            print(f"Identified label photo: {file_name} ({file_id})")

            # Use Vision API to extract text from the label photo
            image = vision.Image(content=image_file.read())
            response = vision_client.text_detection(image=image)
            texts = response.text_annotations

            # Print extracted texts
            if not texts:
                print("No text detected in the image.")
            else:
                print("Detected text:")
                for text in texts:
                    print(text.description)
            
            # Reset white_photo_found and move to next white photo
            white_photo_found = False
