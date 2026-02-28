# Inline Schema Fix Plan - File-Level Implementation Guide

**Dátum:** 2026-02-28
**Scope:** 14 REQUEST inline schemas across 8 files
**Estimated Impact:** +10-14 tests may pass (subset of the 33 "404" failures)

---

## Executive Summary

A bulk validation fix **CSAK** az `app/schemas/*.py` fájlokat érintette.
Az endpoint fájlokban definiált **inline request sémák** nem kapták meg az `extra='forbid'`-et.

**Kritikus felismerés:**
- 160 inline schema létezik 48 fájlban
- **DE** ebből csak **14 REQUEST schema** (a többi Response schema)
- Response sémáknak **NEM KELL** `extra='forbid'`!

---

## Érintett Fájlok és Sémák

### 1. app/api/api_v1/endpoints/auth.py

**Inline Schema:**
```python
# Line 237
class RegisterWithInvitation(BaseModel):
    name: str
    email: EmailStr
    password: str
    invitation_code: str
```

**Fix:**
```python
class RegisterWithInvitation(BaseModel):
    model_config = ConfigDict(extra='forbid')  # <-- ADD THIS

    name: str
    email: EmailStr
    password: str
    invitation_code: str
```

**Használat:** POST /api/v1/register-with-invitation
**Potenciális teszt fix:** test_register_with_invitation_input_validation

---

### 2. app/api/api_v1/endpoints/internship/credits.py

**Inline Schemas (2 db):**

```python
# Line 187
class CreditPurchase(BaseModel):
    amount: int
    payment_reference: str

# Line 206
class CreditSpend(BaseModel):
    amount: int
    reason: str
```

**Fix:**
```python
class CreditPurchase(BaseModel):
    model_config = ConfigDict(extra='forbid')  # <-- ADD
    amount: int
    payment_reference: str

class CreditSpend(BaseModel):
    model_config = ConfigDict(extra='forbid')  # <-- ADD
    amount: int
    reason: str
```

**Használat:**
- POST /api/v1/internship/credits/purchase
- POST /api/v1/internship/credits/spend

**Potenciális teszt fix:** internship credit validation tests

---

### 3. app/api/api_v1/endpoints/internship/licenses.py

**Inline Schemas (2 db):**

```python
# Line 192
class CreditPurchase(BaseModel):
    amount: int
    payment_reference: str

# Line 211
class CreditSpend(BaseModel):
    amount: int
    reason: str
```

**Fix:** Ugyanaz, mint #2 (duplicate schema definíció)

**Megjegyzés:** Ez **code smell** - ugyanaz a schema többször van definiálva különböző fájlokban. Ideális esetben át kellene helyezni `app/schemas/license.py`-ba.

**Használat:**
- POST /api/v1/internship/licenses/{id}/purchase
- POST /api/v1/internship/licenses/{id}/spend

---

### 4. app/api/api_v1/endpoints/internship/xp_renewal.py

**Inline Schemas (2 db):**

```python
# Line 186
class CreditPurchase(BaseModel):
    amount: int
    payment_reference: str

# Line 205
class CreditSpend(BaseModel):
    amount: int
    reason: str
```

**Fix:** Ugyanaz, mint #2 és #3

**Használat:**
- POST /api/v1/internship/xp/{id}/purchase
- POST /api/v1/internship/xp/{id}/spend

---

### 5. app/api/api_v1/endpoints/invitation_codes.py

**Inline Schema:**

```python
# Line 101
class InvitationCodeRedeem(BaseModel):
    code: str
    user_id: int
```

**Fix:**
```python
class InvitationCodeRedeem(BaseModel):
    model_config = ConfigDict(extra='forbid')  # <-- ADD
    code: str
    user_id: int
```

**Használat:** POST /api/v1/invitation-codes/redeem
**Potenciális teszt fix:** test_redeem_invitation_code_input_validation

---

### 6. app/api/api_v1/endpoints/lfa_player/credits.py

**Inline Schemas (2 db):**

```python
# Line 72
class CreditPurchase(BaseModel):
    amount: int

# Line 81
class CreditSpend(BaseModel):
    amount: int
    reason: str
```

