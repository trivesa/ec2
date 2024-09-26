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

# Set up Google Sheets API client
sheets_service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Define the Google Sheet ID and sheet name
spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
sheet_name = 'Sheet1'
sheet_id = 2114301033  # This is the 'sheetId' from the URL of the specific tab in the Google Sheet

# Replace with the folder ID containing your images
folder_id = '1AAUkLJYB7atxv1gDPv_DYH10GkTXhdy3'  # Update this with your specific folder ID

# Define the send_message_to_ui function
def send_message_to_ui(message, block_name):
    """
    Sends a message to a specific block in the user interface.
    This is a placeholder function. Implement the actual logic to send messages to your UI.
    """
    print(f"Message to {block_name}: {message}")

# Define the is_black_photo function
def is_black_photo(image):
    """
    Determines if the given image is a black photo.
    This function calculates the average brightness of the image and
    considers it a black photo if the brightness is below a certain threshold.
    """
    grayscale_image = image.convert('L')
    stat = ImageStat.Stat(grayscale_image)
    brightness = stat.mean[0]
    brightness_threshold = 10  # Adjust this value based on your images
    return brightness < brightness_threshold

# Function to insert data into Google Sheets
def insert_label_data(image_url, extracted_text):
    """
    Inserts label data into Google Sheets.
    :param image_url: URL of the label image to be inserted into the sheet.
    :param extracted_text: Extracted text from the label image.
    """
    try:
        # Find the next empty row in the sheet
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:A'
        ).execute()
        values = result.get('values', [])
        next_row = len(values) + 1

        # Prepare the requests to insert the image and text
        requests = [
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": next_row - 1,
                        "endRowIndex": next_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "formulaValue": f'=IMAGE("{image_url}", 1)'
                                    },
                                    "userEnteredFormat": {
                                        "wrapStrategy": "WRAP"
                                    }
                                }
                            ]
                        }
                    ],
                    "fields": "*"
                }
            },
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": next_row - 1,
                        "endRowIndex": next_row,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "stringValue": extracted_text
                                    },
                                    "userEnteredFormat": {
                                        "wrapStrategy": "WRAP"
                                    }
                                }
                            ]
                        }
                    ],
                    "fields": "*"
                }
            },
            # Set column width for columns A and B
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 2
                    },
                    "properties": {
                        "pixelSize": 350
                    },
                    "fields": "pixelSize"
                }
            },
            # Set row height for the new row
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": next_row - 1,
                        "endIndex": next_row
                    },
                    "properties": {
                        "pixelSize": 350
                    },
                    "fields": "pixelSize"
                }
            }
        ]

        # Execute the batch update request
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()
        print(f"Data successfully inserted into Google Sheets for image {image_url}")
    except Exception as e:
        print(f"Error inserting data: {e}")

# Custom sorting function to extract and compare the last 5 digits of file names
def sort_by_last_5_digits(file):
    last_5_digits = file['name'][-9:-4]
    return int(last_5_digits)

# Fetch list of image files from Google Drive folder
results = drive_service.files().list(
    q=f"'{folder_id}' in parents and mimeType='image/jpeg'",
    fields="files(id, name, mimeType)"
).execute()
files = results.get('files', [])

# Sort files based on the last 5 digits of their names
files_sorted = sorted(files, key=sort_by_last_5_digits)

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

    # If we have a black photo, find the label photo with the closest sequence number
    if black_photo_found:
        current_sequence_number = int(file['name'][-9:-4])
        last_black_photo_sequence_number = int(last_black_photo['name'][-9:-4])

        if current_sequence_number > last_black_photo_sequence_number:
            print(f"Identified label photo: {file['name']} ({file['id']})")

            # Call Vision API to detect text in the label photo
            response = vision_client.text_detection(image=vision_image)
            texts = response.text_annotations

            # Construct Google Drive image URL
            image_url = f'https://drive.google.com/uc?id={file["id"]}'

            # Check if any text was detected
            if not texts:
                # No text detected, send a message to the UI and Sheets
                send_message_to_ui("No label detected. Manual validate and input product information.", "extracted texts block")
                insert_label_data(image_url, "No label detected. Manual validate and input product information.")
                print("No text detected in the image. Notification sent to UI and Sheets.")
            else:
                # Text detected, construct the text layout and send it to the UI and Sheets
                extracted_text = "\n".join([text.description for text in texts])
                send_message_to_ui(extracted_text, "extracted texts block")
                insert_label_data(image_url, extracted_text)

            # Reset flag and last_black_photo to look for the next black photo
            black_photo_found = False
            last_black_photo = None
            print(f"Processed label photo: {file['name']} ({file['id']})")

print("Processing complete.")
