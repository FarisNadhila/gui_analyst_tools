import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Pilih File Excel Laporan Social Media",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    )
    root.destroy()
    return file_path

def remove_hashtags_at_end(text):
    """Hapus hashtag yang ada di paling akhir caption"""
    if not text:
        return text
    
    # Pola: spasi + hashtag (#xxxx) di akhir, bisa satu atau banyak
    # Contoh: " ... #PupukIndonesia #Regional4 #SwasembadaPangan"
    pattern = r'\s+#\w+(?:\s+#\w+)*\s*$'
    cleaned = re.sub(pattern, '', text)
    
    # Juga hapus kalo hashtag langsung setelah spasi tanpa karakter lain
    pattern2 = r'#\w+(?:\s+#\w+)*\s*$'
    cleaned = re.sub(pattern2, '', cleaned)
    
    return cleaned.strip()

def get_one_sentence(text):
    """
    Ambil 1 kalimat UTUH sampai tanda titik yang BENAR-BENAR akhir kalimat.
    - Abaikan titik di singkatan (Ltd., Inc., PT., dll)
    - Abaikan titik di belakang huruf kapital tunggal (A., B., dll)
    - Berhenti di titik yang diikuti spasi + huruf besar atau diikuti akhir teks
    """
    if pd.isna(text) or text == "":
        return ""
    
    text = str(text).strip()
    
    # Daftar singkatan umum (case insensitive)
    abbreviations = {
        'ltd', 'inc', 'corp', 'co', 'dr', 'mr', 'mrs', 'ms', 'pt', 'pg', 'no', 
        'vs', 'eg', 'ie', 'etc', 'al', 'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 
        'aug', 'sep', 'oct', 'nov', 'dec', 'jl', 'jln', 'st', 'ave', 'blvd', 
        'rm', 'dept', 'univ', 'assoc', 'bros', 'sons', 'ph', 'd', 'a', 'b', 'c'
    }
    
    # Cari posisi titik yang beneran akhir kalimat
    i = 0
    while i < len(text):
        if text[i] == '.':
            # Cek apakah ini singkatan
            
            # 1. Cari kata sebelum titik (mulai dari posisi terakhir spasi atau awal teks)
            start = i - 1
            while start > 0 and text[start-1] != ' ':
                start -= 1
            
            word_before = text[start:i].lower().strip()
            
            # 2. Cek apakah kata sebelum titik adalah singkatan
            is_abbrev = word_before in abbreviations
            
            # 3. Cek juga kalo titik didahului huruf kapital tunggal (contoh: "A.")
            if len(word_before) == 1 and word_before.isalpha():
                is_abbrev = True
            
            # 4. Cek setelah titik: kalo masih ada teks dan huruf kecil, kemungkinan bukan akhir kalimat
            if i + 1 < len(text) and text[i+1] == ' ' and i + 2 < len(text):
                next_char = text[i+2] if text[i+1] == ' ' else text[i+1]
                if next_char.isalpha() and next_char.islower():
                    is_abbrev = True
            
            # 5. Kalo bukan singkatan, ini akhir kalimat
            if not is_abbrev:
                # Ambil sampai titik ini
                sentence = text[:i+1].strip()
                return sentence
        
        i += 1
    
    # Kalo ga nemu titik sama sekali, balikin full text
    return text.strip()

def deduplicate_by_followers(df):
    df['duplicate_key'] = df['Text'].fillna('') + "|" + df['Sub Content Type'].fillna('') + "|" + df['URL'].fillna('')
    df_sorted = df.sort_values('Followers', ascending=False)
    df_deduplicated = df_sorted.drop_duplicates(subset=['duplicate_key'], keep='first')
    df_deduplicated = df_deduplicated.drop(columns=['duplicate_key'])
    return df_deduplicated

