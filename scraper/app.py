import os, re, sqlite3, random, datetime, hashlib
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = "/data/db/products.sqlite"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DEFAULT_PROMO = os.getenv("")
CATEGORY_URLS = [u.strip() for u in os.getenv("CATEGORY_URLS", "").split(",") if u.strip()]
CHANGE_EVERY = int(os.getenv("CHANGE_CATEGORY_EVERY_DAYS", "7"))
UA = {"User-Agent": "Mozilla/5.0 ZanimoContentBot/1.0"}

app = FastAPI(title="Zanimo scraper")

class ManualReq(BaseModel):
    url: str
    promo: str | None = None
    tagline: bool | None = None

class DailyReq(BaseModel):
    promo: str | None = None
    category_url: str | None = None


def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS used_products (url TEXT PRIMARY KEY, used_at TEXT)")
    return con


def soup_url(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()
def normalize_url(u: str) -> str:
    """
    Nettoie les URLs mal copiées depuis n8n, navigateur ou ChatGPT.
    Accepte:
    - https://zanimo.tn/...
    - =https://zanimo.tn/...
    - [https://zanimo.tn/...](https://zanimo.tn/...)
    - =[https://zanimo.tn/...](https://zanimo.tn/...)
    """
    u = clean(u).strip("\"'")

    if u.startswith("="):
        u = u[1:].strip()

    # Corrige le format Markdown [url](url)
    m = re.match(r"\[(https?://[^\]]+)\]\((https?://[^\)]+)\)", u)
    if m:
        u = m.group(2)

    # Extrait une URL propre si du texte l'entoure
    m = re.search(r"https?://[^\s\)\]]+", u)
    if m:
        u = m.group(0)

    return u

def meta(soup, prop):
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return clean(tag.get("content")) if tag and tag.get("content") else ""


def extract_product(url: str) -> dict:
    soup = soup_url(url)
    title = meta(soup, "og:title") or clean((soup.find("h1") or soup.find("title")).get_text(" "))
    desc = meta(soup, "og:description") or clean(" ".join(p.get_text(" ") for p in soup.find_all("p")[:6]))
    img = meta(soup, "og:image")
    if not img:
        image_tags = soup.find_all("img")
        candidates = []
        for im in image_tags:
            src = im.get("src") or im.get("data-src") or im.get("data-lazy-src")
            if src and not src.startswith("data:"):
                candidates.append(urljoin(url, src))
        img = candidates[0] if candidates else ""
    else:
        img = urljoin(url, img)

    text = soup.get_text(" ")
    price = ""
    m = re.search(r"(\d+[\d\s,.]*)\s*(DT|TND|د\.ت)", text, flags=re.I)
    if m:
        price = clean(m.group(0))

    return {
        "url": url,
        "id": hashlib.sha1(url.encode()).hexdigest()[:12],
        "name": title[:140] or "Produit Zanimo",
        "description": desc[:500],
        "price": price,
        "image_url": img,
        "source": "zanimo.tn",
    }


def category_links(category_url: str) -> list[str]:
    soup = soup_url(category_url)
    base = f"{urlparse(category_url).scheme}://{urlparse(category_url).netloc}"
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base, href)
        if "/product" in full or "/products/" in full:
            if "category/" not in full:
                links.append(full)
    # fallback: any link with products and boutique
    if not links:
        for a in soup.find_all("a", href=True):
            full = urljoin(base, a["href"])
            if "zanimo.tn" in full and "product" in full:
                links.append(full)
    return list(dict.fromkeys(links))


def choose_category():
    if not CATEGORY_URLS:
        raise HTTPException(400, "Aucune CATEGORY_URLS configurée")
    day_index = datetime.date.today().toordinal() // max(1, CHANGE_EVERY)
    return CATEGORY_URLS[day_index % len(CATEGORY_URLS)]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/product")
def product(req: ManualReq):
    url = normalize_url(req.url)

    p = extract_product(url)

    # Important:
    # Si promo = "", on garde vide.
    # Si promo = None, seulement là on utilise DEFAULT_PROMO.
    promo = DEFAULT_PROMO if req.promo is None else req.promo

   
    return {
        "product": p,
        "promo": promo,
        "normalized_url": url,
        "tagline": bool(req.tagline)
    }
@app.post("/daily")
def daily(req: DailyReq):
    cat = req.category_url or choose_category()
    links = category_links(cat)
    if not links:
        raise HTTPException(404, f"Aucun produit trouvé dans la catégorie: {cat}")
    con = db()
    used = {r[0] for r in con.execute("SELECT url FROM used_products").fetchall()}
    candidates = [u for u in links if u not in used] or links
    url = random.choice(candidates)
    p = extract_product(url)
    con.execute("INSERT OR REPLACE INTO used_products(url, used_at) VALUES(?, ?)", (url, datetime.datetime.now().isoformat()))
    con.commit(); con.close()

    return {
      "product": p,
      "promo": promo,
      "category_url": normalize_url(cat),
      
     }
