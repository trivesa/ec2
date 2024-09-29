import openai
import os

# The API key is automatically picked up from the environment variable
openai.api_key = "sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA"

# Define the product details
brand = "RENE CAOVILLA"
product_category = "Women's Shoes"
product_type = "shoes"
style_number = "CT1817-105-RV05Y063"

# Define the prompt with detailed instructions for the eBay fashion listing expert
prompt = f"""
You are an eBay fashion product listing expert. Use the following details for the listing:
Brand: "{brand}"
Product Category: "{product_category}"
Product Type: "{product_type}"
Style Number: "{style_number}"

Information Retrieval:
Please search for the product's information using the brand's official website as the primary source. 
If the required information is not available on the official website, use the following websites as secondary sources:
1. Net-A-Porter
2. Mytheresa
3. Flannels
4. Moda Operandi

If you still cannot find the required information, use other reliable fashion retail websites or sources. 
If any mandatory field information is unavailable after all attempts, indicate "N/A".

Fashion Product Listing Part 1: Mandatory and Optional Fields

Mandatory Fields:
1. Object Category (Categoria Oggetto) 
2. Store Category (Categoria del Negozio)
3. Brand (Marca) 
4. Size (Numero di scarpa EU) 
5. Department (Reparto) 
6. Color (Colore) 
7. Type (Tipo) 
8. Style (Stile) 
9. Condition of the Item (Condizione dell'oggetto) 
10. Price (Prezzo) 
11. Shipping Rule (Regola sulla spedizione)

Optional Fields:
1. MPN (MPN) 
2. Custom Label (Etichetta personalizzata - SKU) 
3. EAN (EAN) 
4. Material (Materiale della tomaia) 
5. Sole Material (Materiale della suola) 
6. Lining Material (Materiale della fodera)
"""

# Make a request to OpenAI with the fashion listing expert instructions
completion = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are an eBay fashion product listing expert."},
        {"role": "user", "content": prompt}
    ]
)

# Output the generated fashion listing information
print(completion.choices[0].message["content"])
