import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
from queue import Queue

# Nastavení procházených domén
BASE_URLS = ["https://www.novinky.cz", "https://www.idnes.cz", "https://www.ctk.cz"]

# Filtr pro článkové odkazy (příklad - může se lišit dle webu)
ARTICLE_PATTERNS = ["novinky.cz/clanek", "idnes.cz/", "ctk.cz/"]

# Fronta URL a seznam navštívených stránek
url_queue = Queue()
visited_urls = set()

# Výstupní JSON soubor
OUTPUT_FILE = "articles.json"
articles = []

# Interval pro průběžné ukládání
SAVE_INTERVAL = 5

def fetch_html(url):
    """Stáhne HTML obsah stránky."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Chyba při stahování {url}: {e}")
        return None

def parse_article(url, soup):
    """Vyparsuje článek a vrátí jeho data."""
    try:
        # Nadpis
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Neznámý nadpis"

        # Kategorie
        category = (
            soup.find("meta", {"name": "category"})["content"]
            if soup.find("meta", {"name": "category"}) else
            soup.find("meta", {"property": "article:section"})["content"]
            if soup.find("meta", {"property": "article:section"}) else
            soup.find("meta", {"name": "section"})["content"]
            if soup.find("meta", {"name": "section"}) else
            soup.find("div", class_="category").get_text(strip=True)
            if soup.find("div", class_="category") else
            "Neznámá kategorie"
        )

        # Počet komentářů
        comments = "0"  # Defaultní hodnota
        comment_element = soup.find("a", {"class": "c_at c_al e_dW"})  # Podle třídy z obrázku
        if comment_element:
            comments = comment_element.get_text(strip=True)

        # Počet fotek
        images = len(soup.find_all("img"))

        # Obsah článku
        content = " ".join([p.get_text(strip=True) for p in soup.find_all("p")])

        # Datum vytvoření
        date = soup.find("time")["datetime"] if soup.find("time") else "Neznámé datum"

        # Vrácení slovníku s daty článku
        return {
            "url": url,
            "title": title,
            "category": category,
            "comments": comments,
            "images": images,
            "content": content,
            "date": date
        }
    except Exception as e:
        print(f"Chyba při parsování článku z {url}: {e}")
        return None

def save_to_json(data, filename):
    """Uloží data do JSON souboru."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def crawl():
    """Spustí crawler pro dané weby."""
    # Přidání základních URL do fronty
    for base_url in BASE_URLS:
        url_queue.put(base_url)

    while not url_queue.empty() and len(articles) < 2000:  # Omezení počtu článků
        url = url_queue.get()
        if url in visited_urls:
            continue
        
        print(f"Procházím: {url}")
        visited_urls.add(url)
        html = fetch_html(url)
        if not html:
            continue
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Pokud je URL článková, zpracujeme ji
        if any(pattern in url for pattern in ARTICLE_PATTERNS):
            article_data = parse_article(url, soup)
            if article_data:
                articles.append(article_data)
                print(f"Článek uložen: {article_data['title']}")

        # Přidání nových odkazů do fronty
        for link in soup.find_all("a", href=True):
            full_url = urljoin(url, link["href"])
            if full_url not in visited_urls and any(pattern in full_url for pattern in ARTICLE_PATTERNS):
                url_queue.put(full_url)

        # Průběžné ukládání dat
        if len(articles) % SAVE_INTERVAL == 0:
            save_to_json(articles, OUTPUT_FILE)
            print(f"Průběžně uloženo {len(articles)} článků.")

    # Konečné uložení do JSON souboru
    save_to_json(articles, OUTPUT_FILE)
    print(f"Hotovo! Data uložena v {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl()