import requests

# API key directly added for testing purposes
API_KEY = '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'

# Correct Perplexity Sonar Large Model Endpoint for Chat Completions
api_endpoint = 'https://api.perplexity.ai/chat/completions'

# Define the headers including your API key for authentication
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# Define the messages for the conversation, starting with system instructions
messages = [
    {
        'role': 'system',
        'content': 'You are an eBay fashion product listing expert.'
    },
    {
        'role': 'user',
        'content': """
You are an eBay fashion product listing expert. Please provide detailed information for a clothing item in the category “SHOES” based on the brand 'BALENCIAGA', style number '54236 W2FS8 4200', size “36” and condition “placeholder”, following eBay's mandatory and optional fields as described. If you cannot find any field’s production information, please just put “N/A”.

Category: Shoes
Mandatory Fields:
- Listing Title: Not more than 80 characters.
- Object Category: Example: "Clothing & Accessories > Men > Shoes."
- Brand: Brand of the shoes (e.g., Nike).
- Size: Size of the shoes.
- Department: Department (e.g., Men).
- Color: Color of the shoes.
- Type: Type of shoes.
- Style: Style of the shoes (e.g., Casual).
- Condition of the Item: Condition (e.g., New with tags).
- Price: Price of the item including VAT.
- Shipping Rule: Shipping details like weight and dimensions.

Optional Fields:
- Subtitle: Additional subtitle for the listing, not more than 55 characters.
- Custom Label (SKU): Optional SKU for internal tracking.
- EAN: European Article Number.
- MPN (style number): Brand’s Style Number.
- Material: Material of the shoes (e.g., Leather).
- Product Line: Product line (e.g., Air Max).
- Insole Material: Material of the insole (e.g., Foam).
- Outer Material: Material of the outer part (e.g., Mesh).
- Sole Material: Material of the sole (e.g., Rubber).
- Lining Material: Material of the lining (e.g., Textile).
- Closure Type: Type of closure (e.g., Laces).
- Fit: Fit (e.g., Regular).
- Pattern: Pattern (e.g., Solid, Graphic).
- Season: Suitable season (e.g., Winter, Summer).
- Theme: Theme (e.g., Sports).
- Country of Manufacture: Country where the shoes are manufactured (e.g., Italy).
- Product Variants: Variants such as size and color.
- Description: Detailed description of the item.
- Short Description: A brief description.
- Payment and Offers: Payment and offer conditions.
- Object Warnings: Safety or compliance warnings.
"""
    }
]

# Define the payload for the API request using the Sonar Large model
payload = {
    'model': 'llama-3.1-sonar-large-128k-online',  # Sonar Large model name
    'messages': messages,
    'max_tokens': 500,  # Adjust based on how much content you want to generate
    'temperature': 0.7  # Adjust for more or less randomness in responses
}

# Make the API request
try:
    response = requests.post(api_endpoint, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    print("Generated Content:")
    print(data['choices'][0]['message']['content'])  # Adjust based on the API's response structure
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
