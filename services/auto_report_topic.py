import pandas as pd
# from tkinter import Tk
# from tkinter.filedialog import askopenfilename
import os
from datetime import datetime

# def pilih_file_excel():
#     """Menampilkan dialog untuk memilih file Excel"""
#     Tk().withdraw()  # Sembunyikan window utama tkinter
#     file_path = askopenfilename(
#         title="Pilih file Excel Media Monitoring",
#         filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
#     )
#     return file_path

def sort_topik_by_jumlah_artikel(grouped_dict):
    """
    Sorting topik berdasarkan jumlah artikel (paling banyak ke paling sedikit)
    
    Parameters:
    grouped_dict: dictionary dengan format {topik: [list of links]}
    
    Returns:
    list of tuples [(topik, [links]), ...] yang sudah di-sort
    """
    # Convert dictionary ke list of tuples
    items = list(grouped_dict.items())
    
    # Sort berdasarkan panjang list links (jumlah artikel) descending
    items.sort(key=lambda x: len(x[1]), reverse=True)
    
    return items

def baca_sheet_dengan_aman(excel_file, sheet_name):
    """
    Baca sheet dengan aman, return None jika sheet tidak ada atau kosong
    """
    try:
        # Cek dulu apakah sheet ada
        excel_sheets = pd.ExcelFile(excel_file)
        if sheet_name not in excel_sheets.sheet_names:
            print(f"   ⚠️ Sheet '{sheet_name}' tidak ditemukan, dilewati...")
            return None
        
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Cek apakah dataframe kosong
        if df.empty:
            print(f"   ⚠️ Sheet '{sheet_name}' kosong, dilewati...")
            return None
        
        # Cek kolom yang diperlukan
        required_columns = ['Topik', 'Source']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            print(f"   ⚠️ Sheet '{sheet_name}' tidak punya kolom {missing_cols}, dilewati...")
            return None
        
        # Bersihkan data: hapus baris yang kosong di Topik atau Source
        df = df.dropna(subset=['Topik', 'Source'])
        
        if df.empty:
            print(f"   ⚠️ Sheet '{sheet_name}' tidak punya data valid, dilewati...")
            return None
        
        return df
    
    except Exception as e:
        print(f"   ⚠️ Gagal baca sheet '{sheet_name}': {e}")
        return None

