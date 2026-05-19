import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os
from datetime import datetime

def pilih_file_excel():
    """Menampilkan dialog untuk memilih file Excel"""
    Tk().withdraw()
    file_path = askopenfilename(
        title="Pilih file Excel Media Monitoring",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    )
    return file_path

def get_hari_tanggal():
    """Mendapatkan hari dan tanggal dalam Bahasa Indonesia"""
    hari_map = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu',
        'Sunday': 'Minggu'
    }
    
    bulan_map = {
        'January': 'Januari', 'February': 'Februari', 'March': 'Maret',
        'April': 'April', 'May': 'Mei', 'June': 'Juni',
        'July': 'Juli', 'August': 'Agustus', 'September': 'September',
        'October': 'Oktober', 'November': 'November', 'December': 'Desember'
    }
    
    now = datetime.now()
    hari_inggris = now.strftime('%A')
    tanggal = now.strftime('%d')
    bulan_inggris = now.strftime('%B')
    tahun = now.strftime('%Y')
    
    hari = hari_map.get(hari_inggris, hari_inggris)
    bulan = bulan_map.get(bulan_inggris, bulan_inggris)
    
    return f"{hari}, {tanggal} {bulan} {tahun}"

def cari_sheet_dengan_kolom(excel_path, required_columns):
    """
    Mencari sheet yang memiliki kolom yang diperlukan
    
    Parameters:
    excel_path: path ke file Excel
    required_columns: list kolom yang harus ada
    
    Returns:
    tuple (nama_sheet, dataframe) atau (None, None) jika tidak ditemukan
    """
    try:
        # Baca semua sheet names
        xl = pd.ExcelFile(excel_path)
        sheet_names = xl.sheet_names
        
        print(f"📋 Sheet yang tersedia: {', '.join(sheet_names)}")
        
        for sheet in sheet_names:
            df = pd.read_excel(excel_path, sheet_name=sheet, nrows=5)  # Baca 5 baris aja dulu
            columns = [str(col).strip() for col in df.columns]
            
            # Cek apakah semua kolom yang diperlukan ada
            if all(col in columns for col in required_columns):
                print(f"✅ Menemukan sheet '{sheet}' dengan kolom yang sesuai")
                return sheet, pd.read_excel(excel_path, sheet_name=sheet)
        
        print("❌ Tidak menemukan sheet dengan kolom yang diperlukan")
        return None, None
        
    except Exception as e:
        print(f"❌ Error saat membaca file: {e}")
        return None, None

