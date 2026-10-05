"""
Data collection programme for the MSc Psychology dissertation:
Validation of Automated Text Classification of Adult ADHD Documentation Against Human Judgement.

Searches for publicly available documents, pools every unique URL, puts the pool in a
reproducible random order and downloads documents in that order until the target is reached.
Every download respects robots.txt and waits politely between requests to the same website.

Before a fresh run: empty the PDF folder and delete any earlier output files.
"""

# Libraries
import datetime
import hashlib
import io
import os
import random
import time
import urllib.parse
import urllib.robotparser as robotparser

import pandas as pd
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# Settings
Target_documents = 250
Results_per_query = 30
Request_delay = 3   # seconds between requests to the same website
Search_delay = 3    # seconds between searches
Min_text_chars = 500
Random_seed = 2026  # fixed seed so the random order can be reproduced

# Restricted raw-document folder on University OneDrive
Raw_folder = r"PATH\TO\RESTRICTED\RAW\DOCUMENTS\FOLDER"
Output_file = os.path.join(Raw_folder, "dissertation_corpus.csv")
PDF_directory = os.path.join(Raw_folder, "pdfs")
Log_file = os.path.join(Raw_folder, "sampling_log.csv")

# Test queries (unrelated topic), to be replaced with the ADHD queries for data collection
seed_queries = [
    'Game of Thrones Online RPG',
    'Elderscrolls Online',
    'Elderscrolls RPG',
    'Resident Evil',
    'Pathfinder Online RPG',
]

subjects = [
    'Game of Thrones',
    'Elderscrolls',
    'Resident Evil',
    'Pathfinder',
]

modifiers = [
    'Online RPG',
    'RPG',
    'Game',
]

# Every subject paired with every modifier, after the seed queries
queries = list(seed_queries)
for s in subjects:
    for m in modifiers:
        queries.append(s + ' ' + m)

# Identifies the scraper as an academic research project (BPS internet-mediated research guidance)
headers = {
    "User-Agent": "MSc Computational Psychology Research Project - Text Mining (Academic/Non-Commercial)"
}

session = requests.Session()   # one connection per website, reused for every request
session.headers.update(headers)


# ---------------------------------------------------------------------------
# Ethical crawling: robots.txt (read once per website) and a polite delay
# ---------------------------------------------------------------------------
robots_cache = {}
last_request = {}


def polite_wait(host, delay):
    """Wait until at least `delay` seconds have passed since the last request to this website."""
    wait = delay - (time.time() - last_request.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    last_request[host] = time.time()


def get_robots(scheme, host):
    """Fetch and read a website's robots.txt once, then reuse it from the cache."""
    if host in robots_cache:
        return robots_cache[host]

    rp = robotparser.RobotFileParser()
    robots_url = f"{scheme}://{host}/robots.txt"
    try:
        polite_wait(host, Request_delay)
        r = session.get(robots_url, timeout=15)
        if r.status_code in (401, 403) or r.status_code >= 500:
            rp.disallow_all = True    # access refused or server error: treat everything as off limits
        elif r.status_code >= 400:
            rp.allow_all = True       # no robots.txt: no restrictions
        else:
            rp.parse(r.text.splitlines())
    except requests.RequestException as e:
        print(f"Could not read {robots_url} ({e}); skipping this site to be safe")
        rp = None

    robots_cache[host] = rp
    return rp


def is_allowed_by_robots(url):
    """True if robots.txt allows this research user agent to fetch the URL."""
    parsed_url = urllib.parse.urlparse(url)
    rp = get_robots(parsed_url.scheme, parsed_url.netloc)
    if rp is None:
        return False
    return rp.can_fetch(headers["User-Agent"], url)


def crawl_delay(url):
    """The website's requested crawl delay, never shorter than our own Request_delay."""
    parsed_url = urllib.parse.urlparse(url)
    rp = get_robots(parsed_url.scheme, parsed_url.netloc)
    if rp is None:
        return Request_delay
    delay = rp.crawl_delay(headers["User-Agent"])
    return max(Request_delay, delay or 0)


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------
def get_urls_from_duckduckgo(query, max_results=Results_per_query):
    """Return the result URLs for one DuckDuckGo search."""
    urls = []
    print(f"Searching DuckDuckGo for: '{query}'")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, region='uk-en', safesearch='off', max_results=max_results)
            for result in results:
                urls.append(result['href'])
    except Exception as e:
        print(f"Search failed for '{query}': {e}")
    return urls


# ---------------------------------------------------------------------------
# PDF handling: extract the text first; save the original only if the text is usable
# ---------------------------------------------------------------------------
def extract_pdf_text(url, content):
    """Return the PDF's text with a blank line between pages, or None if it is unreadable or too short."""
    if PdfReader is None:
        print("PdfReader not available. Skipping text extraction.")
        return None
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            reader.decrypt('')        # many public PDFs are locked with an empty password
        pages = []
        for i, page in enumerate(reader.pages):
            try:
                pages.append(page.extract_text() or "")
            except Exception as e:    # one bad page shouldn't lose the whole document
                print(f"Error extracting text from page {i + 1} of PDF {url}: {e}")
        text = "\n\n".join(p.strip() for p in pages if p.strip())
        if len(text) < Min_text_chars:
            return None
        return text
    except Exception as e:
        print(f"Error reading PDF {url}: {e}")
        return None


