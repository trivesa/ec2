import openai
import os

# The API key is automatically picked up from the environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

completion = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message["content"])
