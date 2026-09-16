import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, timezone
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

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
    if not date_str:
        return None

    # Common RFC 822/2822 date format used by RSS pubDate
    try:
        parsed = parsedate_to_datetime(date_str.strip())
        if parsed:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
    except (TypeError, ValueError):
        pass

    # ISO 8601 formats (with and without Z)
    try:
        iso_candidate = date_str.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
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
def _looks_like_feed_url(url):
    """Return True if URL appears to directly reference a feed."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    return (
        path.endswith('.xml')
        or path.endswith('.rss')
        or re.search(r'(^|/)(feed|rss|atom)(/|$)', path) is not None
    )


def _local_tag(tag_name):
    """Strip XML namespace from a tag and normalize case."""
    return tag_name.split('}')[-1].lower() if isinstance(tag_name, str) else ''


def _is_feed_xml_document(content_bytes):
    """Return True only when XML content appears to be RSS/Atom feed XML."""
    try:
        root = ET.fromstring(content_bytes)
    except ET.ParseError:
        return False

    root_local = _local_tag(root.tag)
    if root_local in {'rss', 'feed'}:
        return True

    # RSS 1.0 may use <rdf:RDF> with channel/item nodes
    if root_local == 'rdf':
        child_tags = {_local_tag(child.tag) for child in list(root)}
        return 'channel' in child_tags or 'item' in child_tags

    return False


def _extract_feed_url_from_html(page_url, html_content):
    """Extract feed URL from HTML via link rel=alternate or feed-like anchors."""
    soup = BeautifulSoup(html_content, 'html.parser')
    candidates = []

    # Preferred: explicit feed declarations
    for link in soup.find_all('link', href=True):
        rel_values = link.get('rel') or []
        rel_text = " ".join(rel_values).lower() if isinstance(rel_values, list) else str(rel_values).lower()
        type_text = (link.get('type') or '').lower()
        href = urljoin(page_url, link['href'])
        if ('alternate' in rel_text and 'xml' in type_text) or ('rss' in type_text) or ('atom' in type_text):
            candidates.append(href)

    # Fallback: feed-like anchors
    for anchor in soup.find_all('a', href=True):
        href = urljoin(page_url, anchor['href'])
        lowered = href.lower()
        if any(token in lowered for token in ['/feed', 'rss', '.xml', 'atom']):
            candidates.append(href)

    seen = set()
    for candidate in candidates:
        if candidate.startswith(('http://', 'https://')) and candidate not in seen:
            seen.add(candidate)
            return candidate
    return None


def discover_feed_url(url, session):
    """Discover an RSS/Atom feed URL from a podcast page URL."""
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        headers = getattr(response, 'headers', {}) or {}
        content_type = (headers.get('Content-Type') or '').lower()

        response_content = getattr(response, 'content', b'')
        if isinstance(response_content, str):
            response_content = response_content.encode('utf-8', errors='ignore')

        response_text = getattr(response, 'text', None)
        if response_text is None:
            if isinstance(response_content, bytes):
                response_text = response_content.decode('utf-8', errors='ignore')
            else:
                response_text = str(response_content)

        body_prefix = response_text[:512].lower()
        looks_like_xml = (
            'xml' in content_type
            or body_prefix.lstrip().startswith('<?xml')
            or '<rss' in body_prefix
            or '<feed' in body_prefix
        )
        if looks_like_xml:
            return url if _is_feed_xml_document(response_content) else None

        discovered_feed_url = _extract_feed_url_from_html(url, response_text)
        return discovered_feed_url
    except requests.RequestException as e:
        print(f"Error discovering feed for {url}: {e}")
        return None


def get_latest_episode_date_from_feed(feed_url, session):
    """Fetch feed and return latest episode publication datetime or None."""
    try:
        response = session.get(feed_url, timeout=TIMEOUT)
        response.raise_for_status()
        response_content = getattr(response, 'content', b'')
        if response_content in (None, b''):
            response_text = getattr(response, 'text', '')
            response_content = response_text.encode('utf-8', errors='ignore')
        elif isinstance(response_content, str):
            response_content = response_content.encode('utf-8', errors='ignore')
        root = ET.fromstring(response_content)
    except (requests.RequestException, ET.ParseError, ValueError, TypeError) as e:
        print(f"Error fetching/parsing feed {feed_url}: {e}")
        return None

    date_tags = {'pubdate', 'published', 'updated', 'date'}
    episode_dates = []

    # Prefer episode-level dates from <item> (RSS) and <entry> (Atom)
    for element in root.iter():
        local_name = _local_tag(element.tag)
        if local_name in {'item', 'entry'}:
            for child in list(element):
                child_local = _local_tag(child.tag)
                if child_local in date_tags and child.text:
                    parsed = _parse_date(child.text)
                    if parsed:
                        episode_dates.append(parsed)

    if episode_dates:
        return max(episode_dates)

    # Fallback: feed metadata dates only (not recursive across all nodes)
    feed_metadata_container = None
    root_local = _local_tag(root.tag)
    if root_local == 'rss':
        for child in list(root):
            if _local_tag(child.tag) == 'channel':
                feed_metadata_container = child
                break
    elif root_local in {'feed', 'channel'}:
        feed_metadata_container = root
    elif root_local == 'rdf':
        for child in list(root):
            if _local_tag(child.tag) == 'channel':
                feed_metadata_container = child
                break

    if feed_metadata_container is None:
        return None

    for element in list(feed_metadata_container):
        local_name = _local_tag(element.tag)
        if local_name in {'lastbuilddate', 'pubdate', 'updated'} and element.text:
            parsed = _parse_date(element.text)
            if parsed:
                episode_dates.append(parsed)

    return max(episode_dates) if episode_dates else None


# Function to check all websites and build a table
def check_websites(websites):
    data = []
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    session = _make_session()

    for site in websites:
        feed_url = discover_feed_url(site, session)
        latest_episode_date = get_latest_episode_date_from_feed(feed_url, session) if feed_url else None
        if latest_episode_date:
            last_modified_str = latest_episode_date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            is_active = "Yes" if latest_episode_date >= thirty_days_ago else "No"
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