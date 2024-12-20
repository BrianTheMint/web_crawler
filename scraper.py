import requests
from bs4 import BeautifulSoup
import argparse
import urllib.parse
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
import sys

output_files = []
stop_flag = False

def download_image(url, worker_id):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        image_name = os.path.join(f"worker_{worker_id}_images", os.path.basename(url))
        os.makedirs(os.path.dirname(image_name), exist_ok=True)
        with open(image_name, 'wb') as image_file:
            for chunk in response.iter_content(1024):
                image_file.write(chunk)
        print(f"Downloaded image: {url}")
    except requests.RequestException as e:
        print(f"Failed to download image {url}: {e}")

def scrape(url, max_depth, current_depth=0, visited=None, worker_id=None):
    global stop_flag
    if visited is None:
        visited = set()
    
    if current_depth > max_depth or url in visited or stop_flag:
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
    images = [img.get('src') for img in soup.find_all('img', src=True)]
    
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
        
        for image in images:
            absolute_image_url = urllib.parse.urljoin(url, image)
            futures.append(executor.submit(download_image, absolute_image_url, worker_id))
        
        for future in as_completed(futures):
            future.result()

def merge_output_files(output_file):
    with open(output_file, 'w') as outfile:
        for output_file_name in output_files:
            with open(output_file_name, 'r') as infile:
                outfile.write(infile.read())
            os.remove(output_file_name)

def signal_handler(sig, frame):
    global stop_flag
    print("\nGracefully shutting down...")
    stop_flag = True

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Web scraper")
    parser.add_argument("--url", required=True, help="The URL to scrape")
    parser.add_argument("--max_depth", type=int, required=True, help="The maximum depth to follow links")
    parser.add_argument("--output", default="found_urls.txt", help="The output file to write URLs to")
    parser.add_argument("--worker_id", type=int, required=True, help="The worker ID")
    
    args = parser.parse_args()
    
    if not args.url.startswith(('http://', 'https://')):
        print("Error: URL must start with 'http://' or 'https://'")
    else:
        # Create an initial output file for the initial scrape
        initial_output_file_name = f"worker_{args.worker_id}.txt"
        output_files.append(initial_output_file_name)
        with open(initial_output_file_name, 'w') as initial_output_file_handle:
            scrape(args.url, args.max_depth, visited=set(), worker_id=args.worker_id)
        
        # Merge output files on shutdown
        merge_output_files(args.output)