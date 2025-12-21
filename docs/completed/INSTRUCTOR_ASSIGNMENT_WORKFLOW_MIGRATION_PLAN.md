# Instructor Assignment Workflow Migration Plan

**Dátum:** 2025-12-20
**Típus:** 📋 IMPLEMENTATION PLAN
**Státusz:** ⏳ READY TO EXECUTE

---

## 🎯 ÖSSZEFOGLALÓ

**Elvárás:** A **már működő teszt dashboardban implementált** instructor assignment workflow **átemelése** a production-ready admin dashboardba.

**Nem újratervezés, hanem átemelés!**

---

## ✅ MI MÁR LÉTEZIK ÉS MŰKÖDIK

### 1. Backend (KÉSZ ✅)

#### Models:
- ✅ `app/models/instructor_assignment.py`
  - `InstructorAvailabilityWindow` - Instructor általános elérhetőség
  - `InstructorAssignmentRequest` - Admin → Instructor felkérés
  - `AssignmentRequestStatus` enum (PENDING, ACCEPTED, DECLINED, CANCELLED, EXPIRED)

#### API Endpoints:
- ✅ `app/api/api_v1/endpoints/instructor_assignments.py`
  - GET `/api/v1/instructor-assignments/available-instructors` - Elérhető oktatók lekérése
  - POST `/api/v1/instructor-assignments/availability` - Availability window létrehozása
  - GET `/api/v1/instructor-assignments/availability/instructor/{id}` - Oktató elérhetősége
  - DELETE `/api/v1/instructor-assignments/availability/{id}` - Availability törlése
  - POST `/api/v1/instructor-assignments/requests` - Assignment request küldése
  - GET `/api/v1/instructor-assignments/requests/instructor/{id}` - Oktató request-jei
  - GET `/api/v1/instructor-assignments/requests/semester/{id}` - Semester request-jei
  - PATCH `/api/v1/instructor-assignments/requests/{id}/accept` - **Request elfogadása**
  - PATCH `/api/v1/instructor-assignments/requests/{id}/decline` - **Request elutasítása**

#### Schemas:
- ✅ `app/schemas/instructor_assignment.py`

### 2. Test Dashboard (TELJES WORKFLOW MŰKÖDIK ✅)

**Fájl:** `scripts/dashboards/unified_workflow_dashboard.py` (~5036 sor)

#### Admin Workflow (TAB 3: "Admin: Semester Assignment"):

**Sorok 2162-2508:**

```python
# 1. FIND AVAILABLE INSTRUCTORS
if st.button("🔍 Find Available Instructors"):
    avail_response = requests.get(
        f"{API_BASE_URL}/api/v1/instructor-assignments/available-instructors",
        params={"year": sem_year, "time_period": time_period}
    )
    # Display available instructors with licenses, availability windows

# 2. SEND ASSIGNMENT REQUEST
if st.button(f"📨 Send Request to {instructor_name}"):
    req_response = requests.post(
        f"{API_BASE_URL}/api/v1/instructor-assignments/requests",
        json={
            "semester_id": semester['id'],
            "instructor_id": instructor_id,
            "request_message": message,
            "priority": priority
        }
    )
    # Success: st.success("✅ Assignment request sent!")

# 3. CHECK EXISTING PENDING REQUESTS
existing_req_response = requests.get(
    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/semester/{semester_id}"
)
# Warning if PENDING request already exists
```

#### Instructor Workflow (TAB 1: "Instructor: Availability", TAB 2: "Assignment Inbox"):

**Sorok 2997-3110:** Availability Management
```python
# VIEW AVAILABILITY WINDOWS
windows_response = requests.get(
    f"{API_BASE_URL}/api/v1/instructor-assignments/availability/instructor/{instructor_id}"
)

# ADD AVAILABILITY WINDOW
create_response = requests.post(
    f"{API_BASE_URL}/api/v1/instructor-assignments/availability",
    json={"instructor_id": id, "year": year, "time_period": period}
)

# DELETE AVAILABILITY WINDOW
delete_response = requests.delete(
    f"{API_BASE_URL}/api/v1/instructor-assignments/availability/{window_id}"
)
```

