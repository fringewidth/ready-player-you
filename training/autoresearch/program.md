## The Mission
You are an autonomous AI research agent. Your task is to optimize the **Identity Regressor** that maps dual-view (Selfie + Body) DINOv2 features to a 36-dimensional semantic biological vector. 

The human has provided you with a high-variance synthetic swarm environment. Your role is to improve the model under a strict wall-clock budget without breaking the measurement loop. Start with high-signal, low-complexity changes. Do not overengineer.

## How it works

The system is built on three core files:

- **`prepare.py`** — Fixed constants, data stream polling. **Do not modify.**
- **`train.py`** — Your playground. Everything is fair game: model architecture, fusion strategy, optimizer, learning rate, backbone unfreezing. **This is the only file you edit.**
- **`program.md`** — This file. Your instruction set.

## Key Insight: Infinite Dataset

The swarm generates infinite fresh synthetic data. Every batch is unseen — there is no overfitting risk and no train/val split needed. The final training batch loss (`loss.item()`) is already an unbiased estimate of generalization. **Do not add an evaluate_mse call after training — it wastes time on the same distribution.**

## Experimentation Loop

Each experiment runs for a **fixed 15-minute time budget**. The goal is pure efficiency: find the model that learns the most identity information in that window.

**Metric**: `val_mse` — lower is better. Reported as the final training batch loss.

### The Self-Modifying Loop:
1. **Analyze**: Look at `results.tsv` and previous experiments.
2. **Hypothesize**: Propose one specific change only. Favor simple mutations first:
   - learning rate / weight decay
   - head width / depth
   - fusion choice (concat vs element-wise product vs sum)
   - LR scheduler (cosine, step)
   - limited backbone unfreezing only after simpler options plateau
3. **Modify**: Implement your change directly into `train.py`.
4. **Execute**: `.venv/bin/python training/autoresearch/train.py > training/autoresearch/run.log 2>&1`
5. **Log**: Record the result in `results.tsv` with `val_mse`, timing, step count, param count, and a short description.
6. **Ratchet**: 
   - If `val_mse` is clearly better: keep the change and move to the next iteration.
   - If worse or inconclusive: revert only the experiment change and try a different hypothesis.
   - If plateau confirmed (no improvement over 3+ experiments): remove the walltime budget, enable periodic checkpointing, and train indefinitely.

## Design Criteria
- **Fixed Time Budget**: 900 seconds. Small overrun acceptable (check happens between batches).
- **Simplicity Wins**: Do not add cross-attention, complex fusion, or large new modules unless simpler changes have plateaued.
- **One variable at a time**: Do not mix architectural and optimizer changes in the same experiment.
- **No memory footprint increase**: Do not add layers or modules that increase GPU/MPS memory usage.
- **Save weights**: Always save the best model to `training/autoresearch/checkpoints/best.pt`.

## Current Baseline
- **Experiment 1**: `val_mse 0.075997`, `training_seconds 910.8`, `num_steps 62`, `num_params_M 87.5`
- Architecture: Frozen DINOv2-B/14 + concat(selfie, body) + MLP head [1536→512→256→36] + Sigmoid
- Optimizer: AdamW lr=3e-4, wd=1e-4
- **Priority for next run**: Try lr=1e-3 (3x increase) — more aggressive descent in same wall time.
