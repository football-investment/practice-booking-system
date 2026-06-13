# Juggling Contact Type Taxonomy v1

**Version:** v1  
**Created:** 2026-06-13  
**Source of truth:** `datasets/juggling/contact_types_v1.json`  
**Schema:** `datasets/juggling/annotation_schema_v2.json`  
**Policy:** No paid model · No AGPL production dependency · Own dataset · Own model

---

## Overview

The taxonomy defines **18 contact categories**: 17 stable types and 1 extensible custom category. All three surfaces that consume this taxonomy — the browser annotation helper, the iOS app, and the training pipeline — must derive their enumerations from `contact_types_v1.json`. There must never be two divergent category lists.

---

## Invariants (machine-verifiable)

| Invariant | Value |
|---|---|
| Total contact types | 18 |
| Stable keys | 17 |
| `right_*` stable keys | 7 |
| `left_*` stable keys | 7 |
| Center stable keys (chest, head, back) | 3 |
| `custom_other` | 1 |
| Duplicate keys | 0 |
| Duplicate sort_orders | 0 |
| `custom_other.excluded_from_training_auto` | `true` |
| `thigh → hip` auto-migration | **FORBIDDEN** |

---

## The 17 Stable Contact Types

### Group 1 — Lábfej / Foot (sort 1–8)

| # | Key | Magyar | English | Side | Auto-det. | Difficulty |
|---|---|---|---|---|---|---|
| 1 | `right_instep` | Jobb rüszt | Right instep | right (fixed) | Phase D | medium |
| 2 | `left_instep` | Bal rüszt | Left instep | left (fixed) | Phase D | medium |
| 3 | `right_inside_foot` | Jobb belső | Right inside foot | right (fixed) | — | hard |
| 4 | `left_inside_foot` | Bal belső | Left inside foot | left (fixed) | — | hard |
| 5 | `right_outside_foot` | Jobb külső | Right outside foot | right (fixed) | — | very_hard |
| 6 | `left_outside_foot` | Bal külső | Left outside foot | left (fixed) | — | very_hard |
| 7 | `right_heel` | Jobb sarok | Right heel | right (fixed) | — | very_hard |
| 8 | `left_heel` | Bal sarok | Left heel | left (fixed) | — | very_hard |

### Group 2 — Térd / Knee (sort 9–10)

| # | Key | Magyar | English | Side | Auto-det. | Difficulty |
|---|---|---|---|---|---|---|
| 9 | `right_knee` | Jobb térd | Right knee | right (fixed) | Phase D | medium |
| 10 | `left_knee` | Bal térd | Left knee | left (fixed) | Phase D | medium |

### Group 3 — Csípő / Hip (sort 11–12)

| # | Key | Magyar | English | Side | Auto-det. | Difficulty |
|---|---|---|---|---|---|---|
| 11 | `right_hip` | Jobb csípő | Right hip | right (fixed) | — | hard |
| 12 | `left_hip` | Bal csípő | Left hip | left (fixed) | — | hard |

> **Critical note:** `hip` and `thigh` are anatomically distinct contact zones. The v1 annotation schema had a `thigh` body_part that does **not** map automatically to `hip`. If a v1 annotation with `body_part=thigh` is found, it must be flagged `manual_review_required`. Auto-migration is forbidden.

### Group 4 — Felsőtest / Upper Body (sort 13–17)

| # | Key | Magyar | English | Side | Auto-det. | Difficulty |
|---|---|---|---|---|---|---|
| 13 | `chest` | Mellkas | Chest | center (no laterality) | Phase D | easy |
| 14 | `right_shoulder` | Jobb váll | Right shoulder | right (fixed) | Phase D | medium |
| 15 | `left_shoulder` | Bal váll | Left shoulder | left (fixed) | Phase D | medium |
| 16 | `head` | Fej | Head | center (no laterality) | Phase D | easy |
| 17 | `back` | Hát | Back | center (no laterality) | — | very_hard |

---

## The 18th Category — `custom_other` (sort 18)

`custom_other` is a **permanently extensible collector category** for techniques that do not fit any of the 17 stable types.

### Required fields when `contact_type = custom_other`

| Field | Type | Rule |
|---|---|---|
| `custom_label` | string | Required · `[a-z][a-z0-9_]{0,38}[a-z0-9]` · max 40 chars · must not match any existing stable key |
| `custom_description` | string | Required · max 200 chars · must not be empty |
| `side` | enum | Required · `left / right / center / unknown` · must not be null |
| `excluded_from_training` | boolean | Always `true` — not user-settable |
| `review_status` | enum | Always starts as `pending_taxonomy_review` |
| `annotator` | string | Required |

### Training exclusion policy

`custom_other` is **excluded from training in every review state without exception.**

| `review_status` | Excluded from training | Reason |
|---|---|---|
| `pending_taxonomy_review` | Yes | Not yet reviewed |
| `promotion_candidate` | Yes | Under evaluation; not finalised |
| `approved_unclassified` | Yes | Too heterogeneous; no consistent visual pattern |
| `reclassified` | — | Reclassified to a stable key; training uses the stable key label |
| `promoted` | — | A new stable key was created; training uses the new key label |

**There is no `unclassified_custom` training class.** Reason: heterogeneous unlabelled contact types would create a noisy training category with no consistent visual pattern, harming model quality.

### Taxonomy review flow

