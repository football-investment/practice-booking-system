#!/usr/bin/env python3
"""
🔍 ENROLLMENT AUDIT SCRIPT
==========================

This script audits the enrollment table to find invalid enrollments where:
1. Enrollment created_at is outside the semester date range
2. Project semester is not active when enrollment was created
3. Missing or invalid semester data

Usage:
    python audit_invalid_enrollments.py [--fix] [--output report.json]

Options:
    --fix           Mark invalid enrollments with invalid=True flag
    --output FILE   Save audit report to JSON file
    --dry-run       Show what would be fixed without making changes
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.database import get_db
from app.models.project import Project, ProjectEnrollment
from app.models.semester import Semester
from app.models.user import User


class EnrollmentAuditor:
    def __init__(self, db_session):
        self.db = db_session
        self.issues_found = []
        self.stats = {
            'total_enrollments': 0,
            'valid_enrollments': 0,
            'invalid_enrollments': 0,
            'missing_semester_data': 0,
            'outside_semester_range': 0,
            'inactive_semester_enrollment': 0
        }

    def audit_all_enrollments(self) -> Dict[str, Any]:
        """
        Main audit function that checks all enrollments in the database.
        
        Returns:
            Dict containing audit results and statistics
        """
        print("🔍 Starting enrollment audit...")
        
        # Get all enrollments with related data
        enrollments = self.db.query(ProjectEnrollment)\
            .join(Project, ProjectEnrollment.project_id == Project.id)\
            .join(Semester, Project.semester_id == Semester.id)\
            .join(User, ProjectEnrollment.user_id == User.id)\
            .all()
        
        self.stats['total_enrollments'] = len(enrollments)
        print(f"📊 Found {len(enrollments)} total enrollments to audit")
        
        for enrollment in enrollments:
            self._audit_single_enrollment(enrollment)
        
        # Generate summary
        self.stats['valid_enrollments'] = (
            self.stats['total_enrollments'] - self.stats['invalid_enrollments']
        )
        
        return {
            'audit_timestamp': datetime.now(timezone.utc).isoformat(),
            'statistics': self.stats,
            'issues': self.issues_found,
            'summary': self._generate_summary()
        }

    def _audit_single_enrollment(self, enrollment: ProjectEnrollment) -> None:
        """Audit a single enrollment for validity."""
        try:
            project = enrollment.project
            semester = project.semester
            user = enrollment.user
            
            # Check for missing semester data
            if not semester.start_date or not semester.end_date:
                self._record_issue(
                    enrollment_id=enrollment.id,
                    issue_type="missing_semester_data",
                    severity="HIGH",
                    description=f"Semester '{semester.name}' (ID: {semester.id}) has invalid date configuration",
                    details={
                        'enrollment_date': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                        'project_title': project.title,
                        'student_name': user.name,
                        'semester_name': semester.name,
                        'semester_start': None,
                        'semester_end': None
                    }
                )
                self.stats['missing_semester_data'] += 1
                self.stats['invalid_enrollments'] += 1
                return
            
            # Check if enrollment date is within semester range
            enrollment_date = enrollment.enrolled_at.date() if enrollment.enrolled_at else None
            
            if not enrollment_date:
                self._record_issue(
                    enrollment_id=enrollment.id,
                    issue_type="missing_enrollment_date",
                    severity="MEDIUM",
                    description="Enrollment has no enrolled_at timestamp",
                    details={
                        'project_title': project.title,
                        'student_name': user.name,
                        'semester_name': semester.name
                    }
                )
                self.stats['invalid_enrollments'] += 1
                return
            
            # Check if enrollment is within semester date range
            if not (semester.start_date <= enrollment_date <= semester.end_date):
                severity = "HIGH" if enrollment_date < semester.start_date or enrollment_date > semester.end_date + timezone.utc.localize(datetime.now()).date() else "MEDIUM"
                
                self._record_issue(
                    enrollment_id=enrollment.id,
                    issue_type="outside_semester_range",
                    severity=severity,
                    description=f"Enrollment created outside semester date range",
                    details={
                        'enrollment_date': enrollment_date.isoformat(),
                        'semester_start': semester.start_date.isoformat(),
                        'semester_end': semester.end_date.isoformat(),
                        'project_title': project.title,
                        'student_name': user.name,
                        'semester_name': semester.name,
                        'days_outside_range': self._calculate_days_outside(
                            enrollment_date, semester.start_date, semester.end_date
                        )
                    }
                )
                self.stats['outside_semester_range'] += 1
                self.stats['invalid_enrollments'] += 1
                return
            
            # Check if semester was active when enrollment was created
            if not self._was_semester_active_on_date(semester, enrollment_date):
                self._record_issue(
                    enrollment_id=enrollment.id,
                    issue_type="inactive_semester_enrollment",
                    severity="MEDIUM",
                    description=f"Enrolled when semester was not active",
                    details={
                        'enrollment_date': enrollment_date.isoformat(),
                        'semester_start': semester.start_date.isoformat(),
                        'semester_end': semester.end_date.isoformat(),
                        'project_title': project.title,
                        'student_name': user.name,
                        'semester_name': semester.name,
                        'semester_was_future': enrollment_date < semester.start_date,
                        'semester_was_past': enrollment_date > semester.end_date
                    }
                )
                self.stats['inactive_semester_enrollment'] += 1
                self.stats['invalid_enrollments'] += 1
                
        except Exception as e:
            self._record_issue(
                enrollment_id=enrollment.id,
                issue_type="audit_error",
                severity="HIGH",
                description=f"Error during audit: {str(e)}",
                details={'error': str(e)}
            )
            self.stats['invalid_enrollments'] += 1

    def _record_issue(self, enrollment_id: int, issue_type: str, severity: str, 
                     description: str, details: Dict[str, Any]) -> None:
        """Record an issue found during audit."""
        issue = {
            'enrollment_id': enrollment_id,
            'issue_type': issue_type,
            'severity': severity,
            'description': description,
            'details': details,
            'found_at': datetime.now(timezone.utc).isoformat()
        }
        self.issues_found.append(issue)

    def _calculate_days_outside(self, enrollment_date, start_date, end_date) -> int:
        """Calculate how many days outside the semester range."""
        if enrollment_date < start_date:
            return (start_date - enrollment_date).days
        elif enrollment_date > end_date:
            return (enrollment_date - end_date).days
        return 0

    def _was_semester_active_on_date(self, semester, check_date) -> bool:
        """Check if semester was active on a specific date."""
        return semester.start_date <= check_date <= semester.end_date

    def _generate_summary(self) -> str:
        """Generate a human-readable summary of the audit."""
        total = self.stats['total_enrollments']
        invalid = self.stats['invalid_enrollments']
        valid = self.stats['valid_enrollments']
        
        summary_lines = [
            f"📊 AUDIT SUMMARY",
            f"===============",
            f"Total enrollments audited: {total}",
            f"Valid enrollments: {valid} ({(valid/total*100):.1f}%)" if total > 0 else "Valid enrollments: 0",
            f"Invalid enrollments: {invalid} ({(invalid/total*100):.1f}%)" if total > 0 else "Invalid enrollments: 0",
            "",
            f"Issue breakdown:",
            f"- Missing semester data: {self.stats['missing_semester_data']}",
            f"- Outside semester range: {self.stats['outside_semester_range']}",
            f"- Inactive semester enrollment: {self.stats['inactive_semester_enrollment']}"
        ]
        
        if invalid == 0:
            summary_lines.extend([
                "",
                "✅ NO ISSUES FOUND - All enrollments are valid!"
            ])
        else:
            summary_lines.extend([
                "",
                f"⚠️ {invalid} ISSUES REQUIRE ATTENTION"
            ])
        
        return "\n".join(summary_lines)

    def fix_invalid_enrollments(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Mark invalid enrollments in the database.
        
        Args:
            dry_run: If True, don't make actual changes
            
        Returns:
            Dict with fix results
        """
        if not self.issues_found:
            return {'message': 'No invalid enrollments to fix', 'fixed_count': 0}
        
        fixed_count = 0
        errors = []
        
        for issue in self.issues_found:
            try:
                enrollment_id = issue['enrollment_id']
                enrollment = self.db.query(ProjectEnrollment).filter(
                    ProjectEnrollment.id == enrollment_id
                ).first()
                
                if enrollment:
                    if not dry_run:
                        # Add invalid flag to enrollment
                        # Note: This requires adding the 'invalid' column to the model
                        enrollment.instructor_feedback = f"AUDIT: {issue['description']} (Found: {issue['found_at']})"
                        enrollment.enrollment_status = 'audit_flagged'
                        
                    fixed_count += 1
                    print(f"{'[DRY RUN] ' if dry_run else ''}Fixed enrollment {enrollment_id}: {issue['description']}")
                
            except Exception as e:
                errors.append({
                    'enrollment_id': issue['enrollment_id'],
                    'error': str(e)
                })
                print(f"❌ Error fixing enrollment {issue['enrollment_id']}: {e}")
        
        if not dry_run and fixed_count > 0:
            self.db.commit()
            print(f"✅ Successfully fixed {fixed_count} invalid enrollments")
        
        return {
            'fixed_count': fixed_count,
            'errors': errors,
            'dry_run': dry_run
        }


