"""Create Specialization Level System

Revision ID: spec_level_system
Revises: gancuju_license_system
Create Date: 2025-10-09 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'spec_level_system'
down_revision = 'gancuju_license_system'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create level-based progression system for 3 specializations:
    - GanCuju Player (8 levels)
    - LFA Football Coach (8 levels)
    - Startup Spirit Internship (3 levels)
    """

    # 1. Specializations master table
    op.create_table('specializations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('icon', sa.String(10)),
        sa.Column('description', sa.Text),
        sa.Column('max_levels', sa.Integer, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow)
    )

    # 2. Player levels table (8 GanCuju levels)
    op.create_table('player_levels',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(50), nullable=False),
        sa.Column('required_xp', sa.Integer, nullable=False),
        sa.Column('required_sessions', sa.Integer, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('license_title', sa.String(255), nullable=False)
    )

    # 3. Coach levels table (8 LFA coaching levels)
    op.create_table('coach_levels',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('required_xp', sa.Integer, nullable=False),
        sa.Column('required_sessions', sa.Integer, nullable=False),
        sa.Column('theory_hours', sa.Integer, nullable=False),
        sa.Column('practice_hours', sa.Integer, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('license_title', sa.String(255), nullable=False)
    )

    # 4. Internship levels table (3 Startup Spirit levels)
    op.create_table('internship_levels',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('required_xp', sa.Integer, nullable=False),
        sa.Column('required_sessions', sa.Integer, nullable=False),
        sa.Column('total_hours', sa.Integer, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('license_title', sa.String(255), nullable=False)
    )

    # 5. Specialization progress tracking table
    op.create_table('specialization_progress',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('student_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('specialization_id', sa.String(50), sa.ForeignKey('specializations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('current_level', sa.Integer, default=1),
        sa.Column('total_xp', sa.Integer, default=0),
        sa.Column('completed_sessions', sa.Integer, default=0),
        sa.Column('completed_projects', sa.Integer, default=0),
        sa.Column('last_activity', sa.DateTime, default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.UniqueConstraint('student_id', 'specialization_id', name='uq_student_specialization')
    )

    # Create indexes for performance
    op.create_index('ix_specialization_progress_student', 'specialization_progress', ['student_id'])
    op.create_index('ix_specialization_progress_spec', 'specialization_progress', ['specialization_id'])
    op.create_index('ix_specialization_progress_level', 'specialization_progress', ['current_level'])

    # Insert specializations master data
    op.execute("""
        INSERT INTO specializations (id, name, icon, description, max_levels) VALUES
        ('PLAYER', 'GanCuju Player', '⚽', 'GanCuju sport versenyző képzés - bambusz tanítvány-tól sárkány bölcsességig', 8),
        ('COACH', 'LFA Football Coach', '👨‍🏫', 'LFA edzői licensz program - Pre Football-tól PRO szintig', 8),
        ('INTERNSHIP', 'Startup Spirit Intern', '🚀', 'Innovatív startup gyakornoki program - Explorer-től Leader szintig', 3)
    """)

    # Insert player levels (8 GanCuju belt levels)
    op.execute("""
        INSERT INTO player_levels (id, name, color, required_xp, required_sessions, description, license_title) VALUES
        (1, 'Bambusz Tanítvány', 'Fehér', 12000, 10, 'Alapmozgások, Ganball™️ ismeret, játékszabályok', 'GanCuju™️ Bambusz Tanítvány Digitális Igazolvány'),
        (2, 'Hajnali Harmat', 'Sárga', 25000, 12, 'Alapvető technikák, taktikai bevezetés, csapatjáték', 'GanCuju™️ Hajnali Harmat Digitális Igazolvány'),
        (3, 'Rugalmas Nád', 'Zöld', 45000, 15, 'Komplex mozdulatok, alapvető stratégiák, egyéni képességek', 'GanCuju™️ Rugalmas Nád Digitális Igazolvány'),
        (4, 'Égi Folyó', 'Kék', 70000, 18, 'Fejlett technikák, versenyezési tapasztalat, taktikai tudatosság', 'GanCuju™️ Égi Folyó Digitális Igazolvány'),
        (5, 'Erős Gyökér', 'Barna', 100000, 20, 'Magas szintű mozgásformák, mentorálás, leadership', 'GanCuju™️ Erős Gyökér Digitális Igazolvány'),
        (6, 'Téli Hold', 'Sötétszürke', 140000, 22, 'Oktatási alapok, versenyeredmények, szakmai fejlődés', 'GanCuju™️ Téli Hold Digitális Igazolvány'),
        (7, 'Éjfél Őrzője', 'Fekete', 190000, 25, 'Oktatói licensz, módszertani szakértelem, advanced technikák', 'GanCuju™️ Éjfél Őrzője Digitális Igazolvány'),
        (8, 'Sárkány Bölcsesség', 'Vörös', 250000, 30, 'Innovációs képesség, sport fejlesztés, nagymesteri szint', 'GanCuju™️ Sárkány Bölcsesség NAGYMESTERI Digitális Igazolvány')
    """)

    # Insert coach levels (8 LFA coaching licensz levels)
    op.execute("""
        INSERT INTO coach_levels (id, name, required_xp, required_sessions, theory_hours, practice_hours, description, license_title) VALUES
        (1, 'LFA Pre Football Asszisztens Edző', 15000, 15, 30, 50, 'Asszisztensi alapok, Ganball™️ módszertan, óvodás korosztály', 'LFA Pre Football Asszisztens Edző Digitális Licensz'),
        (2, 'LFA Pre Football Vezetőedző', 35000, 18, 40, 60, 'Edzéstervezés, csapatvezetés, 4-7 éves korosztály', 'LFA Pre Football Vezetőedző Digitális Licensz'),
        (3, 'LFA Youth Football Asszisztens Edző', 60000, 20, 35, 55, 'Korosztályos módszertan, tehetségazonosítás, U8-U12', 'LFA Youth Football Asszisztens Edző Digitális Licensz'),
        (4, 'LFA Youth Football Vezetőedző', 90000, 22, 45, 65, 'Ifjúsági program vezetése, komplex fejlesztés, U8-U16', 'LFA Youth Football Vezetőedző Digitális Licensz'),
        (5, 'LFA Amateur Football Asszisztens Edző', 130000, 25, 40, 60, 'Felnőtt futball alapok, amatőr szint, taktikai elemzés', 'LFA Amateur Football Asszisztens Edző Digitális Licensz'),
        (6, 'LFA Amateur Football Vezetőedző', 180000, 28, 35, 55, 'Amatőr program vezetése, mérkőzéselemzés, stratégiai tervezés', 'LFA Amateur Football Vezetőedző Digitális Licensz'),
        (7, 'LFA PRO Football Asszisztens Edző', 240000, 30, 50, 70, 'Professzionális futball, advanced analytics, high performance', 'LFA PRO Football Asszisztens Edző Digitális Licensz'),
        (8, 'LFA PRO Football Vezetőedző', 320000, 35, 60, 80, 'Teljes professzionális program, nemzetközi szint, szakmai innováció', 'LFA PRO Football Vezetőedző MESTER SZINTŰ Digitális Licensz')
    """)

    # Insert internship levels (3 Startup Spirit levels)
    op.execute("""
        INSERT INTO internship_levels (id, name, required_xp, required_sessions, total_hours, description, license_title) VALUES
        (1, 'Startup Explorer', 10000, 15, 80, 'Startup mindset, LFA ecosystem, agile basics, team collaboration', 'LFA Startup Explorer Digitális Igazolvány'),
        (2, 'Growth Hacker', 18000, 18, 120, 'Growth marketing, data-driven decisions, MVP testing, customer development', 'LFA Growth Hacker Digitális Igazolvány'),
        (3, 'Startup Leader', 28000, 22, 130, 'Entrepreneurial leadership, global expansion, fundraising, exit strategies', 'LFA Startup Leader MESTER SZINTŰ Digitális Igazolvány')
    """)


def downgrade():
    # Drop indexes
    op.drop_index('ix_specialization_progress_level', table_name='specialization_progress')
    op.drop_index('ix_specialization_progress_spec', table_name='specialization_progress')
    op.drop_index('ix_specialization_progress_student', table_name='specialization_progress')

    # Drop tables in reverse order
    op.drop_table('specialization_progress')
    op.drop_table('internship_levels')
    op.drop_table('coach_levels')
    op.drop_table('player_levels')
    op.drop_table('specializations')
