import re

# Function to extract URLs containing 'podcastindex.org' from the markdown file
def extract_podcastindex_urls(file_path):
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

# Function to save URLs to a file
def save_urls_to_file(urls, output_file):
    try:
        with open(output_file, 'w') as file:
            for url in urls:
                file.write(url + '\n')
        print(f"URLs saved to {output_file}")
    except Exception as e:
        print(f"Error saving file: {e}")

# Main function to extract URLs and save them
def main():
    input_file = 'readme.md'  # Path to the markdown file
    output_file = 'websites.txt'  # Path to save the URLs

    urls = extract_podcastindex_urls(input_file)

    if urls:
        save_urls_to_file(urls, output_file)
    else:
        print("No URLs containing 'podcastindex.org' found or error occurred.")

# Run the main function
if __name__ == "__main__":
    main()