**Fix:**
```python
class CreditPurchase(BaseModel):
    model_config = ConfigDict(extra='forbid')  # <-- ADD
    amount: int

class CreditSpend(BaseModel):
    model_config = ConfigDict(extra='forbid')  # <-- ADD
    amount: int
    reason: str
```

**Használat:**
- POST /api/v1/lfa-player/credits/purchase
- POST /api/v1/lfa-player/credits/spend

---

### 7. app/api/api_v1/endpoints/lfa_player/licenses.py

**Inline Schemas (2 db):**

```python
# Line 78
class CreditPurchase(BaseModel):
    amount: int

# Line 87
class CreditSpend(BaseModel):
    amount: int
    reason: str
```

**Fix:** Ugyanaz, mint #6

**Használat:**
- POST /api/v1/lfa-player/licenses/{id}/purchase
- POST /api/v1/lfa-player/licenses/{id}/spend

---

### 8. app/api/api_v1/endpoints/lfa_player/skills.py

**Inline Schemas (2 db):**

```python
# Line 74
class CreditPurchase(BaseModel):
    amount: int

# Line 83
class CreditSpend(BaseModel):
    amount: int
    reason: str
```

**Fix:** Ugyanaz, mint #6 és #7

**Használat:**
- POST /api/v1/lfa-player/skills/{id}/purchase
- POST /api/v1/lfa-player/skills/{id}/spend

---

## Implementation Strategy

### Option A: Manual Fix (AJÁNLOTT - Gyors és Biztos)

**Lépések:**
1. Nyisd meg mindegyik fájlt egyesével
2. Adj hozzá `model_config = ConfigDict(extra='forbid')` sort a REQUEST sémákhoz
3. Ellenőrizd, hogy az import megvan: `from pydantic import BaseModel, ConfigDict`
4. Commit fájlonként vagy egy bulk commit-ban

**Becsült idő:** 15-20 perc

**Előnyök:**
- Biztos, pontos
- Lehetőség kódolvasásra
- Könnyű review

### Option B: Automated Script

**Python script:**
```python
#!/usr/bin/env python3
"""Add extra='forbid' to inline request schemas"""
import re
from pathlib import Path

files_to_fix = {
    "app/api/api_v1/endpoints/auth.py": ["RegisterWithInvitation"],
    "app/api/api_v1/endpoints/internship/credits.py": ["CreditPurchase", "CreditSpend"],
    "app/api/api_v1/endpoints/internship/licenses.py": ["CreditPurchase", "CreditSpend"],
    "app/api/api_v1/endpoints/internship/xp_renewal.py": ["CreditPurchase", "CreditSpend"],
    "app/api/api_v1/endpoints/invitation_codes.py": ["InvitationCodeRedeem"],
    "app/api/api_v1/endpoints/lfa_player/credits.py": ["CreditPurchase", "CreditSpend"],
    "app/api/api_v1/endpoints/lfa_player/licenses.py": ["CreditPurchase", "CreditSpend"],
    "app/api/api_v1/endpoints/lfa_player/skills.py": ["CreditPurchase", "CreditSpend"],
}

for file_path, class_names in files_to_fix.items():
    content = Path(file_path).read_text()

    for class_name in class_names:
        # Find class definition
        pattern = rf'(class {class_name}\(BaseModel\):)\n'
        replacement = rf'\1\n    model_config = ConfigDict(extra=\'forbid\')\n\n'
        content = re.sub(pattern, replacement, content)

    # Ensure import
    if "from pydantic import" in content and "ConfigDict" not in content:
        content = re.sub(
            r'from pydantic import (.+)',
            r'from pydantic import \1, ConfigDict',
            content
        )

    Path(file_path).write_text(content)
    print(f"✅ Fixed: {file_path}")
```

**Hátrányok:**
- Regex lehet, hogy nem működik minden edge case-re
- Nehezebb review

---

## Verification Plan

### 1. Import Ellenőrzés

Minden érintett fájlnál:
```bash
grep "from pydantic import.*ConfigDict" app/api/api_v1/endpoints/auth.py
# Várható: from pydantic import BaseModel, ConfigDict
```

### 2. Schema Ellenőrzés

```bash
grep -A 3 "class RegisterWithInvitation" app/api/api_v1/endpoints/auth.py
# Várható:
# class RegisterWithInvitation(BaseModel):
#     model_config = ConfigDict(extra='forbid')
#
#     name: str
```

