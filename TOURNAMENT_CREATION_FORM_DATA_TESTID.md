# Tournament Creation Form - data-testid Documentation
**File**: `streamlit_sandbox_v3_admin_aligned.py`
**Date**: 2026-02-02
**Status**: ✅ COMPLETE - All form elements have Streamlit keys that auto-generate data-testid attributes

---

## Overview

The tournament creation form is **fully instrumented** with Streamlit `key` parameters on all interactive elements. Streamlit automatically converts these keys into `data-testid` attributes in the DOM, making them accessible for Playwright E2E testing.

---

## data-testid Attributes by Section

### Home Page Navigation

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Create New Tournament button | `btn_new_tournament` | Auto-generated | 116 |

### Tournament Configuration Form

#### Basic Information

| Element | key (via `form.field_key()`) | Generated data-testid | Line |
|---------|------------------------------|----------------------|------|
| Tournament Name input | `tournament_name` | `form_tournament_config_tournament_name` | 400-403 |
| Location selectbox | `location` | `form_tournament_config_location` | 419-424 |
| Campus selectbox | `campus` | `form_tournament_config_campus` | 441-446 |
| Age Group selectbox | `age_group` | `form_tournament_config_age_group` | 457-462 |
| Tournament Format selectbox | `tournament_format` | `form_tournament_config_tournament_format` | 468-474 |
| Assignment Type selectbox | `assignment_type` | `form_tournament_config_assignment_type` | 481-486 |
| Scoring Mode selectbox | `scoring_mode` | `form_tournament_config_scoring_mode` | 493-499 |
| Max Players input | `max_players` | `form_tournament_config_max_players` | 580-586 |

#### INDIVIDUAL Scoring Configuration (conditional on `scoring_mode == "INDIVIDUAL"`)

| Element | key (via `form.field_key()`) | Generated data-testid | Line |
|---------|------------------------------|----------------------|------|
| Number of Rounds input | `number_of_rounds` | `form_tournament_config_number_of_rounds` | 506-513 |
| Scoring Type selectbox | `scoring_type` | `form_tournament_config_scoring_type` | 516-521 |
| Ranking Direction selectbox | `ranking_direction` | `form_tournament_config_ranking_direction` | 545-551 |
| Measurement Unit input | `measurement_unit` | `form_tournament_config_measurement_unit` | 565-569 |

#### Schedule

| Element | key (via `form.field_key()`) | Generated data-testid | Line |
|---------|------------------------------|----------------------|------|
| Start Date picker | `start_date` | `form_tournament_config_start_date` | 596-600 |
| End Date picker | `end_date` | `form_tournament_config_end_date` | 605-609 |

#### Participants (Dynamic List)

| Element | key Pattern | Example data-testid | Line |
|---------|-------------|---------------------|------|
| User toggle switches | `participant_{user_id}` | `participant_4`, `participant_5`, etc. | 641-646 |

**Note**: Each user in the system has a unique toggle switch with pattern `participant_{user_id}`.

#### Rewards

**Tournament Placement Rewards:**

| Element | key (via `form.field_key()`) | Generated data-testid | Line |
|---------|------------------------------|----------------------|------|
| 1st Place XP | `first_xp` | `form_tournament_config_first_xp` | 666-673 |
| 1st Place Credits | `first_credits` | `form_tournament_config_first_credits` | 674-681 |
| 2nd Place XP | `second_xp` | `form_tournament_config_second_xp` | 687-694 |
| 2nd Place Credits | `second_credits` | `form_tournament_config_second_credits` | 695-702 |
| 3rd Place XP | `third_xp` | `form_tournament_config_third_xp` | 708-715 |
| 3rd Place Credits | `third_credits` | `form_tournament_config_third_credits` | 716-723 |

**Participation Rewards:**

| Element | key (via `form.field_key()`) | Generated data-testid | Line |
|---------|------------------------------|----------------------|------|
| Participation XP | `participation_xp` | `form_tournament_config_participation_xp` | 730-738 |
| Session Base XP | `session_base_xp` | `form_tournament_config_session_base_xp` | 741-749 |

#### Form Actions

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Save as Template button | `btn_save_template` | Auto-generated | 759 |
| Start Instructor Workflow button | `btn_start_workflow` | Auto-generated | 808 |

#### Template Save Dialog (Conditional)

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Template Name input | `input_template_name` | Auto-generated | 820 |
| Cancel button | `btn_cancel_save_template` | Auto-generated | 834 |
| Save Template button | `btn_confirm_save_template` | Auto-generated | 844 |

---

## How Streamlit Keys Work with Playwright

### Streamlit Behavior
When you provide a `key` parameter to a Streamlit widget:
```python
st.text_input("Tournament Name", key="tournament_name")
```

Streamlit generates a DOM element with a `data-testid` attribute based on the key.

### SingleColumnForm Helper
The `SingleColumnForm` class provides a `field_key()` method that generates consistent keys:
```python
def field_key(self, field_name: str) -> str:
    return f"form_{self.form_id}_{field_name}"
```

For `form_id="tournament_config"` and `field_name="tournament_name"`, this generates:
```
key = "form_tournament_config_tournament_name"
```

### Playwright Selector Usage

```python
# Locate by generated data-testid
page.locator('[data-testid="form_tournament_config_tournament_name"]')

# Fill input
page.fill('[data-testid="form_tournament_config_tournament_name"]', "Test Tournament")

# Select option
page.select_option('[data-testid="form_tournament_config_scoring_mode"]', "INDIVIDUAL")

# Click button
page.click('[data-testid="btn_start_workflow"]')
```

---

## Coverage Summary

| Category | Elements | Status |
|----------|----------|--------|
| Home Navigation | 1 | ✅ Complete |
| Basic Information | 8 | ✅ Complete |
| INDIVIDUAL Scoring | 4 | ✅ Complete (conditional) |
| Schedule | 2 | ✅ Complete |
| Participants | Dynamic (1 per user) | ✅ Complete |
| Rewards | 8 | ✅ Complete |
| Form Actions | 2 | ✅ Complete |
| Template Management | 3 | ✅ Complete |

**Total**: 28+ unique data-testid attributes (excluding dynamic participant toggles)

---

## Testing Notes

### Conditional Fields
Some fields are only visible based on form state:
- **INDIVIDUAL Scoring fields** only appear when `scoring_mode == "INDIVIDUAL"`
- **Measurement Unit** only appears when `scoring_type != "PLACEMENT"`
- **Template Save Dialog** only appears when "Save as Template" is clicked

### Dynamic Elements
- **Participant toggles** are generated dynamically based on users in the system
- Test should query the number of users first to validate toggle count

### Form Validation
The form has built-in validation:
- Template name uniqueness check
- Required field validation (code, name, skills)

---

## Implementation Status

✅ **COMPLETE** - No modifications needed. All elements already have Streamlit keys that auto-generate data-testid attributes.

**Next Steps**: Document sandbox_workflow.py workflow step buttons (Steps 2-8).
