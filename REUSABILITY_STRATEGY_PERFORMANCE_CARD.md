# Reusability Strategy: Tournament Performance Card

**Date:** 2026-02-09
**Strategic Goal:** Design Performance Card as reusable component, not single-use UI

---

## 🎯 VISION

**Performance Card ≠ UI Component**
**Performance Card = Tournament Summary Component**

**Future Use Cases (Beyond Tournament Achievements Tab):**
1. Player Profile Page (showcase top performances)
2. Academy Dashboard (coach view of player progress)
3. Social Share Card (PNG/SVG export for Instagram/Twitter)
4. Email Digest (weekly performance summary)
5. Leaderboard Detail View (click player → see performance card)
6. Tournament History Timeline (compact performance cards)

**Design Once, Use Everywhere → 80% time savings later**

---

## 🏗️ COMPONENT ARCHITECTURE

### Current Plan (Single-Use - BAD)

```python
# tournament_achievement_accordion.py
def render_tournament_accordion_item(...):
    # Performance card hardcoded inside accordion
    st.markdown(f"""
        <div>
            🥇 CHAMPION
            #1 of 64 players
            ...
        </div>
    """)
```

**Problem:** Tightly coupled to accordion, can't reuse

---

### Reusable Design (Multi-Use - GOOD)

#### 1. Standalone Component

**File:** `/streamlit_app/components/tournaments/performance_card.py`

```python
"""
Reusable Tournament Performance Card Component

Can be used in:
- Tournament Achievements Accordion
- Player Profile Page
- Academy Dashboard
- Social Share Export
- Email Digest
"""
from typing import Dict, Any, Optional, Literal
import streamlit as st

# Size presets
CardSize = Literal["compact", "normal", "large"]

def render_performance_card(
    tournament_data: Dict[str, Any],
    size: CardSize = "normal",
    show_badges: bool = True,
    show_rewards: bool = True,
    context: str = "accordion"  # "profile", "share", "email", etc.
) -> None:
    """
    Render tournament performance card.

    Args:
        tournament_data: {
            'tournament_id': int,
            'tournament_name': str,
            'tournament_status': str,
            'badges': List[Dict],  # User's badges for this tournament
            'metrics': {
                'rank': int,
                'points': float,
                'wins': int, 'draws': int, 'losses': int,
                'goals_for': int,
                'avg_points': float,
                'total_participants': int,
                'xp_earned': int,
                'credits_earned': int
            }
        }
        size: "compact" | "normal" | "large"
        show_badges: Whether to render badge section
        show_rewards: Whether to render rewards line
        context: Where card is being rendered (affects styling)
    """
    metrics = tournament_data.get('metrics', {})
    if not metrics:
        st.warning("No performance data available")
        return

    # Extract data
    rank = metrics.get('rank')
    total_participants = metrics.get('total_participants')
    points = metrics.get('points')
    avg_points = metrics.get('avg_points')

    # Compute percentile
    percentile = None
    percentile_badge = None
    if rank and total_participants:
        percentile = (rank / total_participants) * 100
        percentile_badge = _get_percentile_badge(percentile)

    # Determine badge type from badges list
    badge_type = _get_primary_badge_type(tournament_data.get('badges', []))

    # Size-dependent styling
    styles = _get_card_styles(size)

    # Render card
    st.markdown(_render_hero_section(
        badge_type, rank, total_participants, percentile_badge, styles
    ), unsafe_allow_html=True)

    if size != "compact":
        _render_performance_triptych(metrics, avg_points, styles)

    if show_rewards and size != "compact":
        _render_rewards_line(metrics, styles)

    if show_badges and size == "large":
        _render_badge_carousel(tournament_data.get('badges', []))


def _get_percentile_badge(percentile: float) -> Dict[str, str]:
    """Compute percentile tier and styling."""
    if percentile <= 5:
        return {"text": "🔥 TOP 5%", "color": "#FFD700", "gradient": "linear-gradient(135deg, #FFD700 0%, #FFA500 100%)"}
    elif percentile <= 10:
        return {"text": "⚡ TOP 10%", "color": "#FF8C00", "gradient": "linear-gradient(135deg, #FF8C00 0%, #FF6347 100%)"}
    elif percentile <= 25:
        return {"text": "🎯 TOP 25%", "color": "#1E90FF", "gradient": "linear-gradient(135deg, #1E90FF 0%, #00BFFF 100%)"}
    else:
        return {"text": "📊 TOP 50%", "color": "#A9A9A9", "gradient": "linear-gradient(135deg, #A9A9A9 0%, #D3D3D3 100%)"}


def _get_card_styles(size: CardSize) -> Dict[str, str]:
    """Get size-dependent styles."""
    if size == "compact":
        return {
            "badge_icon_size": "32px",
            "badge_font_size": "14px",
            "context_font_size": "11px",
            "padding": "8px",
            "card_height": "80px"
        }
    elif size == "normal":
        return {
            "badge_icon_size": "48px",
            "badge_font_size": "18px",
            "context_font_size": "13px",
            "padding": "12px",
            "card_height": "240px"
        }
    else:  # large
        return {
            "badge_icon_size": "64px",
            "badge_font_size": "24px",
            "context_font_size": "16px",
            "padding": "16px",
            "card_height": "320px"
        }


def _render_hero_section(badge_type, rank, total, percentile_badge, styles) -> str:
    """Render hero status block HTML."""
    # ... (HTML template with f-strings)
    pass


def _render_performance_triptych(metrics, avg_points, styles):
    """Render performance metrics in 3-column layout."""
    # ... (Streamlit columns layout)
    pass


def _render_rewards_line(metrics, styles):
    """Render compact rewards line."""
    # ... (HTML template)
    pass


def _render_badge_carousel(badges):
    """Render badge carousel (collapsed by default)."""
    # ... (Badge grid component)
    pass


# Export function
def export_performance_card_image(tournament_data: Dict[str, Any]) -> bytes:
    """
    Export performance card as PNG image for social sharing.

    Returns:
        PNG image bytes
    """
    # Use Pillow or matplotlib to render card as image
    # For future implementation
    pass
```

