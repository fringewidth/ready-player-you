import os
import time
import json
import torch
import random
from torch.utils.data import IterableDataset, DataLoader
from torchvision import transforms
from PIL import Image

class AvatarStreamingDataset(IterableDataset):
    """
    Consumer for the Infinite Synthetic Swarm (Multi-View).
    Yields (selfie, body, label) and purges files to maintain zero disk footprint.
    """
    def __init__(self, buffer_dir, transform=None, poll_interval=0.5):
        self.buffer_dir = buffer_dir
        self.poll_interval = poll_interval
        # Standard ImageNet normalization for DINO
        self.transform = transform or transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        if not os.path.exists(self.buffer_dir):
            os.makedirs(self.buffer_dir)

    def _get_complete_bundles(self):
        """Finds IDs that have all 3 components: selfie, body, and json metadata."""
        try:
            files = os.listdir(self.buffer_dir)
        except OSError:
            return []
            
        jsons = [f[:-5] for f in files if f.endswith(".json")]
        bundles = []
        for bid in jsons:
            if f"{bid}_selfie.png" in files and f"{bid}_body.png" in files:
                bundles.append(bid)
        return bundles

    def __iter__(self):
        while True:
            bundles = self._get_complete_bundles()
            
            if not bundles:
                time.sleep(self.poll_interval)
                continue
                
            # Random shuffle within the buffer to increase variance
            random.shuffle(bundles)
            
            for bid in bundles:
                json_path = os.path.join(self.buffer_dir, f"{bid}.json")
                selfie_path = os.path.join(self.buffer_dir, f"{bid}_selfie.png")
                body_path = os.path.join(self.buffer_dir, f"{bid}_body.png")
                
                try:
                    # 1. Load Labels (36-float identity vector)
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    label = torch.tensor(data['vector'], dtype=torch.float32)
                    
                    # 2. Load Images
                    selfie_img = Image.open(selfie_path).convert("RGB")
                    body_img = Image.open(body_path).convert("RGB")
                    
                    if self.transform:
                        selfie_img = self.transform(selfie_img)
                        body_img = self.transform(body_img)
                    
                    # 3. Purge Files (Maintain zero footprint)
                    os.remove(json_path)
                    os.remove(selfie_path)
                    os.remove(body_path)
                    
                    yield {
                        "id": bid,
                        "selfie": selfie_img,
                        "body": body_img,
                        "label": label
                    }
                    
                except Exception as e:
                    # Silent skip for race conditions (Blender still writing)
                    continue

# --- DINO Training Integration ---
if __name__ == "__main__":
    # Point to the rolling buffer managed by swarm_manager.py
    BUFFER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../datagen/rolling_buffer"))
    
    dataset = AvatarStreamingDataset(buffer_dir=BUFFER_PATH)
    loader = DataLoader(dataset, batch_size=16) # Batch of 16 avatars = 32 images

    print(f"[*] Streaming Dataset initialized on: {BUFFER_PATH}")
    print("[*] Waiting for swarm bundles...")
    
    for i, batch in enumerate(loader):
        print(f"[*] Batch {i} | Selfie: {batch['selfie'].shape} | Body: {batch['body'].shape} | Labels: {batch['label'].shape}")
        if i >= 10: break # Small test sample
