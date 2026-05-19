import requests
import os
from datetime import datetime

def pull_data(token, sdate, edate, mcat, field, terms, maxsize, output_folder):
    url = "http://128.199.125.205/api/v1/pull"
    headers = {
        "accept": "application/json",
        "x-api-key": f"Token {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "sdate": sdate,
        "edate": edate,
        "mcat": mcat,
        "field": field,
        "terms": terms,
        "maxsize": int(maxsize)
    }
    
    try:
        # Ensure output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        filename = f"pulled_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(output_folder, filename)
        
        with open(output_path, "wb") as f:
            f.write(response.content)
            
        return True, filename
    except requests.exceptions.RequestException as e:
        return False, f"API Error: {str(e)}"
    except Exception as e:
        return False, f"System Error: {str(e)}"
