from google import genai

client = genai.Client(api_key="AIzaSyDKXIUCBooTc51dcT2KbBBkYQ-Y05yvtyQ")

# Use generate_content_stream for streaming
response = client.models.generate_content_stream(
    model="gemini-2.0-flash-lite", 
    contents="能不能写一个基于动物的故事给我？"
)

# Process streaming response
for chunk in response:
    if chunk.text:
        print(chunk.text, end='', flush=True)