def generate_laporan_from_excel(excel_path, output_path, tanggal="XX - XX"):
    """
    Generate laporan harian .txt dari file Excel
    
    Parameters:
    excel_path: path ke file Excel
    output_path: path untuk menyimpan file .txt hasil
    tanggal: string tanggal untuk header (default: "XX - XX")
    """
    
    # Validasi file exists
    if not os.path.exists(excel_path):
        print(f"❌ File tidak ditemukan: {excel_path}")
        return None
    
    # Dapatkan nama sheet yang tersedia
    try:
        excel_file_obj = pd.ExcelFile(excel_path)
        available_sheets = excel_file_obj.sheet_names
        print(f"📑 Sheet yang tersedia: {available_sheets}")
    except Exception as e:
        print(f"❌ Gagal membaca file Excel: {e}")
        return None
    
    # Baca sheet dengan aman
    df_pemkab = baca_sheet_dengan_aman(excel_path, "Pemkab Bogor")
    df_negatif = baca_sheet_dengan_aman(excel_path, "Negatif")
    
    # Validasi minimal ada sheet Pemkab Bogor
    if df_pemkab is None:
        print(f"❌ Sheet 'Pemkab Bogor' tidak ditemukan atau kosong. Proses dihentikan.")
        return None
    
    print(f"📊 Data ditemukan:")
    print(f"   - Sheet Pemkab Bogor: {len(df_pemkab)} baris")
    if df_negatif is not None:
        print(f"   - Sheet Negatif: {len(df_negatif)} baris")
    else:
        print(f"   - Sheet Negatif: TIDAK ADA atau KOSONG (akan dilewati)")
    
    # Klasifikasi berita dari sheet Pemkab Bogor
    berita_bupati = []      # Untuk section Pemberitaan Bupati
    berita_wakil_bupati = [] # Untuk section Pemberitaan Wakil Bupati
    berita_lainnya = []     # Untuk section Pemberitaan Lainnya
    
    # Keyword untuk deteksi berita bupati
    bupati_keywords = ['Bupati Bogor', 'Bupati Rudy', 'Rudy Susmanto']
    
    # Keyword untuk deteksi berita wakil bupati
    wakil_bupati_keywords = ['Wakil Bupati', 'Wabup', 'Ade Ruhandi', 'Wakil Bupati Bogor']
    
    for _, row in df_pemkab.iterrows():
        topik = str(row['Topik']).strip()
        source = str(row['Source']).strip()
        
        # Cek apakah ini berita bupati
        is_bupati = any(keyword.lower() in topik.lower() for keyword in bupati_keywords)
        
        # Cek apakah ini berita wakil bupati
        is_wakil_bupati = any(keyword.lower() in topik.lower() for keyword in wakil_bupati_keywords)
        
        if is_bupati:
            berita_bupati.append({'topik': topik, 'source': source})
        elif is_wakil_bupati:
            berita_wakil_bupati.append({'topik': topik, 'source': source})
        else:
            berita_lainnya.append({'topik': topik, 'source': source})
    
    # Ambil semua berita dari sheet Negatif (jika ada)
    berita_negatif = []
    if df_negatif is not None:
        for _, row in df_negatif.iterrows():
            topik = str(row['Topik']).strip()
            source = str(row['Source']).strip()
            berita_negatif.append({'topik': topik, 'source': source})
    
    # Grouping berita berdasarkan topik (judul)
    def group_by_topic(berita_list):
        grouped = {}
        for item in berita_list:
            topik = item['topik']
            source = item['source']
            if topik not in grouped:
                grouped[topik] = []
            grouped[topik].append(source)
        return grouped
    
    bupati_grouped = group_by_topic(berita_bupati)
    wakil_bupati_grouped = group_by_topic(berita_wakil_bupati)
    lainnya_grouped = group_by_topic(berita_lainnya)
    negatif_grouped = group_by_topic(berita_negatif) if berita_negatif else {}
    
    # Sorting topik berdasarkan jumlah artikel (paling banyak ke paling sedikit)
    bupati_sorted = sort_topik_by_jumlah_artikel(bupati_grouped)
    wakil_bupati_sorted = sort_topik_by_jumlah_artikel(wakil_bupati_grouped)
    lainnya_sorted = sort_topik_by_jumlah_artikel(lainnya_grouped)
    negatif_sorted = sort_topik_by_jumlah_artikel(negatif_grouped) if negatif_grouped else []
    
    # Hitung total artikel per section
    total_bupati = sum(len(links) for links in bupati_grouped.values())
    total_wakil_bupati = sum(len(links) for links in wakil_bupati_grouped.values())
    total_lainnya = sum(len(links) for links in lainnya_grouped.values())
    total_negatif = sum(len(links) for links in negatif_grouped.values()) if negatif_grouped else 0
    
    # Mulai generate konten
    content = []
    
    # Header
    content.append("Selamat Pagi")
    content.append(f"Berikut kami lampirkan Laporan Harian Media Monitoring terkait Pemerintah Kabupaten Bogor periode {tanggal}")
    content.append("")
    
    # Section Pemberitaan Bupati Bogor
    content.append(f"Pemberitaan Bupati Bogor ({total_bupati} artikel)")
    if total_bupati > 0:
        for topik, links in bupati_sorted:
            content.append(topik)
            for i, link in enumerate(links, 1):
                content.append(f"{i}. {link}")
            content.append("")  # Baris kosong antar topik
    else:
        content.append("Tidak ada pemberitaan")
        content.append("")
    
    # Section Pemberitaan Wakil Bupati Bogor
    content.append(f"Pemberitaan Wakil Bupati Bogor ({total_wakil_bupati} artikel)")
    if total_wakil_bupati > 0:
        for topik, links in wakil_bupati_sorted:
            content.append(topik)
            for i, link in enumerate(links, 1):
                content.append(f"{i}. {link}")
            content.append("")  # Baris kosong antar topik
    else:
        content.append("Tidak ada pemberitaan")
        content.append("")
    
    # Separator (setelah Bupati & Wakil Bupati)
    content.append("----------------")
    content.append("")
    
    # Section Pemberitaan Lainnya
    content.append(f"Pemberitaan Lainnya ({total_lainnya} Artikel)")
    if total_lainnya > 0:
        for topik, links in lainnya_sorted:
            content.append(topik)
            for i, link in enumerate(links, 1):
                content.append(f"{i}. {link}")
            content.append("")
    else:
        content.append("Tidak ada pemberitaan")
        content.append("")
    
    # Separator untuk isu negatif (cuma ditambahin kalo ada isu negatif)
    if total_negatif > 0:
        content.append("-------------")
        content.append("")
        
        # Section Isu Negative
        content.append("*Isu Negative*")
        for topik, links in negatif_sorted:
            content.append(topik)
            for i, link in enumerate(links, 1):
                content.append(f"{i}. {link}")
            content.append("")
    else:
        content.append("-------------")
        content.append("")
        content.append("*Isu Negative*")
        content.append("Tidak ada isu negatif pada periode ini")
        content.append("")
    
    # Hapus baris kosong di akhir
    while content and content[-1] == "":
        content.pop()
    
    # Tulis ke file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    print(f"\n✅ Laporan berhasil digenerate: {output_path}")
    print(f"   - Pemberitaan Bupati: {total_bupati} artikel ({len(bupati_sorted)} topik)")
    print(f"   - Pemberitaan Wakil Bupati: {total_wakil_bupati} artikel ({len(wakil_bupati_sorted)} topik)")
    print(f"   - Pemberitaan Lainnya: {total_lainnya} artikel ({len(lainnya_sorted)} topik)")
    if total_negatif > 0:
        print(f"   - Isu Negative: {total_negatif} artikel ({len(negatif_sorted)} topik)")
    else:
        print(f"   - Isu Negative: Tidak ada")
    
    # Tampilkan info sorting untuk verifikasi
    if bupati_sorted:
        print(f"\n📈 Top 3 Pemberitaan Bupati (terbanyak):")
        for i, (topik, links) in enumerate(bupati_sorted[:3], 1):
            print(f"   {i}. {topik[:50]}... ({len(links)} artikel)")
    
    if wakil_bupati_sorted:
        print(f"\n📈 Top 3 Pemberitaan Wakil Bupati (terbanyak):")
        for i, (topik, links) in enumerate(wakil_bupati_sorted[:3], 1):
            print(f"   {i}. {topik[:50]}... ({len(links)} artikel)")
    
    return {
        'total_bupati': total_bupati,
        'total_wakil_bupati': total_wakil_bupati,
        'total_lainnya': total_lainnya,
        'total_negatif': total_negatif
    }

