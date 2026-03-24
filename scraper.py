import json
import re
from urllib.parse import urlparse

import cloudscraper
import requests
from bs4 import BeautifulSoup


BLOCK_MARKERS = [
    "ich bin kein roboter",
    "captcha",
    "access denied",
    "just a moment",
    "verify you are human",
]


def _norm(s):
    if not s:
        return None
    return re.sub(r"\s+", " ", str(s)).strip()


def parse_price(text):
    if not text:
        return None

    # Prefer values explicitly tied to euro signs.
    euro_values = re.findall(r"(\d{1,9}(?:[.\s]\d{3})*(?:,\d{1,2})?)\s*(?:\u20AC|EUR|Euro)", text, re.IGNORECASE)
    if euro_values:
        parsed = []
        for candidate in euro_values:
            value = _to_float(candidate)
            if value:
                parsed.append(value)
        if parsed:
            plausible = [p for p in parsed if 100 <= p <= 50000000]
            if plausible:
                return plausible[0]
            return parsed[0]

    return _to_float_from_text(text)


def parse_sqm(text):
    if not text:
        return None
    m = re.search(r"(\d{1,4}(?:[.,]\d{1,2})?)\s*m(?:²|2)?", text, re.IGNORECASE)
    if not m:
        return None
    value = _to_float(m.group(1))
    if value and 5 <= value <= 2000:
        return value
    return None


def parse_rooms(text):
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:zimmer|zi\.?|z)", text, re.IGNORECASE)
    if m:
        value = _to_float(m.group(1))
        if value and 0.5 <= value <= 20:
            return value
    return None


def _to_float(raw):
    if raw is None:
        return None
    s = str(raw).strip().replace(" ", "")

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # 1.234,56 -> 1234.56
        s = s.replace(".", "").replace(",", ".")
    elif has_comma:
        # 1234,56 -> 1234.56
        s = s.replace(",", ".")
    elif has_dot:
        # 1.234 -> 1234 (thousands) but 20.76 should stay decimal.
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _to_float_from_text(text):
    m = re.search(r"(\d{1,9}(?:[.\s]\d{3})*(?:,\d+)?)", text)
    if not m:
        return None
    return _to_float(m.group(1))


def _domain(url):
    netloc = (urlparse(url).netloc or "").lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _is_blocked_page(html, title):
    blob = f"{title or ''} {html[:5000] if html else ''}".lower()
    return any(marker in blob for marker in BLOCK_MARKERS)


def _extract_json_ld(soup):
    out = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                out.extend(parsed)
            else:
                out.append(parsed)
        except json.JSONDecodeError:
            continue
    return out


def _find_first_jsonld_key(items, keys):
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in keys:
            if key in item and item[key]:
                return item[key]
    return None


def _extract_from_jsonld(items, data):
    if not data.get("title"):
        title = _find_first_jsonld_key(items, ["name", "headline"])
        data["title"] = _norm(title) or data.get("title")

    if not data.get("picture_url"):
        img = _find_first_jsonld_key(items, ["image"])
        if isinstance(img, list) and img:
            img = img[0]
        if isinstance(img, dict):
            img = img.get("url")
        if isinstance(img, str):
            data["picture_url"] = img

    if not data.get("price"):
        for item in items:
            if not isinstance(item, dict):
                continue
            offers = item.get("offers")
            if isinstance(offers, dict) and offers.get("price"):
                data["price"] = _to_float(offers.get("price"))
                if data["price"]:
                    break

    if not data.get("room_count"):
        rooms = _find_first_jsonld_key(items, ["numberOfRooms"])
        if rooms is not None:
            data["room_count"] = _to_float(rooms)

    if not data.get("size_sqm"):
        floor_size = _find_first_jsonld_key(items, ["floorSize"])
        if isinstance(floor_size, dict) and floor_size.get("value"):
            data["size_sqm"] = _to_float(floor_size.get("value"))


def get_title(soup):
    meta_title = soup.find("meta", property="og:title")
    if meta_title and meta_title.get("content"):
        return _norm(meta_title.get("content"))
    title_tag = soup.find("title")
    if title_tag:
        return _norm(title_tag.get_text())
    return None


def get_picture(soup):
    img_tag = soup.find("meta", property="og:image")
    if img_tag and img_tag.get("content"):
        url = img_tag.get("content")
        if "logo" not in url.lower() and "nopic" not in url.lower():
            return url

    img = soup.find("img")
    if img and img.get("src") and str(img.get("src")).startswith("http"):
        return img.get("src")
    return None


