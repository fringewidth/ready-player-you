# Translation logic for assets to continuous feature profiles (Descriptor Vectors)

# Each asset category maps to a 3-float vector [v0, v1, v2]

# Facial Hair Triad: [mustache_density, beard_density, connection]
BEARD_PROFILES = {
    "culturalibre_faun_beard": [0.0, 0.5, 0.0],
    "grinsegold_beard_sigmund_wip": [1.0, 1.0, 1.0],
    "rehmanpolanski_beard_viking": [0.0, 1.0, 0.0],
    "rehmanpolanski_moustache_viking": [1.0, 0.0, 0.0],
    "wdg_scruffy_beard": [0.0, 0.3, 0.0],
    "culturalibre_dal_moustache": [0.8, 0.0, 0.0],
    "elvs_scruffy_beard1": [0.5, 0.5, 1.0],
    "grinsegold_full_beard": [1.0, 1.0, 1.0],
    "grinsegold_moustache": [0.9, 0.0, 0.0],
    "none": [0.0, 0.0, 0.0]
}

# Glasses Triad: [possession, roundness, thickness]
GLASSES_PROFILES = {
    "culturalibre_doc_ock_glasses": [1.0, 1.0, 1.0],
    "frankyaye_glasses_library_male": [1.0, 0.0, 0.5],
    "kwnet_at_optical_glasses": [1.0, 0.2, 0.2],
    "spamrakuen_sagerfrogs_glasses_01": [1.0, 0.5, 0.3],
    "spamrakuen_sagerfrogs_glasses_02": [1.0, 0.5, 0.35],
    "spamrakuen_sagerfrogs_glasses_03": [1.0, 0.5, 0.4],
    "spamrakuen_sagerfrogs_glasses_04": [1.0, 0.5, 0.45],
    "spamrakuen_tbm_glasses_frames_01": [1.0, 0.3, 0.3],
    "toigo_round_glasses_leopard": [1.0, 1.0, 0.8],
    "none": [0.0, 0.0, 0.0]
}

# Head Hair Triad: [length, volume, curliness]
HAIR_PROFILES = {
    "elvs_katherine_hair": [0.7, 0.4, 0.2],
    "elvs_micky_afro": [0.4, 1.0, 1.0],
    "ponytail01": [0.8, 0.5, 0.1],
    "short01": [0.2, 0.2, 0.1],
    "long01": [0.9, 0.4, 0.2],
    "elvs_long_loose_curls": [0.8, 0.7, 0.6],
    "none": [0.0, 0.0, 0.0]
}

def get_asset_vector(category, asset_name):
    """Returns the 3-float vector for a given asset name using heuristics for unknown names."""
    if not asset_name or asset_name.lower() == "none":
        return [0.0, 0.0, 0.0]
    
    if category == "beard":
        return BEARD_PROFILES.get(asset_name, [0.5, 0.5, 0.0]) # Default middle
    
    if category == "glasses":
        return GLASSES_PROFILES.get(asset_name, [1.0, 0.5, 0.5]) # Default presence
        
    if category == "hair":
        if asset_name in HAIR_PROFILES:
            return HAIR_PROFILES[asset_name]
            
        # Heuristics for the 56 hairstyles
        low_name = asset_name.lower()
        length, volume, curliness = 0.5, 0.5, 0.0
        
        # Length
        if any(w in low_name for w in ["long", "braid", "ponytail", "bun"]): length = 0.8
        if any(w in low_name for w in ["short", "buzz", "pixie"]): length = 0.2
        if "bald" in low_name: length = 0.0
        
        # Volume
        if any(w in low_name for w in ["afro", "updo", "bob", "cloud"]): volume = 0.9
        if any(w in low_name for w in ["flat", "straight", "thin"]): volume = 0.2
        
        # Curliness
        if any(w in low_name for w in ["curly", "coily", "kinky", "afro"]): curliness = 1.0
        if any(w in low_name for w in ["wavy"]): curliness = 0.5
        if any(w in low_name for w in ["straight", "bob"]): curliness = 0.0
        
        return [length, volume, curliness]
    
    return [0.0, 0.0, 0.0]
