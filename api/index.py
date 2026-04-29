from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scraper import THNScraper

app = FastAPI(
    title="The Hacker News Scraper API",
    description="""
## 🔐 The Hacker News Unofficial Scraper API

API ini mengambil data secara real-time dari [thehackernews.com](https://thehackernews.com).

### Fitur:
- 📰 Daftar artikel terbaru dengan pagination
- 🔍 Detail artikel lengkap (slug, title, description, image, author, tags, dll)
- 🔎 Pencarian artikel berdasarkan keyword
- ⏱️ Estimasi waktu baca
- 🏷️ Dukungan filter berdasarkan label/tag

### Endpoints:
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/` | Health check |
| GET | `/articles` | Daftar artikel terbaru |
| GET | `/articles/{slug}` | Detail artikel |
| GET | `/search` | Cari artikel by keyword |
| GET | `/labels` | Daftar label/kategori |

### Catatan:
- Data diambil langsung (real-time) tanpa cache
- Struktur HTML bisa berubah sewaktu-waktu
""",
    version="1.1.0",
    contact={
        "name": "THN Scraper API",
        "url": "https://thehackernews.com",
    },
    license_info={
        "name": "MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

scraper = THNScraper()


@app.get(
    "/",
    tags=["Health"],
    summary="Health Check",
    response_description="Status API",
)
async def root():
    """Cek apakah API berjalan dengan baik."""
    return {"status": "ok", "message": "THN Scraper API is running 🚀"}


@app.get(
    "/articles",
    tags=["Articles"],
    summary="Daftar Artikel Terbaru",
    response_description="List artikel dari halaman utama atau label tertentu",
)
async def get_articles(
    page: int = Query(default=1, ge=1, description="Nomor halaman (mulai dari 1)"),
    label: Optional[str] = Query(
        default=None,
        description="Filter berdasarkan label/kategori (contoh: `data-breach`, `malware`, `vulnerability`)",
    ),
):
    """
    Ambil daftar artikel terbaru dari The Hacker News.

    - **page**: Nomor halaman untuk pagination
    - **label**: (Opsional) Slug label/kategori untuk filter artikel
    """
    try:
        result = await scraper.get_articles(page=page, label=label)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/search",
    tags=["Articles"],
    summary="Cari Artikel",
    response_description="Hasil pencarian artikel berdasarkan keyword",
)
async def search_articles(
    q: str = Query(
        ...,
        min_length=1,
        description="Kata kunci pencarian (contoh: `ransomware`, `zero-day`, `CVE-2024`)",
    ),
    page: int = Query(default=1, ge=1, description="Nomor halaman (mulai dari 1)"),
):
    """
    Cari artikel dari The Hacker News berdasarkan keyword.

    - **q**: Kata kunci pencarian
    - **page**: Nomor halaman untuk pagination
    """
    try:
        result = await scraper.search(query=q, page=page)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/articles/{slug}",
    tags=["Articles"],
    summary="Detail Artikel",
    response_description="Data lengkap satu artikel beserta kontennya",
)
async def get_article_detail(
    slug: str,
):
    """
    Ambil detail lengkap sebuah artikel berdasarkan slug-nya.

    - **slug**: Slug artikel (bagian URL setelah domain, tanpa `.html`)

    Contoh slug: `2024/01/new-critical-vulnerability-found`
    """
    try:
        result = await scraper.get_article_detail(slug=slug)
        if not result:
            raise HTTPException(status_code=404, detail="Artikel tidak ditemukan")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/labels",
    tags=["Meta"],
    summary="Daftar Label / Kategori",
    response_description="Semua label yang tersedia di sidebar",
)
async def get_labels():
    """
    Ambil semua label/kategori yang tersedia di The Hacker News.
    """
    try:
        result = await scraper.get_labels()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
-e 

handler = Mangum(app)
