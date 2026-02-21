"""Add GānCuju™️©️ license system with marketing narratives

Revision ID: gancuju_license_system  
Revises: aae67fe19f8d_add_internship_specialization_type
Create Date: 2025-09-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'gancuju_license_system'
down_revision = 'aae67fe19f8d'
branch_labels = None
depends_on = None


def upgrade():
    # Create license_metadata table for marketing-oriented license system
    op.create_table('license_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('specialization_type', sa.String(length=20), nullable=False),
        sa.Column('level_code', sa.String(length=50), nullable=False),
        sa.Column('level_number', sa.Integer(), nullable=False),
        
        # Display Information
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('title_en', sa.String(length=100)),
        sa.Column('subtitle', sa.String(length=200)),
        sa.Column('color_primary', sa.String(length=7), nullable=False),
        sa.Column('color_secondary', sa.String(length=7)),
        sa.Column('icon_emoji', sa.String(length=10)),
        sa.Column('icon_symbol', sa.String(length=50)),
        
        # Marketing Content
        sa.Column('marketing_narrative', sa.Text()),
        sa.Column('cultural_context', sa.Text()),
        sa.Column('philosophy', sa.Text()),
        
        # Visual Assets
        sa.Column('background_gradient', sa.String(length=200)),
        sa.Column('css_class', sa.String(length=50)),
        sa.Column('image_url', sa.String(length=500)),
        
        # Requirements
        sa.Column('advancement_criteria', postgresql.JSONB()),
        sa.Column('time_requirement_hours', sa.Integer()),
        sa.Column('project_requirements', postgresql.JSONB()),
        sa.Column('evaluation_criteria', postgresql.JSONB()),
        
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('specialization_type', 'level_code'),
        sa.UniqueConstraint('specialization_type', 'level_number')
    )
    
    # Create user_licenses table for tracking user license progression
    op.create_table('user_licenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('specialization_type', sa.String(length=20), nullable=False),
        sa.Column('current_level', sa.Integer(), nullable=False, default=1),
        sa.Column('max_achieved_level', sa.Integer(), nullable=False, default=1),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('last_advanced_at', sa.DateTime()),
        sa.Column('instructor_notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'specialization_type')
    )
    
    # Create license_progressions table for tracking advancement history
    op.create_table('license_progressions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_license_id', sa.Integer(), nullable=False),
        sa.Column('from_level', sa.Integer(), nullable=False),
        sa.Column('to_level', sa.Integer(), nullable=False),
        sa.Column('advanced_by', sa.Integer()),
        sa.Column('advancement_reason', sa.Text()),
        sa.Column('requirements_met', sa.Text()),
        sa.Column('advanced_at', sa.DateTime(), server_default=sa.text('now()')),
        
        sa.ForeignKeyConstraint(['user_license_id'], ['user_licenses.id']),
        sa.ForeignKeyConstraint(['advanced_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert Coach LFA license metadata
    coach_levels = [
        (1, 'coach_lfa_pre_assistant', 'LFA Pre Football Asszisztens Edző', 'LFA Pre Football Assistant Coach', 'Kezdő edzői szint', '#8B7355', '#D2B48C', '🥉', 'coach-pre', 40),
        (2, 'coach_lfa_pre_head', 'LFA Pre Football Vezetőedző', 'LFA Pre Football Head Coach', 'Pre kategória vezetői szint', '#A0522D', '#DEB887', '🏆', 'coach-pre-head', 80),
        (3, 'coach_lfa_youth_assistant', 'LFA Youth Football Asszisztens Edző', 'LFA Youth Football Assistant Coach', 'Utánpótlás edzői szint', '#228B22', '#90EE90', '⚽', 'coach-youth', 120),
        (4, 'coach_lfa_youth_head', 'LFA Youth Football Vezetőedző', 'LFA Youth Football Head Coach', 'Utánpótlás vezetői szint', '#32CD32', '#98FB98', '🌟', 'coach-youth-head', 160),
        (5, 'coach_lfa_amateur_assistant', 'LFA Amateur Football Asszisztens Edző', 'LFA Amateur Football Assistant Coach', 'Amateur edzői szint', '#4169E1', '#87CEEB', '🎯', 'coach-amateur', 200),
        (6, 'coach_lfa_amateur_head', 'LFA Amateur Football Vezetőedző', 'LFA Amateur Football Head Coach', 'Amateur vezetői szint', '#1E90FF', '#B0E0E6', '👑', 'coach-amateur-head', 250),
        (7, 'coach_lfa_pro_assistant', 'LFA PRO Football Asszisztens Edző', 'LFA PRO Football Assistant Coach', 'Profi edzői szint', '#8A2BE2', '#DDA0DD', '💎', 'coach-pro', 300),
        (8, 'coach_lfa_pro_head', 'LFA PRO Football Vezetőedző', 'LFA PRO Football Head Coach', 'Profi vezetői szint', '#9932CC', '#E6E6FA', '🏅', 'coach-pro-head', 400)
    ]
    
    for level_num, code, title, title_en, subtitle, color1, color2, icon, css_class, hours in coach_levels:
        op.execute(f"""
            INSERT INTO license_metadata (
                specialization_type, level_code, level_number, title, title_en, subtitle,
                color_primary, color_secondary, icon_emoji, css_class, time_requirement_hours,
                background_gradient, marketing_narrative
            ) VALUES (
                'COACH', '{code}', {level_num}, '{title}', '{title_en}', '{subtitle}',
                '{color1}', '{color2}', '{icon}', '{css_class}', {hours},
                'linear-gradient(135deg, {color1}, {color2})',
                'LFA szakmai fejlődési útvonal - {subtitle.lower()}'
            )
        """)
    
    # Insert Player GānCuju license metadata
    player_levels = [
        (1, 'player_bamboo_student', 'Bambusz Tanítvány', 'Bamboo Student', 'A rugalmasság első leckéi', '#F8F8FF', '#E6E6FA', '🤍', 'player-white', 'A fiatal bambusz hajlik, de nem törik. Itt kezdődik a 4000 éves hagyomány utazása.'),
        (2, 'player_morning_dew', 'Hajnali Harmat', 'Morning Dew', 'Frissítő energia és új technikák', '#FFD700', '#FFFFE0', '💛', 'player-yellow', 'Mint a hajnali harmat frissíti a bambuszerdőt, úgy hoz új energiát képességeidbe ez a szint.'),
        (3, 'player_flexible_reed', 'Rugalmas Nád', 'Flexible Reed', 'Harmónia és alkalmazkodóképesség', '#228B22', '#98FB98', '💚', 'player-green', 'A szélben táncoló nád tanítása - tested és elméd megtanul áramlani a játékban.'),
        (4, 'player_sky_river', 'Égi Folyó', 'Sky River', 'Folyékony játék és intuíció', '#4169E1', '#87CEFA', '💙', 'player-blue', 'Játékod folyékonnyá válik, mint a nagy kínai folyók áramlása. Az intuíció és reflexek felgyorsulnak.'),
        (5, 'player_strong_root', 'Erős Gyökér', 'Strong Root', 'Mély tudás és mentorálás', '#8B4513', '#DEB887', '🤎', 'player-brown', 'A tradíció őrzőjévé válsz. Tudásodat megosztva a 4000 éves lánc újabb szemévé válsz.'),
        (6, 'player_winter_moon', 'Téli Hold', 'Winter Moon', 'Oktatási kiválóság és versenyeredmények', '#2F4F4F', '#A9A9A9', '🩶', 'player-gray', 'A Téli Hold fénye még a legsötétebb éjszakát is megvilágítja - ahogy te is feltárod a rejtett dimenziókat.'),
        (7, 'player_midnight_guardian', 'Éjfél Őrzője', 'Midnight Guardian', 'Módszertani szakértelem és licensz', '#000000', '#404040', '🖤', 'player-black', 'Beavatás a legmélyebb titkokba. Játékod művészetnek tűnik, módszertaned évezredes tudást ötvöz.'),
        (8, 'player_dragon_wisdom', 'Sárkány Bölcsesség', 'Dragon Wisdom', 'Innováció és legendás státusz', '#DC143C', '#FFB6C1', '❤️', 'player-red', 'A GānCuju™️©️ legmagasabb csúcsa. Élő legendává válsz, tradíció és innováció tökéletes egyensúlyában.')
    ]
    
    for level_num, code, title, title_en, subtitle, color1, color2, icon, css_class, narrative in player_levels:
        op.execute(f"""
            INSERT INTO license_metadata (
                specialization_type, level_code, level_number, title, title_en, subtitle,
                color_primary, color_secondary, icon_emoji, css_class,
                background_gradient, marketing_narrative, cultural_context
            ) VALUES (
                'PLAYER', '{code}', {level_num}, '{title}', '{title_en}', '{subtitle}',
                '{color1}', '{color2}', '{icon}', '{css_class}',
                'linear-gradient(135deg, {color1}, {color2})',
                '{narrative}',
                'GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer'
            )
        """)
    
    # Insert Intern IT license metadata
    intern_levels = [
        (1, 'intern_junior', 'Junior Intern', 'Junior Intern', 'IT karrier első lépései', '#20B2AA', '#AFEEEE', '🔰', 'intern-junior', 80),
        (2, 'intern_mid_level', 'Mid-level Intern', 'Mid-level Intern', 'Növekvő technikai kompetencia', '#FF6347', '#FFA07A', '📈', 'intern-mid', 160),
        (3, 'intern_senior', 'Senior Intern', 'Senior Intern', 'Haladó szakmai készségek', '#9932CC', '#DDA0DD', '🎯', 'intern-senior', 240),
        (4, 'intern_lead', 'Lead Intern', 'Lead Intern', 'Vezetői szerepkör és projektirányítás', '#FF8C00', '#FFE4B5', '👑', 'intern-lead', 320),
        (5, 'intern_principal', 'Principal Intern', 'Principal Intern', 'Strategiai szintű technikai vezetés', '#B22222', '#F0E68C', '🚀', 'intern-principal', 400)
    ]
    
    for level_num, code, title, title_en, subtitle, color1, color2, icon, css_class, hours in intern_levels:
        op.execute(f"""
            INSERT INTO license_metadata (
                specialization_type, level_code, level_number, title, title_en, subtitle,
                color_primary, color_secondary, icon_emoji, css_class, time_requirement_hours,
                background_gradient, marketing_narrative
            ) VALUES (
                'INTERNSHIP', '{code}', {level_num}, '{title}', '{title_en}', '{subtitle}',
                '{color1}', '{color2}', '{icon}', '{css_class}', {hours},
                'linear-gradient(135deg, {color1}, {color2})',
                'Nemzetközi IT karrierpálya - {subtitle.lower()}'
            )
        """)


def downgrade():
    op.drop_table('license_progressions')
    op.drop_table('user_licenses')
    op.drop_table('license_metadata')