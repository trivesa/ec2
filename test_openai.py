import openai
import os

# Option 2: Directly assign the key as a string
openai.api_key = 'sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA'

# Define the prompt for the test
prompt = """
You are an eBay fashion product listing expert. Use the following details for the listing:
Brand: "RENE CAOVILLA"
Product Category: "Women's Shoes"
Product Type: "shoes"
Style Number: "CT1817-105-RV05Y063"

Information Retrieval
Please search for the product's information using the brand's official website as the primary source. If the required information is not available on the official website, use the following websites as secondary sources:
1. Net-A-Porter
2. Mytheresa
3. Flannels
4. Moda Operandi
If you still cannot find the required information, use other reliable fashion retail websites or sources. If any mandatory field information is unavailable after all attempts, indicate "N/A".

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

# Call OpenAI API
response = openai.Completion.create(
  model="text-davinci-003",  # Replace with your model name if needed
  prompt=prompt,
  max_tokens=500,            # Adjust token limit as needed
  temperature=0.7            # Adjust creativity level
)

# Print the response
print("Response:")
print(response.choices[0].text.strip())