**Sorok 3112-3280:** Assignment Inbox (CRITICAL!)
```python
# 1. FILTER REQUESTS (Dynamic UI)
st.selectbox("Status", ["All", "PENDING", "ACCEPTED", "DECLINED"])
st.selectbox("Specialization", teachable_specs)  # From instructor licenses!
st.selectbox("Age Group", ["All", "PRE", "YOUTH", "ADULT"])
st.selectbox("Location", ["All", "Budapest", "Budaörs"])
st.selectbox("Min Priority", ["All", "5", "6", "7", "8", "9", "10"])

# 2. FETCH FILTERED REQUESTS
requests_response = requests.get(
    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/instructor/{instructor_id}",
    params={
        "status_filter": status,
        "specialization_type": spec,
        "age_group": age,
        "location_city": location,
        "priority_min": priority
    }
)

# 3. DISPLAY REQUESTS WITH ACTIONS
for req in filtered_requests:
    with st.expander(f"📋 Request #{req['id']} - {req['status']}"):
        st.markdown(f"Semester ID: {req['semester_id']}")
        st.info(req['request_message'])  # Admin message

        if req['status'] == "PENDING":
            # ACCEPT BUTTON
            if st.button("✅ Accept Request"):
                accept_response = requests.patch(
                    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/{req['id']}/accept",
                    json={"response_message": optional_message}
                )
                # Success: st.success("✅ Request accepted! You are now master instructor.")

            # DECLINE BUTTON
            if st.button("❌ Decline Request"):
                decline_response = requests.patch(
                    f"{API_BASE_URL}/api/v1/instructor-assignments/requests/{req['id']}/decline",
                    json={"response_message": decline_reason}
                )
                # Success: st.success("✅ Request declined.")
```

---

## 🚫 MI HIÁNYZIK A PRODUCTION ADMIN DASHBOARDBÓL

**Fájl:** `streamlit_app/pages/Admin_Dashboard.py`

### Jelenleg NEM létezik:

1. ❌ **"Instructor Assignment" tab/section**
2. ❌ **"Find Available Instructors" funkció**
3. ❌ **"Send Assignment Request" funkció**
4. ❌ **Assignment requests listázása semester-enként**
5. ❌ **Pending requests figyelmeztető (ne küldjön duplikátumot)**

### Jelenleg NINCS az Instructor Dashboard-on:

1. ❌ **Availability windows management**
2. ❌ **Assignment request inbox**
3. ❌ **Accept/Decline actions**

---

## 📋 ÁTEMELENDŐ KOMPONENSEK

### 1. Admin Dashboard Components (Prioritás: P0)

#### Component 1: `instructor_assignment_tab.py` (NEW)
**Forrás:** `unified_workflow_dashboard.py` lines 2162-2508

**Tartalom:**
```python
def render_instructor_assignment_tab(token: str):
    """
    Instructor assignment management for semesters

    Features:
    - List all semesters with assignment status
    - Find available instructors by time period
    - Send assignment requests to instructors
    - View pending/accepted/declined requests per semester
    - Prevent duplicate PENDING requests
    """
```

**Funkciók:**
- `find_available_instructors(semester_id, year, time_period, token)`
- `send_assignment_request(semester_id, instructor_id, message, priority, token)`
- `get_semester_requests(semester_id, token)`
- `display_available_instructor_card(instructor_data)`

#### Component 2: `instructor_filters.py` (NEW)
**Forrás:** `unified_workflow_dashboard.py` lines 3134-3176

**Tartalom:**
```python
def render_instructor_availability_filters():
    """
    Dynamic filter UI for instructor assignment requests

    Returns filters: status, specialization, age_group, location, priority
    """
```

### 2. Instructor Dashboard Components (Prioritás: P0)

#### Component 1: `availability_management.py` (NEW)
**Forrás:** `unified_workflow_dashboard.py` lines 2997-3110

**Tartalom:**
```python
def render_availability_management(instructor_id: int, token: str):
    """
    Instructor availability window management

    Features:
    - View current availability windows
    - Add new availability (year + time_period)
    - Delete availability windows
    """
```

#### Component 2: `assignment_inbox.py` (NEW)
**Forrás:** `unified_workflow_dashboard.py` lines 3112-3280

**Tartalom:**
```python
def render_assignment_inbox(instructor_id: int, token: str):
    """
    Assignment request inbox with filtering and actions

    Features:
    - Filter requests (status, spec, age, location, priority)
    - Display request details (semester, message, priority)
    - Accept request (becomes master instructor)
    - Decline request (with optional reason)
    """
```

**Sub-functions:**
- `accept_assignment_request(request_id, response_message, token)`
- `decline_assignment_request(request_id, response_message, token)`
- `get_filtered_requests(instructor_id, filters, token)`

### 3. Semester Tab Enhancement (Prioritás: P1)

**Módosítandó fájl:** `streamlit_app/components/semesters/semester_management.py`

**Hozzáadandó:**
```python
# In semester list/detail view:
if not semester['master_instructor_id']:
    st.warning("⚠️ No instructor assigned")
    if st.button("📨 Send Assignment Request"):
        # Open assignment request modal
        st.session_state.show_assignment_modal = True
        st.session_state.selected_semester_id = semester['id']
```

---

## 🔄 MIGRATION CHECKLIST

### Phase 1: Backend Validation (1 óra)
- [ ] Tesztelés: Backend API endpoints működnek-e
- [ ] Validáció: `/api/v1/instructor-assignments/*` összes endpoint
- [ ] Dokumentáció: OpenAPI spec frissítése (ha szükséges)

