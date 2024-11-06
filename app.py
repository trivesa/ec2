from flask import Flask, jsonify
import os
import logging
import subprocess
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

print("Script is starting")

try:
    from flask import Flask, jsonify
    print("Flask imported successfully")
except ImportError as e:
    print(f"Error importing Flask: {e}")
    exit(1)

import os
import logging
import subprocess
import json
print("Basic modules imported")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    print("Google modules imported successfully")
except ImportError as e:
    print(f"Error importing Google modules: {e}")
    exit(1)

app = Flask(__name__)
print("Flask app created")

# 设置日志
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

# 设置 API 客户端
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

if GOOGLE_APPLICATION_CREDENTIALS_JSON:
    try:
        credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=credentials)
        logging.info("Successfully loaded Google credentials from environment variable")
    except json.JSONDecodeError:
        logging.error("Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON. Please check the JSON format.")
        exit(1)
    except Exception as e:
        logging.error(f"Error setting up Google credentials: {str(e)}")
        exit(1)
else:
    logging.error("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")
    exit(1)

# Google Drive 父文件夹 ID
PARENT_FOLDER_ID = os.getenv('PARENT_FOLDER_ID', '你的父文件夹ID')  # 请替换为实际的 ID

# 照片处理脚本路径
PHOTO_PROCESSING_SCRIPT = os.getenv('PHOTO_PROCESSING_SCRIPT', '/home/ec2-user/photo_processing.py')

@app.route('/trigger-google-drive-script', methods=['POST'])
def trigger_google_drive_script():
    try:
        logging.info("触发 Google Drive 脚本...")

        # 在 Google Drive 中查找最新添加的子文件夹
        query = f"'{PARENT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, orderBy='createdTime desc', pageSize=1, fields="files(id, name)").execute()
        latest_subfolder = results.get('files', [])[0] if results.get('files') else None

        if not latest_subfolder:
            logging.error("在 Google Drive 文件夹中未找到子文件夹")
            return jsonify({"error": "未找到子文件夹"}), 404

        logging.debug(f"找到最新的子文件夹: {latest_subfolder['id']}")

        # 获取并排序子文件夹中的图片文件
        results = drive_service.files().list(
            q=f"'{latest_subfolder['id']}' in parents and mimeType='image/jpeg'",
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])
        files_sorted = sorted(files, key=lambda file: file['name'][-9:-4])
        logging.debug(f"排序后的文件: {files_sorted}")

        # 处理文件（这里可以添加你的图片处理逻辑）
        return jsonify({"message": "处理成功完成", "处理的文件数": len(files_sorted)}), 200

    except Exception as e:
        logging.error(f"触发脚本时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/run-photo-processing', methods=['POST'])
def run_photo_processing():
    try:
        logging.info(f"运行照片处理脚本: {PHOTO_PROCESSING_SCRIPT}")
        
        result = subprocess.run(['python3', PHOTO_PROCESSING_SCRIPT], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logging.info(f"脚本执行成功: {result.stdout}")
            return jsonify({"message": "脚本执行成功", "输出": result.stdout}), 200
        else:
            logging.error(f"脚本执行失败: {result.stderr}")
            return jsonify({"error": "脚本执行失败", "详情": result.stderr}), 500
    except subprocess.TimeoutExpired:
        logging.error("脚本执行超时")
        return jsonify({"error": "脚本执超时"}), 500
    except Exception as e:
        logging.error(f"脚本执行过程中出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)
    print("Flask application has stopped.")
