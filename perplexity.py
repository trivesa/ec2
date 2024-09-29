from flask import Flask, request, jsonify
import requests
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='perplexity_app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

# Set up Google Sheets API client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/path/to/your/google-credentials.json"
sheets_service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Define the Google Sheet ID and sheet name
spreadsheet_id = 'your-spreadsheet-id'
sheet_name = 'Sheet1'

# Perplexity API key
API_KEY = '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'

# Perplexity Sonar Large Model Endpoint for Chat Completions
api_endpoint = 'https://api.perplexity.ai/chat/completions'

@app.route('/generate-perplexity-listing', methods=['POST'])
def generate_perplexity_listing():
    try:
        # Extract data from Google Sheets request
        data = request.json
        if not data or 'brand' not in data or 'styleNumber' not in data:
            return jsonify({'error': 'Invalid request, missing required fields.'}), 400
        
        # Extract product details from the request
        brand = data['brand']
        style_number = data['styleNumber']
        product_category = data.get('productCategory', 'Shoes')

        # Log the received data
        logging.info(f"Received request for {brand}, style: {style_number}")

        # Define the messages for the conversation with Perplexity
        messages = [
            {
                'role': 'system',
                'content': 'You are an eBay fashion product listing expert.'
            },
            {
                'role': 'user',
                'content': f"""
                You are an eBay fashion product listing expert. Please provide detailed information for the product based on the following details:
                Brand: '{brand}', Style Number: '{style_number}', Product Category: '{product_category}'
                Please generate an eBay product listing with both mandatory and optional fields, including title, size, department, color, condition, price, and more.
                """
            }
        ]

        # Define the payload for the API request to Perplexity
        payload = {
            'model': 'llama-3.1-sonar-large-128k-online',  # Sonar Large model
            'messages': messages,
            'max_tokens': 500,
            'temperature': 0.7
        }

        # Make the API request to Perplexity
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.post(api_endpoint, headers=headers, json=payload)
        response.raise_for_status()  # Raise error for bad responses
        result = response.json()

        # Extract listing content from Perplexity response
        listing_text = result['choices'][0]['message']['content']

        # Log the generated listing text
        logging.info(f"Generated listing: {listing_text}")

        # Update the Google Sheet with the generated listing
        range_name = f'{sheet_name}!B2'  # Example: Update in cell B2
        body = {
            'values': [[listing_text]]
        }
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        logging.info("Updated the Google Sheet with the generated listing.")
        
        # Return success response
        return jsonify({'message': 'Listing generated and updated in Google Sheet successfully.'}), 200

    except requests.exceptions.RequestException as e:
        logging.error(f"Error in Perplexity API request: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logging.error(f"Error processing the request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
