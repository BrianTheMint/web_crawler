import requests
from bs4 import BeautifulSoup
import argparse
import urllib.parse
import re
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def scrape(url, max_depth, current_depth=0, visited=None, output_file=None):
    if visited is None:
        visited = set()
    
    if current_depth > max_depth or url in visited:
        return
    
    visited.add(url)
    print(f"Scraping URL: {url} at depth {current_depth}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to retrieve {url}: {e}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = [a.get('href') for a in soup.find_all('a', href=True)]
    
    # Find non-hyperlinked URLs
    text = soup.get_text()
    non_hyperlinked_urls = re.findall(r'(https?://\S+)', text)
    links.extend(non_hyperlinked_urls)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for link in links:
            absolute_link = urllib.parse.urljoin(url, link)
            if output_file:
                with open(output_file, 'a') as f:
                    f.write(absolute_link + '\n')
            futures.append(executor.submit(scrape, absolute_link, max_depth, current_depth + 1, visited, output_file))
        
        for future in as_completed(futures):
            future.result()

def signal_handler(sig, frame):
    print("\nGracefully shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Web scraper")
    parser.add_argument("--url", required=True, help="The URL to scrape")
    parser.add_argument("--max_depth", type=int, required=True, help="The maximum depth to follow links")
    parser.add_argument("--output", default="found_urls.txt", help="The output file to write URLs to")
    
    args = parser.parse_args()
    
    if not args.url.startswith(('http://', 'https://')):
        print("Error: URL must start with 'http://' or 'https://'")
    else:
        # Clear the output file at the start
        with open(args.output, 'w') as f:
            f.write('')
        scrape(args.url, args.max_depth, output_file=args.output)