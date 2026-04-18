# Synthetic Avatar Training Architecture

## Goal

Train a frozen DINO backbone plus a small regression head on synthetic Blender renders generated on demand from MakeHuman-like avatar parameters.

The system should:

- avoid storing a full image corpus
- keep the GPU fed with live synthetic batches
- support endless training steps instead of fixed epochs
- preserve a fixed validation set for regression checks
- keep inference image-only

## Global Avatar Rules

These rules apply to all synthetic data generation, including the prototype and the final generator.

- default human creation must be callable asynchronously and should correspond to clicking `Create Human` from `From scratch`
- phenotype randomization must respect valid constraints, especially `race` summing to `1.0` across `african`, `asian`, and `caucasian`
- `breast shape < 0.5` only when `gender < 0.5`
- minimum age is `0.5`; children are not supported
- height is standardized based on gender to maintain consistent head-level: `height = 0.5 + (0.12 * gender)`. This maps female (gender=0) to 0.5 and male (gender=1) to 0.62.
- left and right arm values must always be equal
- breast and buttocks sections are not touched
- cheek bones, ears, and eyes must always be symmetric
- feet are not touched
- genitals are not touched
- pelvis is not touched
- hands are not touched

These rules define the safe parameter space for the renderer and the labels.

## Core Idea

Synthetic data is a stream, not a dataset file.

The generator produces labeled renders continuously in the background. The trainer consumes mini-batches from a queue. The queue exists to hide Blender render latency and keep training throughput stable.

## Components

### 1. Blender Worker

A headless Blender process:

- loads the base scene
- samples avatar parameters
- applies camera and lighting randomization
- renders the image
- writes labels for the sample

The worker should support a collage-style capture per identity:

- a face selfie tile
- a body `A`-pose tile

The two tiles are packed into one image tensor so the DINO backbone can consume them as a single input. Keep the layout fixed and consistent.

Only the collage image is fed to the model. The other fields are labels or render-time controls. Labels are structured as a fixed-length **Semantic Descriptor Vector** to optimize for a DINO-based regression head.

### 2. Label Vector Structure

To maintain a fixed-length output regardless of library size, assets are tagged with continuous visual features rather than discrete IDs.

#### A. Body & Face Sliders (Macro Targets)
- `[0:9]` : Base phenotype (Gender, Age, Muscle, Weight, African, Asian, Caucasian, Height, Proportions) in `[0, 1]` range.

#### B. Facial Hair (3-Float Descriptor)
- `f[0]: mustache_density` (0 to 1)
- `f[1]: beard_density` (0 to 1)
- `f[2]: connection` (0 or 1, strength of mustache-beard bridge)

#### C. Head Hair (3-Float Descriptor)
- `h[0]: length` (0=Bald to 1=Long)
- `h[1]: volume` (0=Flat to 1=Afro/Voluminous)
- `h[2]: curliness` (0=Straight to 1=Coily)

#### E. Colors (6-Float Descriptor)
- `c[0:2]` : Scalp Hair RGB (0 to 1)
- `c[3:5]` : Non-Scalp Hair RGB (Eyebrows, Lashes, Beards)

#### Color Logic:
 - 90% Natural colors (Black, Blonde, Brunette, Ginger), 10% fully random RGB.
 - 95% matching between Scalp and Non-Scalp; 5% independent.
 - Implementation: Disconnect texture links on material nodes and override with RGB constant.

### 2. Prefetch Queue

A small buffer of ready samples sits between rendering and training.

Recommended behavior:

- keep `batch_size * 16` samples prefetched as a starting point
- return immediately if enough samples already exist
- block only when the queue is empty or undersized
- refill continuously in the background

This is the main mechanism that makes live generation practical.

### 3. Trainer

The trainer pulls batches from the queue and performs ordinary supervised learning.

Important point: this is still batching. The difference is that the batch is assembled from a live stream rather than a static dataset.

Training loop shape:

1. request a batch of size `B`
2. wait if the queue does not yet contain `B` samples
3. run the forward/backward pass
4. repeat for a fixed number of steps

Epochs are optional and usually not the useful unit here. Step count is the useful unit.

### 4. Validation Set

Validation should be fixed and finite.

This lets you check:

- whether synthetic randomization is helping
- whether real-image transfer is improving
- whether the head is collapsing onto shortcuts

Do not generate validation on the fly if you want stable comparisons.

## Sample Flow

1. Blender worker renders sample `n`.
2. The worker serializes labels and render metadata next to the render.
3. The sample enters the prefetch queue.
4. The trainer asks for a batch.
5. The queue returns ready samples immediately if possible.
6. The optimizer takes a step.

## Buffer Sizing

The right buffer size depends on render latency and training speed.

Starting point:

- `batch_size * 16` queued samples

Adjust based on runtime behavior:

- if training stalls, increase generator parallelism or buffer depth
- if the queue grows too large, reduce depth or worker count
- if Blender startup is expensive, keep workers warm instead of respawning them

## Infinite Training

“Infinite synthetic dataset” means:

- no fixed dataset size
- no precomputed full render archive
- no need to cycle over a finite corpus

It does not mean:

- no batch size
- no optimizer steps
- no validation

The training job is simply a long-running consumer of an endless labeled stream.

## Practical Rule

Use live generation when:

- render variation is cheap relative to storage
- you want heavy randomization
- you do not want to manage a giant on-disk dataset

Use caching only as a temporary performance layer, not as the source of truth.

## Focal Length

Do not pass focal length into the model.

If it is varied during rendering, treat it as a hidden nuisance factor the model must tolerate from pixels alone.

If performance degrades badly on real images, revisit the renderer or collage design, not the inference input contract.