def generate_laporan_wa_media_cetak(excel_path, output_path, tanggal=None):
    """
    Generate laporan WhatsApp format media cetak dari file Excel
    """
    
    # Validasi file exists
    if not os.path.exists(excel_path):
        print(f"❌ File tidak ditemukan: {excel_path}")
        return None
    
    # Kolom yang diperlukan
    required_columns = ['Media Name', 'Page', 'Title']
    
    # Cari sheet yang memiliki kolom yang diperlukan
    sheet_name, df = cari_sheet_dengan_kolom(excel_path, required_columns)
    
    if df is None:
        print("\n💡 Pastikan file Excel memiliki kolom: 'Media Name', 'Page', 'Title'")
        print("   (Kolom 'Category' opsional, kalau tidak ada akan dianggap 'Pemberitaan Pemkab Bogor')")
        return None
    
    # Bersihkan data
    df = df.dropna(subset=['Media Name', 'Page', 'Title'], how='all')
    
    # Isi nilai kosong
    df['Media Name'] = df['Media Name'].fillna('-').astype(str)
    df['Page'] = df['Page'].fillna('-').astype(str)
    df['Title'] = df['Title'].fillna('-').astype(str)
    
    # Cek apakah ada kolom Category
    if 'Category' in df.columns:
        df['Category'] = df['Category'].fillna('Pemberitaan Pemkab Bogor').astype(str)
        df['Category'] = df['Category'].str.strip()
    else:
        # Kalau tidak ada, buat kolom Category dengan default
        df['Category'] = 'Pemberitaan Pemkab Bogor'
        print("ℹ️  Kolom 'Category' tidak ditemukan, semua dianggap 'Pemberitaan Pemkab Bogor'")
    
    print(f"📊 Data ditemukan: {len(df)} baris di sheet '{sheet_name}'")
    
    # Group berdasarkan kategori
    kategori_siaran_pers = []
    kategori_pemberitaan = []
    
    for _, row in df.iterrows():
        kategori = str(row['Category']).strip()
        media = str(row['Media Name']).strip()
        halaman = str(row['Page']).strip()
        judul = str(row['Title']).strip()
        
        item = {
            'media': media,
            'halaman': halaman,
            'judul': judul
        }
        
        # Klasifikasi berdasarkan kategori
        if 'Siaran Pers' in kategori or 'Press Release' in kategori:
            kategori_siaran_pers.append(item)
        else:
            kategori_pemberitaan.append(item)
    
    # Jika tanggal tidak disediakan, gunakan tanggal sekarang
    if tanggal is None:
        tanggal = get_hari_tanggal()
    
    # Mulai generate konten
    content = []
    
    # Header
    content.append("Izin Menyampaikan Rekap Monitoring Press Release dan Pemberitaan Pemkab Bogor di Media Cetak")
    content.append(f"Edisi {tanggal}")
    content.append("")
    content.append("")
    
    # Kategori Siaran Pers Pemkab Bogor
    content.append("Kategori Siaran Pers Pemkab Bogor")
    content.append("")
    
    if kategori_siaran_pers:
        for item in kategori_siaran_pers:
            content.append(f"Media\t: {item['media']}")
            content.append(f"Halaman\t: {item['halaman']}")
            content.append(f"Judul\t: {item['judul']}")
            content.append("")
    else:
        content.append("Tidak ada Siaran Pers")
        content.append("")
    
    # Kategori Pemberitaan Pemkab Bogor
    content.append("Kategori Pemberitaan Pemkab Bogor")
    content.append("")
    
    if kategori_pemberitaan:
        for item in kategori_pemberitaan:
            content.append(f"Media\t: {item['media']}")
            content.append(f"Halaman\t: {item['halaman']}")
            content.append(f"Judul\t: {item['judul']}")
            content.append("")
    else:
        content.append("Tidak ada Pemberitaan")
        content.append("")
    
    # Tulis ke file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    print(f"✅ Laporan WhatsApp berhasil digenerate: {output_path}")
    print(f"   - Siaran Pers: {len(kategori_siaran_pers)} item")
    print(f"   - Pemberitaan: {len(kategori_pemberitaan)} item")
    
    return {
        'total_siaran_pers': len(kategori_siaran_pers),
        'total_pemberitaan': len(kategori_pemberitaan)
    }

def main():
    """Fungsi utama dengan pop-up dialog"""
    print("=" * 50)
    print("GENERATE LAPORAN WHATSAPP MEDIA CETAK")
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
    default_nama = f"laporan_wa_media_cetak_{base_name}_{tanggal_now}.txt"
    output_path = os.path.join(folder_path, default_nama)
    
    print(f"📁 Folder output: {folder_path}")
    print(f"📄 Nama file output: {default_nama}")
    
    # Tanya tanggal (opsional)
    print("\n📅 Masukkan tanggal edisi (tekan Enter untuk menggunakan tanggal hari ini)")
    print(f"   Format: Hari, Tanggal Bulan Tahun (contoh: Kamis, 12 Februari 2026)")
    tanggal_input = input("Tanggal: ").strip()
    
    if not tanggal_input:
        tanggal = None
        print(f"   Menggunakan tanggal: {get_hari_tanggal()}")
    else:
        tanggal = tanggal_input
    
    # Generate laporan
    print("\n⚙️  Memproses data...")
    hasil = generate_laporan_wa_media_cetak(excel_file, output_path, tanggal)
    
    if hasil:
        print("\n" + "=" * 50)
        print("✅ PROSES SELESAI!")
        print("=" * 50)
        
        # Tampilkan preview
        print("\n📋 Preview 5 baris pertama:")
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                preview = f.readlines()[:15]
                for line in preview:
                    print(line.rstrip())
        except:
            pass
    else:
        print("\n❌ Gagal memproses file.")

if __name__ == "__main__":
    main()