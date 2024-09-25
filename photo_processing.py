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

# Replace with your actual folder ID containing the subfolder
folder_id = '1ABQ74hq28akUEV0BUOyue4ltztQA52PP'

# Get all JPEG images in the folder
results = drive_service.files().list(
    q=f"'{folder_id}' in parents and mimeType='image/jpeg'",
    fields="files(id, name)").execute()

files = results.get('files', [])

if not files:
    print("No files found in the folder or its subfolders.")
else:
    print("Files found in the folder or its subfolders:")

    # Sort the files by the numeric part in their names for correct sequence
    files = sorted(files, key=lambda x: int(x['name'][-9:-4]))  # Adjust the slice to match your file naming format

    for file in files:
        print(f"Checking file: {file['name']} (image/jpeg)")

    white_photo_found = False

    # Iterate over files to identify white photo and corresponding label photo
    for i in range(len(files)):
        current_file = files[i]
        
        # Load and download current image to check if it's a white photo
        request = drive_service.files().get_media(fileId=current_file['id'])
        image_file = io.BytesIO()
        downloader = MediaIoBaseDownload(image_file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}% complete for {current_file['name']}.")

        image_file.seek(0)

        # Check if current file is a white photo
        image = vision.Image(content=image_file.read())
        properties = vision_client.image_properties(image=image).image_properties_annotation

        # Check if image has a high percentage of white pixels (simple heuristic for white photo)
        white_pixel_threshold = 0.8
        white_ratio = sum([c.pixel_fraction for c in properties.dominant_colors.colors if c.color.red >= 240 and c.color.green >= 240 and c.color.blue >= 240])

        if white_ratio > white_pixel_threshold:
            print(f"Identified white photo: {current_file['name']} ({current_file['id']})")
            white_photo_found = True
            if i < len(files) - 1:
                label_file = files[i + 1]
                print(f"Identified label photo: {label_file['name']} ({label_file['id']})")

                # Download and analyze label photo
                request = drive_service.files().get_media(fileId=label_file['id'])
                image_file = io.BytesIO()
                downloader = MediaIoBaseDownload(image_file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}% complete.")

                image_file.seek(0)
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
            print(f"Skipping non-white photo: {current_file['name']}")

    if not white_photo_found:
        print("No white photo found in the folder.")
