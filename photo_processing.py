from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
from PIL import Image, ImageStat
import io
import os

# Set the path to the Google service account credentials JSON file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# Set up the Google Cloud Vision API client
vision_client = vision.ImageAnnotatorClient()

# Set up Google Drive API client
drive_service = build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Replace with your actual subfolder ID from Google Drive
subfolder_id = '1ABQ74hq28akUEV0BUOyue4ltztQA52PP'

# Get the list of files in the subfolder
results = drive_service.files().list(
    q=f"'{subfolder_id}' in parents and mimeType='image/jpeg'",
    fields="files(id, name)").execute()

files = results.get('files', [])
if not files:
    print("No files found in the folder or its subfolders.")
    exit()

print("Files found in the folder or its subfolders:")

# Sort files by name to ensure sequential processing
files = sorted(files, key=lambda f: f['name'])

# Variables to track the black photo and its corresponding label photo
black_photo_found = False
processed_label_photos = set()  # To track already processed label photos

for file in files:
    file_id = file['id']
    file_name = file['name']

    # Print file being checked
    print(f"Checking file: {file_name} (image/jpeg)")

    # Download the file to memory for analysis
    request = drive_service.files().get_media(fileId=file_id)
    image_file = io.BytesIO()
    downloader = MediaIoBaseDownload(image_file, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    image_file.seek(0)
    print(f"Download 100% complete for {file_id}.")

    # Open image to check if it's black or not
    image = Image.open(image_file)
    stat = ImageStat.Stat(image)
    brightness = sum(stat.mean) / len(stat.mean)
    
    # If the image is detected as black
    if brightness < 10:  # Threshold for detecting black image (adjust as necessary)
        if not black_photo_found:
            black_photo_found = True
            print(f"Identified black photo: {file_name} ({file_id})")
        else:
            print(f"Skipping duplicate black photo: {file_name}")
    elif black_photo_found and file_name not in processed_label_photos:
        # This is the label photo corresponding to the previous black photo
        print(f"Identified label photo: {file_name} ({file_id})")

        # Process this label photo with Google Vision API
        image.seek(0)  # Reset the image file pointer
        content = image_file.read()
        vision_image = vision.Image(content=content)
        response = vision_client.text_detection(image=vision_image)
        texts = response.text_annotations

        # Print extracted texts
        if not texts:
            print("No text detected in the image.")
        else:
            print("Detected text:")
            for text in texts:
                print(text.description)

        # Mark this label photo as processed and reset the flag for next pair
        processed_label_photos.add(file_name)
        black_photo_found = False
