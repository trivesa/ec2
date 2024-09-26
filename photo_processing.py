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

        # Prepare the request to insert the image and text
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
                                        "formulaValue": f'=IMAGE("{image_url}", 4, 150, 150)'  # Custom size for image
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
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": next_row - 1,
                        "endIndex": next_row
                    },
                    "properties": {
                        "pixelSize": 200  # Adjust this value to change the row height
                    },
                    "fields": "pixelSize"
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 1
                    },
                    "properties": {
                        "pixelSize": 150  # Set column width
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
