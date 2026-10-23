import argparse
import os
import time

from bs4 import BeautifulSoup
from curl_cffi import requests as cr

BASE_URL = "https://putusan3.mahkamahagung.go.id"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_detail_links(page_num, tahun):
    """Ambil link halaman detail putusan dari halaman indeks"""
    if page_num == 1:
        url = f"{BASE_URL}/direktori/index/tahunjenis/putus/tahun/{tahun}.html"
    else:
        url = f"{BASE_URL}/direktori/index/tahunjenis/putus/tahun/{tahun}/page/{page_num}.html"

    detail_links = []

    try:
        res = cr.get(url, headers=HEADERS, impersonate='chrome', timeout=15)
        if res.status_code != 200:
            print(f"Gagal akses halaman {page_num} (Status: {res.status_code})")
            return detail_links

        soup = BeautifulSoup(res.text, 'html.parser')

        # Cari semua link yang mengarah ke halaman detail putusan
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/direktori/putusan/' in href:
                if not href.startswith('http'):
                    href = BASE_URL + href
                detail_links.append(href)

    except Exception as e:
        print(f"Error scraping halaman {page_num}: {e}")

    return list(set(detail_links))


def get_pdf_download_link(detail_url):
    """Masuk ke halaman detail untuk ekstrak link file PDF aslinya"""
    try:
        res = cr.get(detail_url, headers=HEADERS, impersonate='chrome', timeout=15)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        # Cari tombol / link download PDF di halaman detail
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/pdf/' in href or href.endswith('.pdf'):
                if not href.startswith('http'):
                    return BASE_URL + href
                return href

    except Exception as e:
        print(f"Error mengambil link PDF dari {detail_url}: {e}")

    return None


def download_pdf(pdf_url, folder):
    """Download file PDF langsung simpan ke folder"""
    filename = pdf_url.split('/')[-1].split('?')[0]
    if not filename.endswith('.pdf'):
        filename += '.pdf'

    file_path = os.path.join(folder, filename)

    if os.path.exists(file_path):
        print(f"  [SKIP] File sudah ada: {filename}")
        return

    try:
        res = cr.get(pdf_url, headers=HEADERS, impersonate='chrome', stream=True, timeout=30)
        if res.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=1024 * 32):
                    if chunk:
                        f.write(chunk)
            print(f"  [OK] Berhasil disimpan: {filename}")
        else:
            print(f"  [FAIL] Gagal download (Status: {res.status_code})")
    except Exception as e:
        print(f"  [ERROR] Gagal download: {e}")


def main():
    parser = argparse.ArgumentParser(description="Scraping putusan Mahkamah Agung (PDF)")
    parser.add_argument("--tahun", default="2023", help="Tahun putusan (default: 2023)")
    parser.add_argument("--max-halaman", type=int, default=5, help="Jumlah halaman indeks (default: 5)")
    parser.add_argument("--folder", default=None,
                        help="Folder tujuan simpan PDF (default: ./Putusan_MA_<tahun>)")
    parser.add_argument("--colab", action="store_true",
                        help="Mount dan simpan ke Google Drive (/content/drive/MyDrive/)")
    args = parser.parse_args()

    if args.colab:
        from google.colab import drive
        drive.mount('/content/drive')
        folder = f"/content/drive/MyDrive/Putusan_MA_{args.tahun}"
    else:
        folder = args.folder or f"Putusan_MA_{args.tahun}"

    os.makedirs(folder, exist_ok=True)

    print(f"=== Mulai scraping putusan tahun {args.tahun} ===")

    for page in range(1, args.max_halaman + 1):
        print(f"\n--- Scraping Halaman Indeks {page} ---")
        details = get_detail_links(page, args.tahun)

        if not details:
            print("Tidak ada link putusan ditemukan di halaman ini.")
            continue

        print(f"Ditemukan {len(details)} item putusan. Memproses link PDF...")

        for detail_url in details:
            pdf_url = get_pdf_download_link(detail_url)
            if pdf_url:
                download_pdf(pdf_url, folder)
            else:
                print(f"  [SKIP] Tidak ada tombol PDF di: {detail_url}")

            time.sleep(1)  # Jeda per request biar ramah ke server MA

    print(f"\n=== Selesai! Cek folder '{folder}' ===")


if __name__ == "__main__":
    main()
