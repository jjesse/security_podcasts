import re
import requests
import csv
from datetime import datetime, timedelta

# Constants
MARKDOWN_FILE = 'readme.md'
OUTPUT_TEXT_FILE = 'urls.txt'
OUTPUT_CSV_FILE = 'url_status.csv'
CURRENT_THRESHOLD = datetime.now() - timedelta(days=30)
TIMEOUT = 10  # seconds

def extract_urls_from_markdown(file_path):
    """Extract all URLs from a markdown file."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return re.findall(r'https?://[^\s\)]+', content)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return []

def get_last_modified_date(url):
    """Return the last modified date of a URL or None if not available or request fails."""
    try:
        response = requests.head(url, timeout=TIMEOUT)
        if 'Last-Modified' in response.headers:
            return datetime.strptime(response.headers['Last-Modified'], "%a, %d %b %Y %H:%M:%S %Z")
    except requests.RequestException as e:
        print(f"Error accessing {url}: {e}")
    return None

def process_urls(urls):
    """Process each URL, checking its last modified date and active status."""
    data = []
    for url in urls:
        last_modified = get_last_modified_date(url)
        if last_modified:
            is_active = last_modified >= CURRENT_THRESHOLD
            data.append({
                'URL': url,
                'Last Updated': last_modified.strftime("%Y-%m-%d"),
                'Active': 'Yes' if is_active else 'No'
            })
        else:
            data.append({'URL': url, 'Last Updated': 'Unknown', 'Active': 'Unknown'})
    return data

def save_urls_to_text_file(urls, file_path):
    """Save extracted URLs to a text file."""
    try:
        with open(file_path, 'w') as file:
            for url in urls:
                file.write(url + '\n')
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")

def save_data_to_csv(data, file_path):
    """Save processed data to a CSV file."""
    try:
        with open(file_path, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['URL', 'Last Updated', 'Active'])
            writer.writeheader()
            writer.writerows(data)
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")

def main():
    # Step 1: Extract URLs from markdown file
    urls = extract_urls_from_markdown(MARKDOWN_FILE)
    if not urls:
        print("No URLs found or file is missing.")
        return

    # Step 2: Save URLs to text file
    save_urls_to_text_file(urls, OUTPUT_TEXT_FILE)

    # Step 3: Process URLs for last modified date and active status
    url_data = process_urls(urls)

    # Step 4: Save the processed data to a CSV file
    save_data_to_csv(url_data, OUTPUT_CSV_FILE)
    print("Processing complete. Check 'url_status.csv' for results.")

if __name__ == "__main__":
    main()
