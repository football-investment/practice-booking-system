# 🏫 Campus Table Migration - COMPLETE

**Implementation Date:** 2025-12-18
**Status:** ✅ STEP 1-5 COMPLETE

---

## 📋 Overview

Implementáltuk a helyes Location → Campus hierarchiát:
- **Location** = City szint (Budapest, Budaörs)
- **Campus** = Venue a városon belül (Pest Campus, Budaörs Campus, Main Field)

## ✅ Completed Steps (1-5)

### Step 1: ✅ Campus Model Created
**File:** `app/models/campus.py`

```python
class Campus(Base):
    """Campus/Venue within a location"""
    __tablename__ = "campuses"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"))
    name = Column(String)  # e.g., "Pest Campus"
    venue = Column(String)
    address = Column(String)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Relationship
    location = relationship("Location", back_populates="campuses")
```

### Step 2: ✅ Location Model Updated
**File:** `app/models/location.py`

Changes:
- Added documentation: Location = city level
- Made `city` field unique (primary identifier)
- Marked `venue` as DEPRECATED (moved to Campus)
- Added relationship: `campuses = relationship("Campus", back_populates="location")`

### Step 3: ✅ Campus Added to Models Init
**File:** `app/models/__init__.py`

```python
from .campus import Campus

__all__ = [
    # ...
    "Location",
    "Campus",  # ✅ NEW
    "Semester",
    # ...
]
```

### Step 4: ✅ Database Migration Created
**File:** `alembic/versions/2025_12_18_1800-create_campuses_table.py`

- **Revision ID:** b2c3d4e5f6a7
- **Down revision:** a9b8c7d6e5f4

Migration creates `campuses` table with:
- Foreign key to `locations.id` with CASCADE delete
- Unique constraint: (location_id, name)
- Indexes on: location_id, is_active, name

**Migration executed successfully:**
```bash
alembic upgrade b2c3d4e5f6a7
# ✅ Running upgrade a9b8c7d6e5f4 -> b2c3d4e5f6a7, create_campuses_table
```

### Step 5: ✅ Data Migration Executed
**File:** `migrate_locations_to_campuses.py`

Migration script created campus entries from existing locations:

**BEFORE:**
```
locations:
  - ID 1: "LFA EC - Budapest" (city: Budapest, venue: Pest Campus)
  - ID 2: "LFA EC - Budaörs" (city: Budaörs, venue: Budaörs Campus)
```

**AFTER:**
```
locations:
  - ID 1: Budapest (city-level)
  - ID 2: Budaörs (city-level)

campuses:
  - ID 1: Pest Campus (location_id: 1)
  - ID 2: Budaörs Campus (location_id: 2)
```

**Verification:**
```
📍 Location 1: Budapest
   └─ 🏫 Campus 1: Pest Campus

📍 Location 2: Budaörs
   └─ 🏫 Campus 2: Budaörs Campus
```

---

## 📊 Current Database Schema

### Locations Table
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),           -- Will be deprecated
    city VARCHAR(100) UNIQUE,    -- Primary identifier ⭐
    postal_code VARCHAR(20),
    country VARCHAR(100),
    venue VARCHAR(200),           -- DEPRECATED (moved to Campus)
    address VARCHAR(500),         -- DEPRECATED (moved to Campus)
    notes TEXT,                   -- DEPRECATED (moved to Campus)
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Campuses Table ⭐ NEW
```sql
CREATE TABLE campuses (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    venue VARCHAR(200),
    address VARCHAR(500),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uix_location_campus_name UNIQUE (location_id, name)
);

CREATE INDEX ix_campuses_location_id ON campuses(location_id);
CREATE INDEX ix_campuses_is_active ON campuses(is_active);
CREATE INDEX ix_campuses_name ON campuses(name);
```

---

## 🎯 Business Logic

### Instructor Binding
**CORRECT:** Instructor bound to **Location** (city)
- Instructor can teach at **ANY campus** within their location
- Instructor **CANNOT** teach at different locations

