import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os
from datetime import datetime
from collections import Counter

def show_popup_and_get_file():
    """Menampilkan popup untuk memilih file Excel"""
    Tk().withdraw()  # Sembunyikan root window
    file_path = askopenfilename(
        title="Pilih file Excel laporan media",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    )
    return file_path

def map_tone(tone):
    """Mapping tone dari English ke Indonesia + emoji"""
    tone_map = {
        'Positive': 'Positif 🆗',
        'Neutral': 'Netral ✅',
        'Negative': 'Negatif ⛔'
    }
    return tone_map.get(tone, 'Netral ✅')  # Default neutral kalo ga dikenal

def generate_report(df):
    """Generate laporan WhatsApp brief dari dataframe"""
    
    # Hitung frekuensi setiap isu untuk Top 5 (Positive dan Neutral saja)
    top_issues_df = df[df['Tone'].isin(['Positive', 'Neutral'])].copy()
    
    # Hitung jumlah kemunculan per isu
    issue_counts = top_issues_df['Isu'].value_counts()
    
    # Ambil top 5 isu berdasarkan frekuensi
    top_5_issues = issue_counts.head(5).index.tolist()
    
    # Pisahkan isu negatif
    negative_issues_df = df[df['Tone'] == 'Negative'].copy()
    
    # Prepare output
    output_lines = []
    
    # Header dengan tanggal sekarang dari data (ambil dari tanggal file atau pakai datetime)
    today_date = datetime.now().strftime("%A, %d/%m/%Y")
    # Ganti hari ke Bahasa Indonesia sederhana
    day_map = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }
    for eng, ind in day_map.items():
        today_date = today_date.replace(eng, ind)
    
    # Hitung total berita dan breakdown sentimen
    total_berita = len(df)
    total_positif = len(df[df['Tone'] == 'Positive'])
    total_netral = len(df[df['Tone'] == 'Neutral'])
    total_negatif = len(df[df['Tone'] == 'Negative'])
    
    # Header laporan
    output_lines.append(f"Selamat Pagi Bapak/Ibu,")
    output_lines.append(f"Pada pagi ini, {today_date} terdapat {total_berita} berita yang terdiri dari {total_positif} berita positif 🆗, {total_netral} berita netral ✅, dan {total_negatif} berita negatif ⛔. Adapun Top 5 pemberitaan tersebut adalah sebagai berikut:")
    output_lines.append("")
    
    # Top 5 pemberitaan (hanya Positive dan Neutral)
    for idx, issue in enumerate(top_5_issues, 1):
        # Ambil tone dari isu ini (ambil dari baris pertama)
        issue_data = top_issues_df[top_issues_df['Isu'] == issue].iloc[0]
        tone_indo = map_tone(issue_data['Tone'])
        
        # Judul isu dengan emoji
        output_lines.append(f"*{idx}. {issue} {tone_indo.split()[1]}*")  # Ambil emoji aja
        output_lines.append("")
        output_lines.append(f"*Summary*")
        output_lines.append(f"-")
        output_lines.append("")
        output_lines.append(f"")  # Kosong untuk analis isi manual
        
        output_lines.append(f"*Link Pemberitaan*")
        
        # Ambil semua Title dan Source untuk isu ini
        issue_articles = top_issues_df[top_issues_df['Isu'] == issue]
        for article_idx, (_, row) in enumerate(issue_articles.iterrows(), 1):
            title = row['Title']
            source_url = row['Source']
            output_lines.append(f"{article_idx}. {title} {source_url}")
        
        output_lines.append("")
        output_lines.append("")  # Spasi antar isu
    
    # Isu Negatif (jika ada)
    if len(negative_issues_df) > 0:
        output_lines.append(f"*Isu Negatif*")
        output_lines.append("")
        
        # Group isu negatif berdasarkan judul isu
        negative_grouped = negative_issues_df.groupby('Isu')
        
        for issue, group in negative_grouped:
            tone_indo = map_tone(group.iloc[0]['Tone'])
            output_lines.append(f"*{issue} {tone_indo.split()[1]}*")
            output_lines.append("")
            output_lines.append(f"*Summary*")
            output_lines.append(f"-")
            output_lines.append("")
            output_lines.append(f"")  # Kosong untuk analis isi manual
            
            output_lines.append(f"*Link Pemberitaan*")
            
            for article_idx, (_, row) in enumerate(group.iterrows(), 1):
                title = row['Title']
                source_url = row['Source']
                output_lines.append(f"{article_idx}. {title} {source_url}")
            
            output_lines.append("")
            output_lines.append("")
    
    return "\n".join(output_lines)

def generate_kemenperin_report(input_file, output_folder="output"):
    """
    Generate Kemenperin report from media monitoring data
    """
    try:
        if not os.path.exists(input_file):
            return False, f"File tidak ditemukan: {input_file}"
        
        # Read excel
        df = pd.read_excel(input_file)
        
        # Clean data (drop baris dengan Isu kosong/null)
        if 'Isu' not in df.columns:
             return False, "Kolom 'Isu' tidak ditemukan dalam file Excel."
             
        df = df.dropna(subset=['Isu'])
        
        if df.empty:
            return False, "Tidak ada data valid dengan kolom 'Isu'."

        # Generate laporan
        report = generate_report(df)
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Tentukan folder output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"WhatsApp_Brief_Kemenperin_{timestamp}.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Simpan laporan
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return True, output_filename
        
    except Exception as e:
        return False, str(e)

def main():
    print("=== WhatsApp Brief Generator ===\n")
    
    # Popup pilih file
    print("Silakan pilih file Excel...")
    file_path = show_popup_and_get_file()
    
    if not file_path:
        print("Tidak ada file yang dipilih. Program berhenti.")
        return
    
    print(f"File dipilih: {file_path}")
    
    # Baca file Excel
    try:
        df = pd.read_excel(file_path)
        print(f"Berhasil membaca {len(df)} baris data")
    except Exception as e:
        print(f"Error membaca file: {e}")
        return
    
    # Validasi kolom yang diperlukan (Summary tidak wajib karena analis yang isi)
    required_columns = ['Isu', 'Tone', 'Title', 'Source']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"Error: Kolom berikut tidak ditemukan di Excel: {missing_columns}")
        print(f"Kolom yang ada: {df.columns.tolist()}")
        return
    
    # Bersihkan data (drop baris dengan Isu kosong/null)
    df = df.dropna(subset=['Isu'])
    
    # Generate laporan
    print("Mengenerate laporan...")
    report = generate_report(df)
    
    # Tentukan folder output (sama dengan folder input)
    input_dir = os.path.dirname(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"WhatsApp_Brief_{timestamp}.txt"
    output_path = os.path.join(input_dir, output_filename)
    
    # Simpan laporan
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Laporan berhasil disimpan di:")
    print(f"{output_path}")
    print(f"\nTotal berita: {len(df)}")
    print(f"Top 5 isu berdasarkan frekuensi pemberitaan (Positive+Neutral)")
    print("=== Selesai ===")

if __name__ == "__main__":
    main()