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
def is_black_photo(image, tolerance=5):
    """
    Determines if the given image is a pure black photo (#000000).
    
    :param image: PIL Image object
    :param tolerance: Allowed deviation from pure black (0-255)
    :return: Boolean indicating if the image is considered black
    """
    # 将图像转换为 RGB 模式（如果不是的话）
    rgb_image = image.convert('RGB')
    
    # 将图像转换为 numpy 数组
    np_image = np.array(rgb_image)
    
    # 检查所有像素是否在容差范围内为黑色
    is_black = np.all(np_image <= tolerance)
    
    return is_black

# Function to insert data into Google Sheets
def insert_label_data(image_url, extracted_text):
    """
    Inserts label data into Google Sheets.
    :param image_url: URL of the label image to be inserted into the sheet.
    :param extracted_text: Extracted text from the label image.
    """
    try:
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

# 主程序逻辑
# Find the latest added subfolder within the parent folder
query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id)").execute()
latest_subfolder = results.get('files', [])[0]

# Fetch list of image files from the latest subfolder
results = drive_service.files().list(
    q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
    fields="files(id, name, mimeType)"
).execute()
files = results.get('files', [])

# Sort files based on the last 5 digits of their names
files_sorted = sorted(files, key=sort_by_dsc_number)

# 变量来跟踪黑色照片和标签照片
black_photo_found = False
last_black_photo = None

# 循环处理所有文件以识别和处理标签照片
for file in files_sorted:
    print(f"Checking file: {file['name']} ({file['mimeType']})")

    # 下载图像内容
    image_file = download_file(file['id'])
    
    # 加载图像用于视觉处理
    vision_image = vision.Image(content=image_file.getvalue())
    
    # 加载图像用于 PIL 处理
    image_file.seek(0)
    pil_image = Image.open(image_file)

    # 检查当前照片是否为黑色照片
    if not black_photo_found:
        if is_black_photo(pil_image):
            black_photo_found = True
            last_black_photo = file
            print(f"Identified black photo: {file['name']} ({file['id']})")
            continue

    # 如果我们有一个黑色照片，找到序列号最接近的标签照片
    if black_photo_found:
        def extract_sequence_number(filename):
            match = re.search(r'DSC(\d{5})', filename)
            if match:
                return int(match.group(1))
            else:
                return -1  # 或者其他适当的默认值

        current_sequence_number = extract_sequence_number(file['name'])
        last_black_photo_sequence_number = extract_sequence_number(last_black_photo['name'])

        if current_sequence_number == -1 or last_black_photo_sequence_number == -1:
            print(f"Warning: Could not extract sequence number from {file['name']} or {last_black_photo['name']}")
            continue

        if current_sequence_number > last_black_photo_sequence_number:
            print(f"Identified label photo: {file['name']} ({file['id']})")

            # 调用 Vision API 检测标签照片中的文本
            response = vision_client.text_detection(image=vision_image)
            texts = response.text_annotations

            # 构造 Google Drive 图像 URL
            image_url = f'https://drive.google.com/uc?id={file["id"]}'

            # 检查是否检测到任何文本
            if not texts:
                # 未检测到文本，向 UI 和 Sheets 发送消息
                send_message_to_ui("未检测到标签。请手动验证并输入产品信息。", "extracted texts block")
                insert_label_data(image_url, "未检测到标签。请手动验证并输入产品信息。")
                print("图像中未检测到文本。通知已发送到 UI 和 Sheets。")
            else:
                # 检测到文本，构造文本布局并发送到 UI 和 Sheets
                extracted_text = "\n".join([text.description for text in texts])
                send_message_to_ui(extracted_text, "extracted texts block")
                insert_label_data(image_url, extracted_text)

            # 重置标志和 last_black_photo 以寻找下一个黑色照片
            black_photo_found = False
            last_black_photo = None
            print(f"Processed label photo: {file['name']} ({file['id']})")

print("Processing complete.")

