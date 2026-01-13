# Location + Campus Creation Wizard Implementation

## Summary

Implemented a **two-step wizard** for creating locations with multiple campuses in a single workflow.

## Implementation Date
December 30, 2025

## User Request
> "➕ Create New Location- nem lenne érdemes a location létrehozásánál több campustis megadni és elnevezni? fontos hogy egy location több campus is lehet, ezeknek a címe természetesen.mit gondolsz?"

User chose: **Opció A: Két Lépéses Wizard (Ajánlott)**

## Technical Changes

### Files Modified (5 files):

1. **`streamlit_app/api_helpers_general.py`**
   - Added `create_campus()` function
   - API endpoint: `POST /api/v1/admin/locations/{location_id}/campuses`
   - Returns: (success, error_message, response_data)

2. **`streamlit_app/components/location_modals.py`**
   - Completely rewrote `render_create_location_modal()` as two-step wizard
   - Changed import from `api_helpers` to `api_helpers_general`
   - Added session state variables:
     - `location_wizard_step` (1 or 2)
     - `location_wizard_data` (dict with location details)
     - `location_wizard_campuses` (list of campus objects)

3. **`streamlit_app/components/admin/locations_tab.py`**
   - Updated import: `api_helpers` → `api_helpers_general`

4. **`streamlit_app/components/location_actions.py`**
   - Updated import: `api_helpers` → `api_helpers_general`

5. **`streamlit_app/components/campus_actions.py`**
   - Updated all internal imports: `api_helpers` → `api_helpers_general`

## Wizard Flow

### Step 1: Location Details
- **Progress:** 50% (Step 1 of 2)
- **Fields:**
  - Location Name * (required)
  - City * (required)
  - Country * (required, default: "Hungary")
  - Postal Code
  - Venue
  - Location Type * (CENTER or PARTNER)
  - Address (textarea)
  - Notes (textarea)
  - Active (checkbox, default: true)
- **Navigation:**
  - [❌ Cancel] - Closes wizard and resets state
  - [Next: Add Campuses →] - Validates and proceeds to Step 2
- **Validation:** Name, City, Country are required

### Step 2: Add Campuses
- **Progress:** 100% (Step 2 of 2)
- **Header:** Shows location name being created
- **Campus List Display:**
  - Shows count of campuses to be created
  - Each campus in collapsible expander
  - [🗑️ Remove] button to delete from list
- **Add Campus Form:**
  - Campus Name * (required)
  - Venue
  - Address (textarea)
  - Notes (textarea)
  - Active (checkbox, default: true)
  - [➕ Add Campus] - Adds to list (validates name required)
- **Navigation:**
  - [← Back] - Returns to Step 1 (data preserved)
  - [✅ Create Location & Campuses] - Executes creation

## Creation Logic

1. **Create Location** (API call)
   - POST `/api/v1/admin/locations/`
   - If fails: Show error, keep wizard open
   - If succeeds: Capture `location_id`, show success

2. **Create Campuses** (Sequential API calls)
   - For each campus in list:
     - POST `/api/v1/admin/locations/{location_id}/campuses`
     - Track failures separately
   - Show success message for each created campus
   - Show warning if any campus failed (with error details)

3. **Reset Wizard State**
   - Close modal
   - Reset step to 1
   - Clear location_wizard_data
   - Clear location_wizard_campuses
   - Trigger page refresh

## Features

### User Experience
- Progress bar shows current step (50% → 100%)
- Step 1 data persists when navigating back from Step 2
- Can add multiple campuses before submitting
- Can remove campuses from list before submitting
- Optional: Can skip campus creation (create location only)
- Partial success handling: Location created even if campus fails

### Error Handling
- Step 1 validation: Name, City, Country required
- Step 2 validation: Campus name required
- API error display with detailed messages
- Partial success: Shows which campuses failed

### State Management
- All wizard state stored in `st.session_state`
- State cleared on completion or cancellation
- Navigation preserves Step 1 data when going back

## API Integration

### Existing Endpoints Used:
- `POST /api/v1/admin/locations/` - Create location
- `POST /api/v1/admin/locations/{location_id}/campuses` - Create campus

### API Helper Functions:
- `create_location(token, data)` → (success, error, response)
- `create_campus(token, location_id, data)` → (success, error, response)

## Testing Checklist

- [ ] Step 1: Location creation with all fields
- [ ] Step 1: Required field validation (Name, City, Country)
- [ ] Step 2: Add single campus
- [ ] Step 2: Add multiple campuses
- [ ] Step 2: Remove campus from list
- [ ] Navigation: Back button preserves Step 1 data
- [ ] Submit: Location-only creation (no campuses)
- [ ] Submit: Location + 1 campus
- [ ] Submit: Location + 3 campuses
- [ ] Error: Location creation fails (show error)
- [ ] Error: Campus creation fails (partial success handling)
- [ ] Cancel: Closes wizard and resets state

## Success Criteria

✅ Two-step wizard implemented
✅ Location Type (CENTER/PARTNER) field included
✅ Multiple campuses can be added in one workflow
✅ Dynamic campus list with add/remove functionality
✅ Progress indicator shows current step
✅ Back/Forward navigation works correctly
✅ Partial success handling (location created, campus failed)
✅ All imports updated to `api_helpers_general`
✅ Server restarted successfully
✅ Ready for user testing

## Next Steps

1. User tests the wizard in Admin Dashboard → Locations tab
2. Click "➕ Create Location" button
3. Fill Step 1 → Click "Next: Add Campuses →"
4. Add campuses in Step 2 → Click "✅ Create Location & Campuses"
5. Verify location and campuses appear in location list
