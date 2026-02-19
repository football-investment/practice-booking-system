"""
Initialize Track-Based Education System
Create LFA tracks, modules, and certificate templates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Track, Module, ModuleComponent, 
    CertificateTemplate, Semester
)
from app.services.certificate_service import CertificateService


def create_lfa_tracks(db: Session):
    """Create the three main LFA tracks"""
    
    # Get current semester
    current_semester = db.query(Semester).order_by(Semester.id.desc()).first()
    
    tracks_data = [
        {
            "name": "LFA Internship",
            "code": "INT",
            "description": "Professional football internship program focusing on practical experience in club operations, player development, and football management.",
            "duration_semesters": 1,
            "prerequisites": {},
            "certificate_title": "LFA Internship Certificate"
        },
        {
            "name": "LFA Coach", 
            "code": "COACH",
            "description": "Comprehensive coaching education program covering tactical analysis, player development, team management, and modern coaching methodologies.",
            "duration_semesters": 2,
            "prerequisites": {},
            "certificate_title": "LFA Coach Certification"
        },
        {
            "name": "GānCuju",
            "code": "GANCUJU", 
            "description": "Ancient Chinese football heritage program exploring traditional techniques, philosophy, and cultural aspects of football development.",
            "duration_semesters": 1,
            "prerequisites": {"recommended_tracks": ["INT"]},
            "certificate_title": "GānCuju Heritage Certificate"
        }
    ]
    
    created_tracks = []
    certificate_service = CertificateService(db)
    
    for track_data in tracks_data:
        # Check if track already exists
        existing_track = db.query(Track).filter(Track.code == track_data["code"]).first()
        if existing_track:
            print(f"Track {track_data['code']} already exists, skipping...")
            created_tracks.append(existing_track)
            continue
        
        # Create track
        track = Track(
            name=track_data["name"],
            code=track_data["code"],
            description=track_data["description"],
            duration_semesters=track_data["duration_semesters"],
            prerequisites=track_data["prerequisites"]
        )
        
        db.add(track)
        db.commit()
        db.refresh(track)
        
        # Create certificate template
        cert_template = certificate_service.create_certificate_template(
            track_id=str(track.id),
            title=track_data["certificate_title"],
            description=f"Certificate of completion for {track_data['name']} track"
        )
        
        # Certificate template is automatically linked via track_id relationship
        
        created_tracks.append(track)
        print(f"✅ Created track: {track.name} ({track.code})")
    
    return created_tracks


def create_internship_modules(db: Session, internship_track: Track, current_semester: Semester):
    """Create modules for LFA Internship track"""
    
    modules_data = [
        {
            "name": "Club Operations Introduction",
            "description": "Introduction to professional football club operations, organizational structure, and daily workflows.",
            "order": 1,
            "estimated_hours": 40,
            "learning_objectives": [
                "Understand club organizational structure",
                "Learn daily operational workflows",
                "Identify key stakeholders and roles"
            ],
            "components": [
                {"type": "theory", "name": "Club Structure Overview", "minutes": 120},
                {"type": "assignment", "name": "Stakeholder Analysis", "minutes": 180},
                {"type": "quiz", "name": "Operations Knowledge Check", "minutes": 30}
            ]
        },
        {
            "name": "Player Development Fundamentals", 
            "description": "Core principles of player development, talent identification, and youth academy operations.",
            "order": 2,
            "estimated_hours": 60,
            "learning_objectives": [
                "Master talent identification techniques",
                "Understand development pathway structures",
                "Learn mentoring and guidance methods"
            ],
            "components": [
                {"type": "theory", "name": "Talent Identification", "minutes": 180},
                {"type": "project", "name": "Development Plan Creation", "minutes": 240},
                {"type": "video", "name": "Case Study Analysis", "minutes": 90}
            ]
        },
        {
            "name": "Practical Experience",
            "description": "Hands-on internship experience with real club operations and mentorship.",
            "order": 3,
            "estimated_hours": 120,
            "learning_objectives": [
                "Apply theoretical knowledge in practice",
                "Develop professional relationships", 
                "Complete assigned internship projects"
            ],
            "components": [
                {"type": "assignment", "name": "Weekly Reflection Reports", "minutes": 480},
                {"type": "project", "name": "Final Internship Project", "minutes": 360},
                {"type": "assignment", "name": "Mentor Evaluation", "minutes": 60}
            ]
        }
    ]
    
    for module_data in modules_data:
        # Create module
        module = Module(
            track_id=internship_track.id,
            semester_id=current_semester.id if current_semester else None,
            name=module_data["name"],
            description=module_data["description"],
            order_in_track=module_data["order"],
            estimated_hours=module_data["estimated_hours"],
            learning_objectives=module_data["learning_objectives"],
            is_mandatory=True
        )
        
        db.add(module)
        db.commit()
        db.refresh(module)
        
        # Create components
        for i, comp_data in enumerate(module_data["components"]):
            component = ModuleComponent(
                module_id=module.id,
                type=comp_data["type"],
                name=comp_data["name"],
                order_in_module=i + 1,
                estimated_minutes=comp_data["minutes"],
                is_mandatory=True,
                component_data={
                    "difficulty": "intermediate",
                    "prerequisites": []
                }
            )
            db.add(component)
        
        db.commit()
        print(f"✅ Created module: {module.name}")


def create_coach_modules(db: Session, coach_track: Track, current_semester: Semester):
    """Create modules for LFA Coach track"""
    
    modules_data = [
        {
            "name": "Modern Coaching Philosophy",
            "description": "Contemporary coaching methodologies, leadership principles, and tactical evolution in modern football.",
            "order": 1,
            "estimated_hours": 50,
            "learning_objectives": [
                "Develop personal coaching philosophy",
                "Understand modern tactical trends", 
                "Master leadership techniques"
            ]
        },
        {
            "name": "Tactical Analysis & Game Planning",
            "description": "Advanced tactical analysis, match preparation, and strategic game planning methodologies.",
            "order": 2, 
            "estimated_hours": 70,
            "learning_objectives": [
                "Master video analysis techniques",
                "Create effective game plans",
                "Understand tactical periodization"
            ]
        },
        {
            "name": "Player Psychology & Communication",
            "description": "Sports psychology principles, effective communication strategies, and team dynamics management.",
            "order": 3,
            "estimated_hours": 45,
            "learning_objectives": [
                "Apply sports psychology principles",
                "Develop communication skills",
                "Manage team dynamics effectively"
            ]
        },
        {
            "name": "Training Session Design",
            "description": "Scientific approach to training design, periodization, and performance optimization.",
            "order": 4,
            "estimated_hours": 60,
            "learning_objectives": [
                "Design effective training sessions", 
                "Understand periodization principles",
                "Apply sports science concepts"
            ]
        }
    ]
    
    for module_data in modules_data:
        module = Module(
            track_id=coach_track.id,
            semester_id=current_semester.id if current_semester else None,
            name=module_data["name"],
            description=module_data["description"],
            order_in_track=module_data["order"],
            estimated_hours=module_data["estimated_hours"],
            learning_objectives=module_data["learning_objectives"],
            is_mandatory=True
        )
        
        db.add(module)
        db.commit()
        print(f"✅ Created module: {module.name}")


def create_gancuju_modules(db: Session, gancuju_track: Track, current_semester: Semester):
    """Create modules for GānCuju track"""
    
    modules_data = [
        {
            "name": "Ancient Football Heritage",
            "description": "Historical overview of GānCuju and its influence on modern football development.",
            "order": 1,
            "estimated_hours": 30,
            "learning_objectives": [
                "Understand GānCuju historical significance",
                "Learn traditional techniques and philosophy",
                "Connect ancient wisdom to modern practice"
            ]
        },
        {
            "name": "Traditional Training Methods",
            "description": "Ancient training methodologies adapted for contemporary football development.",
            "order": 2,
            "estimated_hours": 40,
            "learning_objectives": [
                "Master traditional training techniques",
                "Adapt ancient methods for modern use",
                "Integrate cultural elements in coaching"
            ]
        },
        {
            "name": "Cultural Integration Project",
            "description": "Capstone project integrating GānCuju principles into modern football coaching or playing approach.",
            "order": 3,
            "estimated_hours": 50,
            "learning_objectives": [
                "Create innovative integration approach",
                "Present cultural bridge methodology", 
                "Demonstrate practical application"
            ]
        }
    ]
    
    for module_data in modules_data:
        module = Module(
            track_id=gancuju_track.id,
            semester_id=current_semester.id if current_semester else None,
            name=module_data["name"],
            description=module_data["description"],
            order_in_track=module_data["order"],
            estimated_hours=module_data["estimated_hours"],
            learning_objectives=module_data["learning_objectives"],
            is_mandatory=True
        )
        
        db.add(module)
        db.commit()
        print(f"✅ Created module: {module.name}")


def main():
    """Initialize the complete track-based education system"""
    print("🎯 Initializing Track-Based Education System...")
    
    db = next(get_db())
    
    try:
        # Create tracks and certificate templates
        tracks = create_lfa_tracks(db)
        
        # Get current semester
        current_semester = db.query(Semester).order_by(Semester.id.desc()).first()
        
        # Create modules for each track
        for track in tracks:
            if track.code == "INT":
                create_internship_modules(db, track, current_semester)
            elif track.code == "COACH": 
                create_coach_modules(db, track, current_semester)
            elif track.code == "GANCUJU":
                create_gancuju_modules(db, track, current_semester)
        
        print("\n🎉 Track-Based Education System initialized successfully!")
        print(f"✅ Created {len(tracks)} tracks")
        
        # Display summary
        for track in tracks:
            module_count = db.query(Module).filter(Module.track_id == track.id).count()
            print(f"   • {track.name} ({track.code}): {module_count} modules")
    
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()