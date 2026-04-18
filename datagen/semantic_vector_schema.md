# 36-Float Semantic Vector Specification (V1.1 - Pure Identity)

This document defines the exact index-to-trait mapping for the synthetic avatar dataset. The vector is designed for continuous identity regression using a DINOv2 backbone. The model is expected to learn viewpoint-invariance from the pixels alone.

**Total Length**: 36 Floats
**Normalization**: All values are in the range `[0.0, 1.0]`.

---

### Phase 1: Base Phenotype (Indices 0–8)
| Index | Trait | 0.0 Meaning | 1.0 Meaning |
|-------|-------|-------------|-------------|
| 0 | Gender | Masculine | Feminine |
| 1 | Age | Young (Min) | Old (Max) |
| 2 | Muscle | Low Muscle | High Muscle |
| 3 | Weight | Thin | Heavy |
| 4 | African | Low Probability | Full African Phenotype |
| 5 | Asian | Low Probability | Full Asian Phenotype |
| 6 | Caucasian | Low Probability | Full Caucasian Phenotype |
| 7 | Height | Shortest | Tallest |
| 8 | Proportions | Realistic/Compact | Stylized/Elongated |

---

### Phase 2: Asset Semantic Triads (Indices 9–23)
*Each asset category follows a [Possession, Trait A, Trait B] pattern.*

| Indices | Category | Trait A | Trait B |
|---------|----------|---------|---------|
| 9-11 | **Beard** | Volume (Bushy) | Curliness |
| 12-14 | **Hair** | Length | Volume/Bigness |
| 15-17 | **Glasses** | Roundness | Thickness |
| 18-20 | **Eyebrows**| Thickness | Arch/Elevation |
| 21-23 | **Eyelashes**| Length | Volume/Fullness |

---

### Phase 3: Color Manifest (Indices 24–35)
*All colors are delivered as Linear RGB triplets.*

| Indices | Layer | Notes |
|---------|-------|-------|
| 24-26 | **Hair RGB** | Primary scalp hair color |
| 27-29 | **Beard RGB** | Synchronized or varied facial hair color |
| 30-32 | **Skin RGB** | Melanin-mapped stylized skin tone |
| 33-35 | **Eye RGB** | Procedural stylized eye (Iris) color |

---

## Technical Notes for Training:
1.  **Possession Masking**: For Beard and Glasses (and Hair), the first float in the triad (Possession) acts as a mask. If `Index 9` is 0.0, the model should ignore the loss for `Indices 10 & 11`.
2.  **Color Correlation**: Hair and Beard colors are often identical (95% correlation), which the model should learn as a biological prior.
3.  **Linear RGB**: All color predictions should be mapped to Linear space. sRGB conversion should only happen at the final display layer.
