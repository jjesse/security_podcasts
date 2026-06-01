import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import csv
from datetime import datetime, timedelta

# Constants
MARKDOWN_FILE = 'List_of_podcast.md'
OUTPUT_TEXT_FILE = 'urls.txt'
OUTPUT_CSV_FILE = 'url_status.csv'
CURRENT_THRESHOLD = datetime.now() - timedelta(days=30)
TIMEOUT = 10  # seconds

URL_STATUS_COLUMNS = ['URL', 'Last Updated', 'Active']

# Date formats tried in order when parsing Last-Modified values
DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %Z",   # RFC 7231: Mon, 06 Nov 1994 08:49:37 GMT
    "%a, %d %b %Y %H:%M:%S GMT",  # Explicit GMT variant
    "%Y-%m-%dT%H:%M:%SZ",         # ISO 8601 with Z suffix
    "%Y-%m-%dT%H:%M:%S",          # ISO 8601 without timezone
]

# Social media and profile-only domains to ignore when checking podcast activity
IGNORED_DOMAINS = [
    'twitter.com',
    'x.com',
    'hachyderm.io',
    'infosec.exchange',
    'twit.social',
    'mastodon.social',
    'mastodon.online',
    'fosstodon.org',
    'reddit.com',
]

# YouTube channel/profile patterns that aren't podcast episode pages
IGNORED_URL_PATTERNS = [
    r'https?://(?:www\.)?youtube\.com/(?:c/|@|channel/)[^/\s\)]+/?$',
    r'https?://(?:www\.)?youtube\.com/monicatalkscyber',
]


def _parse_date(date_str):
    """Try to parse a date string using known formats. Returns datetime or None."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _make_session():
    """Create a requests Session with automatic retry on transient errors."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def is_ignored_url(url):
    """Return True if the URL belongs to a social media or non-podcast domain."""
    for domain in IGNORED_DOMAINS:
        if re.search(r'https?://(?:[^/]*\.)?' + re.escape(domain), url):
            return True
    for pattern in IGNORED_URL_PATTERNS:
        if re.match(pattern, url):
            return True
    return False


def extract_urls_from_markdown(file_path):
    """Extract podcast-relevant URLs from a markdown file, skipping social media links."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        all_urls = re.findall(r'https?://[^\s\)<>]+', content)
        return [url for url in all_urls if not is_ignored_url(url)]
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return []


def get_last_modified_date(url):
    """Return the last modified date of a URL or None if not available or request fails."""
    session = _make_session()
    try:
        response = session.head(url, timeout=TIMEOUT)
        if 'Last-Modified' in response.headers:
            return _parse_date(response.headers['Last-Modified'])
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


def validate_csv(file_path, expected_columns):
    """Validate that a CSV file has the expected columns and at least one data row."""
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            actual_columns = reader.fieldnames or []
            missing = set(expected_columns) - set(actual_columns)
            if missing:
                raise ValueError(f"CSV {file_path} is missing columns: {missing}")
            rows = list(reader)
            if not rows:
                print(f"WARNING: {file_path} contains no data rows.")
    except IOError as e:
        print(f"CSV validation error for {file_path}: {e}")
        raise
    return True


def main():
    # Step 1: Extract URLs from markdown file (social media links are excluded)
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
    validate_csv(OUTPUT_CSV_FILE, URL_STATUS_COLUMNS)
    print("Processing complete. Check 'url_status.csv' for results.")


if __name__ == "__main__":
    main()
