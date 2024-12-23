import requests
from bs4 import BeautifulSoup
import argparse
import urllib.parse
import re
import signal
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

output_files = []

def scrape(url, max_depth, current_depth=0, visited=None, worker_id=None):
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
    
    with ThreadPoolExecutor(max_workers=3) as executor:  # Reduced number of threads
        futures = []
        for link in links:
            absolute_link = urllib.parse.urljoin(url, link)
            if absolute_link not in visited:
                worker_file_name = f"worker_{worker_id}.txt"
                output_files.append(worker_file_name)
                with open(worker_file_name, 'a') as output_file_handle:
                    output_file_handle.write(absolute_link + '\n')
                futures.append(executor.submit(scrape, absolute_link, max_depth, current_depth + 1, visited, worker_id))
        
        for future in as_completed(futures):
            future.result()

def merge_output_files(output_file):
    with open(output_file, 'w') as outfile:
        for output_file_name in output_files:
            with open(output_file_name, 'r') as infile:
                outfile.write(infile.read())
            os.remove(output_file_name)

processes = []

def signal_handler(sig, frame):
    print("\nGracefully shutting down...")
    for process in processes:
        process.terminate()
    for process in processes:
        process.wait()
    
    # Kill all Python processes
    os.system("pkill -f scraper.py")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Web scraper manager")
    parser.add_argument("--url", required=True, help="The URL to scrape")
    parser.add_argument("--max_depth", type=int, required=True, help="The maximum depth to follow links")
    parser.add_argument("--output", default="found_urls.txt", help="The output file to write URLs to")
    parser.add_argument("--workers", type=int, default=3, help="The number of worker instances to start")
    
    args = parser.parse_args()
    
    for worker_id in range(1, args.workers + 1):
        process = subprocess.Popen([
            sys.executable, 'scraper.py',
            '--url', args.url,
            '--max_depth', str(args.max_depth),
            '--output', args.output,
            '--worker_id', str(worker_id)
        ])
        processes.append(process)
    
    for process in processes:
        process.wait()