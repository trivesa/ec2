import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
from PIL import Image, ImageStat
import io
import os
import re
import numpy as np

# 从环境变量获取凭证
credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if not credentials_json:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")

# 解析 JSON 字符串
credentials_info = json.loads(credentials_json)

# 创建凭证对象
credentials = service_account.Credentials.from_service_account_info(credentials_info)

# 使用凭证创建客户端
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# Set up Google Drive API client
drive_service = build('drive', 'v3', credentials=credentials)

# Set up Google Sheets API client
sheets_service = build('sheets', 'v4', credentials=credentials)

# Define the Google Sheet ID and sheet name
spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'
sheet_name = 'Sheet1'
sheet_id = 2114301033  # This is the 'sheetId' from the URL of the specific tab in the Google Sheet

# Replace with the parent folder ID
parent_folder_id = '1A9k4cBKuiplG5XJpkzmN_6bl2Ighz-bf'

# Define the send_message_to_ui function
def send_message_to_ui(message, block_name):
    """
    Sends a message to a specific block in the user interface.
    This is a placeholder function. Implement the actual logic to send messages to your UI.
    """
    print(f"Message to {block_name}: {message}")

# Define the is_black_photo function
def is_black_photo(image, tolerance=10, black_pixel_ratio=0.95):
    """
    Determines if the given image is a pure black photo (#000000).
    
    :param image: PIL Image object
    :param tolerance: Allowed deviation from pure black (0-255)
    :return: Boolean indicating if the image is considered black
    """
    rgb_image = image.convert('RGB')
    np_image = np.array(rgb_image)
    black_pixels = np.all(np_image <= tolerance, axis=-1)
    return np.mean(black_pixels) >= black_pixel_ratio

# Function to insert data into Google Sheets
def insert_label_data(image_url, extracted_text):
    """
    Inserts label data into Google Sheets.
    :param image_url: URL of the label image to be inserted into the sheet.
    :param extracted_text: Extracted text from the label image.
    """
    try:
        # 检查是否已经处理过这个图片
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:A'
        ).execute()
        values = result.get('values', [])
        if any(image_url in row for row in values):
            print(f"Image {image_url} already processed. Skipping.")
            return

        # Find the next available row based on the "extracting processing status" column
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!AB:AB'
        ).execute()
        values = result.get('values', [])
        next_row = len(values) + 1
        
        # Check if the row is already marked as "processed"
        while next_row <= len(values) and values[next_row - 1][0] == 'processed':
            next_row += 1
        
        # Prepare the requests to insert the image, text, and update the status
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
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": next_row - 1,
                        "endRowIndex": next_row,
                        "startColumnIndex": 27,
                        "endColumnIndex": 28
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "stringValue": "processed"
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

def download_file(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    file.seek(0)
    return file

# Custom sorting function to extract and compare the last 5 digits of file names
def sort_by_dsc_number(file):
    # 使用正则表达式找到 DSC 后面的 5 位数字
    match = re.search(r'DSC(\d{5})', file['name'])
    if match:
        # 如果找到匹配的数字，返回该数字的整数值
        return int(match.group(1))
    else:
        # 如果没有找到匹配的数字，返回一个非常大的数，确保个文件在最后
        return float('inf')

# 主程序逻辑修改了
query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id)").execute()
latest_subfolder = results.get('files', [])[0]

results = drive_service.files().list(
    q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
    fields="files(id, name, mimeType)"
).execute()
files = results.get('files', [])

files_sorted = sorted(files, key=sort_by_dsc_number)

black_photo_found = False
last_black_photo = None
label_photo_processed = False

for file in files_sorted:
    print(f"Checking file: {file['name']} ({file['mimeType']})")

    image_file = download_file(file['id'])
    image_file.seek(0)
    pil_image = Image.open(image_file)

    if is_black_photo(pil_image):
        black_photo_found = True
        last_black_photo = file
        label_photo_processed = False
        print(f"Identified black photo: {file['name']} ({file['id']})")
    elif black_photo_found and not label_photo_processed:
        print(f"Processing label photo: {file['name']} ({file['id']})")
        
        vision_image = vision.Image(content=image_file.getvalue())
        response = vision_client.text_detection(image=vision_image, image_context={"language_hints": ["en"]})
        texts = response.text_annotations

        image_url = f'https://drive.google.com/uc?id={file["id"]}'

        if not texts:
            print("No text detected in the image.")
            extracted_text = "未检测到标签。请手动验证并输入产品信息。"
        else:
            extracted_text = clean_extracted_text(texts[0].description)
            print(f"Extracted text: {extracted_text}")

        send_message_to_ui(extracted_text, "extracted texts block")
        insert_label_data(image_url, extracted_text)

        label_photo_processed = True
        print(f"Processed label photo: {file['name']} ({file['id']})")
    else:
        print(f"Skipping file: {file['name']} ({file['id']})")

print("Processing complete.")

def clean_extracted_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and line not in cleaned_lines:
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)