**Example:**
- Instructor X → Bound to Budapest (Location ID 1)
- Can teach at: Pest Campus, Buda Campus, Main Field (all in Budapest)
- Cannot teach at: Budaörs Campus (different location)

### Hierarchy
```
Location (City)
  ├─ Campus 1 (Venue within city)
  ├─ Campus 2 (Another venue)
  └─ Campus 3 (Third venue)
```

---

## 🚧 Remaining Steps (6-8)

### Step 6: TODO - Update Session Model
**File:** `app/models/session.py`

**Current:**
```python
class Session(Base):
    location = Column(String)  # ❌ String field
```

**Need to change to:**
```python
class Session(Base):
    campus_id = Column(Integer, ForeignKey("campuses.id"))  # ✅ Foreign key
    campus = relationship("Campus")
```

**Migration needed:**
1. Add `campus_id` column to sessions table
2. Migrate existing `location` string to `campus_id` foreign key
3. Deprecate/remove `location` string field

### Step 7: TODO - Update Instructor Model
**File:** `app/models/user.py` or `app/models/instructor_specialization.py`

Add instructor location binding:
```python
class InstructorSpecialization(Base):
    location_id = Column(Integer, ForeignKey("locations.id"))  # ✅ Bind to city
    location = relationship("Location")
```

**Business rule enforcement:**
- Instructor can only be assigned to sessions at campuses within their bound location
- Admin can only assign instructor to campuses in their location

### Step 8: TODO - Update Admin Dashboard
**File:** `streamlit_app/pages/Admin_Dashboard.py`

**Current:** Location Management tab manages flat locations

**Need to update to:**
1. Location Management: Manage cities (Budapest, Budaörs)
2. Campus Management: Manage campuses within each location
3. Session creation: Select Campus (not location string)
4. Instructor assignment: Check location binding before allowing campus selection

---

## 📁 Files Changed

### Backend Models
- ✅ `app/models/campus.py` (NEW - 47 lines)
- ✅ `app/models/location.py` (MODIFIED - added relationship)
- ✅ `app/models/__init__.py` (MODIFIED - added Campus import)

### Database Migrations
- ✅ `alembic/versions/2025_12_18_1800-create_campuses_table.py` (NEW - 68 lines)
- ✅ `migrate_locations_to_campuses.py` (NEW - 156 lines)

### TODO Files
- ⏳ `app/models/session.py` (PENDING - add campus_id)
- ⏳ `app/models/instructor_specialization.py` (PENDING - add location_id)
- ⏳ `streamlit_app/pages/Admin_Dashboard.py` (PENDING - campus management)
- ⏳ `app/api/api_v1/endpoints/admin.py` (PENDING - campus CRUD endpoints)

---

## 🧪 Testing Checklist

### Completed ✅
- [x] Campus model created
- [x] Campus table created in database
- [x] Campuses table has proper foreign keys
- [x] Unique constraint on (location_id, name)
- [x] Cascade delete works (location → campuses)
- [x] Data migration executed successfully
- [x] Verification: 2 locations, 2 campuses created

### TODO ⏳
- [ ] Session model uses campus_id instead of location string
- [ ] Instructor model has location_id binding
- [ ] Admin can manage campuses within locations
- [ ] Session creation uses campus selection
- [ ] Instructor assignment validates location binding
- [ ] Frontend displays Location → Campus hierarchy

---

## 🎉 Status

**CAMPUS TABLE MIGRATION: 62.5% COMPLETE (5/8 steps)**

✅ Steps 1-5: Database schema, models, and data migration complete
⏳ Steps 6-8: Session/Instructor updates and admin dashboard integration

**Ready for next steps:** Session model update and instructor location binding!

---

## 📝 Next Actions

1. **Update Session Model** (Step 6)
   - Add `campus_id` foreign key
   - Create migration to convert `location` string to `campus_id`
   - Update session creation endpoints

2. **Update Instructor Model** (Step 7)
   - Add `location_id` binding to instructor
   - Enforce business rule: instructor bound to one location

3. **Update Admin Dashboard** (Step 8)
   - Add Campus Management UI
   - Update Session creation to use campus selector
   - Validate instructor location when assigning to sessions
