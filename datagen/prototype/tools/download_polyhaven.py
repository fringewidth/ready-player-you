import os
import requests
import json
import random
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../assets/hdris"))
os.makedirs(BASE_DIR, exist_ok=True)
HEADERS = {"User-Agent": "ReadyPlayerYou-SyntheticDataGen/1.0"}

def download_hdris(limit=20):
    print(f"Fetching asset list from Poly Haven...")
    resp = requests.get("https://api.polyhaven.com/assets?type=hdris", headers=HEADERS)
    data = resp.json()
    
    slugs = list(data.keys())
    random.shuffle(slugs)
    target_slugs = slugs[:limit]
    
    print(f"Found {len(slugs)} total HDRIs. Targeting {limit} for download...")
    
    for i, slug in enumerate(target_slugs):
        filename = f"{slug}_1k.exr"
        target_path = os.path.join(BASE_DIR, filename)
        
        if os.path.exists(target_path):
            print(f"[{i+1}/{limit}] Skipping {slug} (already exists)")
            continue
            
        # Try retrieving direct URL from files API
        try:
            # Predictable URL structure usually works with dl.polyhaven.org
            url = f"https://dl.polyhaven.org/file/ph-assets/HDRIs/exr/1k/{slug}_1k.exr"
            r = requests.get(url, headers=HEADERS, stream=True)
            
            if r.status_code != 200:
                # Fallback to detail API
                detail_url = f"https://api.polyhaven.com/files/{slug}"
                files_data = requests.get(detail_url, headers=HEADERS).json()
                url = files_data.get('hdri', {}).get('1k', {}).get('exr', {}).get('url')
                if url:
                    r = requests.get(url, headers=HEADERS, stream=True)
            
            if r.status_code == 200:
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[{i+1}/{limit}] Downloaded {slug}")
            else:
                print(f"[{i+1}/{limit}] Failed {slug} (Status {r.status_code})")
        except Exception as e:
            print(f"Error {slug}: {e}")
        
        time.sleep(0.5) # Be nice to the API

if __name__ == "__main__":
    download_hdris(30)
