import os
import json
import ssl
import time
import functools
from pathlib import Path
from PIL import Image
import moondream as md

# SSL Bypass for macOS
ssl._create_default_https_context = ssl._create_unverified_context

# Configuration
API_KEY = os.getenv("MOONDREAM_API_KEY")
ASSETS_DIR = Path(os.path.expanduser("~/Library/Application Support/Blender/5.1/extensions/.user/blender_org/mpfb/data"))
OUTPUT_JSON = Path(__file__).resolve().parent.parent / "asset_metadata.json"
CACHE_FILE = Path(__file__).resolve().parent.parent / "comparison_cache.json"

# Initialize Cloud SDK
model = md.vl(api_key=API_KEY)

# Persistent cache for comparisons
COMPARISON_CACHE = {}
if CACHE_FILE.exists():
    with open(CACHE_FILE, "r") as f:
        try:
            COMPARISON_CACHE = json.load(f)
        except json.JSONDecodeError:
            COMPARISON_CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(COMPARISON_CACHE, f)

def compare_assets(path1, path2, trait_label, trait_question):
    """
    Pairs two images and uses the Moondream Cloud SDK to determine the ranking.
    """
    key1, key2 = Path(path1).stem, Path(path2).stem
    t_label = trait_label.lower()
    if key1 > key2:
        cache_key = f"{key2}_vs_{key1}_{t_label}"
        swapped = True
    else:
        cache_key = f"{key1}_vs_{key2}_{t_label}"
        swapped = False
        
    if cache_key in COMPARISON_CACHE:
        val = COMPARISON_CACHE[cache_key]
        return -val if swapped else val

    try:
        img1 = Image.open(path1).convert("RGB").resize((448, 448))
        img2 = Image.open(path2).convert("RGB").resize((448, 448))
        
        new_img = Image.new("RGB", (896, 448))
        new_img.paste(img1, (0, 0))
        new_img.paste(img2, (448, 0))
        
        prompt = f"This image shows two 3D human assets side-by-side. {trait_question} Respond ONLY with 'LEFT', 'RIGHT', or 'EQUAL'."
        
        print(f"    [PIT FIGHT] {key1} vs {key2} ({trait_label})... ", end="", flush=True)
        result = model.query(new_img, prompt)
        answer = result["answer"].strip().upper()
        
        res = 0
        if "LEFT" in answer: 
            res = 1
            print("Winner: LEFT")
        elif "RIGHT" in answer: 
            res = -1
            print("Winner: RIGHT")
        else:
            print("EQUAL")
        
        COMPARISON_CACHE[cache_key] = res
        save_cache()
        return -res if swapped else res
    except Exception as e:
        print(f"  Cloud API Error: {e}")
        return 0

def rank_category(asset_paths, traits, master_metadata):
    for p in asset_paths:
        name = Path(p).stem
        if name not in master_metadata:
            master_metadata[name] = [0.5, 0.5, 0.5]
    
    for trait_idx, (label, question) in enumerate(traits):
        print(f"\nRanking by trait: {label} ({len(asset_paths)} assets)...")
        
        def compare_wrapper(p1, p2):
            return compare_assets(p1, p2, label, question)
        
        sorted_paths = sorted(asset_paths, key=functools.cmp_to_key(compare_wrapper))
        
        for rank, path in enumerate(sorted_paths):
            name = Path(path).stem
            score = rank / (len(sorted_paths) - 1) if len(sorted_paths) > 1 else 0.5
            master_metadata[name][trait_idx] = round(score, 3)
            
        print(f"  [COMMIT] Saving rankings for {label} to {OUTPUT_JSON}...")
        with open(OUTPUT_JSON, "w") as f:
            json.dump(master_metadata, f, indent=4)
            
    return master_metadata

def main():
    print("Initiating Moondream Rank Profiler (ALIGNING WITH ARCHITECTURE DOCS)...")
    
    # SCHEMA reflects the 33-float vector documentation
    SCHEMA = {
        "hair": {
            "folder": "hair",
            "filter": "*",
            "traits": [
                ("length", "Which hair is longer? (0=Bald to 1=Long)"),
                ("volume", "Which hair is more voluminous and body-rich?"),
                ("curliness", "Which hair is curlier or more textured?")
            ]
        },
        "facial_hair": {
            "folder": "clothes",
            "filter": "*beard*|*mous*",
            "traits": [
                ("mustache_density", "Which has a thicker/more prominent moustache region?"),
                ("beard_length", "Which beard is longer?"),
                ("connection", "Which facial hair connects the moustache and beard more strongly?")
            ]
        },
        "eyewear": {
            "folder": "clothes",
            "filter": "*glass*",
            "traits": [
                ("presence", "Which eyewear is more visually dominant?"),
                ("roundness", "Which glasses are more round/circular?"),
                ("thickness", "Which glasses have thicker/chunkier frames?")
            ]
        },
        "eyebrows": {
            "folder": "eyebrows",
            "filter": "*",
            "traits": [
                ("presence", "Which eyebrows are more prominent?"),
                ("thickness", "Which eyebrows are thicker?"),
                ("arch", "Which eyebrows have a higher arch?")
            ]
        }
    }

    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, "r") as f:
            try:
                master_metadata = json.load(f)
            except json.JSONDecodeError:
                master_metadata = {}
    else:
        master_metadata = {}

    for cat_name, cfg in SCHEMA.items():
        cat_path = ASSETS_DIR / cfg["folder"]
        if not cat_path.exists(): continue
        
        print(f"\n--- Category: {cat_name} ---")
        
        # Keyword filtering
        all_thumbs = glob.glob(str(cat_path / "**" / "*.thumb"), recursive=True)
        filters = cfg["filter"].split("|")
        asset_files = []
        for p in all_thumbs:
            if any(f.replace("*", "").lower() in p.lower() for f in filters):
                asset_files.append(p)
        
        if not asset_files:
            continue
            
        print(f"  Found {len(asset_files)} assets.")
        master_metadata = rank_category(asset_files, cfg["traits"], master_metadata)

    print(f"\nDone! Results aligned to architecture spec in {OUTPUT_JSON}")

if __name__ == "__main__":
    import glob
    main()
