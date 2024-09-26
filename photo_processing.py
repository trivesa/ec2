from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import vision
from PIL import Image, ImageStat
import io
import os

# Set environment variable for Google credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"

# Initialize clients
vision_client = vision.ImageAnnotatorClient()
drive_service = build('drive', 'v3')
sheets_service = build('sheets', 'v4')

# Define IDs
spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
sheet_name = 'Sheet1'
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'

def is_black_photo(image):
    grayscale_image = image.convert('L')
    brightness = ImageStat.Stat(grayscale_image).mean[0]
    return brightness < 10

def insert_text_data(extracted_text):
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!B:B'
        ).execute()
        next_row = len(result.get('values', [])) + 1
        body = {'values': [[extracted_text]]}
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!B{next_row}',
            valueInputOption='RAW',
            body=body
        ).execute()
        print(f"Inserted text at row {next_row}")
    except Exception as e:
        print(f"Error inserting text: {e}")

# Get image files
results = drive_service.files().list(
    q=f"'{folder_id}' in parents and mimeType='image/jpeg'",
    fields="files(id, name)"
).execute()
files = sorted(results.get('files', []), key=lambda x: x['name'])

black_photo_found = False

for file in files:
    print(f"Processing file: {file['name']}")
    request = drive_service.files().get_media(fileId=file['id'])
    image_file = io.BytesIO()
    downloader = MediaIoBaseDownload(image_file, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    image_file.seek(0)
    pil_image = Image.open(image_file)

    if not black_photo_found:
        if is_black_photo(pil_image):
            black_photo_found = True
            print(f"Found black photo: {file['name']}")
        continue

    if black_photo_found:
        print(f"Found label photo: {file['name']}")
        image_file.seek(0)
        vision_image = vision.Image(content=image_file.read())
        response = vision_client.text_detection(image=vision_image)
        texts = response.text_annotations
        if texts:
            extracted_text = "\n".join([text.description for text in texts])
            insert_text_data(extracted_text)
        else:
            insert_text_data("No text detected.")
        black_photo_found = False

print("Processing complete.")

