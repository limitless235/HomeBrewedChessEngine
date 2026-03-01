import os
import urllib.request
import sys

def download_openings():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    openings_dir = os.path.join(base_dir, "openings")
    
    if not os.path.exists(openings_dir):
        os.makedirs(openings_dir)
        
    base_url = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/"
    files = ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]
    
    for filename in files:
        filepath = os.path.join(openings_dir, filename)
        url = base_url + filename
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filepath)
                print(f"Successfully downloaded {filename}")
            except Exception as e:
                print(f"Failed to download {filename}: {e}", file=sys.stderr)
        else:
            print(f"{filename} already exists, skipping.")

if __name__ == "__main__":
    download_openings()
