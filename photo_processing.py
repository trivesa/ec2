from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import re
from google.cloud import vision
from google.cloud.vision_v1 import types

# Set up Google Drive API credentials
SERVICE_ACCOUNT_FILE = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# New folder ID of the subfolder containing images
FOLDER_ID = "1ABQ74hq28akUEV0BUOyue4ltztQA52PP"  # Updated with your provided folder ID

# Print the folder ID to ensure it's correct
print(f"Using folder ID: {FOLDER_ID}")

# Authenticate and create the Google Drive API client
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Set up Google Vision API client
vision_client = vision.ImageAnnotatorClient(credentials=creds)

def extract_text_from_image(file_id):
    """Extracts text from an image file stored in Google Drive using Google Vision API."""
    try:
        # Get the image file content from Google Drive
        file = drive_service.files().get_media(fileId=file_id).execute()
        
        # Construct the image object for Vision API
        image = types.Image(content=file)
        
        # Perform text detection on the image
        response = vision_client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            print("Extracted text from the label photo:")
            for text in texts:
                print(f"Text: {text.description}")
            return texts[0].description  # Return the full extracted text
        else:
            print("No text found in the image.")
            return None
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return None

try:
    # List all image files in the specified folder
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'image/'"
    results = drive_service.files().list(q=query, fields="files(id, name, mimeType, parents)").execute()
    items = results.get('files', [])
    
    # Print the raw response for debugging
    print(f"Raw response: {results}")
    
    if not items:
        print('No files found in the folder or its subfolders.')
    else:
        print('Files in the folder or its subfolders:')
        # Sort the items based on the last part of the file name assuming it's a sequence number
        items.sort(key=lambda x: int(re.findall(r'\d+', x['name'])[-1]))
        
        # Identify the white photo (assumed to be the first photo)
        white_photo = items[0]
        print(f"Identified white photo: {white_photo['name']} ({white_photo['id']})")

        # Identify the next photo in sequence as the label photo
        if len(items) > 1:
            label_photo = items[1]
            print(f"Identified label photo: {label_photo['name']} ({label_photo['id']})")
            
            # Extract text from the identified label photo
            label_text = extract_text_from_image(label_photo['id'])
            
            if label_text:
                print(f"\nExtracted Text: {label_text}")
            else:
                print("No text extracted from the label photo.")
        else:
            print("No label photo found after the white photo.")

except Exception as e:
    print(f"Error accessing folder: {e}")
