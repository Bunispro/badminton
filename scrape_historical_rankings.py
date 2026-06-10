import os
import re
import urllib.request
import urllib.parse
import time
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://corporate.bwfbadminton.com/players/historical-rankings/"
OUTPUT_DIR = "data_rankings"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def fetch_page(year):
    url = f"{BASE_URL}?ryear={year}"
    print(f"Fetching listings for year: {year}...")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except Exception as e:
        print(f"Error fetching page for year {year}: {e}")
        return None

def download_file(file_url, dest_path):
    # Check if file exists and has size > 0
    if os.path.exists(dest_path) and os.stat(dest_path).st_size > 0:
        return True
    
    # URL encode spaces and special characters in path
    parsed = urllib.parse.urlparse(file_url)
    encoded_path = urllib.parse.quote(parsed.path)
    url_to_fetch = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, encoded_path, parsed.params, parsed.query, parsed.fragment))
    
    print(f"Downloading: {file_url} -> {dest_path}")
    req = urllib.request.Request(url_to_fetch, headers=HEADERS)
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, "wb") as f:
                f.write(response.read())
            print(f"  [OK] Downloaded successfully.")
            time.sleep(1) # Gentle rate limiting
            return True
        except Exception as e:
            print(f"  [ERROR] Attempt {attempt + 1} failed: {e}")
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except:
                    pass
            time.sleep(2)
    return False

def parse_filename_meta(filename):
    # Regex to find date YYYY-MM-DD
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    # Regex to find week (e.g. Week 20 or Week-01 or Week01)
    week_match = re.search(r"[Ww]eek\s*[-_]?\s*(\d+)", filename)
    
    date_str = date_match.group(1) if date_match else None
    week_num = int(week_match.group(1)) if week_match else None
    
    return date_str, week_num

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Track results
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for year in range(2019, 2027):
        html_content = fetch_page(year)
        if not html_content:
            continue
            
        soup = BeautifulSoup(html_content, "html.parser")
        links = soup.find_all("a", href=True)
        
        found_links = 0
        for link in links:
            href = link["href"].strip()
            # We filter for links pointing to BWF's document system on extranet
            if "extranet.bwf.sport" in href and ("/document-system/" in href or "/docs/" in href):
                found_links += 1
                
                # Try to extract the display filename
                raw_filename = os.path.basename(urllib.parse.unquote(href))
                date_str, week_num = parse_filename_meta(raw_filename)
                
                if not date_str or week_num is None:
                    # Fallback to link title/text if parsing from URL fails
                    link_text = link.get_text() or link.get("title") or ""
                    date_str, week_num = parse_filename_meta(link_text)
                
                if date_str and week_num is not None:
                    ext = os.path.splitext(raw_filename)[1].lower() or ".pdf"
                    dest_filename = f"WR_{date_str}_Week_{week_num}{ext}"
                    dest_path = os.path.join(OUTPUT_DIR, dest_filename)
                    
                    if os.path.exists(dest_path) and os.stat(dest_path).st_size > 0:
                        skipped_count += 1
                        continue
                        
                    if download_file(href, dest_path):
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    print(f"Warning: Could not parse metadata from URL or link text: {href}")
                    
        print(f"Year {year}: Found {found_links} ranking links.")
        
    print("\n==========================================")
    print(" CRAWLER RUN SUMMARY")
    print("==========================================")
    print(f"Successfully Downloaded : {success_count} files")
    print(f"Failed Downloads        : {fail_count} files")
    print(f"Already Existed         : {skipped_count} files")
    print("==========================================")

if __name__ == "__main__":
    main()
