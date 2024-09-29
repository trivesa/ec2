import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests

# Google Sheets API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("product-information-automation-53f8521f02ca.json", scope)
client = gspread.authorize(credentials)

# Open Google Sheet
spreadsheet = client.open_by_key("your_spreadsheet_id")1aI7g0EmMts7Byrd1izlwHSzr9CGl_2s4jBx-6eds3VU  # Replace with your Google Sheet name
sheet1 = spreadsheet.worksheet("Sheet1")  # Replace with your specific sheet name

# Read Data from Google Sheet
data = sheet1.get_all_records()
df = pd.DataFrame(data)

# Perplexity API Endpoint and Key
api_endpoint = "https://api.perplexity.ai/chat/completions"
api_key = "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"

# Example API Call Function to Fetch Product Details
def get_product_details(brand, item_code):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "perplexity",  # Adjust this if the API requires a different model name or structure
        "messages": [
            {
                "role": "user",
                "content": f"Provide details for brand {brand} and item code {item_code}."
            }
        ],
        "max_tokens": 100  # Adjust this based on the amount of data needed
    }
    
    response = requests.post(api_endpoint, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

# Iterate Over the Data and Populate Additional Fields
for index, row in df.iterrows():
    category = row['Category']
    brand = row['Brand']
    item_code = row['Item Code']
    
    # Fetch details using the Perplexity API
    product_details = get_product_details(brand, item_code)
    
    if product_details:
        # Process and update data as per requirements
        try:
            product_content = product_details['choices'][0]['message']['content']
            df.at[index, 'Product Name'] = product_content.get('name', 'N/A')
            df.at[index, 'Description'] = product_content.get('description', 'N/A')
            # Update other fields similarly based on product_content
        except KeyError:
            print(f"Error parsing product details for {brand} - {item_code}")
    else:
        # If no data found, mark as N/A
        df.at[index, 'Product Name'] = 'N/A'
        df.at[index, 'Description'] = 'N/A'

# Update Google Sheet with Processed Data
sheet1.update([df.columns.values.tolist()] + df.values.tolist())
print("Google Sheet updated successfully!")
