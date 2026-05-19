import google.generativeai as genai 
import json
import os
from dotenv import load_dotenv

def test_gemini_connection(api_key):
    """
    Sends a simple request to Gemini to test if the API key is valid.
    Uses 'gemini-2.5-flash' to test for full functionality including tools.
    """
    if not api_key:
        return False, "API Key is missing."
    try:
        # Re-introducing genai.configure() as suggested by the latest error.
        genai.configure(api_key=api_key)
        
        # Using the simplest form for google_search_retrieval.
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
#            tools=[{'google_search_retrieval': {}}] 
        )
        model.generate_content("hello", generation_config={"max_output_tokens": 10})
        return True, "Connection successful with 'gemini-2.5-flash' and google_search_retrieval tool (empty config)!"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def get_gemini_categories(prompt, current_categories_json, api_key):
    """
    Calls Gemini to update categories based on a prompt.
    Uses current_categories_json as a template.
    """
    if not api_key:
        return None, "Error: API Key is missing."

    try:
        # Re-introducing genai.configure() as suggested by the latest error.
        genai.configure(api_key=api_key)
        
        # Using the simplest form for google_search_retrieval.
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[{'google_search_retrieval': {}}]
        )

        system_instruction = f"""
        You are a media monitoring analyst expert in Indonesian politics and social issues.
        Your task is to update a JSON object of categories and keywords based on a user prompt.
        
        TEMPLATE JSON:
        {current_categories_json}
        
        RULES:
        1. Return ONLY the valid JSON object. No markdown, no triple backticks, no explanation.
        2. Keep the keys as "Category Name" and values as a list of "keywords".
        3. Keywords should be lowercase and relevant for search matching.
        4. If the prompt is in Indonesian, provide keywords relevant to Indonesian media.
        """

        full_prompt = f"""User Request: {prompt}

Based on the template and your search capabilities for current issues, please provide the updated JSON."""
        
        response = model.generate_content(full_prompt + "\n\n" + system_instruction)
        
        # Clean response text
        text = response.text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) > 1:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        
        # Validate JSON
        updated_json = json.loads(text)
        return updated_json, None

    except Exception as e:
        return None, str(e)
