import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re

TIMEOUT = 10  # seconds per request

# Date formats tried in order when parsing Last-Modified values
DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %Z",   # RFC 7231: Mon, 06 Nov 1994 08:49:37 GMT
    "%a, %d %b %Y %H:%M:%S GMT",  # Explicit GMT variant
    "%Y-%m-%dT%H:%M:%SZ",         # ISO 8601 with Z suffix
    "%Y-%m-%dT%H:%M:%S",          # ISO 8601 without timezone
]

PODCAST_UPDATE_COLUMNS = ['Website', 'Last Checked', 'Last Updated', 'Active']
PODCAST_STATUS_COLUMNS = ['Website', 'Last Updated']


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


def validate_csv(file_path, expected_columns):
    """Validate that a CSV file has the expected columns and at least one data row."""
    df = pd.read_csv(file_path)
    missing = set(expected_columns) - set(df.columns)
    if missing:
        raise ValueError(f"CSV {file_path} is missing columns: {missing}")
    if df.empty:
        print(f"WARNING: {file_path} contains no data rows.")
    return True


# Function to read podcastindex URLs from List_of_podcast.md
def read_podcastindex_urls_from_readme(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        # Regular expression to match URLs that contain 'podcastindex.org'
        url_pattern = r'(https?://[^\s\)<>]*podcastindex\.org[^\s\)<>]*)'

        # Find all URLs using the regex pattern
        urls = re.findall(url_pattern, content)
        return urls

    except Exception as e:
        print(f"Error reading file: {e}")
        return []


# Function to get the last modified date from headers or meta tags
def get_last_modified(url):
    session = _make_session()
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        # Check the 'Last-Modified' header
        last_modified = response.headers.get('Last-Modified')
        if last_modified:
            parsed = _parse_date(last_modified)
            if parsed:
                return parsed

        # If no header, check the meta tags in HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Attempt to find meta tags that indicate last modified time
        meta_date = (
            soup.find('meta', {'http-equiv': 'last-modified'})
            or soup.find('meta', {'name': 'last-modified'})
        )
        if meta_date and meta_date.get('content'):
            parsed = _parse_date(meta_date['content'])
            if parsed:
                return parsed

    except Exception as e:
        print(f"Error checking {url}: {e}")
    return None


# Function to check all websites and build a table
def check_websites(websites):
    data = []
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)

    for site in websites:
        last_modified = get_last_modified(site)
        if last_modified:
            last_modified_str = last_modified.strftime("%Y-%m-%d %H:%M:%S")
            is_active = "Yes" if last_modified >= thirty_days_ago else "No"
        else:
            last_modified_str = "Unknown"
            is_active = "Unknown"

        data.append({
            'Website': site,
            'Last Checked': now.strftime("%Y-%m-%d %H:%M:%S"),
            'Last Updated': last_modified_str,
            'Active': is_active
        })

    # Create a pandas DataFrame
    df = pd.DataFrame(data)
    return df


# Main function to read URLs from List_of_podcast.md, check them, and save to CSV
def main():
    readme_file = 'List_of_podcast.md'
    output_csv = 'podcast_update.csv'
    active_podcasts_csv = 'podcast_status.csv'
    urls = read_podcastindex_urls_from_readme(readme_file)
    if not urls:
        print("No URLs found or error reading file.")
        return

    df = check_websites(urls)

    # Save the DataFrame to a CSV file
    df.to_csv(output_csv, index=False)
    print(f"Data saved to {output_csv}")
    validate_csv(output_csv, PODCAST_UPDATE_COLUMNS)

    # Filter active podcasts and save to a separate CSV file
    active_podcasts = df[df['Active'] == 'Yes'][['Website', 'Last Updated']]
    active_podcasts.to_csv(active_podcasts_csv, index=False)
    print(f"Active podcasts saved to {active_podcasts_csv}")
    validate_csv(active_podcasts_csv, PODCAST_STATUS_COLUMNS)


# Run the main function
if __name__ == "__main__":
    main()