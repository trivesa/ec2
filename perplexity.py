import os
import subprocess
from flask import Flask, request, jsonify
import requests
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Check if port 5001 is in use, and kill the process if it is
def free_port(port):
    result = subprocess.run(f"sudo lsof -i :{port}", shell=True, capture_output=True, text=True)
    if result.stdout:
        pid = result.stdout.splitlines()[1].split()[1]
        subprocess.run(f"sudo kill -9 {pid}", shell=True)

# Free up port 5001 before running the app
free_port(5001)

app = Flask(__name__)

# The rest of your code continues here...

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
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/google-credentials/photo-to-listing-e89218601911.json"
sheets_service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

# Define the Google Sheet ID (fixed)
spreadsheet_id = '190TeRdEtXI9HXok8y2vomh_d26D0cyWgThArKQ_03_8'

# Perplexity API key
API_KEY = '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'

# Perplexity Sonar Large Model Endpoint for Chat Completions
api_endpoint = 'https://api.perplexity.ai/chat/completions'

@app.route('/generate-perplexity-listing', methods=['POST'])
def generate_perplexity_listing():
    try:
        # Extract data from the request
        data = request.json
        if not data or 'brand' not in data or 'styleNumber' not in data:
            return jsonify({'error': 'Invalid request, missing required fields.'}), 400
        
        # Extract product details from the request
        brand = data['brand']
        style_number = data['styleNumber']
        product_category = data.get('productCategory', 'Shoes').lower()

        # Log the received data
        logging.info(f"Received request for {brand}, style: {style_number}, category: {product_category}")

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

        # Return the generated listing back to the Google Sheets script
        return jsonify({'listing': listing_text}), 200

    except requests.exceptions.RequestException as e:
        logging.error(f"Error in Perplexity API request: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logging.error(f"Error processing the request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

