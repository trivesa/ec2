from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
import io
import os
from PIL import Image, ImageStat

# Set the path to the Google service account credentials JSON file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# Set up the Google Cloud Vision API client
vision_client = vision.ImageAnnotatorClient()

# Set up Google Drive API client
drive_service = build('drive', 'v3', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Replace with the file ID of the subfolder in Google Drive
folder_id = '1ABQ74hq28akUEV0BUOyue4ltztQA52PP'

# Function to download an image from Google Drive to memory
def download_image(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    image_file = io.BytesIO()
    downloader = MediaIoBaseDownload(image_file, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}% complete for {file_id}.")
    image_file.seek(0)
    return image_file

# Function to check if an image is a pure black photo
def is_pure_black(image):
    stat = ImageStat.Stat(image)
    # Check if the average pixel value is close to 0 for a pure black image
    return all(pixel < 10 for pixel in stat.mean)

# Retrieve files from the specified folder
results = drive_service.files().list(q=f"'{folder_id}' in parents and mimeType='image/jpeg'", fields="files(id, name)").execute()

files = results.get('files', [])
print("Files found in the folder or its subfolders:")
for file in files:
    print(f"Checking file: {file['name']} ({file['mimeType']})")

black_photo_found = False
label_photo_id = None

for file in sorted(files, key=lambda x: x['name']):
    file_id = file['id']
    file_name = file['name']

    # Download the image to memory
    image_file = download_image(file_id)
    image = Image.open(image_file)

    # Check if the current image is a pure black photo
    if not black_photo_found and is_pure_black(image):
        print(f"Identified black photo: {file_name} ({file_id})")
        black_photo_found = True
    elif black_photo_found:
        # This is the label photo following the black photo
        print(f"Identified label photo: {file_name} ({file_id})")
        label_photo_id = file_id
        break
    else:
        print(f"Skipping non-black photo: {file_name}")

# If a label photo was identified, extract the text
if label_photo_id:
    # Download and process the label photo
    label_image_file = download_image(label_photo_id)
    label_image = vision.Image(content=label_image_file.read())
    response = vision_client.text_detection(image=label_image)
    texts = response.text_annotations

    # Print extracted texts
    if not texts:
        print("No text detected in the image.")
    else:
        print("Detected text:")
        for text in texts:
            print(text.description)
else:
    print("No label photo found after the black photo.")
