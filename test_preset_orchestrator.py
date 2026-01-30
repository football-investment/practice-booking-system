"""
Quick test script for orchestrator preset integration
"""
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator

def test_preset_integration():
    """Test tournament creation with preset"""
    db: Session = SessionLocal()

    try:
        orchestrator = SandboxTestOrchestrator(db)

        print("🧪 Testing orchestrator with GanFootvolley preset...")

        # Test with preset (should use preset values)
        result = orchestrator.execute_test(
            tournament_type_code="league",
            player_count=4,
            user_ids=[4, 5, 6, 7],
            game_preset_id=1,  # GanFootvolley
            random_seed=42  # For reproducibility
        )

        print(f"\n✅ Tournament created: {result['tournament']['id']}")
        print(f"📊 Verdict: {result['verdict']}")
        print(f"🎮 Execution steps:")
        for step in result['execution_summary']['steps_completed']:
            print(f"   {step}")

        # Check database
        from app.models import Semester
        tournament = db.query(Semester).filter(Semester.id == result['tournament']['id']).first()

        print(f"\n🔍 Database verification:")
        print(f"   game_preset_id: {tournament.game_preset_id}")
        print(f"   game_config version: {tournament.game_config.get('version') if tournament.game_config else 'N/A'}")
        print(f"   skills_tested: {tournament.game_config.get('skill_config', {}).get('skills_tested', [])}")
        print(f"   draw_probability: {tournament.game_config.get('format_config', {}).get('HEAD_TO_HEAD', {}).get('match_simulation', {}).get('draw_probability')}")
        print(f"   game_config_overrides: {tournament.game_config_overrides}")

        print("\n✅ Phase 3 orchestrator integration test PASSED!")

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    test_preset_integration()