def download_pdf(url, content):
    """Save the original PDF, named by a hash of its content. Returns (path, already_saved)."""
    content_hash = hashlib.md5(content).hexdigest()
    pdf_path = os.path.join(PDF_directory, f"{content_hash}.pdf")
    if os.path.exists(pdf_path):
        return pdf_path, True         # the same file was already found at another URL
    with open(pdf_path, 'wb') as f:
        f.write(content)
    return pdf_path, False


# ---------------------------------------------------------------------------
# Downloading pages and extracting the readable text
# ---------------------------------------------------------------------------
def scrape_page_text(url):
    """Return (text, pdf_bytes). pdf_bytes is None for web pages; text is None if unusable."""
    host = urllib.parse.urlparse(url).netloc
    try:
        polite_wait(host, crawl_delay(url))
        response = session.get(url, timeout=20)

        if response.status_code != 200:
            print(f"Skipped {url} - Status Code: {response.status_code}")
            return None, None

        content_type = response.headers.get('Content-Type', '').lower()
        if "pdf" in content_type or url.lower().endswith('.pdf'):
            return extract_pdf_text(url, response.content), response.content

        if "html" not in content_type:
            print(f"Skipped {url} - Content-Type: {content_type}")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Isolate the main content of the page
        main_content = soup.find('main') or soup.find(id='maincontent') or soup.find(role='main') or soup

        # 2. Remove navigation, headers, footers and sidebars
        for element in main_content.find_all(['nav', 'aside', 'footer', 'header']):
            element.decompose()
        for element in main_content.find_all('div', class_=lambda x: x and any(
                word in x.lower() for word in ['sidebar', 'menu', 'widget', 'breadcrumb'])):
            element.decompose()

        # 3. Keep only headings, paragraphs and list items, with a blank line between each
        content_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']
        extracted_chunks = []
        for element in main_content.find_all(content_tags):
            if element.find_parent(content_tags):   # already captured by its parent, e.g. <p> inside <li>
                continue
            text = element.get_text(separator=' ', strip=True)
            if text:
                extracted_chunks.append(text)

        clean_text = "\n\n".join(extracted_chunks)
        if len(clean_text) < Min_text_chars:
            print(f"Skipped {url} - Text too short ({len(clean_text)} characters)")
            return None, None
        return clean_text, None

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None, None


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    TESTING = True  # set to False for the real data collection

    if TESTING:
        # Test runs stay out of the restricted raw-document folder
        run_queries = seed_queries
        per_query_limit = 5
        target = 10
        Output_file = "dummy_corpus.csv"
        PDF_directory = "test_pdfs"
        Log_file = "test_sampling_log.csv"
    else:
        run_queries = queries
        per_query_limit = Results_per_query
        target = Target_documents
    os.makedirs(PDF_directory, exist_ok=True)

    # Stage 1: run every query and pool the unique URLs (searching only, nothing downloaded)
    found = {}
    for query in run_queries:
        for url in get_urls_from_duckduckgo(query, max_results=per_query_limit):
            found.setdefault(url, []).append(query)   # record every query that found each URL
        time.sleep(Search_delay)

    # Stage 2: shuffle the pool and download in that order until the target is reached
    order = sorted(found)
    random.Random(Random_seed).shuffle(order)

    all_pathway_data = []
    log = []
    for rank, url in enumerate(order, 1):
        if len(all_pathway_data) >= target:
            status = "Not needed (target reached)"
        elif not is_allowed_by_robots(url):
            status = "Skipped (disallowed by robots.txt)"
            print(f"{status}: {url}")
        else:
            print(f"Scraping ({len(all_pathway_data) + 1}/{target}): {url}")
            page_text, pdf_bytes = scrape_page_text(url)
            pdf_path = ""
            status = "Kept"
            if not page_text:
                status = "Skipped (no usable text)"
            elif pdf_bytes:
                # a PDF is only saved once its text has passed the length check
                pdf_path, already_saved = download_pdf(url, pdf_bytes)
                if already_saved:
                    status = "Skipped (duplicate PDF)"

            if status == "Kept":
                all_pathway_data.append({
                    "Sample_Rank": rank,
                    "Search_Query": " | ".join(found[url]),
                    "URL": url,
                    "Retrieval_Date": datetime.date.today().isoformat(),
                    "Document_Type": "PDF" if pdf_bytes else "HTML",
                    "PDF_File": pdf_path,
                    "Raw_Text": page_text,
                })
                # save progress so a crash doesn't lose documents already collected
                pd.DataFrame(all_pathway_data).to_csv(Output_file, index=False, encoding="utf-8")

        log.append({
            "Sample_Rank": rank,
            "URL": url,
            "Found_By_Query": " | ".join(found[url]),
            "Status": status,
        })

    # Save the corpus for coding, plus a log of what happened to every URL
    pd.DataFrame(all_pathway_data).to_csv(Output_file, index=False, encoding="utf-8")
    pd.DataFrame(log).to_csv(Log_file, index=False, encoding="utf-8")
    print(f"Scraping complete. Saved {len(all_pathway_data)} documents to {Output_file}")
    print(f"Log of all {len(found)} URLs saved to {Log_file}")
