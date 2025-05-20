from openai import OpenAI

# Initialize Deepseek client
client = OpenAI(
    api_key="sk-95a1a740edb949de9a8152c00fb81f00",
    base_url="https://api.deepseek.com/v1"
)

# Send a test message to the Deepseek Reasoner model
test_prompt = "Ping? Are you alive?"
response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[{"role": "user", "content": test_prompt}],
    stream=False
)

# Print the response content
print("Deepseek response:", response.choices[0].message.content) 