import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: Gemini API key not found!")
    exit()

print("API key loaded successfully!")
print("Initializing Gemini...")

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        timeout=15000,
        retry_options=types.HttpRetryOptions(
            attempts=1
        )
    )
)

try:
    print("Sending request to Gemini...")

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents="Reply with exactly: Gemini connection successful!",
        config=types.GenerateContentConfig(
            max_output_tokens=32
        )
    )

    print("\nSUCCESS!")
    print(response.text)

except Exception as e:
    print("\nGEMINI ERROR:")
    print(type(e).__name__)
    print(str(e))

finally:
    client.close()