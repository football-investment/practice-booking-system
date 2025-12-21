# 👨‍🏫 Master Instructor Capabilities - AUDIT

**Date**: 2025-12-14
**Purpose**: Audit what a master instructor can/should do after accepting a semester assignment

---

## Koncepció

Amikor egy instructor **elfogadja** egy semester assignment request-et:
1. A `semesters.master_instructor_id` field → instructor.id
2. Az instructor **szakmailag felelős** lesz a semester működéséért
3. Jogosultságokat kap a semester operatív irányítására

---

## ✅ JELENLEG IMPLEMENTÁLT Funkciók

### 1. **Session Management** (Session CRUD)

**Endpoint**: `POST /api/v1/sessions/`

**Implementáció**: [app/api/api_v1/endpoints/sessions.py:27-58](app/api/api_v1/endpoints/sessions.py#L27-L58)

```python
@router.post("/", response_model=SessionSchema)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)  # ✅
):
    """Create new session (Admin/Instructor only)"""

    # Instructor validation: can only create sessions for their specialization
    if current_user.role == UserRole.INSTRUCTOR:
        if not current_user.can_teach_specialization(session_data.target_specialization):
            raise HTTPException(403, "No teaching qualification")

    session = SessionTypel(**session_data.model_dump())
    db.add(session)
    db.commit()
    return session
```

**Jogosultság**: ✅ Admin + Instructor

**Hiányosság**: ❌ Nincs ellenőrzés, hogy az instructor a semester **master instructor**-e!
- Junior instructor is létrehozhat session-t bármilyen semester-re, ha van rá license-e
- Nem ellenőrzi, hogy `semester.master_instructor_id == current_user.id`

---

### 2. **Session Update**

**Endpoint**: `PATCH /api/v1/sessions/{session_id}`

**Implementáció**: [app/api/api_v1/endpoints/sessions.py:367-393](app/api/api_v1/endpoints/sessions.py#L367-L393)

```python
@router.patch("/{session_id}", response_model=SessionSchema)
def update_session(
    session_id: int,
    session_data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)  # ✅
):
    """Update session (Admin/Instructor only)"""
    session = db.query(SessionTypel).filter(SessionTypel.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    # Update session fields
    for key, value in session_data.model_dump(exclude_unset=True).items():
        setattr(session, key, value)

    db.commit()
    return session
```

**Jogosultság**: ✅ Admin + Instructor

**Hiányosság**: ❌ Ugyanaz - nincs master instructor check!

---

### 3. **Session Delete**

**Endpoint**: `DELETE /api/v1/sessions/{session_id}`

**Implementáció**: [app/api/api_v1/endpoints/sessions.py:395-413](app/api/api_v1/endpoints/sessions.py#L395-L413)

**Jogosultság**: ✅ Admin + Instructor

**Hiányosság**: ❌ Ugyanaz - nincs master instructor check!

---

### 4. **Attendance Management**

**Web Routes**:
- `POST /sessions/{session_id}/attendance/mark` - Mark attendance
- `POST /sessions/{session_id}/attendance/confirm` - Confirm attendance
- `POST /sessions/{session_id}/attendance/change-request` - Request change

**Implementáció**: [app/api/web_routes.py](app/api/web_routes.py)

**Jogosultság**: Valószínűleg instructor jogosultság van, de nem vizsgáltam részletesen

---

### 5. **Session Control (Start/Stop)**

**Web Routes**:
- `POST /sessions/{session_id}/start` - Start session
- `POST /sessions/{session_id}/stop` - Stop session

**Jogosultság**: Valószínűleg instructor

---

### 6. **Student Evaluation**

**Web Routes**:
- `POST /sessions/{session_id}/evaluate-student/{student_id}` - Evaluate student performance
- `POST /sessions/{session_id}/evaluate-instructor` - Students evaluate instructor

**Jogosultság**: Instructor (evaluation)

---

## ❌ HIÁNYZÓ / NEM ELLENŐRZÖTT Funkciók

### 1. **Master Instructor Authorization Check**

**Probléma**: Jelenleg NEM ellenőrzi, hogy az instructor a semester master instructor-e!

**Példa**:
```python
# Junior Instructor (user_id=5) tries to create session for Semester 154
# Semester 154 master_instructor_id = 3 (Grand Master)
# Currently: ✅ ALLOWED (if Junior has COACH license)
# Should be: ❌ FORBIDDEN (not the master instructor!)
```

**Megoldás szükséges**:
```python
@router.post("/", response_model=SessionSchema)
def create_session(...):
    # Get semester
    semester = db.query(Semester).filter(Semester.id == session_data.semester_id).first()

    # Check master instructor authorization
    if current_user.role == UserRole.INSTRUCTOR:
        if semester.master_instructor_id != current_user.id:
            raise HTTPException(
                403,
                f"Only the master instructor (ID: {semester.master_instructor_id}) "
                f"can create sessions for this semester"
            )
```

---

### 2. **Credit Meghatározása (Session Credit Cost)**

**Kérdés**: Hány credit-et kell fizetniük a studenteknek egy session-ért?

**Jelenlegi állapot**: ❓ Nem világos, hogy ki határozza meg

**Lehetséges megoldások**:

#### Opció A: Session szinten (per session)
```python
# sessions table
credit_cost: int = 1  # Default: 1 credit per session
```

**Master instructor állíthatja be**:
```json
POST /api/v1/sessions/
{
  "semester_id": 154,
  "date": "2026-03-15",
  "credit_cost": 2  // This session costs 2 credits
}
```

#### Opció B: Semester szinten (uniform)
```python
# semesters table
default_session_credit_cost: int = 1
```

**Admin vagy master instructor állítja be a semester szinten**

#### Opció C: Session Type szinten
```python
# Enum mapping
SessionType.ON_SITE → 1 credit
SessionType.HYBRID → 2 credits
SessionType.VIRTUAL → 0.5 credits
```

**Mit gondolsz?** Melyik opció lenne a legjobb?

---

### 3. **Semester Status Management**

**Kérdés**: Ki változtathatja a semester status-t?

**Jelenlegi állapot**: Valószínűleg admin-only

**Lehetséges mast instructor jogosultságok**:
- `DRAFT` → `READY_FOR_ENROLLMENT` (master instructor készre jelentheti)
- `ACTIVE` → `PAUSED` (emergency pause)
- `ACTIVE` → `COMPLETED` (lezárás)

---

### 4. **Semester Settings/Configuration**

**Hiányzó funkciók**:
- Max student count beállítása
- Session időpontok bulk létrehozása (template alapján)
- Semester leírás/követelmények szerkesztése
- Előfeltételek módosítása

---

### 5. **Student Enrollment Management**

**Kérdés**: Master instructor jóváhagyhatja/elutasíthatja a student enrollment-eket?

**Use case**:
- Student jelentkezik semester-re
- Master instructor review-olja (tapasztalat, motiváció, stb.)
- Master instructor approve/reject

---

### 6. **Session Materials Upload**

**Hiányzó**: Instructor feltölthet session materials-t?
- PDF notes
- Video recordings
- Exercise sheets
- Quiz templates

---

### 7. **Reporting & Analytics**

**Hiányzó**: Master instructor dashboard semester szinten
- Student attendance rate
- Average performance
- Credit usage statistics
- Session completion rate

---

## 🎯 JAVASLAT: Master Instructor Permissions System

### Új Authorization Decorator

```python
from functools import wraps
from fastapi import HTTPException

def require_master_instructor(semester_id_param: str = "semester_id"):
    """
    Decorator to ensure only the master instructor of a semester can perform action

    Args:
        semester_id_param: Name of the parameter containing semester_id
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract semester_id from request
            semester_id = kwargs.get(semester_id_param)
            db = kwargs.get('db')
            current_user = kwargs.get('current_user')

            # Get semester
            semester = db.query(Semester).filter(Semester.id == semester_id).first()
            if not semester:
                raise HTTPException(404, "Semester not found")

            # Admin bypass
            if current_user.role == UserRole.ADMIN:
                return await func(*args, **kwargs)

            # Check master instructor
            if semester.master_instructor_id != current_user.id:
                raise HTTPException(
                    403,
                    f"Only the master instructor can perform this action"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Használat**:
```python
@router.post("/")
@require_master_instructor(semester_id_param="session_data.semester_id")
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only master instructor or admin can create sessions
    ...
```

---

## 📋 TODO: Master Instructor Features

### P0 (Critical)
1. ✅ Add master instructor authorization check to session CRUD
2. ❓ Define credit cost model (session-level? semester-level?)
3. ✅ Create master instructor permissions decorator

### P1 (Important)
4. ❓ Master instructor can update semester settings
5. ❓ Master instructor can approve/reject student enrollments
6. ❓ Master instructor dashboard (semester analytics)

### P2 (Nice to have)
7. ❓ Session materials upload
8. ❓ Bulk session creation (template-based)
9. ❓ Semester completion workflow

---

## Kérdések Számodra

1. **Credit Model**: Melyik opciót preferálod?
   - A) Session-level (minden session külön credit cost)
   - B) Semester-level (uniform cost az összes session-re)
   - C) Session Type-based (on_site vs hybrid vs virtual)

2. **Master Instructor vs Admin**: Mi legyen admin-only vs mi lehet master instructor is?
   - Semester status changes?
   - Student enrollment approval?
   - Credit cost setting?

3. **Priority**: Mit implementáljunk először?
   - Authorization check (P0)
   - Credit system (P0/P1)
   - Dashboard (P1)
   - Materials upload (P2)

---

**Status**: ⚠️ AUDIT COMPLETE - ACTION REQUIRED
**Next Step**: Define master instructor permission model

