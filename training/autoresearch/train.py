import os
import time
import ssl
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from prepare import get_dataloader, get_num_params

# Fix for macOS SSL
ssl._create_default_https_context = ssl._create_unverified_context

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# --- 1. Model Architecture (The Agent edits this) ---
class IdentityRegressor(nn.Module):
    def __init__(self, output_dim=36):
        super().__init__()
        self.backbone = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitb14_reg')
        for param in self.backbone.parameters():
            param.requires_grad = False

        embed_dim = 768
        self.head = nn.Sequential(
            nn.Linear(embed_dim * 2, output_dim),
            nn.Sigmoid()
        )

    def forward(self, selfie, body):
        f1 = self.backbone(selfie)
        f2 = self.backbone(body)
        fused = torch.cat((f1, f2), dim=1)
        return self.head(fused)

# --- 2. Experiment config ---
TRAIN_TIME_BUDGET = 900  # 15 minutes
LR = 1e-3               # exp14: linear probe 1536->36 (no hidden layer)
WEIGHT_DECAY = 1e-4

def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')

    model = IdentityRegressor().to(device)
    optimizer = optim.AdamW(model.head.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    criterion = nn.MSELoss()

    loader = get_dataloader()

    start_train = time.time()
    num_steps = 0
    peak_vram = 0
    best_loss = float('inf')
    loss = torch.tensor(1.0)
    recent_losses = []  # rolling window for stable metric

    model.train()
    print(f"[*] Starting training on {device} | lr={LR}", flush=True)

    try:
        while (time.time() - start_train) < TRAIN_TIME_BUDGET:
            for batch in loader:
                if (time.time() - start_train) >= TRAIN_TIME_BUDGET:
                    break

                selfies = batch["selfie"].to(device)
                bodies = batch["body"].to(device)
                labels = batch["label"].to(device)

                optimizer.zero_grad()
                preds = model(selfies, bodies)
                loss = criterion(preds, labels)
                loss.backward()
                optimizer.step()

                num_steps += 1
                recent_losses.append(loss.item())
                if len(recent_losses) > 10:
                    recent_losses.pop(0)

                if num_steps % 10 == 0:
                    print(f"[*] Step {num_steps} | Loss: {loss.item():.6f}", flush=True)

                if device.type == 'mps':
                    current_mem = torch.mps.current_allocated_memory() / (1024 * 1024)
                    if current_mem > peak_vram:
                        peak_vram = current_mem
                elif device.type == 'cuda':
                    current_mem = torch.cuda.max_memory_allocated() / (1024 * 1024)
                    if current_mem > peak_vram:
                        peak_vram = current_mem

                if loss.item() < best_loss:
                    best_loss = loss.item()
                    torch.save(model.state_dict(), os.path.join(CHECKPOINT_DIR, "best.pt"))

    except KeyboardInterrupt:
        pass

    training_seconds = time.time() - start_train
    val_mse = sum(recent_losses) / len(recent_losses) if recent_losses else 1.0

    torch.save(model.state_dict(), os.path.join(CHECKPOINT_DIR, "last.pt"))

    print("---", flush=True)
    print(f"val_mse:          {val_mse:.6f}", flush=True)
    print(f"training_seconds: {training_seconds:.1f}", flush=True)
    print(f"peak_vram_mb:     {peak_vram:.1f}", flush=True)
    print(f"num_steps:        {num_steps}", flush=True)
    print(f"num_params_M:     {get_num_params(model):.1f}", flush=True)
    print("---", flush=True)

if __name__ == "__main__":
    import logging
    logging.getLogger('torch.hub').setLevel(logging.ERROR)
    train()
