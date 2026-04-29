import httpx
import re
import math
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

BASE_URL = "https://thehackernews.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

WORDS_PER_MINUTE = 200


def estimate_read_time(text: str) -> int:
    """Estimasi waktu baca dalam menit berdasarkan jumlah kata."""
    words = len(text.split())
    minutes = math.ceil(words / WORDS_PER_MINUTE)
    return max(1, minutes)


def parse_datetime(raw: Optional[str]) -> Optional[str]:
    """Parse datetime dari atribut HTML ke format ISO 8601."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception:
        return raw


def extract_slug(url: str) -> str:
    """Ekstrak slug dari URL artikel Blogger THN."""
    # URL format: https://thehackernews.com/YYYY/MM/title-slug.html
    match = re.search(r"thehackernews\.com/(.+?)(?:\.html)?$", url)
    if match:
        return match.group(1)
    return url


def parse_article_card(item) -> dict:
    """Parse satu card artikel dari halaman listing."""
    # Title
    title_el = item.select_one("h2.home-title, .story-title, h2")
    title = title_el.get_text(strip=True) if title_el else ""

    # URL & slug
    link_el = item.select_one("a.story-link, a[rel='bookmark'], h2 a, a")
    url = link_el["href"] if link_el and link_el.get("href") else ""
    slug = extract_slug(url)

    # Description
    desc_el = item.select_one(".home-desc, .story-excerpt, p")
    description = desc_el.get_text(strip=True) if desc_el else ""

    # Image
    img_el = item.select_one("img.home-img-src, img[data-src], img")
    image = (
        img_el.get("data-src") or img_el.get("src") or ""
        if img_el else ""
    )
    # Bersihkan base64 placeholder
    if image and image.startswith("data:"):
        image = img_el.get("data-src", "") if img_el else ""

    # Author
    author_el = item.select_one(".item-label a, .author a, span.author")
    author = author_el.get_text(strip=True) if author_el else "The Hacker News"

    # Published at
    time_el = item.select_one("time[datetime], abbr[title]")
    published_at = None
    if time_el:
        published_at = parse_datetime(
            time_el.get("datetime") or time_el.get("title")
        )

    # Tags
    tags = []
    tag_els = item.select(".item-label a, .story-label a, span.label a")
    for tag in tag_els:
        t = tag.get_text(strip=True)
        if t and t not in tags:
            tags.append(t)

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "image": image,
        "author": author,
        "published_at": published_at,
        "modified_at": None,
        "tags": tags,
        "url": url,
    }


def extract_article_content(soup: BeautifulSoup) -> str:
    """
    Ekstrak konten artikel, berhenti sebelum div.cf.note-b
    """
    post_body = soup.select_one("div.articlebody, div#articlebody, div.post-body")
    if not post_body:
        return ""

    content_parts = []
    for child in post_body.children:
        # Berhenti jika menemukan div dengan class 'cf note-b'
        if hasattr(child, "attrs"):
            classes = child.get("class", [])
            if "cf" in classes and "note-b" in classes:
                break
            # Juga stop jika id atau class mengandung 'note-b'
            if "note-b" in " ".join(classes):
                break
        text = child.get_text(separator=" ", strip=True) if hasattr(child, "get_text") else str(child).strip()
        if text:
            content_parts.append(text)

    return "\n\n".join(content_parts)


class THNScraper:
    def __init__(self):
        self.client_options = {
            "headers": HEADERS,
            "timeout": 30.0,
            "follow_redirects": True,
        }

    async def _fetch(self, url: str) -> BeautifulSoup:
        async with httpx.AsyncClient(**self.client_options) as client:
            response = await client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")

    async def get_articles(self, page: int = 1, label: Optional[str] = None) -> dict:
        """Ambil daftar artikel dari listing page."""
        if label:
            # Label pages: /search/label/malware
            url = f"{BASE_URL}/search/label/{label}"
            if page > 1:
                # Blogger pagination pakai max-results + start param via ?updated-max
                # Kita approx pakai halaman sederhana
                url = f"{BASE_URL}/search/label/{label}?page={page}"
        else:
            if page == 1:
                url = BASE_URL
            else:
                url = f"{BASE_URL}/search?updated-max=9999-12-31&max-results=10&start={( page-1)*10}"

        soup = await self._fetch(url)

        articles = []

        # Coba selector utama
        items = soup.select("div.body-post, div.home-right, article, div.clear")
        
        # Fallback: cari semua link artikel
        if not items:
            items = soup.select(".story-link")

        for item in items:
            try:
                parsed = parse_article_card(item)
                if parsed["title"] and parsed["slug"]:
                    articles.append(parsed)
            except Exception:
                continue

        # Deduplikasi berdasarkan slug
        seen = set()
        unique = []
        for a in articles:
            if a["slug"] not in seen:
                seen.add(a["slug"])
                unique.append(a)

        # Cari info next page
        next_page_el = soup.select_one("a.blog-pager-older-link, #blog-pager-older-link")
        has_next = next_page_el is not None

        return {
            "page": page,
            "label": label,
            "total_results": len(unique),
            "has_next_page": has_next,
            "articles": unique,
        }

    async def get_article_detail(self, slug: str) -> Optional[dict]:
        """Ambil detail lengkap satu artikel."""
        # Slug format: YYYY/MM/title.html atau YYYY/MM/title
        if not slug.endswith(".html"):
            url = f"{BASE_URL}/{slug}.html"
        else:
            url = f"{BASE_URL}/{slug}"

        soup = await self._fetch(url)

        # Title
        title_el = soup.select_one("h1.story-title, h1.postTitle, h1")
        title = title_el.get_text(strip=True) if title_el else ""

        # Description / meta
        desc_el = soup.select_one('meta[name="description"], meta[property="og:description"]')
        description = desc_el.get("content", "") if desc_el else ""

        # Image (og:image paling reliable)
        image_el = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
        image = image_el.get("content", "") if image_el else ""
        if not image:
            img_el = soup.select_one("div.articlebody img, .post-body img")
            image = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

        # Author
        author_el = soup.select_one(
            'span[itemprop="author"] span[itemprop="name"], '
            '.author-name, span.author, a[rel="author"]'
        )
        author = author_el.get_text(strip=True) if author_el else "The Hacker News"

        # Published at
        pub_el = soup.select_one(
            'meta[property="article:published_time"], '
            'time[itemprop="datePublished"], time[datetime]'
        )
        published_at = None
        if pub_el:
            published_at = parse_datetime(
                pub_el.get("content") or pub_el.get("datetime")
            )

        # Modified at
        mod_el = soup.select_one(
            'meta[property="article:modified_time"], '
            'time[itemprop="dateModified"]'
        )
        modified_at = None
        if mod_el:
            modified_at = parse_datetime(
                mod_el.get("content") or mod_el.get("datetime")
            )

        # Tags / labels
        tags = []
        tag_els = soup.select(
            'a[rel="tag"], .story-tags a, '
            'span.label a, .post-labels a, '
            'meta[property="article:tag"]'
        )
        for tag in tag_els:
            if tag.name == "meta":
                t = tag.get("content", "").strip()
            else:
                t = tag.get_text(strip=True)
            if t and t not in tags:
                tags.append(t)

        # Content (stop di div.cf.note-b)
        content = extract_article_content(soup)

        # Read time
        read_time = estimate_read_time(content) if content else 1

        return {
            "slug": slug,
            "title": title,
            "description": description,
            "image": image,
            "author": author,
            "published_at": published_at,
            "modified_at": modified_at,
            "tags": tags,
            "read_time_minutes": read_time,
            "content": content,
            "url": url,
        }

    async def search(self, query: str, page: int = 1) -> dict:
        """Cari artikel berdasarkan keyword menggunakan Blogger search."""
        # Blogger search endpoint
        url = f"{BASE_URL}/search?q={query}"
        if page > 1:
            url += f"&start={( page - 1) * 10}"

        soup = await self._fetch(url)

        articles = []
        items = soup.select("div.body-post, div.home-right, article, div.clear")

        if not items:
            items = soup.select(".story-link")

        for item in items:
            try:
                parsed = parse_article_card(item)
                if parsed["title"] and parsed["slug"]:
                    articles.append(parsed)
            except Exception:
                continue

        # Deduplikasi berdasarkan slug
        seen = set()
        unique = []
        for a in articles:
            if a["slug"] not in seen:
                seen.add(a["slug"])
                unique.append(a)

        # Cek next page
        next_page_el = soup.select_one("a.blog-pager-older-link, #blog-pager-older-link")
        has_next = next_page_el is not None

        return {
            "query": query,
            "page": page,
            "total_results": len(unique),
            "has_next_page": has_next,
            "articles": unique,
        }

    async def get_labels(self) -> dict:
        """Ambil semua label/kategori dari sidebar."""
        soup = await self._fetch(BASE_URL)

        labels = []
        label_els = soup.select(
            '.label-list a, .widget .label-list a, '
            '#Label1 a, .cloud-label a, '
            'ul.labels li a'
        )

        for el in label_els:
            href = el.get("href", "")
            slug_match = re.search(r"/label/(.+?)(?:\?|$)", href)
            label_slug = slug_match.group(1) if slug_match else ""
            name = el.get_text(strip=True)
            if name and label_slug:
                labels.append({
                    "name": name,
                    "slug": label_slug,
                    "url": href if href.startswith("http") else f"{BASE_URL}{href}",
                })

        return {
            "total": len(labels),
            "labels": labels,
        }
