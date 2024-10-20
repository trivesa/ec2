import openai

# Replace 'your-api-key' with your actual OpenAI API key
openai.api_key = "sk-0ZmM3wMLzmOd-hQcAmOlNphK3IbpalKQseu4eebvlDT3BlbkFJ3mDX_5R4gT2cSXNCRdndUgr5WOcVeadTkyqKDl9zgA"

# Test a simple chat completion
response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
	{"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response['choices'][0]['message']['content'].strip())