class FakeResponse:
    def __init__(self, text, url, status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code


def _fetch(url):
    if "immobilienscout24.de" in url:
        from seleniumbase import Driver
        import time
        import random
        from selenium.common.exceptions import TimeoutException
        
        # Retry up to 3 times to bypass flaky bot detection
        for attempt in range(3):
            driver = None
            try:
                driver = Driver(uc=True, headless=True)
                driver.get(url)
                time.sleep(3 + random.uniform(1, 3)) # Wait for JS/Captcha to resolve
                
                # If still blocked, wait a bit longer to see if UC handles it
                if "ich bin kein roboter" in driver.page_source.lower() or "captcha" in driver.page_source.lower() or "verify you are human" in driver.page_source.lower():
                    time.sleep(5)
                    
                html = driver.page_source
                current_url = driver.current_url
                
                # Check explicitly if we got passed the bot check
                if "ich bin kein roboter" not in html.lower() and "verify you are human" not in html.lower():
                    try:
                        driver.quit()
                    except:
                        pass
                    return FakeResponse(html, current_url)
                    
            except Exception as e:
                print(f"Selenium attempt {attempt+1} failed for {url}: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            
            # Brief pause before retrying
            time.sleep(2)
            
        # Fallback to last fetched HTML or empty if all retries failed
        return FakeResponse(locals().get('html', ''), locals().get('current_url', url))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
    response = scraper.get(url, headers=headers, timeout=20)
    return response


def _parse_kleinanzeigen(soup, data):
    price_tag = soup.find("h2", id="viewad-price")
    if price_tag:
        data["price"] = parse_price(price_tag.get_text())

    for detail in soup.find_all("li", class_=re.compile("addetailslist--detail")):
        txt = _norm(detail.get_text(" ")) or ""
        value = detail.find("span", class_=re.compile("detail--value"))
        value_txt = _norm(value.get_text(" ")) if value else txt

        if "wohnfl" in txt.lower():
            data["size_sqm"] = data.get("size_sqm") or parse_sqm(value_txt)
        if "zimmer" in txt.lower():
            data["room_count"] = data.get("room_count") or parse_rooms(value_txt + " Zimmer")

    loc_tag = soup.find("span", id="viewad-locality")
    if loc_tag:
        data["location"] = _norm(loc_tag.get_text(" "))


def _parse_immowelt_or_rheinpfalz(soup, data):
    selectors = [
        ("strong", {"data-cy": "expose-obprice"}, "price"),
        ("span", {"data-cy": "expose-obarea"}, "size"),
        ("span", {"data-cy": "expose-obrooms"}, "rooms"),
        ("span", {"data-cy": "expose-obaddress"}, "location"),
    ]

    extracted = {}
    for tag, attrs, key in selectors:
        node = soup.find(tag, attrs=attrs)
        if node:
            extracted[key] = _norm(node.get_text(" "))

    if extracted.get("price"):
        data["price"] = data.get("price") or parse_price(extracted["price"])
    if extracted.get("size"):
        data["size_sqm"] = data.get("size_sqm") or parse_sqm(extracted["size"])
    if extracted.get("rooms"):
        data["room_count"] = data.get("room_count") or parse_rooms(extracted["rooms"] + " Zimmer")
    if extracted.get("location"):
        data["location"] = data.get("location") or extracted["location"]

    # Label-based fallback for pages that changed data-cy attributes.
    for node in soup.find_all(string=re.compile(r"(Kaufpreis|Preis|Wohnfl.che|Zimmer)", re.IGNORECASE)):
        chunk = _norm(node.parent.get_text(" ") if node.parent else node) or ""
        low = chunk.lower()
        if ("kaufpreis" in low or re.search(r"\bpreis\b", low)) and not data.get("price"):
            data["price"] = parse_price(chunk)
        if "wohnfl" in low and not data.get("size_sqm"):
            data["size_sqm"] = parse_sqm(chunk)
        if "zimmer" in low and not data.get("room_count"):
            data["room_count"] = parse_rooms(chunk)

    if data.get("price") and data["price"] < 10:
        data["price"] = None

    if not data.get("price") and data.get("title"):
        data["price"] = parse_price(data["title"])

    if not data.get("room_count") and data.get("title"):
        data["room_count"] = parse_rooms(data["title"] + " Zimmer")


def _parse_rheinpfalz(soup, data):
    price_box = soup.find("div", class_=re.compile(r"eps-item-price"))
    if price_box:
        data["price"] = data.get("price") or parse_price(_norm(price_box.get_text(" ")))

    rooms_box = soup.find("div", class_=re.compile(r"eps-item-rooms"))
    if rooms_box:
        data["room_count"] = data.get("room_count") or parse_rooms(_norm(rooms_box.get_text(" ")) + " Zimmer")

    area_box = soup.find("div", class_=re.compile(r"eps-item-area"))
    if area_box:
        data["size_sqm"] = data.get("size_sqm") or parse_sqm(_norm(area_box.get_text(" ")))

    location_box = soup.find("div", class_=re.compile(r"eps-item-location"))
    if location_box:
        data["location"] = data.get("location") or _norm(location_box.get_text(" "))


def _parse_immoscout(soup, data):
    title = soup.find("h1")
    if title:
        data["title"] = data.get("title") or _norm(title.get_text(" "))

    # ImmoScout uses specific is24qa-* classes
    kaufpreis_tag = soup.find(class_="is24qa-kaufpreis")
    if not kaufpreis_tag:
        kaufpreis_tag = soup.find(class_="is24qa-kaltmiete")
    if kaufpreis_tag:
        data["price"] = data.get("price") or parse_price(kaufpreis_tag.get_text(" "))

    wohnflaeche_tag = soup.find(class_=re.compile(r"is24qa-wohnflaeche"))
    if wohnflaeche_tag:
        data["size_sqm"] = data.get("size_sqm") or parse_sqm(wohnflaeche_tag.get_text(" "))

    zimmer_tag = soup.find(class_=re.compile(r"is24qa-zimmer"))
    if zimmer_tag:
        data["room_count"] = data.get("room_count") or parse_rooms(zimmer_tag.get_text(" ") + " Zimmer")

    location_tag = soup.find(class_=re.compile(r"zip-region-and-country"))
    if location_tag:
        data["location"] = data.get("location") or _norm(location_tag.get_text(" "))

    # If the precise classes aren't found, try finding them in definitions
    for node in soup.find_all(string=re.compile(r"(Kaufpreis|Kaltmiete|Wohnfl.che|Zimmer)\b", re.IGNORECASE)):
        parent = node.parent
        sibling = parent.find_next_sibling() if parent else None
        if not sibling:
            continue
            
        txt = _norm(sibling.get_text(" "))
        low = _norm(node).lower()
        
        if "kaufpreis" in low or "kaltmiete" in low:
            data["price"] = data.get("price") or parse_price(txt)
        elif "wohnfl" in low:
            data["size_sqm"] = data.get("size_sqm") or parse_sqm(txt)
        elif "zimmer" in low:
            data["room_count"] = data.get("room_count") or parse_rooms(txt)


def scrape_apartment_details(url):
    try:
        response = _fetch(url)
    except requests.RequestException as exc:
        return False, {"error": f"Network error: {exc}"}

    if response.status_code in (404, 410):
        return False, {"error": "Listing not found (404/410).", "unavailable": True}

    resolved_url = response.url
    domain = _domain(resolved_url)
    html = response.text or ""

    soup = BeautifulSoup(html, "html.parser")
    title = get_title(soup)
    if _is_blocked_page(html, title):
        return False, {
            "error": "Blocked by anti-bot protection on source website.",
            "blocked": True,
            "resolved_url": resolved_url,
        }

    data = {
        "resolved_url": resolved_url,
        "title": title,
        "price": None,
        "room_count": None,
        "size_sqm": None,
        "location": None,
        "picture_url": get_picture(soup),
        "site": domain,
    }

    json_ld = _extract_json_ld(soup)
    if json_ld:
        _extract_from_jsonld(json_ld, data)

    if "kleinanzeigen.de" in domain:
        _parse_kleinanzeigen(soup, data)
    elif "immo.rheinpfalz.de" in domain:
        _parse_rheinpfalz(soup, data)
    elif "immowelt.de" in domain:
        _parse_immowelt_or_rheinpfalz(soup, data)
    elif "immobilienscout24.de" in domain:
        _parse_immoscout(soup, data)

    body_text = _norm(soup.get_text(" ")) or ""
    if not data.get("price"):
        for label in ["kaufpreis", "kaltmiete", "warmmiete", "miete", "preis"]:
            labeled = re.search(
                rf"(?:{label})[^\u20AC]{{0,80}}(\d{{1,9}}(?:[.\s]\d{{3}})*(?:,\d{{1,2}})?)\s*\u20AC",
                body_text,
                re.IGNORECASE,
            )
            if labeled:
                data["price"] = _to_float(labeled.group(1))
                break
        if not data.get("price") and data.get("title"):
            data["price"] = parse_price(data["title"])

    if not data.get("size_sqm"):
        if data.get("title"):
            data["size_sqm"] = parse_sqm(data["title"])
        if not data.get("size_sqm"):
            sqm_labeled = re.search(r"wohnfl[^\d]{0,20}(\d{1,4}(?:[.,]\d{1,2})?)\s*m", body_text, re.IGNORECASE)
            if sqm_labeled:
                data["size_sqm"] = _to_float(sqm_labeled.group(1))

    if not data.get("room_count"):
        if data.get("title"):
            data["room_count"] = parse_rooms(data["title"] + " Zimmer")
        if not data.get("room_count"):
            room_labeled = re.search(r"zimmer[^\d]{0,20}(\d+(?:[.,]\d+)?)", body_text, re.IGNORECASE)
            if room_labeled:
                data["room_count"] = _to_float(room_labeled.group(1))

    if not data.get("location") and data.get("title"):
        # Fallback: many titles include city after a comma, e.g. "...,Kaiserslautern (67663)".
        m = re.search(r",\s*([^,()]+)\s*(?:\(|$)", data["title"])
        if m:
            data["location"] = _norm(m.group(1))

    has_details = any(
        [
            data.get("title"),
            data.get("price"),
            data.get("room_count"),
            data.get("size_sqm"),
            data.get("location"),
            data.get("picture_url"),
        ]
    )

    if not has_details:
        return False, {"error": "Could not extract useful information.", "resolved_url": resolved_url}

    return True, data