def process_report(file_path):
    try:
        df = pd.read_excel(file_path)
        
        valid_content_types = ["instagram post", "facebook page post", "Threads Post", "tiktok post", "tweet"]
        df = df[df['Sub Content Type'].str.lower().isin([ct.lower() for ct in valid_content_types])]
        
        df = df[df['Keyword\'s Label'].fillna('').str.contains('Pupuk Indonesia', case=False, na=False)]
        df = df[df['Polarity'].str.lower().isin(['positive', 'neutral'])]
        
        if df.empty:
            return None, "Tidak ada data yang memenuhi kriteria!"
        
        # Ambil 1 kalimat utuh
        df['One_Sentence'] = df['Text'].apply(get_one_sentence)
        
        # Hapus hashtag di akhir caption
        df['One_Sentence'] = df['One_Sentence'].apply(remove_hashtags_at_end)
        
        # Deduplikasi
        df = deduplicate_by_followers(df)
        
        # Sorting
        polarity_order = {'positive': 0, 'neutral': 1}
        df['polarity_rank'] = df['Polarity'].str.lower().map(polarity_order)
        df = df.sort_values(['polarity_rank', 'Followers'], ascending=[True, False])
        
        df = df.reset_index(drop=True)
        
        total = len(df)
        positive_count = len(df[df['Polarity'].str.lower() == 'positive'])
        neutral_count = len(df[df['Polarity'].str.lower() == 'neutral'])
        
        report_lines = []
        report_lines.append(f"Pada periode ini terdapat {total} postingan yang terdiri dari {positive_count} postingan positif✅, {neutral_count} postingan netral🆗, 0 postingan sensitif❗, dan 0 postingan negatif⛔")
        report_lines.append("")
        report_lines.append("Postingan tersebut adalah sebagai berikut:")
        report_lines.append("")
        
        for idx, row in df.iterrows():
            caption = row['One_Sentence']
            url = row['URL']
            sentiment = row['Polarity']
            emoji = "✅" if sentiment.lower() == 'positive' else "🆗"
            
            report_lines.append(f"{idx+1}. {caption} {url} {emoji}")
            report_lines.append("")
        
        return "\n".join(report_lines), None
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def save_report(output_text, input_path):
    input_folder = os.path.dirname(input_path)
    input_filename = os.path.splitext(os.path.basename(input_path))[0]
    output_filename = f"{input_filename}_social_intelligence_report.txt"
    output_path = os.path.join(input_folder, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    return output_path

def generate_pupuk_indonesia_report(input_file, output_folder="output"):
    """
    Generate Pupuk Indonesia report from media monitoring data
    """
    try:
        if not os.path.exists(input_file):
            return False, f"File tidak ditemukan: {input_file}"
        
        report_text, error = process_report(input_file)
        
        if error:
            return False, error
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Tentukan folder output
        input_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{input_filename}_social_intelligence_report.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Simpan laporan
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return True, output_filename
        
    except Exception as e:
        return False, str(e)

def main():
    print("📁 Silakan pilih file Excel laporan...")
    file_path = select_file()
    
    if not file_path:
        messagebox.showwarning("Peringatan", "Tidak ada file yang dipilih!")
        print("❌ Tidak ada file yang dipilih")
        return
    
    print(f"📄 Memproses file: {os.path.basename(file_path)}")
    
    report, error = process_report(file_path)
    
    if error:
        messagebox.showerror("Error", error)
        print(f"❌ {error}")
        return
    
    output_path = save_report(report, file_path)
    
    print("\n" + "="*60)
    print("✅ LAPORAN BERHASIL DIGENERATE!")
    print("="*60)
    print(f"📁 Disimpan di: {output_path}")
    print("\n📊 PREVIEW:")
    print("-"*40)
    lines = report.split('\n')
    for line in lines[:20]:
        print(line)
    print("="*60)
    
    messagebox.showinfo("Sukses", f"Laporan berhasil disimpan!\n\n{output_path}")

if __name__ == "__main__":
    main()