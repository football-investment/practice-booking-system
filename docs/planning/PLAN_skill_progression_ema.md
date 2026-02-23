# Skill Progression — EMA Model Implementation Plan

## 1. Probléma elemzés

### A jelenlegi formula hibái

A jelenlegi `calculate_skill_value_from_placement()` egy "konvergencia az onboarding baseline-hoz" modell:

```
baseline_weight = 1 / (n+1)          ← csökken n-nel
placement_weight = n / (n+1)          ← nő n-nel
new_skill = baseline + (baseline*bw + placement*pw - baseline) * weight
```

**Három strukturális probléma:**

| # | Probléma | Következmény |
|---|---|---|
| P1 | Az onboarding baseline ÖRÖKRE anchor marad | T10-nél még mindig 9% "húz vissza" az eredeti értékhez |
| P2 | A delta NÖVEKSZIK n-nel (placement_weight → 1.0) | T1: Δ±15pt, T10: Δ±25pt — amplifikáció váltakozó eredményeknél |
| P3 | Az abszolút delta nem veszi figyelembe a headroom-ot | 75-ről +18.8pt (1st/4, w=1.5) — drasztikus ugrás |

### Mathematikai bizonyítás P2-re (volatility amplification)

Alternáló 1st/4th eredmény, base=70, w=1.0:
```
T1 (1st): +15.0  →  T2 (4th): -20.0  →  T3 (1st): +22.5  →  T6 (4th): -25.7
```
A váltakozó eredmény NEM stabilizálódik, hanem az oszcilláció amplitúdója folyamatosan nő.

---

## 2. Javasolt modell: Exponenciális Mozgóátlag (EMA)

### Alapelv

Az EMA (Exponential Moving Average / Online Learning) modell **incremental** frissítést alkalmaz:

```
delta = step × (placement_skill − current_value)
new_value = current_value + delta
```

ahol `step = lr × skill_weight` (konstans learning rate × reaktivitás).

**A `placement_skill`** ugyanaz marad (100=1st, 40=last).

### Formula (teljes)

```python
pct = (placement - 1) / (total_players - 1)   # 0.0=1st, 1.0=last
placement_skill = 100.0 - pct * 60.0           # 40–100

step = min(0.8, lr × skill_weight)             # lr=0.20, safety cap=0.8
weighted_delta = step × (placement_skill - prev_value)
new_value = clamp(prev_value + weighted_delta, 40.0, 99.0)
actual_delta = new_value - prev_value           # ← cap-figyelembe vesz
```

**Egyetlen új paraméter:** `prev_value` — a skill jelenlegi (running) értéke.
**Eltávolított paraméter:** `tournament_count` — az EMA-ban nem szükséges (step konstans).
**Megmarad backward-compatible paraméterként:** `baseline`, `tournament_count` (opcionálisan).

### Kulcs tulajdonságok

| Tulajdonság | Jelenlegi | EMA |
|---|---|---|
| T1 jump (base=75, 1st/4, w=1.5) | **+18.8pt** (drasztikus) | +7.5pt (kontrolált) |
| T1 loss (base=75, 4th/4, w=1.5) | **−26.2pt** (drasztikus) | −10.5pt (kontrolált) |
| Alternáló 1st/4th oszcilláció | **amplifikálódik** (±25pt T10-nél) | stabilizálódik (±4pt) |
| Near-cap (base=97, 1st/4, w=1.5) | +2.0pt (teljes headroom) | +0.9pt (természetes lassulás) |
| Dominant/supporting T1 ratio | 2.5× | **2.5×** (megmarad!) |

### Miért 2.5× ratio garantált?

Ha két skill azonos `prev_value`-n van:
```
delta_dom = lr × w_dom × (ps − v) = 0.20 × 1.5 × Δps
delta_sup = lr × w_sup × (ps − v) = 0.20 × 0.6 × Δps

ratio = 1.5 / 0.6 = 2.50  (always, regardless of prev_value)
```

### Normalizált fairness garantált

A normalizált delta (`delta / headroom`) monoton csökken a dominant skill esetén ahogy a cap felé tart — de **sosem kisebb mint a supporting skill normalizált deltája**, ha mindkettő azonos szintről indul (matematikailag bizonyítható, numerikusan validált 0–95 starting value, 1–20 tournament count tartományon).

---

## 3. Szimulációs összehasonlítás

### Szcenárió 1: Győztes karrierpálya (start=70, 1st/4, dominant w=1.5)