def main():
    parser = argparse.ArgumentParser(description='Audit enrollment validity')
    parser.add_argument('--fix', action='store_true', 
                       help='Mark invalid enrollments with flags')
    parser.add_argument('--output', type=str, 
                       help='Save audit report to JSON file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be fixed without making changes')
    
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create auditor and run audit
        auditor = EnrollmentAuditor(db)
        audit_results = auditor.audit_all_enrollments()
        
        # Print summary
        print("\n" + audit_results['summary'])
        
        # Show detailed issues if any
        if audit_results['issues']:
            print(f"\n🔍 DETAILED ISSUES:")
            print("==================")
            for i, issue in enumerate(audit_results['issues'], 1):
                print(f"\n{i}. [{issue['severity']}] {issue['description']}")
                print(f"   Enrollment ID: {issue['enrollment_id']}")
                if 'project_title' in issue['details']:
                    print(f"   Project: {issue['details']['project_title']}")
                if 'student_name' in issue['details']:
                    print(f"   Student: {issue['details']['student_name']}")
                if 'enrollment_date' in issue['details']:
                    print(f"   Enrollment Date: {issue['details']['enrollment_date']}")
        
        # Fix issues if requested
        if args.fix or args.dry_run:
            print(f"\n🔧 {'DRY RUN - ' if args.dry_run else ''}FIXING INVALID ENROLLMENTS...")
            fix_results = auditor.fix_invalid_enrollments(dry_run=args.dry_run)
            
            if fix_results['fixed_count'] > 0:
                audit_results['fix_results'] = fix_results
        
        # Save report if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(audit_results, f, indent=2, default=str)
            print(f"\n📁 Audit report saved to: {args.output}")
        
        # Exit with appropriate code
        exit_code = 1 if audit_results['statistics']['invalid_enrollments'] > 0 else 0
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        sys.exit(2)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()