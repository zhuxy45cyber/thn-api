# 🔐 The Hacker News Scraper API

API serverless real-time untuk mengambil data dari [thehackernews.com](https://thehackernews.com), dibangun dengan **FastAPI** dan di-deploy ke **Vercel**.

---

## 📦 Struktur Proyek

```
thn-scraper/
├── api/
│   └── index.py          # Entry point FastAPI (Vercel handler)
├── core/
│   ├── __init__.py
│   └── scraper.py        # Logic scraping (httpx + BeautifulSoup)
├── requirements.txt
├── vercel.json
└── README.md
```

---

## 🚀 Deploy ke Vercel

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Login & Deploy
```bash
vercel login
vercel --prod
```

### 3. Buka Swagger UI
Setelah deploy, buka:
```
https://<your-project>.vercel.app/docs
```

---

## 🔧 Jalankan Lokal

```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan server
uvicorn api.index:app --reload --port 8000
```

Buka Swagger UI di: `http://localhost:8000/docs`

---

## 📡 Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/` | Health check |
| GET | `/articles` | Daftar artikel terbaru (support pagination & label filter) |
| GET | `/articles/{slug}` | Detail artikel lengkap |
| GET | `/search` | Cari artikel berdasarkan keyword |
| GET | `/labels` | Semua label/kategori |

---

## 📋 Contoh Response

### `GET /articles`
```json
{
  "page": 1,
  "label": null,
  "total_results": 10,
  "has_next_page": true,
  "articles": [
    {
      "slug": "2024/01/critical-vulnerability-openssl",
      "title": "Critical Vulnerability Found in OpenSSL",
      "description": "Researchers have discovered...",
      "image": "https://blogger.googleusercontent.com/...",
      "author": "Ravie Lakshmanan",
      "published_at": "2024-01-15T10:30:00+00:00",
      "modified_at": null,
      "tags": ["Vulnerability", "OpenSSL"],
      "url": "https://thehackernews.com/2024/01/critical-vulnerability-openssl.html"
    }
  ]
}
```

### `GET /articles/{slug}`
```json
{
  "slug": "2024/01/critical-vulnerability-openssl",
  "title": "Critical Vulnerability Found in OpenSSL",
  "description": "Researchers have discovered...",
  "image": "https://blogger.googleusercontent.com/...",
  "author": "Ravie Lakshmanan",
  "published_at": "2024-01-15T10:30:00+00:00",
  "modified_at": "2024-01-15T12:00:00+00:00",
  "tags": ["Vulnerability", "OpenSSL"],
  "read_time_minutes": 4,
  "content": "Full article content here...",
  "url": "https://thehackernews.com/2024/01/critical-vulnerability-openssl.html"
}
```

### `GET /search?q=ransomware&page=1`

**Query Parameters:**

| Parameter | Tipe | Wajib | Default | Deskripsi |
|-----------|------|-------|---------|-----------|
| `q` | string | ✅ | — | Kata kunci pencarian |
| `page` | integer | ❌ | `1` | Nomor halaman (≥ 1) |

```json
{
  "query": "ransomware",
  "page": 1,
  "total_results": 10,
  "has_next_page": true,
  "articles": [
    {
      "slug": "2024/03/new-ransomware-group-targets-healthcare",
      "title": "New Ransomware Group Targets Healthcare Sector",
      "description": "A newly identified ransomware group...",
      "image": "https://blogger.googleusercontent.com/...",
      "author": "Ravie Lakshmanan",
      "published_at": "2024-03-10T08:00:00+00:00",
      "modified_at": null,
      "tags": ["Ransomware", "Healthcare"],
      "url": "https://thehackernews.com/2024/03/new-ransomware-group-targets-healthcare.html"
    }
  ]
}
```

---

## ⚠️ Catatan

- Data diambil **real-time** (tanpa cache) — setiap request fetch langsung ke THN
- Jika struktur HTML THN berubah, selector di `core/scraper.py` perlu disesuaikan
- Gunakan dengan bijak, jangan overload server THN

---

## 📄 Lisensi

MIT — bebas digunakan untuk kebutuhan pribadi dan edukasi.
