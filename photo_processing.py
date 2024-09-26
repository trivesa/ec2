from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
from PIL import Image, ImageStat
import io
import os

# Set up credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
credentials = service_account.Credentials.from_service_account_file(
    '/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json',
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)

# Google Sheets and Drive API clients
sheets_service = build('sheets', 'v4', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)
vision_client = vision.ImageAnnotatorClient()

# Google Sheet details
SPREADSHEET_ID = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'  # Replace with your Google Sheet ID
SHEET_NAME = 'Sheet1'

# Folder ID containing the images
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'  # Replace with your folder ID

# Define the send_message_to_ui function (placeholder)
def send_message_to_ui(message, block_name):
    print(f"Message to {block_name}: {message}")

# Define function to insert data into Google Sheets
def insert_label_data(image_url, extracted_text, row):
    try:
        # Insert image URL in Column A
        requests = [
            {
                "updateCells": {
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {"formulaValue": f'=IMAGE("{image_url}")'}
                                }
                            ]
                        }
                    ],
                    "fields": "userEnteredValue",
                    "start": {
                        "sheetId": 0,
                        "rowIndex": row - 1,
                        "columnIndex": 0
                    }
                }
            },
            # Insert text in Column B
            {
                "updateCells": {
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {"stringValue": extracted_text}
                                }
                            ]
                        }
                    ],
                    "fields": "userEnteredValue",
                    "start": {
                        "sheetId": 0,
                        "rowIndex": row - 1,
                        "columnIndex": 1
                    }
                }
            }
        ]
        body = {"requests": requests}
        sheets_service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        print(f"Data inserted successfully at row {row}.")
    except Exception as e:
        print(f"Error inserting data: {e}")

# Define the is_black_photo function
def is_black_photo(image):
    grayscale_image = image.convert('L')
    stat = ImageStat.Stat(grayscale_image)
    brightness = stat.mean[0]
    brightness_threshold = 10
    return brightness < brightness_threshold

# Fetch list of image files from Google Drive folder
results = drive_service.files().list(
    q=f"'{folder_id}' in parents and mimeType='image/jpeg'",
    fields="files(id, name, mimeType)"
).execute()
files = results.get('files', [])

# Sort files based on their name to ensure sequential processing
files_sorted = sorted(files, key=lambda x: x['name'])

black_photo_found = False
row = 1  # Starting row for Google Sheets

for file in files_sorted:
    print(f"Checking file: {file['name']} ({file['mimeType']})")

    request = drive_service.files().get_media(fileId=file['id'])
    image_file = io.BytesIO()
    downloader = MediaIoBaseDownload(image_file, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    image_file.seek(0)

    vision_image = vision.Image(content=image_file.read())
    image_file.seek(0)
    pil_image = Image.open(image_file)

    if not black_photo_found:
        if is_black_photo(pil_image):
            black_photo_found = True
            print(f"Identified black photo: {file['name']} ({file['id']})")
        continue

    if black_photo_found:
        print(f"Identified label photo: {file['name']} ({file['id']})")
        response = vision_client.text_detection(image=vision_image)
        texts = response.text_annotations

        if not texts:
            send_message_to_ui("No label detected. Manual validate and input product information.", "extracted texts block")
            print("No text detected in the image. Notification sent to UI.")
        else:
            extracted_text = "\n".join([text.description for text in texts])
            send_message_to_ui(extracted_text, "extracted texts block")

            # Insert data into Google Sheets
            image_url = f"https://drive.google.com/uc?id={file['id']}"
            insert_label_data(image_url, extracted_text, row)
            row += 1

        black_photo_found = False

print("Processing complete.")