```
Annotator creates custom_other
  └─ review_status = pending_taxonomy_review (automatic)
  └─ excluded_from_training = true (automatic, immutable)

Taxonomy reviewer evaluates:
  ├─ Matches existing stable key
  │    └─ contact_type → stable key, review_status = reclassified
  │       (custom_label + custom_description preserved for audit)
  │
  ├─ Same custom_label in ≥3 different videos
  │    └─ review_status = promotion_candidate
  │       └─ Full taxonomy review
  │           ├─ Approved → new stable key added to contact_types_v2.json
  │           │              review_status = promoted
  │           │              Existing annotations migrated to new stable key
  │           └─ Rejected → review_status = approved_unclassified
  │
  └─ Rare or unclassifiable
       └─ review_status = approved_unclassified
          excluded_from_training = true (permanent)
```

### Promotion rules

1. Same `custom_label` seen in ≥ 3 different videos
2. Taxonomy reviewer sets `promotion_candidate = true`
3. New key name: normalised, deduplicated, manually approved (never auto-generated from `custom_label`)
4. New key added to `contact_types_v2.json` (version bump)
5. All `promoted` events updated: `contact_type → new stable key`; `custom_label` / `custom_description` preserved as audit fields
6. `custom_label` value **must never become an enum key automatically**

---

## Side Policy

### For stable contact types

The `side` value is fully determined by the `contact_type` key. Users and the iOS picker must not provide a separate side input for stable types. Validators must enforce this.

| Contact type pattern | Enforced `side` |
|---|---|
| `right_*` (7 keys) | `right` |
| `left_*` (7 keys) | `left` |
| `chest`, `head`, `back` | `center` |

### For `custom_other` only

`side` is required and must be one of: `left / right / center / unknown`. It must not be `null`.

---

## Unified Review Status Enum

Single enum used for all contact events regardless of source. Stable types and `custom_other` use non-overlapping subsets.

| Status | Used by | Meaning |
|---|---|---|
| `pending` | stable | Created; not yet reviewed |
| `confirmed` | stable | Reviewer confirmed type and side are correct |
| `corrected` | stable | Type or side was changed from a previous value |
| `rejected` | stable | Invalid event (false detection, double count). Excluded from `total_juggling_count` and training. |
| `pending_taxonomy_review` | custom_other | Initial state; awaiting taxonomy review |
| `reclassified` | custom_other | Reclassified to an existing stable key |
| `promotion_candidate` | custom_other | Under evaluation for new stable type |
| `promoted` | custom_other | New stable type created; `contact_type` updated |
| `approved_unclassified` | custom_other | Reviewed; will not be promoted; permanently excluded from training |

### Excluded from training

Events with these statuses must not be used as training labels:
`pending`, `rejected`, `pending_taxonomy_review`, `promotion_candidate`, `approved_unclassified`

---

## Annotation Source Enum

| Value | Who | Context |
|---|---|---|
| `manual_annotator` | Internal annotator | Browser helper or CLI — ground truth production |
| `manual_user` | Athlete / student | iOS app manual fallback (Phase C, after detection) |
| `model_prediction` | Trained model | Phase D+ auto-detection; not yet reviewed |
| `user_corrected` | Athlete / reviewer | Model prediction changed by a person |

---

## iOS Feature Rollout Order

**Phase A — Internal annotator mode** (first to implement)
- Full 18 contact type picker
- Timestamp recording
- Edit / delete
- Ground truth production tool
- Not visible to end users

**Phase B — Model correction mode** (after Phase D detection)
- Display model predictions (`annotation_source=model_prediction`)
- User can confirm (`confirmed`) or change (`user_corrected`) each prediction
- User cannot add contacts not detected by the model in this mode

**Phase C — Athlete simplified summary** (later)
- Shows `total_juggling_count` and dominant body region(s)
- Does not expose 18 granular contact type buttons to the athlete
- Read-only summary of the model's annotated result

---

## Backward Compatibility: v1 → v2 Mapping

| v1 `body_part` | v2 `contact_type` candidates | Migration rule |
|---|---|---|
| `foot` | right/left_instep, right/left_inside_foot, right/left_outside_foot, right/left_heel | Manual review required to pick the specific sub-type |
| `knee` | `right_knee`, `left_knee` | Manual review for side |
| `thigh` | **None** | **FORBIDDEN to auto-migrate to hip.** Flag `manual_review_required`. |
| `shoulder` | `right_shoulder`, `left_shoulder` | Manual review for side |
| `head` | `head` | Direct (no side change needed) |
| `chest` | `chest` | Direct (no side change needed) |

**v2 new keys not in v1:** `right_hip`, `left_hip`, `back`  
**v1 deprecated key:** `thigh` (not present in v2 enum; must not be used in new annotations)

### Current status of the 4 Batch 1 skeleton JSONs

All 4 annotation files (`jug_b1_001..004.json`) have `contact_events: null`. There is **no contact event data to migrate**. The skeleton JSON headers need updating from `annotation_version: v1.0` and `annotation_schema_version: 1.0` to v2 values when v2 is formally adopted, but this does not require migrating any contact event fields.

---

## No-Paid-Model Policy (unchanged from v1)

| Component | Tool | Licence |
|---|---|---|
| Video processing | ffmpeg | LGPL-2.1 |
| Preprocessing | opencv-python-headless | Apache 2.0 |
| Model training | PyTorch + torchvision | BSD-3-Clause |
| Model inference | ONNX + onnxruntime | Apache 2.0 / MIT |
| Pose detection | MediaPipe Pose | Apache 2.0 |
| Bounding box annotation | LabelImg | MIT |

**Not allowed in production:** YOLO / Ultralytics (AGPL-3.0), any paid API, FootAndBall (unverified licence), any cloud inference.
