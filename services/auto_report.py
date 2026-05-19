import pandas as pd
from datetime import datetime
import os

def generate_whatsapp_report(input_file, client_name, output_folder="output"):
    """
    Generate WhatsApp-friendly reports from media monitoring data
    """
    try:
        if not os.path.exists(input_file):
            return False, f"File tidak ditemukan: {input_file}"
        
        # Read excel
        df = pd.read_excel(input_file, sheet_name='Sheet1', header=0)
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # Cek kolom yang diperlukan
        required_columns = ['Title', 'Media Name', 'Tone', 'Media Type', 'Media Tier', 'Source']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Kolom yang tidak ditemukan: {missing_columns}"
        
        # Clean data
        df_clean = df.dropna(subset=['Title', 'Media Name', 'Tone'])
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Get current date
        current_date = datetime.now().strftime("%d %B %Y")
        
        # Process each sentiment
        for tone in ['Positive', 'Neutral', 'Negative']:
            tone_data = df_clean[df_clean['Tone'] == tone]
            
            if len(tone_data) > 0:
                filename = f"{output_folder}/{tone}.txt"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    if tone == 'Positive':
                        f.write(f"Laporan Media Monitoring\n")
                        f.write(f"{client_name}\n")
                        f.write(f"{current_date}\n")
                        f.write(f"Cut off XX.00 WIB \n\n")
                        
                        tone_counts = df_clean['Tone'].value_counts()
                        f.write(f"Positive: {tone_counts.get('Positive', 0)} berita\n")
                        f.write(f"Neutral: {tone_counts.get('Neutral', 0)} berita\n")
                        f.write(f"Negative: {tone_counts.get('Negative', 0)} berita\n\n\n")
                    
                    f.write(f"*{tone}*\n\n")
                    
                    for media_type in ['media tv', 'media cetak', 'media online']:
                        media_data = tone_data[tone_data['Media Type'] == media_type]
                        
                        if len(media_data) > 0:
                            f.write(f"*{media_type.title()}*\n\n")
                            counter = 1
                            for tier in [1, 2, 3]:
                                tier_data = media_data[media_data['Media Tier'].astype(str).str.strip() == str(tier)]
                                if len(tier_data) > 0:
                                    f.write(f"*Tier {tier}*\n\n")
                                    for _, row in tier_data.iterrows():
                                        f.write(f"{counter}. {row['Media Name']}\n")
                                        f.write(f"{row['Title']}:\n")
                                        f.write(f"{row['Source']}\n\n")
                                        counter += 1
                                    f.write("\n")
        
        return True, output_folder
        
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='WhatsApp Report Generator')
    parser.add_argument('--input', help='Input Excel file')
    parser.add_argument('--client', help='Client name')
    parser.add_argument('--output', default='output', help='Output folder')
    args = parser.parse_args()
    
    if args.input and args.client:
        success, msg = generate_whatsapp_report(args.input, args.client, args.output)
        if success:
            print(f"Success! Reports generated in {msg}")
        else:
            print(f"Error: {msg}")
    else:
        print("Please use the GUI (main_gui.py) or provide --input and --client arguments.")
