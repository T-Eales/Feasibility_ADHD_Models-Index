## Web Scrapper Test Script ##
# This script is a test for the web scrapper that will be used for data collection
# This script is only testing HTML scrapping, not PDF scrapping
# This script is not complete, and does not include all the ethical safegaurds that will be inlcuded in the final version
# e.g. respecting robots.txt, and not scraping sites that do not allow it, will both need to be added in the final version
# However, it does work! The dummy corpus.csv file is created and will be used for building skelton code


# Libraries to be used
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from ddgs import DDGS

# Provisional Search Queries
queries = [
    'Game of Thrones Online RPG',
    'Elderscrolls Online',
    'Elderscrolls RPG',
    'Resident Evil',
    'Pathfinder Online RPG',
]
'''
# User ID description to identify researcher and project in line with BPS standards /// Will be used during data collection
headers = {
    "User-Agent": "MSc Computational Psychology Research Project - Text Mining (Academic/Non-Commercial)"
}
'''
# Using DDGO to search for the documents and return the URLs
def get_urls_from_duckduckgo(query, max_results=5):
    urls = []
    print(f"Searching DuckDuckGo for: '{query}'")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(
                query,
                region='uk-en',
                safesearch='off',
                max_results=max_results
            )
            # In this test, the programme kept pulling YouTube videos and steam store pages, so these have been filtered
            for result in results:
                urls.append(result['href'])
                if 'youtube.com' in result['href']:
                    print(f"Skipping YouTube URL: {result['href']}")
                    continue
                if 'steamcommunity.com' in result['href']:
                    print(f"Skipping Steam URL: {result['href']}")
                    continue
                if 'steamstore.com' in result['href']:
                    print(f"Skipping Steam Store URL: {result['href']}")
                    continue
                if 'store.steampowered.com' in result['href']:
                    print(f"Skipping Steam Store URL: {result['href']}")
                    continue
                if 'twitch.tv' in result['href']:
                    print(f"Skipping Twitch URL: {result['href']}")
                    continue
    except Exception as e:
        print(f"Search failed for '{query}': {e}")
    return urls

# Downloading the webpage and extracting the raw text
def scrape_page_text(url):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Attempt to isolate the main article content, as menu's kept appearing
            main_content = soup.find('main') or soup.find(id='maincontent') or soup.find(role='main') or soup

            # 2. Remove unwanted parts of the page, a step 1 proved not enough
            for element in main_content.find_all(['nav', 'aside', 'footer', 'header']):
                element.decompose()
            for element in main_content.find_all('div', class_=lambda x: x and any(word in x.lower() for word in ['sidebar', 'menu', 'widget', 'breadcrumb'])):
                element.decompose()

            # 3. Extracting text from ONLY the main content - it keeps pulling random text
            content_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']
            extracted_chunks = []
            
            for element in main_content.find_all(content_tags):
                text = element.get_text(separator=' ', strip=True)
                if text:
                    extracted_chunks.append(text)
                    
            clean_text = " ".join(extracted_chunks)
            return clean_text
        # 4. If the page is not accessible, print the status code
        else:
            print("Skipped {url} - Status Code: {response.status_code}")
            return None
    except Exception as e:
        print("Error scraping {url}: {e}")
        return None

# Main Execution
if __name__ == "__main__":
    all_pathway_data = []

    for query in queries:
        urls = get_urls_from_duckduckgo(query, max_results=5) # This has been set to 5 for testing

        for url in urls:
            print(f"Scraping: {url}")
            page_text = scrape_page_text(url)

            if page_text:
                all_pathway_data.append({
                    "Search_Query": query,
                    "URL": url,
                    "Raw_Text": page_text
                })
# ETHICAL RATE LIMITING: Pause for 3 seconds between requests to avoid overloading servers
        time.sleep(3)
# Save to a CSV for the coding
    df = pd.DataFrame(all_pathway_data)
    df.to_csv("dummy_corpus.csv", index=False, encoding="utf-8")
    print("Scraping complete. Saved {len(df)} documents to dummy_corpus.csv")
