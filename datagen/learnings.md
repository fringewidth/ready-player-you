# MPFB & Blender Data Generation: Comprehensive Pilot Learnings

This document provides absolute technical context for the `ready-player-you` synthetic data generation pipeline. It is intended to allow a developer or AI agent with no prior knowledge of this conversation to implement the generator from scratch.

---

## 1. Environment & Technical Stack

### Core Versions
- **Blender**: 5.1.0 
- **MPFB (MakeHuman Plugin For Blender)**: v2 (specifically the version tailored for Blender 5.x extensions).

### The Extension Namespace (Critical)
Blender 4.2+ changed how addons/extensions are loaded. 
- **Problem**: Standard `import mpfb` or `from mpfb.services import ...` will fail.
- **Solution**: MPFB is now nested under the extension namespace: `bl_ext.blender_org.mpfb`.
- **Import Pattern**:
  ```python
  # Dynamic or absolute imports
  from bl_ext.blender_org.mpfb.services.humanservice import HumanService
  from bl_ext.blender_org.mpfb.services.targetservice import TargetService
  ```
- **Filesystem Location**: On macOS, the source code and targets are located at:
  `/Users/hrishik/Library/Application Support/Blender/5.1/extensions/blender_org/mpfb`

---

## 2. API & Service Architecture

Contrary to standard Blender scripting which relies on `bpy.ops`, MPFB is best controlled via its **Service Layer** for headless data generation.

### Human Creation
- **Method**: `HumanService.create_human()`
- **Context**: Every generation run starts with an empty scene. Do **not** assume a human exists in `prototype.blend`.
- **Scale**: The default `scale=0.1` results in human models where $1.0$ unit $\approx 1$ meter. A typical head will be at $Z \approx 1.6 \text{ to } 1.8$.

### Phenotype & Macro Parameters
Macro parameters (Gender, Age, Muscle, Weight, Height, Proportions, Race) are the primary control surface.
- **Race Dict**: Must contains keys `african`, `asian`, `caucasian`. They **must sum to 1.0**.
- **Age**: Minimum age is `0.5` (Young). `0.0` is Baby, `1.0` is Old.
- **Height**: Locked at `0.5` for all samples in this project.
- **Breast Constraint**: The user requirement "breast shape < 0.5 only when gender < 0.5" is implemented by restricting the `cupsize` macro parameter based on the `gender` value ($0.0$ = Female, $1.0$ = Male).

### Shape Keys (Targets)
MPFB deforms a base mesh using **Shape Keys** (called "Targets" in MakeHuman legacy).
- **Discovery**: Use `TargetService.get_target_stack(basemesh)` to inspect active deformations.
- **Symmetry**: MPFB uses specific naming (`left`/`right`, `.L`/`.R`) but does not always auto-symmetrize. Scripts must explicitly call `TargetService.symmetrize_shape_key()` or manually sync values for ears, eyes, cheeks, and arms.

---

## 3. Implementation Challenges & Solutions

### Problem: `ModuleNotFoundError`
**Scenario**: Attempting to `import mpfb` in a background script.
**Root Cause**: The addon is an extension and its directory is not automatically in `sys.path` for the site-packages.
**Resolution**: Use the full extension prefix `bl_ext.blender_org.mpfb`. If that fails, manually append the extension path to `sys.path`.

### Problem: `AttributeError: module 'bpy' has no attribute 'mathutils'`
**Scenario**: Calling `bpy.mathutils.Vector`.
**Root Cause**: `mathutils` is a standalone module in Blender 2.8+.
**Resolution**: Always `import mathutils` directly.

### Problem: Headless Operator Context
**Scenario**: `bpy.ops.mpfb.create_human()` failing in background mode.
**Root Cause**: Operators often check for specific UI regions/windows.
**Resolution**: Call `HumanService.create_human(...)` directly from the Python API. This bypasses the UI checks.

---

## 4. Assumptions: Validated vs. Refuted

| Assumption | Result | Learning |
| :--- | :--- | :--- |
| `prototype.blend` has a model. | **Refuted** | The file is just a "Stage" (Camera/Lights). Humans must be created at runtime. |
| One image is enough. | **Refuted** | A single capture misses body details. 2 captures (Selfie + A-Pose) are required. |
| Standard symmetry is active. | **Refuted**| MPFB allows asymmetric meshes by default. Symmetry must be enforced programmatically. |
| Height is randomized. | **Refuted** | Height is a constant (`0.5`) to reduce variance in scale/bounding boxes. |

---

## 5. Rendering Specifics

### Camera Positions (Scale 0.1)
To generate consistent crops for the collage:
- **Face Selfie**: 
  - Look At: `(0, 0, 1.65)` 
  - Cam Location: `(0, -0.8, 1.65)` (approximate)
- **Body A-Pose**:
  - Look At: `(0, 0, 0.9)`
  - Cam Location: `(0, -4.0, 0.9)`

### Lighting
The baseline lighting in `prototype.blend` may be insufficient for synthetic data.
**Recommendation**: Explicitly set the energy of the "Light" object to `1000+` or add an HDRI environment.

---

## 6. Glossary of Constraints
- **Race**: African + Asian + Caucasian = 1.0.
- **Age**: $\in [0.5, 1.0]$.
- **Gender**: $\in [0.0, 1.0]$.
- **Height**: Standardized using `0.5 + (0.12 * gender)` to keep heads at the same level across genders.
- **Symmetry Zones**: Cheek bones, Ears, Eyes, Arms.
## 7. Labeling Strategy (DINO Optimization)

*   **Avoid Asset IDs**: Predicting discrete IDs as floats (e.g., `0.7` for ID 7) fails because it implies a false spatial relationship between assets.
*   **Semantic Descriptor Groups**:
    *   **Face_Hair_3**: [mush, beard, connection]
    *   **Colors_6**: [Scalp RGB (3), Non-Scalp RGB (3)]
    *   **Cam_Pose_6**: [Selfie Yaw/Pitch/Roll, Body Yaw/Pitch/Roll]
    *   **Feature Alignment**: DINO learns visual features (texture/shape) rather than abstract IDs.
    *   **Graceful Degress**: Model mistakes result in "visually similar" assets rather than random ID jumps.

## 8. Realism & Correlation Rules

*   **Gender-Beard Correlation**: Facial hair (beards/mush) is only applied when `gender > 0.6` (Masculine).
*   **Gender-Macro Correlation**: Biological consistency is enforced. Characters with `gender > 0.6` (Masculine) are restricted to `cupsize < 0.1`.
*   **Age-Hair correlation**: "Natural" hair colors like Gray and White are restricted to elderly phenotypes (`age > 0.75`).
*   **Probability Distribution**:
    *   **Glasses**: ~10% occurrence.
    *   **Beards**: ~25% of masculine phenotypes.
    *   **Exotic Colors**: ~10% occurrence.
*   **Framing (Body A-Pose)**: Target distance set to **6.0m** to guarantee full-body coverage (head-to-toe) across the entire 24mm-85mm focal range.
