# Frontend UX: Mandatory Skill Selection Implementation Guide

## Overview

This document specifies the **frontend UX requirements** for tournament reward configuration skill selection.

**Core Principle**: Skills must be **explicitly selected per tournament** - no defaults, no auto-enable.

---

## 🎯 UX Requirements

### 1. Visual Hierarchy

The skill selection block must be visually prominent:

```
┌─────────────────────────────────────────────────────────┐
│  Reward Configuration                                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Template: [Standard ▼]                                 │
│                                                          │
│  ⚠️ SKILL SELECTION (REQUIRED) ⚠️                       │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Select at least 1 skill for this tournament:      │ │
│  │                                                    │ │
│  │ Physical Skills:                                   │ │
│  │ ☐ Speed (weight: 1.5x)                            │ │
│  │ ☐ Agility (weight: 1.2x)                          │ │
│  │ ☐ Stamina (weight: 1.0x)                          │ │
│  │ ☐ Strength (weight: 1.3x)                         │ │
│  │                                                    │ │
│  │ Technical Skills:                                  │ │
│  │ ☐ Ball Control (weight: 1.2x)                     │ │
│  │ ☐ Passing (weight: 1.0x)                          │ │
│  │ ☐ Shooting (weight: 1.1x)                         │ │
│  │                                                    │ │
│  │ Mental Skills:                                     │ │
│  │ ☐ Decision Making (weight: 1.0x)                  │ │
│  │ ☐ Composure (weight: 1.0x)                        │ │
│  │                                                    │ │
│  │ Selected: 0 skills                                 │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
│  ⚠️ You must select at least 1 skill to continue        │
│                                                          │
│  [◀ Back]  [Next (Disabled) ▶]                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Visual Indicators**:
- ⚠️ Warning icons next to "SKILL SELECTION (REQUIRED)"
- Red/orange border around skill selection block when 0 skills selected
- Green checkmark when ≥1 skill selected
- Disabled state for Next/Save button

---

## 🔒 Validation Rules

### Client-Side Validation (Immediate Feedback)

```typescript
// Validation state
const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
const [validationError, setValidationError] = useState<string | null>(null);

// Computed property
const isSkillSelectionValid = selectedSkills.length >= 1;

// Effect to show/hide warning
useEffect(() => {
  if (selectedSkills.length === 0) {
    setValidationError("⚠️ You must select at least 1 skill to continue");
  } else {
    setValidationError(null);
  }
}, [selectedSkills]);

// Button state
const isNextButtonDisabled = !isSkillSelectionValid;
```

### Server-Side Validation (Safety Net)

Even with client-side validation, the backend will **reject invalid configs**:

```python
# API Response when 0 skills selected
{
  "status": 400,
  "error": "Invalid skill configuration: At least 1 skill must be enabled for tournament rewards. You must select at least 1 skill for this tournament."
}
```

**Frontend Error Handling**:
```typescript
try {
  await saveRewardConfig(tournamentId, config);
} catch (error) {
  if (error.status === 400) {
    // Show error banner
    showErrorBanner(error.detail);
    // Scroll to skill selection block
    scrollToElement("#skill-selection");
    // Highlight skill section in red
    highlightElement("#skill-selection", "error");
  }
}
```

---

## 🎨 Component Structure

### SkillSelectionBlock Component

```typescript
interface SkillSelectionBlockProps {
  skills: SkillMappingConfig[];
  selectedSkills: string[];
  onSkillToggle: (skillName: string) => void;
  validationError?: string | null;
}

const SkillSelectionBlock: React.FC<SkillSelectionBlockProps> = ({
  skills,
  selectedSkills,
  onSkillToggle,
  validationError
}) => {
  const selectedCount = selectedSkills.length;
  const isValid = selectedCount >= 1;

  return (
    <div className={`skill-selection-block ${!isValid ? 'invalid' : 'valid'}`}>
      {/* Header */}
      <div className="skill-selection-header">
        <h3>
          {!isValid && <WarningIcon />}
          SKILL SELECTION
          <span className="required-badge">REQUIRED</span>
        </h3>
        <p className="instruction">
          Select at least 1 skill for this tournament:
        </p>
      </div>

      {/* Skill Groups */}
      <div className="skill-groups">
        {/* Physical Skills */}
        <SkillCategoryGroup
          category="Physical Skills"
          skills={skills.filter(s => s.category === "PHYSICAL")}
          selectedSkills={selectedSkills}
          onSkillToggle={onSkillToggle}
        />

        {/* Technical Skills */}
        <SkillCategoryGroup
          category="Technical Skills"
          skills={skills.filter(s => s.category === "TECHNICAL")}
          selectedSkills={selectedSkills}
          onSkillToggle={onSkillToggle}
        />

        {/* Mental Skills */}
        <SkillCategoryGroup
          category="Mental Skills"
          skills={skills.filter(s => s.category === "MENTAL")}
          selectedSkills={selectedSkills}
          onSkillToggle={onSkillToggle}
        />
      </div>

      {/* Selection Counter */}
      <div className="selection-counter">
        <span className={selectedCount === 0 ? 'error' : 'success'}>
          Selected: {selectedCount} skill{selectedCount !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Inline Validation Warning */}
      {validationError && (
        <div className="inline-warning">
          <WarningIcon />
          {validationError}
        </div>
      )}
    </div>
  );
};
```

### SkillCategoryGroup Component

```typescript
interface SkillCategoryGroupProps {
  category: string;
  skills: SkillMappingConfig[];
  selectedSkills: string[];
  onSkillToggle: (skillName: string) => void;
}

