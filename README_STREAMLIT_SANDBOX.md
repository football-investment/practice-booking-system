# Sandbox Tournament Test - Streamlit UI

Prototype frontend for testing the `sandbox-api-v1` endpoint.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r streamlit_requirements.txt
```

Or if using existing venv:
```bash
source venv/bin/activate
pip install streamlit requests
```

### 2. Start Backend Server

Make sure the FastAPI backend is running:
```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Launch Streamlit App

```bash
streamlit run streamlit_sandbox.py
```

The app will open automatically at `http://localhost:8501`

## Usage

### Screen 1: Configuration
1. **Authenticate**: Use admin credentials (default: `admin@lfa.com` / `admin123`)
2. **Configure Tournament**:
   - Select tournament type (league, knockout, hybrid)
   - Choose player count (4-16)
   - Select skills to test (1-4 skills)
3. **Advanced Options** (optional):
   - Performance variation (LOW/MEDIUM/HIGH)
   - Ranking distribution (NORMAL/TOP_HEAVY/BOTTOM_HEAVY)
4. Click **"🚀 Run Sandbox Test"**

### Screen 2: Progress
- Visual progress bar shows execution steps
- Real-time status updates
- Automatic transition to results when complete

### Screen 3: Results
- **Verdict**: WORKING ✅ or NOT_WORKING ❌
- **Tabs**:
  - **Skill Progression**: Before/after stats with averages and ranges
  - **Top Performers**: Top 3 players with detailed skill changes
  - **Bottom Performers**: Bottom 2 players (if applicable)
  - **Insights**: Success messages, errors, execution summary

## API Integration

The app integrates with the frozen `sandbox-api-v1` contract:

**Endpoint**: `POST /api/v1/sandbox/run-test`

**Request**:
```json
{
  "tournament_type": "league",
  "skills_to_test": ["passing", "dribbling"],
  "player_count": 8,
  "test_config": {
    "performance_variation": "MEDIUM",
    "ranking_distribution": "NORMAL"
  }
}
```

**Response**: See `/docs/API_CONTRACT_Sandbox_Tournament_MVP.md`

## Features

✅ **Configuration Screen**
- Tournament type selector
- Multi-select skills (1-4 limit enforced)
- Player count slider (4-16)
- Advanced options collapsible
- Admin authentication

✅ **Progress Screen**
- Step-by-step execution visualization
- Progress bar with status text
- Simulated real-time updates
- Error handling with retry

✅ **Results Screen**
- Color-coded verdict badge
- Tournament metadata cards
- Tabbed skill progression data
- Top/bottom performers with skill details
- Insights categorized by severity
- Execution summary timeline
- Export options (JSON download)

## Architecture

```
streamlit_sandbox.py
├── get_auth_token()          # Authentication
├── run_sandbox_test()        # API call
├── render_configuration_screen()
├── render_progress_screen()
└── render_results_screen()
    ├── render_skill_progression()
    ├── render_top_performers()
    ├── render_bottom_performers()
    └── render_insights()
```

## Troubleshooting

**Backend not responding**:
- Check FastAPI server is running on `http://localhost:8000`
- Verify database connection

**Authentication fails**:
- Ensure admin user exists in database
- Check credentials: `admin@lfa.com` / `admin123`

**API errors**:
- Check browser console for detailed error messages
- Verify API endpoint is correct
- Ensure `sandbox-api-v1` is deployed

## Future Integration

This Streamlit prototype can be converted to React/Vue components for integration into the main admin dashboard:

1. **Configuration Component**: Form with validation
2. **Progress Component**: Real-time status display
3. **Results Component**: Tabbed data visualization

The API contract is frozen (`sandbox-api-v1`), so frontend can be developed independently.

## Development

**Backend Status**: 🔒 LOCKED (`sandbox-api-v1`)
- No backend changes allowed
- Only integration support

**Frontend Status**: 🚧 Prototype
- Streamlit for rapid prototyping
- Full "Ship It" flow implemented
- Ready for conversion to production framework