---

#### 2. Usage in Tournament Achievements Accordion

**File:** `/streamlit_app/components/tournaments/tournament_achievement_accordion.py`

```python
from components.tournaments.performance_card import render_performance_card

def render_tournament_accordion_item(...):
    with st.expander(f"🏆 {tournament_name}", expanded=is_expanded):
        # Tournament header (status badge, date)
        st.markdown(...)

        # Performance Card (reusable component)
        render_performance_card(
            tournament_data=tournament_data,
            size="normal",
            show_badges=True,
            show_rewards=True,
            context="accordion"
        )
```

---

#### 3. Usage in Player Profile Page

**File:** `/streamlit_app/pages/LFA_Player_Profile.py`

```python
from components.tournaments.performance_card import render_performance_card

def render_player_profile(user_id: int):
    st.header("🏆 Top Performances")

    # Get user's top 3 tournaments (by percentile)
    top_tournaments = get_top_tournaments(user_id, limit=3)

    for tournament in top_tournaments:
        # Render compact performance card
        render_performance_card(
            tournament_data=tournament,
            size="compact",
            show_badges=False,  # Save space
            show_rewards=False,
            context="profile"
        )
```

---

#### 4. Usage in Social Share (Export PNG)

**File:** `/streamlit_app/components/social/share_card.py`

```python
from components.tournaments.performance_card import export_performance_card_image

def generate_share_card(tournament_data: Dict[str, Any]) -> bytes:
    """
    Generate PNG image for social media sharing.
    """
    img_bytes = export_performance_card_image(tournament_data)

    # Add branding (logo, watermark)
    # Add social media template (Instagram 1080x1080)

    return img_bytes

# Usage in UI:
if st.button("📤 Share on Instagram"):
    img = generate_share_card(tournament_data)
    st.download_button("Download Image", data=img, file_name="my_performance.png")
```

---

## 📊 COMPONENT API DESIGN

### Input Schema

```python
TournamentData = {
    # Tournament Identity
    'tournament_id': int,
    'tournament_name': str,
    'tournament_code': str | None,
    'tournament_status': Literal['COMPLETED', 'REWARDS_DISTRIBUTED', 'IN_PROGRESS', 'UPCOMING'],
    'start_date': str,  # ISO format

    # Performance Metrics
    'metrics': {
        'rank': int | None,
        'points': float | None,
        'wins': int | None,
        'draws': int | None,
        'losses': int | None,
        'goals_for': int | None,
        'goals_against': int | None,
        'avg_points': float | None,      # Tournament average
        'total_participants': int | None,
        'xp_earned': int,
        'credits_earned': int,
        'badges_earned': int
    },

    # Badges
    'badges': List[{
        'badge_type': str,
        'icon': str,
        'title': str,
        'rarity': str
    }]
}
```

