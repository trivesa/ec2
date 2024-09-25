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

# Folder ID containing the images
FOLDER_ID = '1ABQ74hq28akUEV0BUOyue4ltztQA52PP'  # Update this with the folder ID containing your images

# Fetch all files in the folder
results = drive_service.files().list(q=f"'{FOLDER_ID}' in parents", fields="files(id, name, mimeType)").execute()
files = results.get('files', [])

# Check if files were found
if not files:
    print("No files found in the folder or its subfolders.")
else:
    print(f"Files found in the folder or its subfolders:")
    white_photo = None
    label_photo = None

    # Find the white photo and label photo
    for file in files:
        print(f"Checking file: {file['name']} ({file['mimeType']})")
        if 'white' in file['name'].lower() and file['mimeType'].startswith('image/'):
            white_photo = file
            print(f"Identified white photo: {file['name']} ({file['id']})")
            break

    # Find the label photo which is next in sequence
    if white_photo:
        white_photo_number = int(white_photo['name'].split('.')[0][-5:])
        print(f"White photo sequence number: {white_photo_number}")
        
        for file in files:
            try:
                file_number = int(file['name'].split('.')[0][-5:])
                print(f"Checking potential label photo: {file['name']} with sequence number {file_number}")
                if file_number == white_photo_number + 1 and file['mimeType'].startswith('image/'):
                    label_photo = file
                    print(f"Identified label photo: {file['name']} ({file['id']})")
                    break
            except ValueError:
                print(f"Skipping file with invalid number format: {file['name']}")
                continue
    
    # If label photo is found, proceed to extract text
    if label_photo:
        file_id = label_photo['id']
        print(f"Processing label photo with ID: {file_id}")

        # Download the image content from Google Drive to memory
        request = drive_service.files().get_media(fileId=file_id)
        image_file = io.BytesIO()
        downloader = MediaIoBaseDownload(image_file, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}% complete.")

        # Move to the beginning of the BytesIO object to read the image
        image_file.seek(0)

        # Use the downloaded image content for Vision API text detection
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
    else:
        print("No label photo found after the white photo.")
