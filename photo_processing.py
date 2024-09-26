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

# Replace with the folder ID containing your images
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'

# Define the send_message_to_ui function
def send_message_to_ui(message, block_name):
    """
    Sends a message to a specific block in the user interface.
    This is a placeholder function. Implement the actual logic to send messages to your UI.
    """
    # Example placeholder print statement (replace with actual UI communication logic)
    print(f"Message to {block_name}: {message}")

# Define the is_black_photo function here
def is_black_photo(image):
    """
    Determines if the given image is a black photo.
    This function calculates the average brightness of the image and 
    considers it a black photo if the brightness is below a certain threshold.
    """
    # Convert the image to grayscale
    grayscale_image = image.convert('L')
    # Calculate the average brightness of the image
    stat = ImageStat.Stat(grayscale_image)
    brightness = stat.mean[0]
    
    # Define a threshold below which the image is considered black
    brightness_threshold = 10  # Adjust this value based on your images
    
    # Return True if the image is mostly black, False otherwise
    return brightness < brightness_threshold

# Fetch list of image files from Google Drive folder
results = drive_service.files().list(
    q=f"'{folder_id}' in parents and mimeType='image/jpeg'",
    fields="files(id, name, mimeType)"
).execute()
files = results.get('files', [])

# Sort files based on their name to ensure sequential processing
files_sorted = sorted(files, key=lambda x: x['name'])

# Variables to track the black and label photos
black_photo_found = False
last_black_photo = None

# Loop through all files to identify and process label photos
for file in files_sorted:
    print(f"Checking file: {file['name']} ({file['mimeType']})")
    
    # Download the image content
    request = drive_service.files().get_media(fileId=file['id'])
    image_file = io.BytesIO()
    downloader = MediaIoBaseDownload(image_file, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    image_file.seek(0)

    # Load the image for vision processing
    vision_image = vision.Image(content=image_file.read())

    # Load the image for PIL processing
    image_file.seek(0)
    pil_image = Image.open(image_file)

    # Check if the current photo is a black photo
    if not black_photo_found:
        if is_black_photo(pil_image):
            black_photo_found = True
            last_black_photo = file
            print(f"Identified black photo: {file['name']} ({file['id']})")
        continue
    
    # If we have a black photo, this file is the corresponding label photo
    if black_photo_found:
        print(f"Identified label photo: {file['name']} ({file['id']})")
        
        # Call Vision API to detect text in the label photo
        response = vision_client.text_detection(image=vision_image)
        texts = response.text_annotations
        
        # Check if any text was detected
        if not texts:
            # No text detected, send a message to the UI
            send_message_to_ui("No label detected. Manual validate and input product information.", "extracted texts block")
            print("No text detected in the image. Notification sent to UI.")
        else:
            # Text detected, print it out or send it to the UI
            print("Detected text:")
            for text in texts:
                print(text.description)
                send_message_to_ui(text.description, "extracted texts block")
        
        # Reset flag to look for the next black photo
        black_photo_found = False

print("Processing complete.")

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Set up the Google Sheets API client using the existing JSON file
credentials = service_account.Credentials.from_service_account_file(
    '/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json',
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheets_service = build('sheets', 'v4', credentials=credentials)


# Google Sheets Document ID
spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'

# Function to send data to Google Sheet
def send_data_to_sheet(image_url, extracted_texts):
    sheet_range = 'Sheet1!A:B'
    values = [[image_url, extracted_texts]]
    body = {'values': values}
    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