### Phase 2: Admin Dashboard (3-4 óra)
- [ ] Create `streamlit_app/components/instructor_assignment/`
- [ ] Create `instructor_assignment_tab.py` (copy from test dashboard)
- [ ] Create `instructor_filters.py` (copy from test dashboard)
- [ ] Integrate into `Admin_Dashboard.py` új tab-ként
- [ ] Update `api_helpers.py` with instructor assignment API calls
- [ ] Testing: Admin workflow (find → send → check)

### Phase 3: Instructor Dashboard (2-3 óra)
- [ ] Create `streamlit_app/components/instructor/`
- [ ] Create `availability_management.py` (copy from test dashboard)
- [ ] Create `assignment_inbox.py` (copy from test dashboard)
- [ ] Integrate into `Instructor_Dashboard.py` új tab-okként
- [ ] Testing: Instructor workflow (availability → inbox → accept/decline)

### Phase 4: Semester Tab Enhancement (1 óra)
- [ ] Add "Send Assignment Request" button to semester management
- [ ] Display instructor assignment status
- [ ] Show pending requests warning

### Phase 5: Integration Testing (2 óra)
- [ ] End-to-end test: Admin send → Instructor accept
- [ ] Test: Semester activation after instructor acceptance
- [ ] Test: Duplicate request prevention
- [ ] Test: Filter functionality

### Phase 6: Documentation (1 óra)
- [ ] Update user guide with new workflow
- [ ] Create instructor onboarding guide
- [ ] Document admin assignment workflow

---

## ⏱️ IDŐBECSLÉS

| Phase | Időigény | Típus |
|-------|----------|-------|
| Phase 1: Backend Validation | 1 óra | Tesztelés |
| Phase 2: Admin Dashboard | 3-4 óra | Copy + Integrate |
| Phase 3: Instructor Dashboard | 2-3 óra | Copy + Integrate |
| Phase 4: Semester Enhancement | 1 óra | Integration |
| Phase 5: Integration Testing | 2 óra | Testing |
| Phase 6: Documentation | 1 óra | Dokumentáció |
| **ÖSSZESEN** | **10-12 óra** | **Átemelés + Testing** |

---

## 🎯 VÁRHATÓ EREDMÉNY

### Admin Dashboard:
✅ Új "Instructor Assignment" tab
✅ Available instructors finder (semester alapján)
✅ Assignment request sender
✅ Pending requests tracking

### Instructor Dashboard:
✅ Új "Availability" tab
✅ Új "Assignment Inbox" tab
✅ Accept/Decline actions
✅ Filtered request view

### Semester Management:
✅ Instructor assignment status display
✅ Quick assignment request button
✅ Activation logic tied to instructor acceptance

---

## 📝 KRITIKUS MEGJEGYZÉSEK

### 1. Koncepció (Fontos!)

**Availability Windows:**
- Oktató NEM választ location-t előre
- Oktató csak TIME PERIOD-ot ad meg (Q1, Q2, Q3, Q4 vagy M01-M12)
- Location a **assignment request-ben** van megadva admin által

**Assignment Request Flow:**
1. Admin létrehoz semester-t (location + specialization + age_group + dates)
2. Admin keres available instructor-okat (year + time_period alapján)
3. Admin kiválaszt 1 instructor-t és küld request-et (location most megadva!)
4. Instructor lát minden részletet (location, specialization, dates)
5. Instructor accept/decline

**Semester Activation:**
- Semester CSAK akkor aktiválható, ha:
  - `master_instructor_id IS NOT NULL`
  - Assignment request `status = 'ACCEPTED'`

### 2. Backend API (Már Működik!)

Minden endpoint **tesztelve van** a test dashboard-dal:
- ✅ Available instructors filtering
- ✅ Assignment request creation
- ✅ Request accept/decline
- ✅ Availability window CRUD

**NEM kell backend módosítás!**

### 3. Eltérések (Ha Vannak)

Ha a teszt dashboard-ról az átemelés során **bármilyen eltérés** van:
- **JELEZNI KELL!**
- **Indokolni KELL!**

Alapelv: **Változatlan átemelés**, kivéve:
- UI/UX javítások (színek, layout, stb.)
- Production error handling
- Logging hozzáadása

---

## 🚀 KÖVETKEZŐ LÉPÉS

**Döntés szükséges:**

1. ✅ **Jóváhagyás:** Megkezdjük az átemelést az ebben a terv szerint?
2. ⚠️ **Módosítás:** Van-e bármilyen eltérés az elvárásokhoz képest?
3. 🔄 **Ütemezés:** Mikor szeretnéd hogy elkészüljön? (10-12 óra munka)

**Válaszok:**
- A) "Rendben, kezdjétek" → Megkezdjük Phase 1-et
- B) "Módosítás szükséges: XYZ" → Frissítjük a tervet
- C) "Csak egy részét szeretném: ABC" → Priorizálunk

---

**状态:** Várakozás jóváhagyásra ⏳