def main():
    """Fungsi utama dengan pop-up dialog"""
    print("=" * 50)
    print("GENERATE LAPORAN HARIAN MEDIA MONITORING")
    print("=" * 50)
    
    # Pilih file Excel
    print("\n📂 Pilih file Excel yang akan diproses...")
    excel_file = pilih_file_excel()
    
    if not excel_file:
        print("❌ Tidak ada file dipilih. Program dibatalkan.")
        return
    
    print(f"✅ File dipilih: {excel_file}")
    
    # Otomatis buat output path di folder yang sama dengan file Excel
    folder_path = os.path.dirname(excel_file)
    tanggal_now = datetime.now().strftime("%Y%m%d")
    
    # Ambil nama file Excel tanpa ekstensi untuk nama output
    base_name = os.path.splitext(os.path.basename(excel_file))[0]
    default_nama = f"laporan_harian_{base_name}_{tanggal_now}.txt"
    output_path = os.path.join(folder_path, default_nama)
    
    print(f"📁 Folder output: {folder_path}")
    print(f"📄 Nama file output: {default_nama}")
    
    # Input tanggal (opsional)
    print("\n📅 Masukkan periode tanggal (tekan Enter untuk menggunakan 'XX - XX')")
    tanggal_input = input("Periode (contoh: 13 - 14 Februari 2026): ").strip()
    
    if not tanggal_input:
        tanggal = "XX - XX"
    else:
        tanggal = tanggal_input
    
    # Generate laporan
    print("\n⚙️  Memproses data...")
    hasil = generate_laporan_from_excel(excel_file, output_path, tanggal)
    
    if hasil:
        print("\n" + "=" * 50)
        print("✅ PROSES SELESAI!")
        print(f"📁 File laporan: {output_path}")
        print("=" * 50)
    else:
        print("\n❌ Gagal memproses file.")

if __name__ == "__main__":
    main()