const SkillCategoryGroup: React.FC<SkillCategoryGroupProps> = ({
  category,
  skills,
  selectedSkills,
  onSkillToggle
}) => {
  return (
    <div className="skill-category-group">
      <h4>{category}</h4>
      <div className="skill-checkboxes">
        {skills.map(skill => (
          <SkillCheckbox
            key={skill.skill}
            skill={skill}
            isSelected={selectedSkills.includes(skill.skill)}
            onToggle={() => onSkillToggle(skill.skill)}
          />
        ))}
      </div>
    </div>
  );
};
```

### SkillCheckbox Component

```typescript
interface SkillCheckboxProps {
  skill: SkillMappingConfig;
  isSelected: boolean;
  onToggle: () => void;
}

const SkillCheckbox: React.FC<SkillCheckboxProps> = ({
  skill,
  isSelected,
  onToggle
}) => {
  return (
    <label className={`skill-checkbox ${isSelected ? 'selected' : ''}`}>
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggle}
      />
      <span className="skill-name">{formatSkillName(skill.skill)}</span>
      <span className="skill-weight">(weight: {skill.weight}x)</span>
    </label>
  );
};

// Helper function
function formatSkillName(skillName: string): string {
  return skillName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
```

---

## 🔄 Template Switching Behavior

**CRITICAL RULE**: Template switching must **KEEP 0 skills selected** (no auto-enable).

```typescript
const handleTemplateChange = (templateName: string) => {
  // Load template config
  const template = REWARD_CONFIG_TEMPLATES[templateName];

  // ⚠️ IMPORTANT: ALL skills in templates are disabled by default
  // DO NOT auto-enable any skills
  setRewardConfig(template);

  // Reset skill selection to empty
  setSelectedSkills([]);

  // Show reminder message
  showInfoToast("Template loaded. Please select relevant skills for this tournament.");
};
```

**UI Flow**:
1. User selects "Championship" template
2. Template loads with 8 skills (all disabled)
3. UI shows: "Selected: 0 skills"
4. Inline warning appears: "⚠️ You must select at least 1 skill to continue"
5. Next button remains DISABLED
6. Admin must manually check relevant skill boxes

---

## 📝 Real-World Examples

### Example 1: NIKE Speed Test

```
Tournament: NIKE Speed Test
Format: INDIVIDUAL_RANKING
Measurement: seconds (Lower is Better)

Step 1: Select Template
  → Admin selects "Standard" template

Step 2: Enable Relevant Skills ✅
  ☑ Speed (weight: 1.5x)
  ☑ Agility (weight: 1.2x)
  ☐ Stamina
  ☐ Strength
  ☐ Ball Control
  ☐ Passing
  ... (all others disabled)

Step 3: Validation
  ✅ 2 skills selected → Next button ENABLED

Step 4: Save
  → API accepts config
  → Tournament ready for distribution
```

### Example 2: Plank Competition

```
Tournament: Plank Hold Competition
Format: INDIVIDUAL_RANKING
Measurement: seconds (Higher is Better)

Step 1: Select Template
  → Admin selects "Friendly" template

Step 2: Enable Relevant Skills ✅
  ☐ Speed
  ☐ Agility
  ☑ Stamina (weight: 2.0x)
  ☑ Core Strength (weight: 1.5x)  [if available]
  ☐ Ball Control
  ... (all others disabled)

Step 3: Validation
  ✅ 2 skills selected → Next button ENABLED

Step 4: Save
  → API accepts config
  → Only stamina + core_strength earn skill points
```

---

## 🚨 Error States

### State 1: No Skills Selected (Initial Load)

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ SKILL SELECTION (REQUIRED) ⚠️                       │
│  ┌───────────────────────────────────────────────────┐ │
│  │ [Border: Red]                                      │ │
│  │                                                    │ │
│  │ ☐ Speed                                            │ │
│  │ ☐ Agility                                          │ │
│  │ ...                                                │ │
│  │                                                    │ │
│  │ Selected: 0 skills                                 │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
│  ⚠️ You must select at least 1 skill to continue        │
│                                                          │
│  [Next (Disabled - Gray) ▶]                             │
└─────────────────────────────────────────────────────────┘
```

### State 2: At Least 1 Skill Selected (Valid)

```
┌─────────────────────────────────────────────────────────┐
│  ✅ SKILL SELECTION (REQUIRED)                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │ [Border: Green]                                    │ │
│  │                                                    │ │
│  │ ☑ Speed (weight: 1.5x)                            │ │
│  │ ☑ Agility (weight: 1.2x)                          │ │
│  │ ☐ Stamina                                          │ │
│  │ ...                                                │ │
│  │                                                    │ │
│  │ Selected: 2 skills ✅                              │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
│  [Next (Enabled - Blue) ▶]                              │
└─────────────────────────────────────────────────────────┘
```

### State 3: API Validation Error (Safety Net)

```
┌─────────────────────────────────────────────────────────┐
│  🔴 ERROR BANNER                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ ⚠️ Failed to save reward configuration             │ │
│  │                                                    │ │
│  │ Invalid skill configuration: At least 1 skill     │ │
│  │ must be enabled for tournament rewards. You must  │ │
│  │ select at least 1 skill for this tournament.      │ │
│  │                                                    │ │
│  │ [Dismiss ✕]                                        │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
│  ⚠️ SKILL SELECTION (REQUIRED) ⚠️   [← Auto-scroll here]│
│  ┌───────────────────────────────────────────────────┐ │
│  │ [Border: Red - Pulsing animation]                 │ │
│  │ ...                                                │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Button State Logic

```typescript
// Compute button states
const canProceed = useMemo(() => {
  const hasSelectedSkills = selectedSkills.length >= 1;
  const hasValidPlacementRewards = validatePlacementRewards(rewardConfig);

  return hasSelectedSkills && hasValidPlacementRewards;
}, [selectedSkills, rewardConfig]);

// Render buttons
<div className="action-buttons">
  <button
    onClick={handleBack}
    className="btn-secondary"
  >
    ◀ Back
  </button>

  <button
    onClick={handleNext}
    className="btn-primary"
    disabled={!canProceed}
    title={!canProceed ? "Select at least 1 skill to continue" : ""}
  >
    Next ▶
  </button>
</div>
```

**Button Appearance**:
- **Disabled**: Gray background, no hover effect, cursor: not-allowed
- **Enabled**: Blue background, hover effect, cursor: pointer

---

## 📱 Mobile Responsiveness

On mobile devices, the skill selection block should:
- Use full width
- Stack skill categories vertically
- Increase touch target size for checkboxes (min 44x44px)
- Show sticky warning at bottom when 0 skills selected
- Keep Next button visible at bottom with validation state

```css
@media (max-width: 768px) {
  .skill-selection-block {
    width: 100%;
    padding: 16px;
  }

  .skill-checkbox {
    min-height: 44px;
    padding: 12px;
  }

  .inline-warning {
    position: sticky;
    bottom: 0;
    z-index: 10;
    background: #fff3cd;
    border-top: 2px solid #ffc107;
  }

  .action-buttons {
    position: sticky;
    bottom: 0;
    background: white;
    padding: 16px;
    border-top: 1px solid #ddd;
  }
}
```

---

## 🔍 Accessibility (a11y)

### ARIA Attributes

```tsx
<div
  className="skill-selection-block"
  role="group"
  aria-labelledby="skill-selection-header"
  aria-required="true"
  aria-invalid={selectedSkills.length === 0}
>
  <h3 id="skill-selection-header">
    Skill Selection (Required)
  </h3>

  {/* Skills */}
  {skills.map(skill => (
    <label key={skill.skill}>
      <input
        type="checkbox"
        role="checkbox"
        aria-checked={selectedSkills.includes(skill.skill)}
        aria-label={`${formatSkillName(skill.skill)} (weight: ${skill.weight}x)`}
      />
      {formatSkillName(skill.skill)}
    </label>
  ))}

  {/* Validation Message */}
  {validationError && (
    <div
      role="alert"
      aria-live="assertive"
      className="inline-warning"
    >
      {validationError}
    </div>
  )}
</div>

<button
  disabled={!canProceed}
  aria-disabled={!canProceed}
  aria-label={!canProceed ? "Cannot proceed: Select at least 1 skill" : "Proceed to next step"}
>
  Next ▶
</button>
```

### Keyboard Navigation

- **Tab**: Navigate between skill checkboxes
- **Space**: Toggle checkbox
- **Enter**: Toggle checkbox
- **Shift+Tab**: Navigate backwards

---

## 🧪 Frontend Testing Checklist

### Manual Testing

- [ ] Load tournament creation page → 0 skills selected by default
- [ ] Verify Next button is DISABLED
- [ ] Verify inline warning is visible
- [ ] Check 1 skill → Next button ENABLED, warning disappears
- [ ] Uncheck all skills → Next button DISABLED again
- [ ] Switch template → All skills reset to 0 (no auto-enable)
- [ ] Try to submit with 0 skills → API returns 400 error
- [ ] Verify error banner appears with descriptive message
- [ ] Verify page scrolls to skill selection block
- [ ] Verify skill block border turns red on error

### Automated Testing (Example)

```typescript
describe('SkillSelectionBlock', () => {
  it('should disable Next button when 0 skills selected', () => {
    render(<RewardConfigEditor />);

    const nextButton = screen.getByText('Next');
    expect(nextButton).toBeDisabled();
  });

  it('should enable Next button when 1+ skills selected', () => {
    render(<RewardConfigEditor />);

    const speedCheckbox = screen.getByLabelText(/Speed/i);
    fireEvent.click(speedCheckbox);

    const nextButton = screen.getByText('Next');
    expect(nextButton).not.toBeDisabled();
  });

  it('should show inline warning when 0 skills selected', () => {
    render(<RewardConfigEditor />);

    expect(screen.getByText(/You must select at least 1 skill/i)).toBeInTheDocument();
  });

  it('should reset skills to 0 when switching templates', () => {
    render(<RewardConfigEditor />);

    // Select a skill
    const speedCheckbox = screen.getByLabelText(/Speed/i);
    fireEvent.click(speedCheckbox);

    // Switch template
    const templateSelect = screen.getByLabelText(/Template/i);
    fireEvent.change(templateSelect, { target: { value: 'CHAMPIONSHIP' } });

    // Verify 0 skills selected
    expect(screen.getByText(/Selected: 0 skills/i)).toBeInTheDocument();
    expect(speedCheckbox).not.toBeChecked();
  });

  it('should show API error when backend validation fails', async () => {
    const mockSave = jest.fn().mockRejectedValue({
      status: 400,
      detail: 'Invalid skill configuration: At least 1 skill must be enabled'
    });

    render(<RewardConfigEditor onSave={mockSave} />);

    // Try to save with 0 skills (somehow bypassing client validation)
    fireEvent.click(screen.getByText('Save'));

    // Verify error banner appears
    await waitFor(() => {
      expect(screen.getByText(/Invalid skill configuration/i)).toBeInTheDocument();
    });
  });
});
```

---

## 📊 Summary: UX Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| 0 skills selected by default | ✅ | Templates have `enabled=False` |
| Visual "Required" indicator | ✅ | Warning icon + "REQUIRED" badge |
| Next/Save button disabled when 0 skills | ✅ | `disabled={!canProceed}` |
| Inline warning (not just toast) | ✅ | `<div role="alert">` component |
| Template switching keeps 0 skills | ✅ | `setSelectedSkills([])` on change |
| Client-side validation | ✅ | Real-time skill count check |
| Server-side validation | ✅ | 400 error from API |
| Error banner on API failure | ✅ | Error handling + scroll to block |
| Red border on invalid state | ✅ | Conditional CSS class |
| Green border on valid state | ✅ | Conditional CSS class |
| Skill counter display | ✅ | "Selected: X skills" |
| Mobile-friendly | ✅ | Responsive CSS + sticky warning |
| Accessible (a11y) | ✅ | ARIA attributes + keyboard nav |

---

## 🚀 Implementation Priority

1. **Phase 1: Core Validation** (Must-have)
   - Skill selection counter
   - Button disabled state
   - Inline warning message

2. **Phase 2: Visual Polish** (Should-have)
   - Red/green border states
   - Warning icons
   - Hover effects

3. **Phase 3: Error Handling** (Must-have)
   - API error banner
   - Auto-scroll to skill block
   - Error highlight animation

4. **Phase 4: UX Refinements** (Nice-to-have)
   - Skill category grouping
   - Weight display
   - Selection counter animation

---

## ✅ Ready for Production

Once the frontend implements these UX requirements:

1. ✅ Backend validation guards are in place
2. ✅ API returns clear error messages
3. ✅ Runtime fallback prevents crashes
4. ✅ All tests passing
5. ✅ Documentation complete
6. ⏳ **Frontend UX enforces skill selection**
7. ⏳ **Admin guide with examples**

→ **System ready for live tournament configuration** 🎉
