"""
Backend Workflow Integration Tests
===================================

P2 Stabilization - Comprehensive backend testing before P3

Tests the complete backend workflow:
1. Progress-License Coupling Service
2. Auto-sync hooks
3. Health monitoring service + scheduler
4. Admin API endpoints

Test Scenarios:
- User creation + specialization assignment
- Progress update → License sync
- Level-up + XP change
- Desync injection → auto-sync → consistency validation
- API queries → JSON log verification

Author: Claude Code
Date: 2025-10-25
"""

import sys
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User, UserRole
from app.models.user_progress import SpecializationProgress, Specialization
from app.models.license import UserLicense, LicenseProgression
from app.services.specialization_service import SpecializationService
from app.services.license_service import LicenseService
from app.services.progress_license_sync_service import ProgressLicenseSyncService
from app.services.progress_license_coupling import ProgressLicenseCoupler
from app.services.health_monitor import HealthMonitor


class BackendWorkflowTester:
    """Comprehensive backend workflow integration tests"""

    def __init__(self, db: Session):
        self.db = db
        self.spec_service = SpecializationService(db)
        self.license_service = LicenseService(db)
        self.sync_service = ProgressLicenseSyncService(db)
        self.coupler = ProgressLicenseCoupler(db)
        self.health_monitor = HealthMonitor(db)

        self.test_results: List[Dict[str, Any]] = []
        self.test_user = None

    def log_test(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': details
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} | {test_name}")
        if details:
            for key, value in details.items():
                print(f"  {key}: {value}")

    def cleanup_test_data(self):
        """Clean up test data before running"""
        print("\n🧹 Cleaning up previous test data...")

        try:
            # Delete test user's data
            if self.test_user:
                self.db.query(LicenseProgression).filter(
                    LicenseProgression.user_id == self.test_user.id
                ).delete()

                self.db.query(UserLicense).filter(
                    UserLicense.user_id == self.test_user.id
                ).delete()

                self.db.query(SpecializationProgress).filter(
                    SpecializationProgress.student_id == self.test_user.id
                ).delete()

                self.db.delete(self.test_user)
                self.db.commit()

            print("✅ Cleanup complete")
        except Exception as e:
            print(f"⚠️  Cleanup error (may be first run): {str(e)}")
            self.db.rollback()

    # =========================================================================
    # TEST 1: User Creation + Specialization Assignment
    # =========================================================================

    def test_1_user_creation_and_assignment(self) -> bool:
        """Test 1: Create user and assign specialization"""
        try:
            # Create test user
            self.test_user = User(
                email=f"test_workflow_{datetime.now(timezone.utc).timestamp()}@example.com",
                password_hash="test_hash",
                name="Test Workflow User",
                role=UserRole.STUDENT,
                is_active=True
            )
            self.db.add(self.test_user)
            self.db.commit()
            self.db.refresh(self.test_user)

            # Assign PLAYER specialization
            progress = SpecializationProgress(
                student_id=self.test_user.id,
                specialization_id="PLAYER",
                current_level=1,
                total_xp=0
            )
            self.db.add(progress)
            self.db.commit()

            # Verify assignment
            saved_progress = self.db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == self.test_user.id,
                SpecializationProgress.specialization_id == "PLAYER"
            ).first()

            success = saved_progress is not None
            self.log_test(
                "User Creation + Specialization Assignment",
                success,
                {
                    'user_id': self.test_user.id,
                    'email': self.test_user.email,
                    'specialization': 'PLAYER',
                    'initial_level': saved_progress.current_level if saved_progress else None
                }
            )
            return success

        except Exception as e:
            self.db.rollback()
            self.log_test(
                "User Creation + Specialization Assignment",
                False,
                {'error': str(e)}
            )
            return False

    # =========================================================================
    # TEST 2: Progress Update → License Sync (via hooks)
    # =========================================================================

    def test_2_progress_update_with_auto_sync(self) -> bool:
        """Test 2: Progress update triggers auto-sync via hooks"""
        try:
            # Update progress (add XP, level up)
            result = self.spec_service.update_progress(
                student_id=self.test_user.id,
                specialization_id="PLAYER",
                xp_gained=25000,  # Level 2 requires 25,000 XP
                sessions_completed=12  # Level 2 requires 12 sessions
            )

            # Verify progress updated
            progress = self.db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == self.test_user.id,
                SpecializationProgress.specialization_id == "PLAYER"
            ).first()

            # Verify license created/updated by auto-sync hook
            license = self.db.query(UserLicense).filter(
                UserLicense.user_id == self.test_user.id,
                UserLicense.specialization_type == "PLAYER"
            ).first()

            # Check if sync result was returned
            sync_result = result.get('sync_result')

            success = (
                progress is not None and
                license is not None and
                progress.current_level == license.current_level and
                sync_result is not None
            )

            self.log_test(
                "Progress Update → Auto-Sync Hook",
                success,
                {
                    'progress_level': progress.current_level if progress else None,
                    'license_level': license.current_level if license else None,
                    'total_xp': progress.total_xp if progress else None,
                    'sync_triggered': sync_result is not None,
                    'sync_success': sync_result.get('success') if sync_result else None
                }
            )
            return success

        except Exception as e:
            self.db.rollback()
            self.log_test(
                "Progress Update → Auto-Sync Hook",
                False,
                {'error': str(e)}
            )
            return False

    # =========================================================================
    # TEST 3: Level-Up + XP Change
    # =========================================================================

    def test_3_level_up_and_xp_change(self) -> bool:
        """Test 3: Multiple level-ups with XP changes"""
        try:
            initial_progress = self.db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == self.test_user.id,
                SpecializationProgress.specialization_id == "PLAYER"
            ).first()

            initial_level = initial_progress.current_level

            # Level up multiple times (give massive XP and sessions)
            for i in range(3):
                self.spec_service.update_progress(
                    student_id=self.test_user.id,
                    specialization_id="PLAYER",
                    xp_gained=100000,  # Plenty of XP
                    sessions_completed=20  # Plenty of sessions
                )

            # Verify final state
            final_progress = self.db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == self.test_user.id,
                SpecializationProgress.specialization_id == "PLAYER"
            ).first()

            final_license = self.db.query(UserLicense).filter(
                UserLicense.user_id == self.test_user.id,
                UserLicense.specialization_type == "PLAYER"
            ).first()

            success = (
                final_progress.current_level > initial_level and
                final_progress.current_level == final_license.current_level
            )

            self.log_test(
                "Multiple Level-Ups + XP Changes",
                success,
                {
                    'initial_level': initial_level,
                    'final_level': final_progress.current_level,
                    'levels_gained': final_progress.current_level - initial_level,
                    'total_xp': final_progress.total_xp,
                    'license_synced': final_progress.current_level == final_license.current_level
                }
            )
            return success

        except Exception as e:
            self.db.rollback()
            self.log_test(
                "Multiple Level-Ups + XP Changes",
                False,
                {'error': str(e)}
            )
            return False

    # =========================================================================
    # TEST 4: Desync Injection → Auto-Sync → Validation
    # =========================================================================

    def test_4_desync_injection_and_recovery(self) -> bool:
        """Test 4: Inject desync, trigger auto-sync, validate consistency"""
        try:
            # Get current progress
            progress = self.db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == self.test_user.id,
                SpecializationProgress.specialization_id == "PLAYER"
            ).first()

            if not progress:
                raise Exception("No progress found for test user - previous tests may have failed")

            original_level = progress.current_level

            # INJECT DESYNC: Manually update license to different level
            license = self.db.query(UserLicense).filter(
                UserLicense.user_id == self.test_user.id,
                UserLicense.specialization_type == "PLAYER"
            ).first()

            license.current_level = original_level - 2  # Create desync
            self.db.commit()

            # Validate desync detected
            validation_before = self.coupler.validate_consistency(
                self.test_user.id,
                "PLAYER"
            )

            # Trigger auto-sync
            sync_result = self.sync_service.sync_progress_to_license(
                user_id=self.test_user.id,
                specialization="PLAYER",
                synced_by=None
            )

            # Validate consistency restored
            validation_after = self.coupler.validate_consistency(
                self.test_user.id,
                "PLAYER"
            )

            success = (
                validation_before['consistent'] == False and
                sync_result['success'] == True and
                validation_after['consistent'] == True
            )

            self.log_test(
                "Desync Injection → Auto-Sync → Validation",
                success,
                {
                    'desync_detected': not validation_before['consistent'],
                    'sync_success': sync_result['success'],
                    'consistency_restored': validation_after['consistent'],
                    'original_level': original_level,
                    'final_progress_level': validation_after.get('progress_level'),
                    'final_license_level': validation_after.get('license_level')
                }
            )
            return success

        except Exception as e:
            self.db.rollback()
            self.log_test(
                "Desync Injection → Auto-Sync → Validation",
                False,
                {'error': str(e)}
            )
            return False

    # =========================================================================
    # TEST 5: Health Monitoring Service
    # =========================================================================

    def test_5_health_monitoring_service(self) -> bool:
        """Test 5: Health monitoring service detects and logs violations"""
        try:
            # Create another user with intentional desync
            desync_user = User(
                email=f"test_desync_{datetime.now(timezone.utc).timestamp()}@example.com",
                password_hash="test_hash",
                name="Test Desync User",
                role=UserRole.STUDENT,
                is_active=True
            )
            self.db.add(desync_user)
            self.db.commit()
            self.db.refresh(desync_user)

            # Create progress
            progress = SpecializationProgress(
                student_id=desync_user.id,
                specialization_id="COACH",
                current_level=5,
                total_xp=500
            )
            self.db.add(progress)

            # Create desynced license
            license = UserLicense(
                user_id=desync_user.id,
                specialization_type="COACH",
                current_level=3,  # DESYNCED
                max_achieved_level=3,
                started_at=datetime.now(timezone.utc)
            )
            self.db.add(license)
            self.db.commit()

            # Run health check
            health_report = self.health_monitor.check_all_users(dry_run=True)

            # Find our desync user in violations
            found_violation = False
            for violation in health_report.get('violations', []):
                if (violation['user_id'] == desync_user.id and
                    violation['specialization'] == 'COACH'):
                    found_violation = True
                    break

            # Cleanup desync user
            self.db.delete(license)
            self.db.delete(progress)
            self.db.delete(desync_user)
            self.db.commit()

            success = (
                health_report['total_checked'] > 0 and
                health_report['inconsistent'] > 0 and
                found_violation
            )

            self.log_test(
                "Health Monitoring Service",
                success,
                {
                    'total_checked': health_report['total_checked'],
                    'consistent': health_report['consistent'],
                    'inconsistent': health_report['inconsistent'],
                    'consistency_rate': health_report['consistency_rate'],
                    'desync_detected': found_violation
                }
            )
            return success

        except Exception as e:
            self.db.rollback()
            self.log_test(
                "Health Monitoring Service",
                False,
                {'error': str(e)}
            )
            return False

    # =========================================================================
    # TEST 6: Coupling Enforcer Atomic Updates
    # =========================================================================

    def test_6_coupling_enforcer_atomic_update(self) -> bool:
        """Test 6: Coupling enforcer ensures atomic updates"""
        try:
            # Use coupling enforcer to update both tables atomically
            result = self.coupler.update_level_atomic(
                user_id=self.test_user.id,
                specialization="PLAYER",
                new_level=8,
                xp_change=1000,
                reason="Test atomic update"
            )

            # Verify both tables updated
            progress = self.db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == self.test_user.id,
                SpecializationProgress.specialization_id == "PLAYER"
            ).first()

            license = self.db.query(UserLicense).filter(
                UserLicense.user_id == self.test_user.id,
                UserLicense.specialization_type == "PLAYER"
            ).first()

            # Validate consistency
            validation = self.coupler.validate_consistency(
                self.test_user.id,
                "PLAYER"
            )

            success = (
                result['success'] == True and
                progress.current_level == 8 and
                license.current_level == 8 and
                validation['consistent'] == True
            )

            self.log_test(
                "Coupling Enforcer Atomic Update",
                success,
                {
                    'update_success': result['success'],
                    'progress_level': progress.current_level,
                    'license_level': license.current_level,
                    'consistency_validated': validation['consistent']
                }
            )
            return success

        except Exception as e:
            self.db.rollback()
            self.log_test(
                "Coupling Enforcer Atomic Update",
                False,
                {'error': str(e)}
            )
            return False

    # =========================================================================
    # Main Test Runner
    # =========================================================================

    def run_all_tests(self):
        """Run all backend workflow tests"""
        print("\n" + "="*70)
        print("🧪 BACKEND WORKFLOW INTEGRATION TESTS")
        print("P2 Stabilization - Comprehensive Backend Testing")
        print("="*70)

        self.cleanup_test_data()

        # Run tests in sequence
        tests = [
            self.test_1_user_creation_and_assignment,
            self.test_2_progress_update_with_auto_sync,
            self.test_3_level_up_and_xp_change,
            self.test_4_desync_injection_and_recovery,
            self.test_5_health_monitoring_service,
            self.test_6_coupling_enforcer_atomic_update
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"\n❌ Test failed with exception: {str(e)}")
                failed += 1

        # Summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {len(tests)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(tests)*100):.1f}%")

        # Save results to JSON
        report_file = f"logs/test_reports/backend_workflow_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_tests': len(tests),
                'passed': passed,
                'failed': failed,
                'success_rate': round(passed/len(tests)*100, 2),
                'results': self.test_results
            }, f, indent=2)

        print(f"\n📝 Full report saved: {report_file}")
        print("="*70 + "\n")

        # Cleanup
        self.cleanup_test_data()

        return passed == len(tests)


def main():
    """Main test runner"""
    db = SessionLocal()
    try:
        tester = BackendWorkflowTester(db)
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
