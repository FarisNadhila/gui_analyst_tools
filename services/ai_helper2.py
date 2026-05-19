import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def test_gemini_connection(api_key):
    if not api_key:
        return False, "API KEY is missing."
    try:
        client = genai.Client(api_key=api_key)
        # Testing with a simple generation call
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents="hello",
            config=types.GenerateContentConfig(max_output_tokens=10)
        )
        return True, "connection success"
    except Exception as e:
        return False, f"connection failed: {str(e)}"

def get_gemini_categories(prompt, current_categories_json, api_key):
    if not api_key:
        return None, "Error: API Key is missing."

    try:
        client = genai.Client(api_key=api_key)
        
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )

        system_instruction = f"""
        You are a media monitoring analyst expert in Indonesian politics and social issues.
        Your task is to update a JSON object of categories and keywords based on a user prompt.
        
        TEMPLATE JSON:
        {current_categories_json}
        
        RULES:
        1. Return ONLY the valid JSON object.
        2. Keep the keys as "Category Name" and values as a list of "keywords".
        3. Keywords should be lowercase and relevant for search matching.
        4. If the prompt is in Indonesian, provide keywords relevant to Indonesian media.
        5. You can change to any topic other than on TEMPLATE JSON and most be related to the prompt.
        """

        full_prompt = f"User Request: {prompt}\n\n{system_instruction}\n\nBased on the template and your search capabilities for current issues, please provide the updated JSON."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=full_prompt,
            config=config
        )
        
        # Extract JSON from response
        # The new SDK might return a dict directly if response_mime_type is set, 
        # but let's handle both cases.
        if isinstance(response.parsed, dict):
            return response.parsed, None
        
        text = response.text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) > 1:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        
        updated_json = json.loads(text)
        return updated_json, None

    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    import sys
    load_dotenv()
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("GOOGLE_API_KEY not found in .env")
        sys.exit(1)
        
    p = input("Your prompt: ")
    cat = "{}"
    res, err = get_gemini_categories(p, cat, key)
    if err:
        print(f"Error: {err}")
    else:
        print(json.dumps(res, indent=4))
