
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# Function to read websites from a file
def read_websites_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            websites = [line.strip() for line in file.readlines() if line.strip()]
        return websites
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

    for site in websites:
        last_modified = get_last_modified(site)
        data.append({
            'Website': site,
            'Last Checked': now.strftime("%Y-%m-%d %H:%M:%S"),
            'Last Updated': last_modified.strftime("%Y-%m-%d %H:%M:%S") if last_modified else "Unknown"
        })
    
    # Create a pandas DataFrame
    df = pd.DataFrame(data)
    return df

# Main function to read websites from file and check them
def main():
    file_path = 'websites.txt'  # Change this path if your file is located elsewhere
    websites = read_websites_from_file(file_path)
    if not websites:
        print("No websites found or error reading file.")
        return

    df = check_websites(websites)
    print(df)

# Run the main function
if __name__ == "__main__":
    main()
