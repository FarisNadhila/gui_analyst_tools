### DIGIVLA ANALYST TOOLS ###

import pandas as pd
import os
import re
import json

#### TOPIK CONFIG ####
HARDCODED_DEFAULT_CATEGORIES = {
    "Polemik Ijazah": ["ijazah", "palsu", "universitas", "pendidikan jokowi"],
    "Manuver Politik": ["2 periode", "dua periode", "2029"],
    "Seputar Korupsi": ["korupsi", "kpk", "suap", "blt"],
    "Keluarga": ["iriana", "menantu", "anak presiden", "dinasti"],
    "Infrastruktur": ["ikn", "nusantara", "pembangunan", "tol", "kereta", "bandara", "infrastruktur"],
    "Agama & Identitas Politik": ["islam", "ulama", "kafir", "pki", "khilafah", "intoleran"],
    "Kebijakan Publik": ["bpjs", "rs", "vaksin", "bbm", "listrik"],
}

def load_categories(config_path="categories.json"):
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except:
            return HARDCODED_DEFAULT_CATEGORIES
    return HARDCODED_DEFAULT_CATEGORIES

def classify_theme(text, categories):
    if pd.isna(text):
        return "Umum"
    text_lower = str(text).lower()
    for theme, keywords in categories.items():
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                return theme
    return "Umum"

def direct_mention(row, text_column, whitelist, keyword_column):
    text = str(row[text_column]).lower() if not pd.isna(row[text_column]) else ""
    
    if any(word.lower() in text for word in whitelist):
        return "Direct"

    if keyword_column and not pd.isna(row[keyword_column]):
        keyword_text = str(row[keyword_column]).lower()
        keyword_text = re.sub(r'[^a-zA-Z\s]', '', keyword_text)
        keyword_text = keyword_text.strip().lower()
        return keyword_text in text
    
    return "Undirect"

def run_auto_topic(file_path, output_folder, categories=None, whitelist_path="whitelist.txt", categories_path="categories.json"):
    if categories is None:
        categories = load_categories(categories_path)
        
    os.makedirs(output_folder, exist_ok=True)
    df = pd.read_excel(file_path)

    # Detect text column
    if "Text" in df.columns:
        text_column = "Text"
    elif "Title" in df.columns:
        text_column = "Title"
    else:
        raise KeyError("Kolom 'Text' atau 'Title' tidak ditemukan di file Excel kamu.")

    if "Category Group" in df.columns:
        keyword_column = "Category Group"
    elif "Category" in df.columns:
        keyword_column = "Category"
    else:
        keyword_column = None

    df["Tema"] = df[text_column].apply(lambda x: classify_theme(x, categories))

    if os.path.exists(whitelist_path):
        with open(whitelist_path, "r") as whitelists:
            whitelist = [str(line.strip()) for line in whitelists if line.strip()]
    else:
        whitelist = []

    df["Direct Mentions"] = df.apply(lambda row: direct_mention(row, text_column, whitelist, keyword_column), axis=1)

    input_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(output_folder, f"Output_{input_name}.xlsx")
    df.to_excel(output_file, index=False)
    
    return output_file

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Auto Topic Analysis')
    parser.add_argument('--input', help='Input Excel file')
    parser.add_argument('--output', help='Output folder')
    args = parser.parse_args()
    
    if args.input and args.output:
        print(f"Running analysis on {args.input}...")
        res = run_auto_topic(args.input, args.output)
        print(f"Done! Saved to {res}")
    else:
        print("Please use the GUI (main_gui.py) or provide --input and --output arguments.")
