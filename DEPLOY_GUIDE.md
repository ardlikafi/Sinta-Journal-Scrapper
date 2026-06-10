# Panduan Deploy Online - SintaJournal Scraper & Email Sender

Aplikasi ini berbasis **Streamlit (Python)**. Untuk mengonlinekan aplikasi Streamlit secara gratis dan stabil, platform terbaik adalah **Streamlit Community Cloud** (karena Vercel memiliki limit waktu eksekusi serverless 10-60 detik yang akan membuat proses scraping terputus di tengah jalan).

Berikut adalah langkah-langkah mudah untuk mengonlinekan aplikasi ini:

---

## Langkah 1: Upload ke GitHub
1. Buat repository baru di GitHub (bisa diset privat/public).
2. Upload file berikut ke repository Anda:
   * `app.py`
   * `requirements.txt` (sudah dibuat secara otomatis)

---

## Langkah 2: Hubungkan ke Streamlit Community Cloud
1. Buka website **[Streamlit Community Cloud](https://share.streamlit.io)**.
2. Masuk menggunakan akun **GitHub** Anda.
3. Klik tombol **"Create app"** atau **"New app"** di kanan atas.
4. Isi data berikut:
   * **Repository**: Pilih repository GitHub tempat Anda mengunggah kode tadi.
   * **Branch**: `main` atau `master`.
   * **Main file path**: `app.py`.
5. Klik **"Deploy!"**.

---

## Langkah 3: Mengonfigurasi Kredensial Pengirim (.env) secara Aman
Di Streamlit Cloud, Anda tidak perlu mengunggah file `.env` ke GitHub (karena berbahaya jika terpublikasi). Sebagai gantinya:
1. Setelah aplikasi berhasil di-deploy, buka dashboard Streamlit Cloud Anda.
2. Klik tombol menu (titik tiga) di samping nama aplikasi Anda, lalu pilih **Settings**.
3. Pilih menu **Secrets** di sebelah kiri.
4. Salin isi file `.env` lokal Anda dan tempelkan ke kolom Secrets tersebut, seperti ini:
   ```toml
   SENDER_NAME="Nama Anda"
   SENDER_INSTITUTION="Nama Universitas"
   SENDER_EMAIL="emailanda@gmail.com"
   SENDER_PASSWORD="apppassword16digit"
   EMAIL_SUBJECT="Pertanyaan Mengenai Kuota Publikasi - {nama_jurnal}"
   ```
5. Klik **Save**. Aplikasi akan otomatis memuat kredensial tersebut secara aman.
