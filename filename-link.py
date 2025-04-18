import requests
import re
import os
from urllib.parse import urljoin, urlparse, unquote
import json
from bs4 import BeautifulSoup, Tag

# Headers for the HTTP requests
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://portal.nyserda.ny.gov"
}

# Import the process_link function from utils.http_utils
from utils.http_utils import process_link, download_snapshot
from utils.text_utils import clean_text



def sanitize_filename(text):
    """Convert text to a safe filename format."""
    if not text:
        return ""

    # First, clean basic whitespace issues
    text = clean_text(text)

    # Replace characters that are invalid in filenames with underscores
    # Windows/Unix invalid filename chars: / \ : * ? " < > | and control chars
    text = re.sub(r'[\\/*?:"<>|]', '_', text)

    # Replace spaces, periods, commas, semicolons, and parentheses with underscores
    text = re.sub(r'[\s\.,;()]', '_', text)

    # Replace multiple underscores with a single underscore
    text = re.sub(r'_+', '_', text)

    # Trim underscores from start and end
    text = text.strip('_')

    # Truncate to reasonable length for a filename (max 100 chars)
    if len(text) > 100:
        text = text[:100]

    # Make sure we don't end with a period (problematic for Windows)
    if text.endswith('.'):
        text = text[:-1]

    # If nothing left after sanitizing, return a default
    if not text:
        text = "unnamed_file"

    return text


def extract_filename_from_url(url):
    """Extract the filename from a URL, if present."""
    if not url:
        return None

    # Parse the URL
    parsed_url = urlparse(url)
    # Get the path component
    path = parsed_url.path

    # URL decode the path (handles %20 spaces, etc.)
    path = unquote(path)

    # Split the path by '/' and get the last component
    path_parts = path.split('/')
    last_part = path_parts[-1] if path_parts else ""

    # If the last part has a file extension or looks like a filename, return it
    if last_part and ('.' in last_part or re.search(r'[a-zA-Z0-9_-]+$', last_part)):
        # Remove any query string or fragment
        filename = last_part.split('?')[0].split('#')[0]
        # Clean the filename for use as an actual filename
        filename = sanitize_filename(filename)
        return filename

    # If no obvious filename is found
    return None


def extract_all_links(url, headers=None):
    """Extract all links from a webpage, excluding those with unknown file types."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')

        all_links = []
        unique_urls = set()  # To avoid processing the same URL multiple times

        # Find all anchor tags with href attribute
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            # Get and clean the link text
            raw_text = clean_text(link.text)
            # Also create a filename-safe version of the text
            safe_text = sanitize_filename(link.text)

            # Skip empty or javascript links
            if not href or href.startswith('javascript:') or href == '#':
                continue

            # Create absolute URL
            absolute_url = urljoin(url, href)

            # Skip if we've already processed this URL
            if absolute_url in unique_urls:
                continue

            unique_urls.add(absolute_url)

            # Use the imported process_link function to get detailed information
            link_data = process_link(href, raw_text, headers, url)

            # Add the filename-safe version of the text
            link_data["safe_text"] = safe_text

            # Extract filename from URL
            filename = extract_filename_from_url(link_data["file_url"])
            link_data["filename"] = filename

            # Only include links with known file types
            if link_data["file_type"] != "unknown":
                all_links.append(link_data)

        return all_links

    except Exception as e:
        print(f"Error extracting links from {url}: {str(e)}")
        return []


def extract_links_from_tables(url, headers=None):
    """Extract links specifically from tables in the webpage, excluding those with unknown file types."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        table_links = []
        unique_urls = set()

        # Find all tables
        tables = soup.find_all('table')
        for table in tables:
            # Find all links within the table
            for link in table.find_all('a', href=True):
                href = link.get('href')
                # Get and clean the link text
                raw_text = clean_text(link.text)
                # Also create a filename-safe version of the text
                safe_text = sanitize_filename(link.text)

                # Skip empty or javascript links
                if not href or href.startswith('javascript:') or href == '#':
                    continue

                # Create absolute URL
                absolute_url = urljoin(url, href)

                # Skip if we've already processed this URL
                if absolute_url in unique_urls:
                    continue

                unique_urls.add(absolute_url)

                # Process the link
                link_data = process_link(href, raw_text, headers, url)

                # Add the filename-safe version of the text
                link_data["safe_text"] = safe_text

                # Extract filename from URL
                filename = extract_filename_from_url(link_data["file_url"])
                link_data["filename"] = filename

                # Only include links with known file types
                if link_data["file_type"] != "unknown":
                    # Add a flag to indicate this link was found in a table
                    link_data["in_table"] = True
                    table_links.append(link_data)

        return table_links

    except Exception as e:
        print(f"Error extracting table links from {url}: {str(e)}")
        return []


def main():
    target_url = 'https://www.nyserda.ny.gov/All-Programs/Offshore-Wind/Focus-Areas/Offshore-Wind-Solicitations/2018-Solicitation'
    download_snapshot(target_url, "data/snaps", "2018.html")

    print(f"Extracting links from: {target_url}")

    # Extract all links from the webpage (excluding unknown file types)
    all_links = extract_all_links(target_url, headers)

    # Optional: Extract links specifically from tables
    # table_links = extract_links_from_tables(target_url, headers)
    # all_links.extend(table_links)

    # Remove duplicates based on URL
    seen_urls = set()
    unique_links = []
    for link in all_links:
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            unique_links.append(link)

    # Print summary statistics
    pdf_count = sum(1 for link in unique_links if link["is_pdf"])
    files_with_names = sum(1 for link in unique_links if link.get("filename"))

    print(f"Total links with known file types: {len(unique_links)}")
    print(f"PDF links found: {pdf_count}")
    print(f"Links with filenames: {files_with_names}")

    # Count by file type
    file_type_counts = {}
    for link in unique_links:
        file_type = link["file_type"]
        file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1

    print("\nFile type distribution:")
    for file_type, count in file_type_counts.items():
        print(f"- {file_type}: {count}")

    # Save results to JSON file
    output_file = 'data/document_info/extracted_links_2018.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_links, f, ensure_ascii=False, indent=2)

    print(f"\nLinks data saved to {output_file}")

    # Print some example links
    print("\nExample links with filenames:")
    examples_shown = 0
    for link in unique_links:
        if link.get("filename") and examples_shown < 5:
            print(
                f"- {link['text']} | Safe: {link['safe_text']} | Filename: {link['filename']} | Type: {link['file_type']}")
            examples_shown += 1

    if examples_shown == 0:
        print("No links with filenames found in the first 5 links.")


if __name__ == "__main__":
    main()

