from google.oauth2 import service_account
from googleapiclient.discovery import build

# Define the path to your credentials file
SERVICE_ACCOUNT_FILE = '/home/ec2-user/google_sheets_automation/product-information-automation-53f8521f02ca.json'

# Specify the Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Define the ID of the spreadsheet and the range you want to read
SPREADSHEET_ID = '1aI7g0EmMts7Byrd1izlwHSzr9CGl_2s4jBx-6eds3VU'
RANGE_NAME = 'Sheet1!A1:E10'  # Update this range according to your sheet

# Authenticate and build the Google Sheets API service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

# Call the Sheets API to fetch the data
sheet = service.spreadsheets()
result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
values = result.get('values', [])

# Print the fetched data
if not values:
    print('No data found.')
else:
    for row in values:
        print(row)
