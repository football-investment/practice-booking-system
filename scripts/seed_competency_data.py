"""
Seed Competency Categories, Skills, and Milestones
Run with: python scripts/seed_competency_data.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from sqlalchemy import text

def seed_competency_data():
    db = SessionLocal()

    try:
        print("🎯 Seeding competency system...")

        # ==========================================
        # PLAYER COMPETENCIES (GanCuju)
        # ==========================================
        print("\n📊 Creating PLAYER competencies...")

        db.execute(text("""
            INSERT INTO competency_categories (specialization_id, name, description, icon, weight, display_order)
            VALUES
            ('PLAYER', 'Technical Skills', 'Ball control, first touch, passing, shooting technique', '⚽', 1.5, 1),
            ('PLAYER', 'Tactical Understanding', 'Game awareness, positioning, decision making', '🧠', 1.0, 2),
            ('PLAYER', 'Physical Fitness', 'Speed, agility, endurance, strength', '💪', 0.8, 3),
            ('PLAYER', 'Mental Strength', 'Focus, resilience, confidence, pressure handling', '🎯', 1.2, 4)
        """))

        # Get category IDs
        categories = db.execute(text("SELECT id, name FROM competency_categories WHERE specialization_id = 'PLAYER' ORDER BY display_order")).fetchall()
        category_map = {cat[1]: cat[0] for cat in categories}

        # Technical Skills breakdown
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({category_map['Technical Skills']}, 'First Touch', 'Ball control on first contact', 1),
            ({category_map['Technical Skills']}, 'Passing Accuracy', 'Precise short and long passes', 2),
            ({category_map['Technical Skills']}, 'Shooting Technique', 'Power and accuracy in shots', 3),
            ({category_map['Technical Skills']}, 'Dribbling', 'Close ball control while moving', 4)
        """))

        # Tactical Understanding breakdown
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({category_map['Tactical Understanding']}, 'Spatial Awareness', 'Understanding of field positioning', 1),
            ({category_map['Tactical Understanding']}, 'Reading the Game', 'Anticipating opponent and teammate movements', 2),
            ({category_map['Tactical Understanding']}, 'Decision Making', 'Making quick, effective choices under pressure', 3)
        """))

        # Physical Fitness breakdown
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({category_map['Physical Fitness']}, 'Speed & Agility', 'Quick movements and direction changes', 1),
            ({category_map['Physical Fitness']}, 'Endurance', 'Sustained performance over time', 2),
            ({category_map['Physical Fitness']}, 'Strength', 'Physical power and stability', 3)
        """))

        # Mental Strength breakdown
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({category_map['Mental Strength']}, 'Focus & Concentration', 'Maintaining attention throughout activity', 1),
            ({category_map['Mental Strength']}, 'Resilience', 'Bouncing back from setbacks', 2),
            ({category_map['Mental Strength']}, 'Confidence', 'Self-belief in abilities', 3)
        """))

        # Milestones for each category
        for cat_name, cat_id in category_map.items():
            db.execute(text(f"""
                INSERT INTO competency_milestones (competency_category_id, level, level_name, required_score, description, badge_icon, xp_reward)
                VALUES
                ({cat_id}, 1, 'Beginner', 0, 'Starting to develop {cat_name.lower()} abilities', '🥉', 100),
                ({cat_id}, 2, 'Developing', 40, 'Showing improvement in {cat_name.lower()}', '🥈', 200),
                ({cat_id}, 3, 'Competent', 60, 'Solid {cat_name.lower()} foundation', '🥇', 300),
                ({cat_id}, 4, 'Proficient', 80, 'Advanced {cat_name.lower()}', '💎', 500),
                ({cat_id}, 5, 'Expert', 95, 'Mastery of {cat_name.lower()}', '👑', 1000)
            """))

        print("  ✅ PLAYER competencies created")

        # ==========================================
        # COACH COMPETENCIES (LFA License)
        # ==========================================
        print("\n📊 Creating COACH competencies...")

        db.execute(text("""
            INSERT INTO competency_categories (specialization_id, name, description, icon, weight, display_order)
            VALUES
            ('COACH', 'Training Design', 'Ability to plan effective, engaging training sessions', '📋', 1.5, 1),
            ('COACH', 'Communication', 'Clear instructions, feedback, and motivation', '🗣️', 1.3, 2),
            ('COACH', 'Leadership', 'Team management, decision-making, inspiration', '👨‍🏫', 1.2, 3),
            ('COACH', 'Technical Knowledge', 'Deep understanding of tactics, techniques, and game principles', '🧠', 1.0, 4)
        """))

        # Get coach category IDs
        coach_categories = db.execute(text("SELECT id, name FROM competency_categories WHERE specialization_id = 'COACH' ORDER BY display_order")).fetchall()
        coach_map = {cat[1]: cat[0] for cat in coach_categories}

        # Training Design skills
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({coach_map['Training Design']}, 'Session Planning', 'Structured, progressive training plans', 1),
            ({coach_map['Training Design']}, 'Drill Design', 'Creative, effective practice exercises', 2),
            ({coach_map['Training Design']}, 'Time Management', 'Efficient use of training time', 3)
        """))

        # Communication skills
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({coach_map['Communication']}, 'Verbal Communication', 'Clear, concise instructions', 1),
            ({coach_map['Communication']}, 'Feedback Quality', 'Constructive, actionable feedback', 2),
            ({coach_map['Communication']}, 'Motivation', 'Inspiring and energizing players', 3)
        """))

        # Leadership skills
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({coach_map['Leadership']}, 'Team Management', 'Organizing and directing groups', 1),
            ({coach_map['Leadership']}, 'Decision Making', 'Quick, strategic choices', 2),
            ({coach_map['Leadership']}, 'Conflict Resolution', 'Managing disputes effectively', 3)
        """))

        # Milestones for coach categories
        for cat_name, cat_id in coach_map.items():
            db.execute(text(f"""
                INSERT INTO competency_milestones (competency_category_id, level, level_name, required_score, description, badge_icon, xp_reward)
                VALUES
                ({cat_id}, 1, 'Beginner', 0, 'Starting coaching journey in {cat_name.lower()}', '🥉', 150),
                ({cat_id}, 2, 'Developing', 40, 'Building coaching skills in {cat_name.lower()}', '🥈', 250),
                ({cat_id}, 3, 'Competent', 60, 'Confident coaching in {cat_name.lower()}', '🥇', 400),
                ({cat_id}, 4, 'Proficient', 80, 'Advanced coaching skills in {cat_name.lower()}', '💎', 600),
                ({cat_id}, 5, 'Expert', 95, 'Mastery of coaching {cat_name.lower()}', '👑', 1200)
            """))

        print("  ✅ COACH competencies created")

        # ==========================================
        # INTERNSHIP COMPETENCIES
        # ==========================================
        print("\n📊 Creating INTERNSHIP competencies...")

        db.execute(text("""
            INSERT INTO competency_categories (specialization_id, name, description, icon, weight, display_order)
            VALUES
            ('INTERNSHIP', 'Professional Skills', 'Office operations, project management, communication', '💼', 1.0, 1),
            ('INTERNSHIP', 'Digital Competency', 'Technology tools, digital communication, data analysis', '💻', 1.0, 2),
            ('INTERNSHIP', 'Collaboration', 'Teamwork, networking, relationship building', '🤝', 1.0, 3),
            ('INTERNSHIP', 'Initiative & Growth', 'Proactivity, problem-solving, learning mindset', '🚀', 1.2, 4)
        """))

        # Get internship category IDs
        intern_categories = db.execute(text("SELECT id, name FROM competency_categories WHERE specialization_id = 'INTERNSHIP' ORDER BY display_order")).fetchall()
        intern_map = {cat[1]: cat[0] for cat in intern_categories}

        # Professional Skills
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({intern_map['Professional Skills']}, 'Email Etiquette', 'Professional written communication', 1),
            ({intern_map['Professional Skills']}, 'Meeting Participation', 'Active, productive meeting engagement', 2),
            ({intern_map['Professional Skills']}, 'Time Management', 'Efficient task prioritization', 3)
        """))

        # Digital Competency
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({intern_map['Digital Competency']}, 'Spreadsheet Proficiency', 'Excel/Google Sheets mastery', 1),
            ({intern_map['Digital Competency']}, 'Presentation Skills', 'Creating compelling slideshows', 2),
            ({intern_map['Digital Competency']}, 'Data Analysis', 'Basic analytics and insights', 3)
        """))

        # Collaboration
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({intern_map['Collaboration']}, 'Teamwork', 'Effective group collaboration', 1),
            ({intern_map['Collaboration']}, 'Networking', 'Building professional relationships', 2),
            ({intern_map['Collaboration']}, 'Peer Feedback', 'Giving and receiving constructive input', 3)
        """))

        # Initiative & Growth
        db.execute(text(f"""
            INSERT INTO competency_skills (competency_category_id, name, description, display_order)
            VALUES
            ({intern_map['Initiative & Growth']}, 'Proactivity', 'Taking initiative without prompting', 1),
            ({intern_map['Initiative & Growth']}, 'Problem Solving', 'Finding creative solutions', 2),
            ({intern_map['Initiative & Growth']}, 'Learning Mindset', 'Embracing challenges and feedback', 3)
        """))

        # Milestones for internship categories
        for cat_name, cat_id in intern_map.items():
            db.execute(text(f"""
                INSERT INTO competency_milestones (competency_category_id, level, level_name, required_score, description, badge_icon, xp_reward)
                VALUES
                ({cat_id}, 1, 'Beginner', 0, 'Starting professional journey in {cat_name.lower()}', '🥉', 100),
                ({cat_id}, 2, 'Developing', 40, 'Growing skills in {cat_name.lower()}', '🥈', 200),
                ({cat_id}, 3, 'Competent', 60, 'Competent professional in {cat_name.lower()}', '🥇', 350),
                ({cat_id}, 4, 'Proficient', 80, 'Advanced proficiency in {cat_name.lower()}', '💎', 550),
                ({cat_id}, 5, 'Expert', 95, 'Expert level {cat_name.lower()}', '👑', 1100)
            """))

        print("  ✅ INTERNSHIP competencies created")

        db.commit()

        # Summary
        total_categories = db.execute(text("SELECT COUNT(*) FROM competency_categories")).scalar()
        total_skills = db.execute(text("SELECT COUNT(*) FROM competency_skills")).scalar()
        total_milestones = db.execute(text("SELECT COUNT(*) FROM competency_milestones")).scalar()

        print(f"\n🎉 Competency System Seeded Successfully!")
        print(f"   📊 {total_categories} categories")
        print(f"   🎯 {total_skills} skills")
        print(f"   🏆 {total_milestones} milestones")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_competency_data()
