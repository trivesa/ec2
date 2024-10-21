from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging
import sys

# 设置日志级别为 DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = '/Users/yinxianzhi/Projects/ec2/google-credentials/photo-to-listing-e89218601911.json'
SPREADSHEET_ID = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'

def main():
    try:
        logging.info("Starting the script...")
        logging.info(f"Using service account file: {SERVICE_ACCOUNT_FILE}")
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        logging.info("Credentials loaded successfully")
        
        service = build('sheets', 'v4', credentials=credentials)
        logging.info("Sheets service built successfully")
        
        sheet = service.spreadsheets()
        logging.info("Attempting to read spreadsheet...")
        
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1!A1:B2').execute()
        values = result.get('values', [])
        
        logging.info(f"Values read from spreadsheet: {values}")
        
        if not values:
            logging.warning("No data found in the spreadsheet")
        else:
            logging.info("Data successfully retrieved from the spreadsheet")
        
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
