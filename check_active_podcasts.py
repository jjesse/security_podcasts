import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta

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

# Main function to read websites from file, check them, and save to CSV
def main():
    file_path = 'websites.txt'  # Change this path if your file is located elsewhere
    output_csv = 'podcast_update.csv'
    websites = read_websites_from_file(file_path)
    if not websites:
        print("No websites found or error reading file.")
        return

    df = check_websites(websites)

    # Save the DataFrame to a CSV file
    df.to_csv(output_csv, index=False)
    print(f"Data saved to {output_csv}")

# Run the main function
if __name__ == "__main__":
    main()
