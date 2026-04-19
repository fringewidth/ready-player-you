import os
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Setup paths for synthetic data loader
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from streaming_dataset import AvatarStreamingDataset

# --- Constants ---
MAX_SEQ_LEN = 1 # Not used for regression, but keeping for structural 1:1
TRAIN_TIME_BUDGET = 300 # 5 Minutes in seconds
EVAL_STEPS = 50
BATCH_SIZE = 16

def get_dataloader():
    """Fixed dataloader for 1:1 experiment comparison."""
    buffer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../datagen/rolling_buffer"))
    dataset = AvatarStreamingDataset(buffer_dir=buffer_path)
    # num_workers=0 is safer for file-stream polling
    return DataLoader(dataset, batch_size=BATCH_SIZE, num_workers=0)

@torch.no_grad()
def evaluate_mse(model, device):
    """
    Fixed evaluation harness. 
    The Ground Truth metric for our research agent.
    """
    model.eval()
    loader = get_dataloader()
    criterion = nn.MSELoss()
    
    total_loss = 0
    count = 0
    
    # We poll a fixed number of samples from the rolling buffer for eval consistency
    for i, batch in enumerate(loader):
        if i >= EVAL_STEPS: break
        
        selfies = batch["selfie"].to(device)
        bodies = batch["body"].to(device)
        labels = batch["label"].to(device)
        
        preds = model(selfies, bodies)
        loss = criterion(preds, labels)
        
        total_loss += loss.item()
        count += 1
        
    avg_loss = total_loss / count if count > 0 else 1.0
    return avg_loss

def get_num_params(model):
    """Calculates model size in Millions."""
    return sum(p.numel() for p in model.parameters()) / 1e6
