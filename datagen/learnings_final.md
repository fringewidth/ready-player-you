# Prototype Learnings: Synthetic Human Avatar Generation

This document serves as the technical hand-off for the **DINO regression model** data pipeline. It summarizes the architectural decisions, non-obvious hurdles, and "golden" configurations discovered during the headless Blender-MPFB prototype phase.

## 1. Core Labeling Strategy: The 36-Float Semantic Vector
For DINO-based regression, we moved away from categorical classes. Instead, every identity is represented by a **36-float vector**. This allows the model to learn feature relationships (e.g., thickness, hair length, volume) rather than unique asset IDs.

### Vector Schema:
| Index | Feature | Range | Notes |
|-------|---------|-------|-------|
| 0 | Gender | [0, 1] | 0=Male, 1=Female |
| 1 | Age | [0, 1] | Young to Old |
| 2-8 | Phenotype | [0, 1] | Muscle, Weight, African, Asian, Caucasian, Height, Proportions |
| 9-11 | Beard Triad | [0, 1] | Possession, Volume, Curliness |
| 12-14 | Hair Triad | [0, 1] | Length, Volume, Curliness |
| 15-17 | Glasses Triad| [0, 1] | Possession, Roundness, Thickness |
| 18-20 | Eyebrows Triad| [0, 1] | Possession, Thickness, Arching |
| 21-23 | Eyelashes Triad| [0, 1] | Possession, Length, Volume |
| 24-26 | Hair RGB | [0, 1] | Linear RGB |
| 27-29 | Facial Hair RGB| [0, 1] | Linear RGB |
| 30-32 | Skin RGB | [0, 1] | Palette-mapped Linear RGB |
| 33-35 | Eye RGB | [0, 1] | Procedural Linear RGB |

---

## 2. Material Science: The "Stylized" Skin Pipeline
A major hurdle was the MPFB auto-material system. Default MPFB materials use complex texture stacks that are inconsistent across races and don't match the "Stylized" aesthetic.

### The Solution: Direct Slot-0 Injection
To ensure a flat, reliable color:
1.  **Skip MPFB Shaders**: We do not look for "Skin" by name (which can vary).
2.  **Target Slot 0**: The human basemesh always keeps the body skin in the first material slot.
3.  **Overwrite with Principled BSDF**: We create a fresh material, assign it to `obj.data.materials[0]`, and set the `Base Color` to our sampled Linear RGB.
4.  **Gamma Correction**: Perceptual hex codes from the user (sRGB) must be converted using `val ** 2.2` before being passed to Blender's `default_value` nodes.

### Melanin Sampler:
We use a **32-point curated palette** instead of linear math. We pick two neighboring sRGB anchors and linearly interpolate between them before converting to Linear space. This avoids "Gray" mid-tones.

---

## 3. Camera Framing: The "Head Bone" Tracking
Initially, camera centering was erratic. Tracking the "object center" hidden behind hair or looking too low at the chest.

### Winning Formula:
- **Target Point**: Center of the `head` bone (`mixamorig:Head`).
- **Selfie Framing**:
    - **Distance**: 0.75m to 0.9m.
    - **No Offset**: Looking directly at the bone center provides the best "Portrait" centering.
    - **Focal Length**: 35mm to 85mm (simulating real phone/portrait lenses).
- **Body Framing**: Distance of 6.0m targeting the `hips` bone.

---

## 4. Asset Management (Vision-Based Digitization)
We have transitioned from manual heuristics to a **Digitized Asset Pipeline**.
- **The "Pit-Fight" System**: Using Moondream, assets are ranked pairwise (e.g., "Which hair is longer?") to eliminate subjective model bias.
- **asset_metadata.json**: This file serves as the definitive Ground Truth. The generator loads it at startup and performs a $O(1)$ lookup for the 3-float semantic triad of any assigned asset.
- **Zero-Fallback**: If an asset is missing from the metadata, the script defaults to `[0.0, 0.0, 0.0]` ensure the labels remain valid for training.

---

## 5. Environment & Lighting
High variance in environmental lighting is achieved through **Poly Haven HDRI** integration.
- **Intensity Jitter**: `0.5` to `2.5` to simulate indoor/outdoor extremes.
- **Rotation Jitter**: 360-degree Z-rotation to move shadows around the face.
- **Fallback**: Maintain a 3-point light rig for CI/CD environments where HDRIs might be missing.

---

## 6. Technical Gotchas (Post-Mortem)
1.  **Name Instability**: MPFB uses `Basemesh` as the object name, but this can change to `Human` or `Identity`. Always identify the human via the `ARMATURE` parent or the presence of specific phenotype shapekeys.
2.  **Shader Node Trees**: Some hair assets use `Hair BSDF` vs `Principled BSDF`. The color script must walk the node tree and check for any `BSDF` input that has "Color" or "Base Color" in its name.
3.  **Mixamo Overlap**: When applying Mixamo rigging, ensure the mesh is in T-pose *before* binding. MPFB's `rigservice` handles this well if the character is initialized to standard "A-pose" defaults first.

## 7. Next Phase: Scaling to 100k Samples
For the full rewrite, the bottleneck will be Blender session startup.
- **Strategy**: One Blender process per GPU core.
- **Worker Pattern**: Each worker spawns and renders ~1000 identities before recycling the Blender instance (to avoid memory leaks in the shader cache).
- **Format**: Render to `.webp` or `.jpg` (90% quality) to save disk space over `.png` for the training set.

---
*Documentation Compiled by Antigravity AI Prototype Pilot*
