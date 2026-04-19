# Infinite Streaming Synthetic Training Pipeline (Specification)

## 1. Architectural Overview
This pipeline implements an **Infinite Online Synthetic Training** (Streaming Generative Training) architecture. Instead of generating a massive fixed dataset to disk, the system dynamically generates data "just-in-time" for the ML model.

This is a Producer-Consumer architecture:
*   **Producer**: A multi-process swarm of headless Blender workers rendering infinite procedural variance.
*   **Buffer**: A localized rolling file buffer tracking un-consumed samples.
*   **Consumer**: A custom PyTorch `IterableDataset` that loads batches into VRAM and instantly deletes the source files from disk.

### Key Benefits
*   **Zero Overfitting (True Epoch-Free)**: The DINO backbone never sees the same pixel configuration twice. The variance is nearly infinite.
*   **Zero Storage Waste**: Disk footprint caps out at ~1GB (a few thousand buffered images) instead of terabytes.
*   **Memory Safe**: Blender is notoriously poor at garbage collection. By making Blender workers "Disposable" (they die and respawn rhythmically), we circumvent C++ memory leaks entirely.

---

## 2. Component 1: The Blender Swarm (Producers)
The generator script orchestrates the Blender instances to ensure high-throughput GPU saturation without locking the OS.

### 2.1 The Master Orchestrator
A Python script (`swarm_manager.py`) runs on the host OS.
*   **CPU Core Matching**: The master detects available CPU/GPU cores and maintains exactly $N$ active Blender sub-processes.
*   **High-Water Mark (Throttle)**: Before spawning a new worker or sending new instructions, the Master checks the Rolling Buffer. If the buffer contains > `MAX_BUFFER` (e.g., 2000) images, the Master sleeps. This prevents disk explosion if Blender runs faster than DINO.

### 2.2 The Disposable Worker (`worker_kernel.py`)
The actual Blender process.
*   **Batch Quota**: When a worker starts, it is instructed to generate exactly $K$ avatars (e.g., $K=50$).
*   **Atomic Writes**: To prevent race-conditions where DINO tries to read an image currently being saved:
    1.  Worker renders to `sample_1234_selfie.png.tmp`.
    2.  Worker writes labels to `sample_1234_labels.json.tmp`.
    3.  Worker performs an atomic OS rename: `.tmp` $\rightarrow$ `.png` / `.json`.
*   **Kamikaze Protocol**: Once $K$ avatars are complete, `sys.exit(0)`. The Master immediately notices the process termination and spins up a fresh replacement.

---

## 3. Component 2: The PyTorch Consumer (Dataloader)
The regression model consumes data via a specialized `IterableDataset` (`streaming_dataset.py`).

### 3.1 The Watcher Interface
*   The Dataset constantly polls the Rolling Buffer directory.
*   It looks for valid pairs (e.g., `hash_selfie.png`, `hash_body.png`, `hash_labels.json`).
*   **Low-Water Mark (Block)**: If no valid pairs are found, the PyTorch training loop simply blocks/sleeps until the Blenders catch up.

### 3.2 The Read-And-Destroy Cycle
Inside the `__iter__` method:
1.  **Pop**: Retrieve the paths to a randomly selected valid sample pair.
2.  **Load**: Read the image files into Tensors (via `torchvision` or PIL) and parse the 36-float JSON.
3.  **Delete**: Issue an `os.remove()` for all three files immediately to free space.
4.  **Yield**: Pass the loaded, transformed tensors and the 36-float array to the DINO collator.

---

## 4. Pipeline File Structure
```text
ready-player-you/
├── datagen/
│   ├── SPEC.md                    # This document
│   ├── swarm_manager.py           # The Orchestrator (Subprocess pool management)
│   ├── worker_kernel.py           # The Blender script (Runs inside Blender context)
│   ├── asset_metadata.json        # Ground Truth digitized semantic triads
│   └── rolling_buffer/            # The localized /tmp/ directory for IPC
│       ├── .gitkeep
│       └── (transient png/json pairs live here)
├── training/
│   └── streaming_dataset.py       # Custom PyTorch IterableDataset
```

---

## 5. Potential Bottlenecks & mitigations
1.  **I/O Thrashing**: If your storage drive is slow (e.g., HDD), writing and deleting 30 files a second will cause OS-level bottlenecking. 
    *   *Mitigation*: Mount `rolling_buffer/` as a RAM Disk (`tmpfs` on Linux/Mac) so zero physical disk I/O occurs.
2.  **Blender Startup Overhead**: It takes ~2-3 seconds for a headless Blender to boot.
    *   *Mitigation*: Optimize the Batch Quota ($K$). If $K$ is too high, memory leaks happen. If $K$ is too low, the system wastes too much CPU time booting Blender. $K=50$ to $K=100$ is usually the golden ratio for MPFB generation.