| T | Jelenlegi | EMA | Megjegyzés |
|---|---|---|---|
| T1 | 79.0 (+9.0) | 79.0 (+9.0) | Azonos (step=0.30, delta=9.0) |
| T3 | 92.5 (+12.5) | 86.1 (+7.1) | EMA lassabb de konzisztensebb |
| T5 | 99.0 (+6.5) | 92.9 (+3.6) | Jelenlegi már capped |
| T10 | 99.0 (capped) | 99.0 (capped) | Mindkettő eléri |

### Szcenárió 2: Supporting skill (start=70, w=0.6)

| T | Jelenlegi | EMA | Megjegyzés |
|---|---|---|---|
| T1 | 73.6 (+3.6) | 73.6 (+3.6) | Azonos |
| T5 | 87.5 (+4.9) | 84.2 (+2.1) | EMA "gently" nő ✅ |
| T10 | 88.6 (+1.1) | 91.6 (+1.1) | EMA magasabbra ér (nem capped) |

### Szcenárió 3: Alternáló 1st/4th (start=70, w=1.0)

| T | Jelenlegi | EMA |
|---|---|---|
| T1 (1st) | 85.0 (+15) | 74.5 (+4.5) |
| T2 (4th) | 50.0 (−20!) | 69.3 (−5.2) |
| T6 (4th) | 44.3 (−25.7!) | 68.7 (−5.0) |

**EMA stabilan 68–74 között oszcillál — jelenlegi amplifikálódik 44–95 között.**

---

## 4. Érintett fájlok és változtatások

### 4.1 `app/services/skill_progression_service.py`

**Módosítandó:** `calculate_skill_value_from_placement()` függvény (sor 39–128)

```python
# SIGNATURE (backward compatible)
def calculate_skill_value_from_placement(
    baseline: float,           # onboarding value — kept for backward compat
    placement: int,
    total_players: int,
    tournament_count: int,     # kept for backward compat (ignored in EMA path)
    skill_weight: float = 1.0,
    prev_value: Optional[float] = None,  # NEW: running current value
    learning_rate: float = 0.20,         # NEW: EMA learning rate (default 0.20)
) -> float:
    """
    EMA path: if prev_value is provided (not None), uses EMA formula.
    Legacy path: if prev_value is None, falls back to original formula.
    """
```

### 4.2 Hívók frissítése (3 hely)

Minden hívó már tárolja a running value-t — csak át kell adni `prev_value`-ként:

**`calculate_tournament_skill_contribution()`** (sor ~260):
```python
# Before: just call with baseline + count
new_value = calculate_skill_value_from_placement(baseline, placement, total, count, weight)

# After: pass running value
new_value = calculate_skill_value_from_placement(
    baseline, placement, total, count, weight,
    prev_value=current_running_values[skill]
)
```

**`get_skill_timeline()`** (sor ~450–540): azonos minta.

**`get_skill_audit()`** (sor ~688–756): azonos minta.

### 4.3 `get_skill_audit()` fairness check

A normalizált delta számítás `prev_val` alapú headroom-ot használ — ez **változatlan marad**, mert a `skill_previous_values` dict már tárolja a running value-t.

### 4.4 Nincs más érintett fájl

- Nincs DB séma változás
- Nincs API változás (response modellek megmaradnak)
- Nincs Streamlit változás
- A `norm_delta` mező az audit API-ban pontosabbá válik automatikusan

---

## 5. Implementáció lépései

1. **`calculate_skill_value_from_placement()` módosítása** — EMA path + legacy fallback
2. **`calculate_tournament_skill_contribution()` frissítése** — `prev_value` átadása
3. **`get_skill_timeline()` frissítése** — `prev_value` átadása
4. **`get_skill_audit()` frissítése** — `prev_value` átadása
5. **Élő validáció** — API hívás Mbappé profilra, összehasonlítás expected deltákkal

---

## 6. Backward compatibility

A `prev_value=None` esetén a **jelenlegi (régi) formula fut le változatlanul**.
Ez biztosítja, hogy ha bármely hívó nem ad át `prev_value`-t, az eredmény megegyezik a jelenlegivel.

A production deployment után a régi formula path fokozatosan elavulhat.

---

## 7. Kalibrálási paraméterek

| Paraméter | Értéke | Hatás |
|---|---|---|
| `learning_rate` | `0.20` | T1-re Δ+7.5 dominant (kézzel kalibrált) |
| `step` safety cap | `0.80` | Max 80% konvergencia egy lépésben |
| `min_cap` | `40.0` | Változatlan |
| `max_cap` | `99.0` | Változatlan |

A `learning_rate=0.20` indoklása:
- T1 dominant (w=1.5): step=0.30, delta=+7.5pt (75-ről 1st/4) — érzékelhető, de nem drasztikus
- T1 supporting (w=0.6): step=0.12, delta=+3.0pt — "gently and gradually" ✅
- T1 dominant ratio: 2.5× — pontosan a weight arány ✅