### 3. App Import Test

```bash
python -c "from app.main import app; print('✅ App imports successfully')"
```

### 4. Run Affected Tests

```bash
pytest tests/integration/api_smoke/test_auth_smoke.py::TestAuthSmoke::test_register_with_invitation_input_validation -v
pytest tests/integration/api_smoke/test_invitation_codes_smoke.py -v
# ... stb.
```

---

## Expected Impact

### Test Javulás Becslés

**Konzervatív becslés:** +5-8 teszt pass
- Biztos javulás azoknak a teszteknek, ahol:
  - Endpoint létezik ✅
  - Inline REQUEST schema van ✅
  - Test helyes URL-t használ ✅

**Optimista becslés:** +10-14 teszt pass
- Ha minden érintett endpoint teszt helyes

**Reális becslés:** +7-10 teszt pass
- Néhány 404 teszt még mindig failing lehet (rossz URL, stb.)

### Maradék Hibák Fix Után

**Jelenlegi:** 100 failed
**Fix után (becslés):** 90-93 failed

**Maradék hibák összetétele:**
- Test fixture errors (50) - változatlan
- Empty body endpoints (13) - változatlan
- Endpoint not found (33 → 23-26) - **7-10 javul**
- Permission errors (4) - változatlan

---

## Code Quality Improvement Opportunity

### Duplicate Schema Problem

A `CreditPurchase` és `CreditSpend` sémák **4-szer vannak duplikálva**:
- internship/credits.py
- internship/licenses.py
- internship/xp_renewal.py
- lfa_player/*.py fájlok (3x)

**Javaslat refactoring-ra (FUTURE WORK):**

```python
# app/schemas/credits.py - CENTRALIZED
class CreditPurchase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    amount: int = Field(gt=0)
    payment_reference: Optional[str] = None

class CreditSpend(BaseModel):
    model_config = ConfigDict(extra='forbid')
    amount: int = Field(gt=0)
    reason: str
```

**Előnyök:**
- DRY principle
- Egyetlen fix helyen
- Konsisztens validáció

**Hátrányok:**
- Refactoring effort
- Import changes szükségesek

**Prioritás:** LOW (current fix works, refactoring optional)

---

## Implementation Checklist

- [ ] 1. Backup jelenlegi állapot (git stash vagy branch)
- [ ] 2. Fix auth.py (1 schema)
- [ ] 3. Fix internship/credits.py (2 schemas)
- [ ] 4. Fix internship/licenses.py (2 schemas)
- [ ] 5. Fix internship/xp_renewal.py (2 schemas)
- [ ] 6. Fix invitation_codes.py (1 schema)
- [ ] 7. Fix lfa_player/credits.py (2 schemas)
- [ ] 8. Fix lfa_player/licenses.py (2 schemas)
- [ ] 9. Fix lfa_player/skills.py (2 schemas)
- [ ] 10. Verify all imports contain ConfigDict
- [ ] 11. Run `python -c "from app.main import app"`
- [ ] 12. Run affected smoke tests
- [ ] 13. Commit with descriptive message
- [ ] 14. Push and monitor CI/CD
- [ ] 15. Update FAILED_TESTS_TECHNICAL_ANALYSIS.md with new counts

---

## Commit Message Template

```
fix(validation): Add extra='forbid' to 14 inline request schemas

Add input validation strictness to inline request schemas that were
missed by the bulk validation fix (which only covered app/schemas/*.py).

Modified files (8):
- app/api/api_v1/endpoints/auth.py
- app/api/api_v1/endpoints/internship/credits.py
- app/api/api_v1/endpoints/internship/licenses.py
- app/api/api_v1/endpoints/internship/xp_renewal.py
- app/api/api_v1/endpoints/invitation_codes.py
- app/api/api_v1/endpoints/lfa_player/credits.py
- app/api/api_v1/endpoints/lfa_player/licenses.py
- app/api/api_v1/endpoints/lfa_player/skills.py

Affected schemas (14):
- RegisterWithInvitation (auth)
- CreditPurchase, CreditSpend (6x across files)
- InvitationCodeRedeem

Expected impact: +7-10 passed tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

**Dokumentum vége**