### Output Variants

| Variant | Size | Show Badges | Show Rewards | Use Case |
|---------|------|-------------|--------------|----------|
| **Compact** | 80px | ❌ | ❌ | Profile page, timeline |
| **Normal** | 240px | ✅ (carousel) | ✅ | Accordion, default view |
| **Large** | 320px | ✅ (grid) | ✅ | Detail view, modal |
| **Export** | PNG | ✅ | ✅ | Social share, email |

---

## 🎨 DESIGN SYSTEM INTEGRATION

### Component Library Structure

```
streamlit_app/
├── components/
│   ├── tournaments/
│   │   ├── __init__.py
│   │   ├── performance_card.py       ← NEW: Reusable component
│   │   ├── performance_card_styles.py ← NEW: Style presets
│   │   ├── tournament_achievement_accordion.py
│   │   └── tournament_filters.py
│   │
│   ├── profile/
│   │   └── player_profile.py         → Uses performance_card
│   │
│   ├── social/
│   │   └── share_card.py             → Uses performance_card (export)
│   │
│   └── email/
│       └── digest_template.py        → Uses performance_card (HTML email)
```

### Style Presets (Reusable CSS)

**File:** `/streamlit_app/components/tournaments/performance_card_styles.py`

```python
"""
Reusable style presets for Performance Card
"""

# Color palettes
PERCENTILE_COLORS = {
    "top_5": {"primary": "#FFD700", "secondary": "#FFA500", "gradient": "linear-gradient(135deg, #FFD700 0%, #FFA500 100%)"},
    "top_10": {"primary": "#FF8C00", "secondary": "#FF6347", "gradient": "linear-gradient(135deg, #FF8C00 0%, #FF6347 100%)"},
    "top_25": {"primary": "#1E90FF", "secondary": "#00BFFF", "gradient": "linear-gradient(135deg, #1E90FF 0%, #00BFFF 100%)"},
    "default": {"primary": "#A9A9A9", "secondary": "#D3D3D3", "gradient": "linear-gradient(135deg, #A9A9A9 0%, #D3D3D3 100%)"}
}

BADGE_COLORS = {
    "CHAMPION": "#FFD700",
    "RUNNER_UP": "#C0C0C0",
    "THIRD_PLACE": "#CD7F32",
    "PARTICIPATION": "#4A90E2"
}

# Size presets (matching design system)
CARD_SIZES = {
    "compact": {
        "width": "100%",
        "height": "80px",
        "padding": "8px",
        "badge_icon": "32px",
        "font_title": "14px",
        "font_context": "11px"
    },
    "normal": {
        "width": "100%",
        "height": "240px",
        "padding": "12px",
        "badge_icon": "48px",
        "font_title": "18px",
        "font_context": "13px"
    },
    "large": {
        "width": "100%",
        "height": "320px",
        "padding": "16px",
        "badge_icon": "64px",
        "font_title": "24px",
        "font_context": "16px"
    }
}
```

---

## 🚀 IMPLEMENTATION PHASING

### Phase 1: Reusable Core (Week 1)
- [ ] Create `performance_card.py` (standalone component)
- [ ] Create `performance_card_styles.py` (style presets)
- [ ] Implement size variants (compact, normal, large)
- [ ] Unit tests (rendering logic)

### Phase 2: Accordion Integration (Week 1)
- [ ] Refactor `tournament_achievement_accordion.py` to use `render_performance_card()`
- [ ] Test in Tournament Achievements tab
- [ ] Deploy to production

### Phase 3: Profile Integration (Week 2)
- [ ] Add "🏆 Top Performances" section to Player Profile page
- [ ] Use `render_performance_card(size="compact")`
- [ ] Show top 3 tournaments

### Phase 4: Social Share (Week 3)
- [ ] Implement `export_performance_card_image()` (PNG export)
- [ ] Add "Share on Instagram" button
- [ ] Add branding + watermark

### Phase 5: Email Digest (Week 4)
- [ ] Create HTML email template using performance card
- [ ] Weekly digest: "Your top performance this week"
- [ ] Render card as inline HTML (not image)

