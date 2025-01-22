import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re

# Function to read podcastindex URLs from README.md
def read_podcastindex_urls_from_readme(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        # Regular expression to match URLs that contain 'podcastindex.org'
        url_pattern = r'(https?://[^\s\)]+podcastindex\.org[^\s\)]*)'

        # Find all URLs using the regex pattern
        urls = re.findall(url_pattern, content)
        return urls

    except Exception as e:
        print(f"Error reading file: {e}")
        return []

# Function to get the last modified date from headers or meta tags
def get_last_modified(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Check the 'Last-Modified' header
        last_modified = response.headers.get('Last-Modified')
        if last_modified:
            return datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")

        # If no header, check the meta tags in HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Attempt to find meta tags that indicate last modified time
        meta_date = soup.find('meta', {'http-equiv': 'last-modified'}) or soup.find('meta', {'name': 'last-modified'})
        if meta_date and meta_date.get('content'):
            return datetime.strptime(meta_date['content'], "%Y-%m-%dT%H:%M:%S")

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

# Main function to read URLs from README.md, check them, and save to CSV
def main():
    readme_file = 'README.md'  # Path to the markdown file
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

    # Filter active podcasts and save to a separate CSV file
    active_podcasts = df[df['Active'] == 'Yes'][['Website', 'Last Updated']]
    active_podcasts.to_csv(active_podcasts_csv, index=False)
    print(f"Active podcasts saved to {active_podcasts_csv}")

# Run the main function
if __name__ == "__main__":
    main()