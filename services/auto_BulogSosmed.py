import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os
from datetime import datetime

def convert_platform(content_type):
    mapping = {
        'instagram': 'Instagram',
        'tiktok': 'TikTok',
        'video': 'YouTube',
        'facebook': 'Facebook',
        'twitter': 'Twitter'
    }
    return mapping.get(str(content_type).lower().strip(), str(content_type))

def extract_first_sentence(text):
    if pd.isna(text):
        return ""
    text = str(text).strip()
    for delimiter in ['. ', '.\n', '? ', '! ', '.', '?', '!']:
        if delimiter in text:
            first_sentence = text.split(delimiter)[0] + delimiter.strip()
            return first_sentence
    return text

def format_mention(index, platform, author, text, url):
    if not str(author).startswith('@'):
        author = f"@{author}"
    platform = convert_platform(platform)
    text = extract_first_sentence(text)
    mention = f"{index}. {platform} {author} - {text}\n{url}"
    return mention

def generate_report(df, limit=15):
    report_lines = []
    
    report_lines.append("Laporan Social Media Monitoring")
    report_lines.append("Perum BULOG")
    report_lines.append(datetime.now().strftime("%d %B %Y"))
    report_lines.append("")
    
    # Mapping polarity dari Inggris ke Indonesia
    polarity_map = {
        'positive': 'Positif',
        'neutral': 'Netral',
        'negative': 'Negatif'
    }
    
    sentiments = ['Positif', 'Netral', 'Negatif']
    
    for sentiment in sentiments:
        english_polarity = [k for k, v in polarity_map.items() if v == sentiment][0]
        
        # Filter data berdasarkan sentimen
        sentiment_df = df[df['Polarity'].astype(str).str.strip().str.lower() == english_polarity]
        
        # === NASIONAL ===
        nasional_df = sentiment_df[sentiment_df['Isu'].astype(str).str.strip().str.lower() == 'nasional']
        
        # Sort by Number of likes (descending) dan ambil top {limit}
        if len(nasional_df) > 0:
            nasional_df = nasional_df.sort_values('Number of likes', ascending=False).head(limit)
        
        report_lines.append(f"*{sentiment} Nasional*\t\t\t\t\t")
        
        if len(nasional_df) > 0:
            for idx, (_, row) in enumerate(nasional_df.iterrows(), 1):
                mention = format_mention(
                    idx,
                    row['Content Type'],
                    row['Author'],
                    row['Text'],
                    row['URL']
                )
                report_lines.append(mention)
                report_lines.append("")
        else:
            report_lines.append("-\t\t\t\t\t")
            report_lines.append("")
        
        # === REGIONAL ===
        regional_df = sentiment_df[sentiment_df['Isu'].astype(str).str.strip().str.lower() == 'regional']
        
        # Sort by Number of likes (descending) dan ambil top {limit}
        if len(regional_df) > 0:
            regional_df = regional_df.sort_values('Number of likes', ascending=False).head(limit)
        
        report_lines.append(f"*{sentiment} Regional*\t\t\t\t\t")
        
        if len(regional_df) > 0:
            for idx, (_, row) in enumerate(regional_df.iterrows(), 1):
                mention = format_mention(
                    idx,
                    row['Content Type'],
                    row['Author'],
                    row['Text'],
                    row['URL']
                )
                report_lines.append(mention)
                report_lines.append("")
        else:
            report_lines.append("-\t\t\t\t\t")
            report_lines.append("")
        
        report_lines.append("------------------")
        report_lines.append("")
    
    return "\n".join(report_lines)

def generate_bulog_sosmed_report(input_file, output_folder="output"):
    """
    Generate Bulog Sosmed report from media monitoring data
    """
    try:
        if not os.path.exists(input_file):
            return False, f"File tidak ditemukan: {input_file}"
        
        # Read excel
        df = pd.read_excel(input_file)
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # Cek kolom yang diperlukan
        required_columns = ['Content Type', 'Author', 'Text', 'URL', 'Polarity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Kolom yang tidak ditemukan: {missing_columns}"
        
        # Generate laporan
        report = generate_report(df)
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Tentukan folder output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"Report_BulogSosmed_{timestamp}.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Simpan laporan
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return True, output_filename
        
    except Exception as e:
        return False, str(e)

def main():
    Tk().withdraw()
    
    file_path = askopenfilename(
        title="Pilih file Excel laporan monitoring Bulog",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    )
    
    if not file_path:
        print("Tidak ada file yang dipilih. Program berhenti.")
        return
    
    try:
        df = pd.read_excel(file_path, header=0, sheet_name=0)
        print(f"✅ Berhasil membaca file: {os.path.basename(file_path)}")
        print(f"📊 Jumlah baris data: {len(df)}")
        
        # Tanya limit ke user
        try:
            limit_input = input("\n🔢 Berapa limit per section? (default 15, tekan Enter untuk lanjut): ").strip()
            limit = int(limit_input) if limit_input else 15
        except:
            limit = 15
        
        print(f"📌 Limit per section: {limit} mention teratas berdasarkan likes\n")
        
        # Generate laporan
        report = generate_report(df, limit=limit)
        
        # Simpan output
        output_dir = os.path.dirname(file_path)
        input_basename = os.path.splitext(os.path.basename(file_path))[0]
        output_filename = f"{input_basename}_laporan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ Laporan berhasil dibuat!")
        print(f"📁 Lokasi: {output_path}")
        
        # Statistik
        polarity_counts = df['Polarity'].value_counts()
        print(f"\n📊 Statistik total:")
        print(f"   Positive: {polarity_counts.get('positive', 0)} mentions")
        print(f"   Neutral: {polarity_counts.get('neutral', 0)} mentions")
        print(f"   Negative: {polarity_counts.get('negative', 0)} mentions")
        
        # Preview
        print("\n--- PREVIEW 10 BARIS PERTAMA LAPORAN ---")
        preview_lines = report.split('\n')[:10]
        for line in preview_lines:
            print(line)
        print("...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
