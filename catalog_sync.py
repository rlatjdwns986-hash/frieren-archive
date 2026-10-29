#!/usr/bin/env python3
"""Conservative daily collector for official Frieren merchandise listing pages.

This intentionally collects only metadata visible in official pages. Unknown facts stay null.
Respect each source site's terms, robots.txt, rate limits, and image usage requirements.
"""
from __future__ import annotations
import hashlib, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
OUT = ROOT / "catalog.json"
UA = "FrierenArchiveCatalogBot/1.0 (+personal collection catalog; respectful low-frequency access)"
TIMEOUT = 25
EXCLUDED = re.compile(r"(缶\s*バッジ|缶バッジ|缶バッチ|カンバッジ|can[\s-]*badge|缶バッヂ|캔\s*뱃지|캔뱃지|캔\s*배지)", re.I)
FRIEREN = re.compile(r"(フリーレン|葬送のフリーレン|frieren|sousou no frieren|frieren: beyond journey.s end)", re.I)
MAKERS = set(CONFIG.get("allowed_maker_domains", []))
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8,ko;q=0.6"})

def norm_url(url: str) -> str:
    url = urldefrag(url)[0]
    p = urlparse(url)
    return p._replace(query="", fragment="").geturl().rstrip("/")

def digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:20]

def get_html(url: str):
    try:
        r = SESSION.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type", ""):
            return None
        return r.text
    except Exception as e:
        print(f"[WARN] fetch failed: {url} ({e})")
        return None

def meta(soup, *names):
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None

def title_from_anchor(a):
    return " ".join(a.get_text(" ", strip=True).split())

def category_for(title: str) -> str | None:
    if EXCLUDED.search(title):
        return None
    t = title.lower()
    if re.search(r"(figure|フィギュア|スケールフィギュア|プライズ)", t): return "피규어"
    if re.search(r"(ぬいぐるみ|マスコット|plush|doll|ぬい|인형)", t): return "봉제·인형"
    if re.search(r"(アクリル|キーホルダー|キーチェーン|acrylic|keychain|키링)", t): return "아크릴·키링"
    if re.search(r"(カード|ブロマイド|クリアカード|card|フォトカード)", t): return "카드·브로마이드"
    if re.search(r"(カプセル|ガシャポン|ガチャ|capsule|gacha)", t): return "가챠·캡슐토이"
    if re.search(r"(tシャツ|パーカー|ジャケット|アパレル|shirt|hoodie|clothing)", t): return "의류·패션"
    if re.search(r"(特典|限定|bonus|limited|特装|購入特典)", t): return "특전·한정 굿즈"
    if re.search(r"(マグカップ|タオル|ポーチ|時計|バッグ|ケース|雑貨|生活|香水|ルーム)", t): return "생활 잡화"
    return "기타"

def clean_image(src, base):
    if not src: return None
    src = src.strip()
    if src.startswith("data:") or src.startswith("blob:"): return None
    return urljoin(base, src)

def extract_from_page(url, source_name, is_official=True):
    html = get_html(url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    found = []
    # Product detail pages can expose OG/Twitter metadata.
    page_title = meta(soup, "og:title", "twitter:title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    page_desc = meta(soup, "og:description", "description", "twitter:description")
    image = clean_image(meta(soup, "og:image", "twitter:image"), url)
    if page_title and FRIEREN.search(page_title + " " + (page_desc or "")):
        title = re.sub(r"\s*[|｜]\s*.*$", "", page_title).strip()
        cat = category_for(title)
        if cat:
            found.append(make_item(title, url, image, source_name, cat, None, None, is_official))
    # Listing pages: links with a useful visible product title. Prefer links with images.
    for a in soup.find_all("a", href=True):
        title = title_from_anchor(a)
        if not title or len(title) < 4 or len(title) > 180: continue
        if not FRIEREN.search(title) and not FRIEREN.search(url) and not FRIEREN.search(a.get("href", "")):
            # On the official Frieren goods listing, the page context itself establishes relevance.
            if "frieren-anime.jp/goods" not in url: continue
        cat = category_for(title)
        if not cat: continue
        href = norm_url(urljoin(url, a["href"]))
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"): continue
        if href == norm_url(url): continue
        img = a.find("img")
        img_src = None
        if img:
            img_src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("srcset", "").split(",")[0].strip().split(" ")[0]
        img_url = clean_image(img_src, url)
        # Avoid capturing navigation/menu links unless they look product-like.
        if title.lower() in {"goods", "商品情報", "グッズ", "more", "詳しくはこちら", "詳細はこちら"}: continue
        found.append(make_item(title, href, img_url, source_name, cat, None, None, is_official))
    return found

def make_item(title, url, image_url, source_name, category, release_date, price, official):
    title = " ".join(title.split())
    return {
        "catalog_id": digest(norm_url(url) + "|" + title.casefold()),
        "title": title,
        "category": category,
        "maker": None,
        "series": None,
        "release_date": release_date,
        "price": price,
        "image_url": image_url,
        "source_url": norm_url(url),
        "source_name": source_name,
        "verified": bool(official),
        "verification_status": "source-page-found; product facts may need review",
        "last_seen_at": datetime.now(timezone.utc).isoformat()
    }

def is_allowed_maker_link(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in MAKERS)

def main():
    old = {}
    if OUT.exists():
        try:
            data = json.loads(OUT.read_text(encoding="utf-8"))
            old = {x.get("catalog_id"): x for x in data.get("items", [])}
        except Exception:
            pass
    collected = []
    for source in CONFIG.get("sources", []):
        url = source["url"]
        html = get_html(url)
        if not html: continue
        soup = BeautifulSoup(html, "html.parser")
        # Main listing extraction.
        collected.extend(extract_from_page(url, source.get("name", url), source.get("official", False)))
        # Only follow external links on an explicitly trusted manufacturer domain allowlist.
        # To keep requests low, crawl product links from this source only when they are direct product links.
        for a in soup.find_all("a", href=True):
            href = norm_url(urljoin(url, a["href"]))
            if is_allowed_maker_link(href) and FRIEREN.search(title_from_anchor(a) + " " + href):
                title = title_from_anchor(a)
                cat = category_for(title)
                if cat:
                    time.sleep(0.4)
                    collected.extend(extract_from_page(href, urlparse(href).hostname or "manufacturer", True))
    # Deduplicate on normalized source URL; keep the richer record and preserve prior unknown values.
    merged = {}
    for item in list(old.values()) + collected:
        if not item.get("title") or EXCLUDED.search(item["title"]): continue
        key = norm_url(item.get("source_url") or "") or item.get("catalog_id")
        prev = merged.get(key)
        if prev:
            for field, value in item.items():
                if value not in (None, "", []):
                    prev[field] = value
            prev["catalog_id"] = prev.get("catalog_id") or item["catalog_id"]
        else:
            merged[key] = dict(item)
    items = sorted(merged.values(), key=lambda x: (x.get("title") or "").casefold())
    result = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(CONFIG.get("sources", [])),
        "items": items
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} catalog candidates to {OUT}")

if __name__ == "__main__":
    main()
