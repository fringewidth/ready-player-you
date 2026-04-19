import os
import time
import ssl
import torch
import torch.nn as nn
import torch.optim as optim
from prepare import get_dataloader, evaluate_mse, get_num_params, TRAIN_TIME_BUDGET

# Fix for macOS SSL
ssl._create_default_https_context = ssl._create_unverified_context

# --- 1. Model Architecture (The Agent edits this) ---
class IdentityRegressor(nn.Module):
    def __init__(self, output_dim=36):
        super().__init__()
        # Load DINOv2 Base with Registers
        self.backbone = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitb14_reg')
        
        # Initial Hill-climbing Constraint: Freeze Backbone
        for param in self.backbone.parameters():
            param.requires_grad = False
            
        embed_dim = 768 
        self.head = nn.Sequential(
            nn.Linear(embed_dim * 2, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Linear(256, output_dim),
            nn.Sigmoid() 
        )

    def forward(self, selfie, body):
        f1 = self.backbone(selfie)
        f2 = self.backbone(body)
        fused = torch.cat((f1, f2), dim=1)
        return self.head(fused)

# --- 2. Training Loop (Agent can optimize hyperparameters here) ---
def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
    
    model = IdentityRegressor().to(device)
    optimizer = optim.AdamW(model.head.parameters(), lr=3e-4, weight_decay=1e-4)
    criterion = nn.MSELoss()
    
    loader = get_dataloader()
    
    start_total = time.time()
    start_train = time.time()
    num_steps = 0
    
    model.train()
    print(f"[*] Starting 5-minute training run on {device}...")
    
    # Track peak memory (using torch.mps if on Mac)
    peak_vram = 0
    
    try:
        while (time.time() - start_train) < TRAIN_TIME_BUDGET:
            for batch in loader:
                if (time.time() - start_train) >= TRAIN_TIME_BUDGET: break
                
                selfies = batch["selfie"].to(device)
                bodies = batch["body"].to(device)
                labels = batch["label"].to(device)
                
                optimizer.zero_grad()
                preds = model(selfies, bodies)
                loss = criterion(preds, labels)
                loss.backward()
                optimizer.step()
                
                num_steps += 1
                
                # Update peak memory
                if device.type == 'mps':
                    current_mem = torch.mps.current_allocated_memory() / (1024 * 1024)
                    if current_mem > peak_vram: peak_vram = current_mem
                elif device.type == 'cuda':
                    current_mem = torch.cuda.max_memory_allocated() / (1024 * 1024)
                    if current_mem > peak_vram: peak_vram = current_mem

    except KeyboardInterrupt:
        pass
        
    training_seconds = time.time() - start_train
    
    # --- 3. Final Evaluation (Ground Truth) ---
    val_mse = evaluate_mse(model, device)
    total_seconds = time.time() - start_total
    
    # --- 4. Required Output Summary (Do not modify format) ---
    print("---")
    print(f"val_mse:          {val_mse:.6f}")
    print(f"training_seconds: {training_seconds:.1f}")
    print(f"total_seconds:    {total_seconds:.1f}")
    print(f"peak_vram_mb:     {peak_vram:.1f}")
    print(f"num_steps:        {num_steps}")
    print(f"num_params_M:     {get_num_params(model):.1f}")
    print("---")

if __name__ == "__main__":
    import logging
    logging.getLogger('torch.hub').setLevel(logging.ERROR)
    train()
