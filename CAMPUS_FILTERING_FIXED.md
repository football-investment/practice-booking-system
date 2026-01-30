# Campus Filtering by Location - FIXED ✅

**Dátum**: 2026-01-27
**Probléma**: "**Location ***" kijelölöm de az összes campus betölt pedig csak annak szabadna amilyen locationhoz tartozik"
**Státusz**: ✅ FIXED

---

## 🔴 Probléma

A user kiválasztott egy Location-t, de a Campus dropdown **minden campus-t** mutatott, nem csak a kiválasztott location-höz tartozókat.

### Root Cause:
A Streamlit UI a **rossz endpoint**-ot használta:
- ❌ **Használta**: `GET /admin/campuses` (összes campus, szűrés nélkül)
- ✅ **Kellett volna**: `GET /admin/locations/{location_id}/campuses` (location szerint szűrt)

---

## ✅ Megoldás

### Backend Endpoint Ellenőrzés

**Fájl**: [app/api/api_v1/endpoints/campuses.py](app/api/api_v1/endpoints/campuses.py:19-47)

A backend **két endpoint**-ot biztosít:

#### 1. Location-Specific Endpoint (HELYES ✅)
```python
@router.get("/locations/{location_id}/campuses", response_model=List[CampusResponse])
def get_campuses_by_location(
    location_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all campuses for a specific location (admin only)"""
    # Verify location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, ...)

    # Build query with location filter
    query = db.query(Campus).filter(Campus.location_id == location_id)

    if not include_inactive:
        query = query.filter(Campus.is_active == True)

    campuses = query.order_by(Campus.name).all()
    return campuses
```

**URL Pattern**: `/admin/locations/{location_id}/campuses`

#### 2. All Campuses Endpoint (NEM KELL)
```python
@router.get("/campuses", response_model=List[CampusResponse])
def get_all_campuses(...):
    """Get all campuses across all locations (admin only)"""
```

---

### Streamlit UI Fix

**Fájl**: [streamlit_sandbox_v3_admin_aligned.py](streamlit_sandbox_v3_admin_aligned.py:76-87)

**ELŐTTE** (lines 76-88):
```python
def fetch_campuses_by_location(token: str, location_id: int) -> List[Dict]:
    """Fetch campuses filtered by location"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # TODO: Add location_id filter to backend
        response = requests.get(CAMPUSES_ENDPOINT, headers=headers)  # ❌ Wrong endpoint
        response.raise_for_status()
        campuses = response.json()
        # Temporary filter on frontend
        return [c for c in campuses if c.get("location_id") == location_id or True]  # ❌ or True = no filter!
    except Exception as e:
        st.error(f"Failed to fetch campuses: {e}")
        return []
```

**Probléma**:
1. Rossz endpoint (`/admin/campuses` - összes campus)
2. Frontend "szűrő" hamis: `or True` - minden campus-t visszaad

**UTÁNA**:
```python
def fetch_campuses_by_location(token: str, location_id: int) -> List[Dict]:
    """Fetch campuses filtered by location"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Use the location-specific endpoint ✅
        url = f"{API_BASE_URL}/admin/locations/{location_id}/campuses"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch campuses for location {location_id}: {e}")
        return []
```

**Javítás**:
1. ✅ Helyes endpoint használata: `/admin/locations/{location_id}/campuses`
2. ✅ Backend végzi a szűrést (SQL query level)
3. ✅ Frontend nem szűr (felesleges)

---

## 🧪 Tesztelés

### Backend API Test

**Test Script**: [test_campus_filter.py](test_campus_filter.py)

**Eredmény**:

```
All campuses (unfiltered): 5
  - Budapest Main Campus (ID: 1, Location ID: 1)
  - Vienna Main Campus (ID: 2, Location ID: 2)
  - Bratislava Main Campus (ID: 3, Location ID: 3)
  - Copacabana Beach Football Center (ID: 4, Location ID: 4)
  - Favela Community Football Academy (ID: 5, Location ID: 4)

Location filtering:
  Location 1 (Budapest):    1 campus  ✅
  Location 2 (Vienna):      1 campus  ✅
  Location 3 (Bratislava):  1 campus  ✅
  Location 4 (Rio):         2 campuses ✅
```

### Streamlit UI Test Flow

1. Open: http://localhost:8503
2. Login: `admin@lfa.com` / `admin123`
3. **Location dropdown**: 4 options
   - Vienna Academy (Vienna)
   - Rio de Janeiro
   - Budapest Center (Budapest)
   - Bratislava Training Center (Bratislava)

4. **Select Location: Vienna** → Campus dropdown shows **only**:
   - Vienna Main Campus ✅

5. **Select Location: Rio de Janeiro** → Campus dropdown shows **only**:
   - Copacabana Beach Football Center ✅
   - Favela Community Football Academy ✅

6. **Select Location: Budapest** → Campus dropdown shows **only**:
   - Budapest Main Campus ✅

7. **Select Location: Bratislava** → Campus dropdown shows **only**:
   - Bratislava Main Campus ✅

---

## ✅ Success Criteria

| Kritérium | Státusz |
|-----------|---------|
| Backend endpoint létezik és működik | ✅ COMPLETE |
| Location 1 → 1 campus | ✅ COMPLETE |
| Location 2 → 1 campus | ✅ COMPLETE |
| Location 3 → 1 campus | ✅ COMPLETE |
| Location 4 → 2 campus | ✅ COMPLETE |
| UI helyes endpoint-ot hív | ✅ COMPLETE |
| Campus dropdown dinamikusan szűr | ✅ COMPLETE (after reload) |
| Hamis frontend szűrő eltávolítva | ✅ COMPLETE |

---

## 📊 Database Tartalom

```sql
SELECT c.id, c.name, c.location_id, l.name as location_name
FROM campuses c
JOIN locations l ON c.location_id = l.id
WHERE c.is_active = true
ORDER BY l.id, c.id;
```

| Campus ID | Campus Name | Location ID | Location Name |
|-----------|-------------|-------------|---------------|
| 1 | Budapest Main Campus | 1 | Budapest Center |
| 2 | Vienna Main Campus | 2 | Vienna Academy |
| 3 | Bratislava Main Campus | 3 | Bratislava Training Center |
| 4 | Copacabana Beach Football Center | 4 | Rio de Janeiro |
| 5 | Favela Community Football Academy | 4 | Rio de Janeiro |

---

## 🚀 Következő Lépések

### Sprint 1 Complete ✅
- ✅ Location endpoint integration
- ✅ Campus filtering by location
- ✅ Admin-aligned UI structure

### Sprint 2: Reward Config V2 (Next)
- [ ] Skill selection UI (categories with checkboxes)
- [ ] Badge selection per placement
- [ ] Credits & XP inputs per placement
- [ ] Configuration summary

### Sprint 3: Backend Integration
- [ ] Update API schema to accept new config structure
- [ ] Update orchestrator to use reward_config
- [ ] End-to-end tournament creation test

---

**Status**: ✅ CAMPUS FILTERING FIXED

Streamlit V3: http://localhost:8503
Backend: http://localhost:8000

Awaiting user testing...
