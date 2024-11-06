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

# 所有函数定义

def send_message_to_ui(message, block_name):
    print(f"Message to {block_name}: {message}")

def is_black_photo(image, tolerance=10, black_pixel_ratio=0.95):
    rgb_image = image.convert('RGB')
    np_image = np.array(rgb_image)
    black_pixels = np.all(np_image <= tolerance, axis=-1)
    return np.mean(black_pixels) >= black_pixel_ratio

def insert_label_data(image_url, extracted_text):
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

        # 准备要插入的数据
        row_data = [
            image_url,
            extracted_text,
            f'=IMAGE("{image_url}", 1)'  # 这将在 Google Sheets 中显示图片
        ]

        # 插入数据
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:C',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row_data]}
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

def sort_by_dsc_number(file):
    match = re.search(r'DSC(\d{5})', file['name'])
    if match:
        return int(match.group(1))
    else:
        return float('inf')

def clean_extracted_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and line not in cleaned_lines:
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

# 主程序逻辑
if __name__ == "__main__":
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
        try:
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
        except Exception as e:
            print(f"Error processing file {file['name']}: {str(e)}")

    print("Processing complete.")
