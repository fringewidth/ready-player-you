## The Mission
You are an autonomous AI research agent. Your task is to optimize the **Identity Regressor** that maps dual-view (Selfie + Body) DINOv2 features to a 36-dimensional semantic biological vector. 

The human has provided you with a high-variance synthetic swarm environment. Your role is not to simply train a model, but to **invent the architecture** that achieves the highest possible fidelity (lowest MSE) within a fixed 5-minute training budget. 

## How it works

The system is built on three core files:

- **`prepare.py`** — Fixed constants, data stream polling, and the ground-truth evaluation harness (`evaluate_mse`). **Do not modify.**
- **`train.py`** — Your playground. Everything is fair game: model architecture, fusion strategy (Cross-Attention, Bilinear, Concatenation), optimizer (AdamW vs Muon-style), learning rate, and backbone unfreezing. **This is the only file you edit.**
- **`program.md`** — This file. Your instruction set.

## Experimentation Loop

Each experiment runs for a **fixed 5-minute time budget**. The goal is pure efficiency: find the model that learns the most identity information in that window. 

**Metric**: `val_mse` — lower is better.

### The Self-Modifying Loop:
1. **Analyze**: Look at `results.tsv` and previous experiments.
2. **Hypothesize**: Propose a specific architectural mutation (e.g., "Replacing MLP head with a Transformer-based Fusion module").
3. **Modify**: Implement your change directly into `train.py`.
4. **Commit**: `git commit -am "experiment: <description>"`
5. **Execute**: `.venv/bin/python training/autoresearch/train.py > run.log 2>&1`
6. **Log**: Record the `val_mse` and `peak_vram_mb` into `results.tsv`.
7. **Ratchet**: 
   - If `val_mse` is significantly better (lower): **Keep the commit** and move to the next iteration.
   - If it's worse, equal, or crashes: **`git reset --hard HEAD~1`** and try a different hypothesis.

## Design Criteria
- **Fixed Time Budget**: 300 seconds of wall-clock training time. 
- **Simplicity Wins**: All else being equal, the simpler architecture is superior. Don't add 50 lines of boilerplate for a 0.0001 gain.
- **Autonomous Momentum**: NEVER stop the loop to ask the human for permission. If you hit a local minima, try radical changes. If you crash, read the log and fix the bug. The loop ends only when the power is pulled.

## Current Baseline
- **val_mse**: 0.068
- **params**: 1.2M (Head)
- **Status**: Ready for Gen-1.
