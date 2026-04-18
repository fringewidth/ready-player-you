# Datagen

Synthetic avatar data generation for MakeHuman + Blender.

## Goal

Generate labeled renders in headless Blender from a parameter sweep over:

- body and face sliders
- skin tone
- camera angle
- HDRI / lighting setup
- assets such as hair and clothing

Global avatar constraints are documented in [architecture.md](./architecture.md) and apply to the prototype and the final generator.

The current model input plan is a fixed-layout collage containing a face selfie tile and a body `A`-pose tile. The model is image-only at inference; focal length and other camera properties are renderer-side variables only.

## Current shape

This folder is a scaffold. The first implementation step is a headless Blender runner that:

1. loads a base scene
2. iterates over sampled parameter combinations
3. renders images
4. writes labels next to each render

## Suggested entrypoint

Run Blender in background mode with a Python script:

```bash
blender --background --python datagen/blender/render_sweep.py -- --config datagen/config/sweep.toml
```
