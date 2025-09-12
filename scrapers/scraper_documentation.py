import json
import os
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

output_path = "knowledge_base/atlan_documentation.json"

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(output_path), exist_ok=True)

start_time = time.time()
sitemap_url = "https://docs.atlan.com/sitemap.xml"
resp = requests.get(sitemap_url)
resp.raise_for_status()

root = ET.fromstring(resp.text)
namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

urls = [
    url.find("ns:loc", namespace).text
    for url in root.findall("ns:url", namespace)
    if "how-tos" in url.find("ns:loc", namespace).text
]

print(f"Found {len(urls)} how-to pages")

def scrape_page(u):
    try:
        r = requests.get(u, timeout=15)
        r.encoding = "utf-8"
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        main_content = soup.find("main") or soup.find("article") or soup.body
        text = main_content.get_text(" ", strip=True) if main_content else ""
        return {"url": u, "content": text}
    except Exception as e:
        print(f"Failed scraping {u}: {e}")
        return None

data = []
# Starting a thread pool with 10 workers (reduces 80% of time required)
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(scrape_page, u): u for u in urls}
    for future in as_completed(futures):
        result = future.result()
        if result:
            data.append(result)

end_time = time.time()
print(f"Scraped {len(data)} pages successfully")
print(f"Time taken: {end_time - start_time:.2f} seconds")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)