---

## 📊 COST-BENEFIT ANALYSIS

### Cost of Reusable Design

| Aspect | Single-Use (Current Plan) | Reusable Design | Delta |
|--------|--------------------------|-----------------|-------|
| **Initial Dev Time** | 6 hours | 8 hours | +2 hours |
| **Code Lines** | ~150 lines | ~250 lines | +100 lines |
| **Testing Effort** | 2 hours | 3 hours | +1 hour |
| **Documentation** | 1 hour | 2 hours | +1 hour |
| **TOTAL UPFRONT** | 9 hours | 13 hours | **+4 hours** |

### Benefit of Reusable Design (Future Use Cases)

| Use Case | Time Saved (vs. Rebuild) | Lines Saved |
|----------|-------------------------|-------------|
| Player Profile | 4 hours | ~100 lines |
| Social Share | 6 hours | ~150 lines |
| Email Digest | 4 hours | ~100 lines |
| Academy Dashboard | 4 hours | ~100 lines |
| **TOTAL SAVINGS** | **18 hours** | **~450 lines** |

**ROI:** +4 hours upfront → **18 hours saved later** → **Net: +14 hours saved**

**Break-Even:** After 2 additional use cases (Profile + Social Share)

---

## ✅ DECISION CHECKLIST

### Design Principles

- [ ] **Separation of Concerns:** Component logic ≠ page logic
- [ ] **Size Variants:** Support compact/normal/large presets
- [ ] **Context Aware:** Adapt styling based on where it's rendered
- [ ] **Export Ready:** Can generate PNG/HTML for external use
- [ ] **Style System:** Use design tokens (colors, sizes) from central config
- [ ] **Accessibility:** ARIA labels, semantic HTML, screen reader support

### Implementation Requirements

- [ ] Create standalone `performance_card.py` file
- [ ] Support 3 size variants (compact, normal, large)
- [ ] Accept `context` parameter (accordion, profile, share, email)
- [ ] Implement `export_performance_card_image()` stub (for future)
- [ ] Add docstrings for all public functions
- [ ] Unit tests for rendering logic

---

## 🎯 ACCEPTANCE CRITERIA (Reusability)

- [ ] **AC-R1:** Performance card renders in accordion (size="normal")
- [ ] **AC-R2:** Performance card renders in profile (size="compact")
- [ ] **AC-R3:** Component can be imported and used in ANY page (not coupled to accordion)
- [ ] **AC-R4:** Size variants correctly apply styling (compact=80px, normal=240px, large=320px)
- [ ] **AC-R5:** Export function stub exists (ready for PNG implementation)
- [ ] **AC-R6:** Style presets centralized in `performance_card_styles.py`

---

## 📝 DOCUMENTATION

### Component README

**File:** `/streamlit_app/components/tournaments/README.md`

```markdown
# Tournament Performance Card

Reusable component for displaying tournament performance summary.

## Usage

```python
from components.tournaments.performance_card import render_performance_card

render_performance_card(
    tournament_data={
        'tournament_id': 1543,
        'tournament_name': "Speed Test 2026",
        'metrics': {...},
        'badges': [...]
    },
    size="normal",  # "compact" | "normal" | "large"
    show_badges=True,
    show_rewards=True,
    context="accordion"
)
```

## Variants

- **Compact (80px):** Profile page, timeline
- **Normal (240px):** Accordion, default view
- **Large (320px):** Detail modal, showcase

## Future: Export to PNG

```python
img_bytes = export_performance_card_image(tournament_data)
st.download_button("Download", data=img_bytes)
```
```

---

## ✅ FINAL RECOMMENDATION

**Approve:** ✅ Implement reusable design (+4 hours upfront, +18 hours saved later)

**Key Changes to Implementation Plan:**
1. Create `performance_card.py` as standalone component
2. Support 3 size variants (compact, normal, large)
3. Refactor accordion to use component (not inline HTML)
4. Add export stub for future PNG generation

**Net Impact:** **+4 hours** initial development (worth it for future savings)

---

**Status:** ✅ Strategy defined - Ready for implementation
**Next Step:** Update Implementation Plan with reusability requirements

---

**Prepared by:** Claude Sonnet 4.5
**Date:** 2026-02-09
**Priority:** HIGH (strategic, not urgent)
