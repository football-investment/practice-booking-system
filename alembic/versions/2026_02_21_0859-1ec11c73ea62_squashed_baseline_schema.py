"""squashed_baseline_schema

Revision ID: 1ec11c73ea62
Revises:
Create Date: 2026-02-21 08:59:01.173343

MIGRATION SQUASH - Canonical baseline schema
==============================================
All historical migrations (2025-08-01 → 2026-02-21) have been squashed into this single
baseline migration. This represents the complete, production-ready schema as of 2026-02-21.

Previous migration history archived in: alembic/versions_legacy/

This migration creates:
- All enum types
- All tables with constraints, indexes, foreign keys
- All comments and metadata

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1ec11c73ea62'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create complete baseline schema.
    Uses raw SQL from pg_dump to ensure exact schema reproduction.
    """
    # Execute complete schema DDL
    op.execute("""
        CREATE TYPE public.applicationstatus AS ENUM (
            'PENDING',
            'ACCEPTED',
            'DECLINED'
        );

        CREATE TYPE public.assignmentrequeststatus AS ENUM (
            'PENDING',
            'ACCEPTED',
            'DECLINED',
            'CANCELLED',
            'EXPIRED'
        );

        CREATE TYPE public.attendancestatus AS ENUM (
            'present',
            'absent',
            'late',
            'excused'
        );

        CREATE TYPE public.bookingstatus AS ENUM (
            'PENDING',
            'CONFIRMED',
            'CANCELLED',
            'WAITLISTED'
        );

        CREATE TYPE public.confirmationstatus AS ENUM (
            'pending_confirmation',
            'confirmed',
            'disputed'
        );

        CREATE TYPE public.coupontype AS ENUM (
            'BONUS_CREDITS',
            'PURCHASE_DISCOUNT_PERCENT',
            'PURCHASE_BONUS_CREDITS',
            'PERCENT',
            'FIXED',
            'CREDITS'
        );

        CREATE TYPE public.enrollmentstatus AS ENUM (
            'PENDING',
            'APPROVED',
            'REJECTED',
            'WITHDRAWN'
        );

        CREATE TYPE public.locationtype AS ENUM (
            'PARTNER',
            'CENTER'
        );

        CREATE TYPE public.masterofferstatus AS ENUM (
            'OFFERED',
            'ACCEPTED',
            'DECLINED',
            'EXPIRED'
        );

        CREATE TYPE public.messagepriority AS ENUM (
            'LOW',
            'NORMAL',
            'HIGH',
            'URGENT'
        );

        CREATE TYPE public.moduleprogressstatus AS ENUM (
            'NOT_STARTED',
            'IN_PROGRESS',
            'COMPLETED',
            'FAILED'
        );

        CREATE TYPE public.notificationtype AS ENUM (
            'BOOKING_CONFIRMED',
            'BOOKING_CANCELLED',
            'SESSION_REMINDER',
            'SESSION_CANCELLED',
            'WAITLIST_PROMOTED',
            'GENERAL',
            'JOB_OFFER',
            'OFFER_ACCEPTED',
            'OFFER_DECLINED',
            'TOURNAMENT_APPLICATION_APPROVED',
            'TOURNAMENT_APPLICATION_REJECTED',
            'TOURNAMENT_DIRECT_INVITATION',
            'TOURNAMENT_INSTRUCTOR_ACCEPTED',
            'TOURNAMENT_INSTRUCTOR_DECLINED'
        );

        CREATE TYPE public.positionstatus AS ENUM (
            'OPEN',
            'FILLED',
            'CLOSED',
            'CANCELLED'
        );

        CREATE TYPE public.questiontype AS ENUM (
            'MULTIPLE_CHOICE',
            'TRUE_FALSE',
            'FILL_IN_BLANK',
            'MATCHING',
            'SHORT_ANSWER',
            'LONG_ANSWER',
            'CALCULATION',
            'SCENARIO_BASED'
        );

        CREATE TYPE public.quizcategory AS ENUM (
            'GENERAL',
            'MARKETING',
            'ECONOMICS',
            'INFORMATICS',
            'SPORTS_PHYSIOLOGY',
            'NUTRITION',
            'LESSON'
        );

        CREATE TYPE public.quizdifficulty AS ENUM (
            'EASY',
            'MEDIUM',
            'HARD'
        );

        CREATE TYPE public.semester_status AS ENUM (
            'DRAFT',
            'SEEKING_INSTRUCTOR',
            'INSTRUCTOR_ASSIGNED',
            'READY_FOR_ENROLLMENT',
            'ONGOING',
            'COMPLETED',
            'CANCELLED'
        );

        CREATE TYPE public.sessiontype AS ENUM (
            'on_site',
            'virtual',
            'hybrid'
        );

        CREATE TYPE public.specializationtype AS ENUM (
            'GANCUJU_PLAYER',
            'LFA_FOOTBALL_PLAYER',
            'LFA_COACH',
            'INTERNSHIP',
            'LFA_PLAYER_PRE',
            'LFA_PLAYER_YOUTH',
            'LFA_PLAYER_AMATEUR',
            'LFA_PLAYER_PRO',
            'LFA_PLAYER_PRE_ACADEMY',
            'LFA_PLAYER_YOUTH_ACADEMY',
            'LFA_PLAYER_AMATEUR_ACADEMY',
            'LFA_PLAYER_PRO_ACADEMY'
        );

        CREATE TYPE public.systemeventlevel AS ENUM (
            'INFO',
            'WARNING',
            'SECURITY'
        );

        CREATE TYPE public.tournament_phase_enum AS ENUM (
            'GROUP_STAGE',
            'KNOCKOUT',
            'FINALS',
            'PLACEMENT',
            'INDIVIDUAL_RANKING',
            'SWISS'
        );

        CREATE TYPE public.trackprogressstatus AS ENUM (
            'ENROLLED',
            'ACTIVE',
            'COMPLETED',
            'SUSPENDED',
            'DROPPED'
        );

        CREATE TYPE public.userrole AS ENUM (
            'ADMIN',
            'INSTRUCTOR',
            'STUDENT'
        );

        CREATE TABLE public.achievements (
            id integer NOT NULL,
            code character varying(50) NOT NULL,
            name character varying(100) NOT NULL,
            description text,
            icon character varying(10),
            xp_reward integer,
            category character varying(50) NOT NULL,
            requirements json,
            is_active boolean,
            created_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.achievements_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.achievements_id_seq OWNED BY public.achievements.id;

        CREATE TABLE public.adaptive_learning_sessions (
            id integer NOT NULL,
            user_id integer NOT NULL,
            category public.quizcategory NOT NULL,
            started_at timestamp with time zone DEFAULT now(),
            ended_at timestamp with time zone,
            questions_presented integer,
            questions_correct integer,
            xp_earned integer,
            target_difficulty double precision,
            performance_trend double precision,
            session_time_limit_seconds integer,
            session_start_time timestamp with time zone
        );

        CREATE SEQUENCE public.adaptive_learning_sessions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.adaptive_learning_sessions_id_seq OWNED BY public.adaptive_learning_sessions.id;

        CREATE TABLE public.attendance (
            id integer NOT NULL,
            user_id integer NOT NULL,
            session_id integer NOT NULL,
            booking_id integer,
            status public.attendancestatus,
            check_in_time timestamp without time zone,
            check_out_time timestamp without time zone,
            notes character varying,
            marked_by integer,
            confirmation_status public.confirmationstatus,
            student_confirmed_at timestamp without time zone,
            dispute_reason character varying,
            pending_change_to character varying,
            change_requested_by integer,
            change_requested_at timestamp without time zone,
            change_request_reason character varying,
            xp_earned integer,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        COMMENT ON COLUMN public.attendance.xp_earned IS 'XP earned for this attendance';

        CREATE TABLE public.attendance_history (
            id integer NOT NULL,
            attendance_id integer NOT NULL,
            changed_by integer NOT NULL,
            change_type character varying NOT NULL,
            old_value character varying,
            new_value character varying NOT NULL,
            reason character varying,
            created_at timestamp without time zone
        );

        CREATE SEQUENCE public.attendance_history_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.attendance_history_id_seq OWNED BY public.attendance_history.id;

        CREATE SEQUENCE public.attendance_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.attendance_id_seq OWNED BY public.attendance.id;

        CREATE TABLE public.audit_logs (
            id integer NOT NULL,
            user_id integer,
            action character varying(100) NOT NULL,
            resource_type character varying(50),
            resource_id integer,
            details json,
            ip_address character varying(50),
            user_agent character varying(500),
            request_method character varying(10),
            request_path character varying(500),
            status_code integer,
            "timestamp" timestamp with time zone DEFAULT now() NOT NULL
        );

        CREATE SEQUENCE public.audit_logs_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;

        CREATE TABLE public.belt_promotions (
            id integer NOT NULL,
            user_license_id integer NOT NULL,
            from_belt character varying(50),
            to_belt character varying(50) NOT NULL,
            promoted_by integer NOT NULL,
            promoted_at timestamp with time zone DEFAULT now() NOT NULL,
            notes text,
            exam_score integer,
            exam_notes text
        );

        CREATE SEQUENCE public.belt_promotions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.belt_promotions_id_seq OWNED BY public.belt_promotions.id;

        CREATE TABLE public.bookings (
            id integer NOT NULL,
            user_id integer NOT NULL,
            session_id integer NOT NULL,
            status public.bookingstatus,
            waitlist_position integer,
            notes character varying,
            created_at timestamp without time zone,
            updated_at timestamp without time zone,
            cancelled_at timestamp without time zone,
            attended_status character varying(20),
            enrollment_id integer
        );

        CREATE SEQUENCE public.bookings_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.bookings_id_seq OWNED BY public.bookings.id;

        CREATE TABLE public.campus_schedule_configs (
            id integer NOT NULL,
            tournament_id integer NOT NULL,
            campus_id integer NOT NULL,
            match_duration_minutes integer,
            break_duration_minutes integer,
            parallel_fields integer,
            venue_label character varying(100),
            is_active boolean NOT NULL,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL,
            CONSTRAINT ck_csc_break_duration_max CHECK ((break_duration_minutes <= 120)),
            CONSTRAINT ck_csc_break_duration_min CHECK ((break_duration_minutes >= 0)),
            CONSTRAINT ck_csc_match_duration_max CHECK ((match_duration_minutes <= 480)),
            CONSTRAINT ck_csc_match_duration_min CHECK ((match_duration_minutes >= 1)),
            CONSTRAINT ck_csc_parallel_fields_max CHECK ((parallel_fields <= 20)),
            CONSTRAINT ck_csc_parallel_fields_min CHECK ((parallel_fields >= 1))
        );

        COMMENT ON COLUMN public.campus_schedule_configs.tournament_id IS 'Tournament (Semester) this campus schedule config belongs to';

        COMMENT ON COLUMN public.campus_schedule_configs.campus_id IS 'Campus this schedule config applies to';

        COMMENT ON COLUMN public.campus_schedule_configs.match_duration_minutes IS 'Duration of each match in minutes for this campus. NULL = use TournamentConfiguration.match_duration_minutes global default.';

        COMMENT ON COLUMN public.campus_schedule_configs.break_duration_minutes IS 'Break between matches in minutes for this campus. NULL = use TournamentConfiguration.break_duration_minutes global default.';

        COMMENT ON COLUMN public.campus_schedule_configs.parallel_fields IS 'Number of parallel pitches/courts at this campus. NULL = use TournamentConfiguration.parallel_fields global default.';

        COMMENT ON COLUMN public.campus_schedule_configs.venue_label IS 'Human-readable venue label for this campus in this tournament (e.g. ''North Pitch'', ''Hall B'')';

        COMMENT ON COLUMN public.campus_schedule_configs.is_active IS 'If False, sessions will not be generated for this campus';

        CREATE SEQUENCE public.campus_schedule_configs_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.campus_schedule_configs_id_seq OWNED BY public.campus_schedule_configs.id;

        CREATE TABLE public.campuses (
            id integer NOT NULL,
            location_id integer NOT NULL,
            name character varying NOT NULL,
            venue character varying,
            address character varying,
            notes text,
            is_active boolean NOT NULL,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        );

        CREATE SEQUENCE public.campuses_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.campuses_id_seq OWNED BY public.campuses.id;

        CREATE TABLE public.certificate_templates (
            id uuid NOT NULL,
            track_id uuid NOT NULL,
            title character varying(255) NOT NULL,
            description text,
            design_template text,
            validation_rules json,
            created_at timestamp without time zone
        );

        CREATE TABLE public.coach_levels (
            id integer NOT NULL,
            name character varying(255) NOT NULL,
            required_xp integer NOT NULL,
            required_sessions integer NOT NULL,
            theory_hours integer NOT NULL,
            practice_hours integer NOT NULL,
            description text,
            license_title character varying(255) NOT NULL
        );

        CREATE SEQUENCE public.coach_levels_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.coach_levels_id_seq OWNED BY public.coach_levels.id;

        CREATE TABLE public.coupon_usages (
            id integer NOT NULL,
            coupon_id integer NOT NULL,
            user_id integer NOT NULL,
            credits_awarded integer NOT NULL,
            used_at timestamp with time zone DEFAULT now() NOT NULL
        );

        COMMENT ON COLUMN public.coupon_usages.credits_awarded IS 'Amount of credits awarded from this coupon';

        CREATE SEQUENCE public.coupon_usages_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.coupon_usages_id_seq OWNED BY public.coupon_usages.id;

        CREATE TABLE public.coupons (
            id integer NOT NULL,
            code character varying(50) NOT NULL,
            type public.coupontype NOT NULL,
            discount_value double precision NOT NULL,
            description character varying(200) NOT NULL,
            is_active boolean NOT NULL,
            expires_at timestamp with time zone,
            max_uses integer,
            current_uses integer NOT NULL,
            requires_purchase boolean NOT NULL,
            requires_admin_approval boolean NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL
        );

        COMMENT ON COLUMN public.coupons.requires_purchase IS 'True if coupon can only be used during credit purchase';

        COMMENT ON COLUMN public.coupons.requires_admin_approval IS 'True if coupon requires admin approval after purchase';

        CREATE SEQUENCE public.coupons_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.coupons_id_seq OWNED BY public.coupons.id;

        CREATE TABLE public.credit_transactions (
            id integer NOT NULL,
            user_id integer,
            user_license_id integer,
            transaction_type character varying(50) NOT NULL,
            amount integer NOT NULL,
            balance_after integer NOT NULL,
            description text,
            idempotency_key character varying(255) NOT NULL,
            semester_id integer,
            enrollment_id integer,
            created_at timestamp without time zone NOT NULL,
            CONSTRAINT check_one_credit_reference CHECK ((((user_id IS NOT NULL) AND (user_license_id IS NULL)) OR ((user_id IS NULL) AND (user_license_id IS NOT NULL))))
        );

        CREATE SEQUENCE public.credit_transactions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.credit_transactions_id_seq OWNED BY public.credit_transactions.id;

        CREATE TABLE public.feedback (
            id integer NOT NULL,
            user_id integer NOT NULL,
            session_id integer NOT NULL,
            rating double precision NOT NULL,
            instructor_rating double precision,
            session_quality double precision,
            would_recommend boolean,
            comment text,
            is_anonymous boolean,
            created_at timestamp without time zone,
            updated_at timestamp without time zone,
            CONSTRAINT instructor_rating_range CHECK (((instructor_rating IS NULL) OR ((instructor_rating >= (1.0)::double precision) AND (instructor_rating <= (5.0)::double precision)))),
            CONSTRAINT rating_range CHECK (((rating >= (1.0)::double precision) AND (rating <= (5.0)::double precision))),
            CONSTRAINT session_quality_range CHECK (((session_quality IS NULL) OR ((session_quality >= (1.0)::double precision) AND (session_quality <= (5.0)::double precision))))
        );

        CREATE SEQUENCE public.feedback_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;

        CREATE TABLE public.football_skill_assessments (
            id integer NOT NULL,
            user_license_id integer NOT NULL,
            skill_name character varying(50) NOT NULL,
            points_earned integer NOT NULL,
            points_total integer NOT NULL,
            percentage double precision NOT NULL,
            assessed_by integer NOT NULL,
            assessed_at timestamp without time zone NOT NULL,
            notes text
        );

        CREATE SEQUENCE public.football_skill_assessments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.football_skill_assessments_id_seq OWNED BY public.football_skill_assessments.id;

        CREATE TABLE public.game_configurations (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            game_preset_id integer,
            game_config jsonb,
            game_config_overrides jsonb,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        );

        COMMENT ON COLUMN public.game_configurations.semester_id IS 'Tournament this game configuration belongs to (1:1 relationship)';

        COMMENT ON COLUMN public.game_configurations.game_preset_id IS 'Reference to pre-configured game type (e.g., GanFootvolley, Stole My Goal). Preset defines default skills, weights, and match rules.';

        COMMENT ON COLUMN public.game_configurations.game_config IS 'Merged game configuration (preset + overrides). Final configuration used for tournament simulation. Includes match probabilities, ranking rules, skill weights, and simulation options.';

        COMMENT ON COLUMN public.game_configurations.game_config_overrides IS 'Custom overrides applied to preset configuration. Tracks what was customized from the base preset. NULL if using preset defaults.';

        COMMENT ON COLUMN public.game_configurations.created_at IS 'When this game configuration was created';

        COMMENT ON COLUMN public.game_configurations.updated_at IS 'When this game configuration was last updated';

        CREATE SEQUENCE public.game_configurations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.game_configurations_id_seq OWNED BY public.game_configurations.id;

        CREATE TABLE public.game_presets (
            id integer NOT NULL,
            code character varying(50) NOT NULL,
            name character varying(100) NOT NULL,
            description text,
            game_config jsonb NOT NULL,
            is_active boolean NOT NULL,
            is_recommended boolean NOT NULL,
            is_locked boolean NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            created_by integer
        );

        COMMENT ON COLUMN public.game_presets.code IS 'Unique code identifier (e.g., ''gan_footvolley'', ''stole_my_goal'')';

        COMMENT ON COLUMN public.game_presets.name IS 'Display name (e.g., ''GanFootvolley'', ''Stole My Goal'')';

        COMMENT ON COLUMN public.game_presets.description IS 'Description of the game type and its characteristics';

        COMMENT ON COLUMN public.game_presets.game_config IS 'Complete game configuration including: format_config (match simulation, ranking rules), skill_config (skills tested, weights), simulation_config (variation, distribution), metadata (category, player count, difficulty)';

        COMMENT ON COLUMN public.game_presets.is_active IS 'Whether this preset is available for selection';

        COMMENT ON COLUMN public.game_presets.is_recommended IS 'Whether this preset is recommended as default choice';

        COMMENT ON COLUMN public.game_presets.is_locked IS 'Whether this preset''s configuration is locked (cannot be overridden)';

        COMMENT ON COLUMN public.game_presets.created_at IS 'When this preset was created';

        COMMENT ON COLUMN public.game_presets.updated_at IS 'When this preset was last updated';

        COMMENT ON COLUMN public.game_presets.created_by IS 'Admin user who created this preset';

        CREATE SEQUENCE public.game_presets_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.game_presets_id_seq OWNED BY public.game_presets.id;

        CREATE TABLE public.group_users (
            group_id integer NOT NULL,
            user_id integer NOT NULL
        );

        CREATE TABLE public.groups (
            id integer NOT NULL,
            name character varying NOT NULL,
            description text,
            semester_id integer NOT NULL,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        CREATE SEQUENCE public.groups_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;

        CREATE TABLE public.instructor_assignment_requests (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            instructor_id integer NOT NULL,
            requested_by integer,
            location_id integer,
            status public.assignmentrequeststatus NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            responded_at timestamp with time zone,
            expires_at timestamp with time zone,
            request_message text,
            response_message text,
            priority integer NOT NULL
        );

        COMMENT ON COLUMN public.instructor_assignment_requests.semester_id IS 'Semester needing an instructor';

        COMMENT ON COLUMN public.instructor_assignment_requests.instructor_id IS 'Instructor receiving the request';

        COMMENT ON COLUMN public.instructor_assignment_requests.requested_by IS 'Admin who sent the request';

        COMMENT ON COLUMN public.instructor_assignment_requests.location_id IS 'Location for the assignment';

        COMMENT ON COLUMN public.instructor_assignment_requests.status IS 'PENDING, ACCEPTED, DECLINED, CANCELLED, EXPIRED';

        COMMENT ON COLUMN public.instructor_assignment_requests.responded_at IS 'When instructor responded';

        COMMENT ON COLUMN public.instructor_assignment_requests.expires_at IS 'Request expiration (optional)';

        COMMENT ON COLUMN public.instructor_assignment_requests.request_message IS 'Message from admin to instructor';

        COMMENT ON COLUMN public.instructor_assignment_requests.response_message IS 'Message from instructor (if declined, reason)';

        COMMENT ON COLUMN public.instructor_assignment_requests.priority IS 'Higher number = higher priority (0-10)';

        CREATE SEQUENCE public.instructor_assignment_requests_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_assignment_requests_id_seq OWNED BY public.instructor_assignment_requests.id;

        CREATE TABLE public.instructor_assignments (
            id integer NOT NULL,
            location_id integer NOT NULL,
            instructor_id integer NOT NULL,
            specialization_type character varying(50) NOT NULL,
            age_group character varying(20) NOT NULL,
            year integer NOT NULL,
            time_period_start character varying(10) NOT NULL,
            time_period_end character varying(10) NOT NULL,
            is_master boolean NOT NULL,
            assigned_by integer,
            is_active boolean NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            deactivated_at timestamp with time zone
        );

        COMMENT ON COLUMN public.instructor_assignments.location_id IS 'Assignment location';

        COMMENT ON COLUMN public.instructor_assignments.instructor_id IS 'Assigned instructor';

        COMMENT ON COLUMN public.instructor_assignments.specialization_type IS 'LFA_PLAYER, INTERNSHIP, etc.';

        COMMENT ON COLUMN public.instructor_assignments.age_group IS 'PRE, YOUTH, AMATEUR, PRO';

        COMMENT ON COLUMN public.instructor_assignments.year IS 'Year (e.g., 2026)';

        COMMENT ON COLUMN public.instructor_assignments.time_period_start IS 'Start period code (M01, Q1, etc.)';

        COMMENT ON COLUMN public.instructor_assignments.time_period_end IS 'End period code (M06, Q2, etc.)';

        COMMENT ON COLUMN public.instructor_assignments.is_master IS 'True if this is the master instructor';

        COMMENT ON COLUMN public.instructor_assignments.assigned_by IS 'Master instructor who made assignment';

        COMMENT ON COLUMN public.instructor_assignments.is_active IS 'Active assignment';

        COMMENT ON COLUMN public.instructor_assignments.deactivated_at IS 'When assignment was deactivated';

        CREATE SEQUENCE public.instructor_assignments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_assignments_id_seq OWNED BY public.instructor_assignments.id;

        CREATE TABLE public.instructor_availability_windows (
            id integer NOT NULL,
            instructor_id integer NOT NULL,
            year integer NOT NULL,
            time_period character varying(10) NOT NULL,
            is_available boolean NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            notes text
        );

        COMMENT ON COLUMN public.instructor_availability_windows.instructor_id IS 'Instructor setting availability';

        COMMENT ON COLUMN public.instructor_availability_windows.year IS 'Year (e.g., 2026)';

        COMMENT ON COLUMN public.instructor_availability_windows.time_period IS 'Q1, Q2, Q3, Q4 or M01-M12';

        COMMENT ON COLUMN public.instructor_availability_windows.is_available IS 'True if instructor is available for this window';

        COMMENT ON COLUMN public.instructor_availability_windows.notes IS 'Optional notes from instructor';

        CREATE SEQUENCE public.instructor_availability_windows_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_availability_windows_id_seq OWNED BY public.instructor_availability_windows.id;

        CREATE TABLE public.instructor_positions (
            id integer NOT NULL,
            location_id integer NOT NULL,
            posted_by integer NOT NULL,
            is_master_position boolean NOT NULL,
            specialization_type character varying(50) NOT NULL,
            age_group character varying(20) NOT NULL,
            year integer NOT NULL,
            time_period_start character varying(10) NOT NULL,
            time_period_end character varying(10) NOT NULL,
            description text NOT NULL,
            priority integer NOT NULL,
            status public.positionstatus NOT NULL,
            application_deadline timestamp with time zone NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL
        );

        COMMENT ON COLUMN public.instructor_positions.location_id IS 'Location for position';

        COMMENT ON COLUMN public.instructor_positions.posted_by IS 'Admin or master instructor who posted';

        COMMENT ON COLUMN public.instructor_positions.is_master_position IS 'True if this is a master instructor opening, False for assistant positions';

        COMMENT ON COLUMN public.instructor_positions.specialization_type IS 'LFA_PLAYER, INTERNSHIP, etc.';

        COMMENT ON COLUMN public.instructor_positions.age_group IS 'PRE, YOUTH, AMATEUR, PRO';

        COMMENT ON COLUMN public.instructor_positions.year IS 'Year (e.g., 2026)';

        COMMENT ON COLUMN public.instructor_positions.time_period_start IS 'Start period code (M01, Q1, etc.)';

        COMMENT ON COLUMN public.instructor_positions.time_period_end IS 'End period code (M06, Q2, etc.)';

        COMMENT ON COLUMN public.instructor_positions.description IS 'Job description and requirements';

        COMMENT ON COLUMN public.instructor_positions.priority IS '1=low, 5=medium, 10=high';

        COMMENT ON COLUMN public.instructor_positions.status IS 'OPEN, FILLED, CLOSED, CANCELLED';

        COMMENT ON COLUMN public.instructor_positions.application_deadline IS 'Application deadline';

        CREATE SEQUENCE public.instructor_positions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_positions_id_seq OWNED BY public.instructor_positions.id;

        CREATE TABLE public.instructor_session_reviews (
            id integer NOT NULL,
            session_id integer NOT NULL,
            student_id integer NOT NULL,
            instructor_id integer NOT NULL,
            instructor_clarity integer NOT NULL,
            support_approachability integer NOT NULL,
            session_structure integer NOT NULL,
            relevance integer NOT NULL,
            environment integer NOT NULL,
            engagement_feeling integer NOT NULL,
            feedback_quality integer NOT NULL,
            satisfaction integer NOT NULL,
            comments text,
            created_at timestamp without time zone,
            updated_at timestamp without time zone,
            CONSTRAINT check_engagement_feeling_range CHECK (((engagement_feeling >= 1) AND (engagement_feeling <= 5))),
            CONSTRAINT check_environment_range CHECK (((environment >= 1) AND (environment <= 5))),
            CONSTRAINT check_feedback_quality_range CHECK (((feedback_quality >= 1) AND (feedback_quality <= 5))),
            CONSTRAINT check_instructor_clarity_range CHECK (((instructor_clarity >= 1) AND (instructor_clarity <= 5))),
            CONSTRAINT check_relevance_range CHECK (((relevance >= 1) AND (relevance <= 5))),
            CONSTRAINT check_satisfaction_range CHECK (((satisfaction >= 1) AND (satisfaction <= 5))),
            CONSTRAINT check_session_structure_range CHECK (((session_structure >= 1) AND (session_structure <= 5))),
            CONSTRAINT check_support_approachability_range CHECK (((support_approachability >= 1) AND (support_approachability <= 5)))
        );

        CREATE SEQUENCE public.instructor_session_reviews_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_session_reviews_id_seq OWNED BY public.instructor_session_reviews.id;

        CREATE TABLE public.instructor_specialization_availability (
            id integer NOT NULL,
            instructor_id integer NOT NULL,
            specialization_type character varying(50) NOT NULL,
            time_period_code character varying(10) NOT NULL,
            year integer NOT NULL,
            location_city character varying(100),
            is_available boolean NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            notes character varying(500),
            CONSTRAINT check_time_period_code_format CHECK (((((time_period_code)::text ~~ 'Q_'::text) AND ((time_period_code)::text = ANY (ARRAY[('Q1'::character varying)::text, ('Q2'::character varying)::text, ('Q3'::character varying)::text, ('Q4'::character varying)::text]))) OR (((time_period_code)::text ~~ 'M__'::text) AND ((time_period_code)::text >= 'M01'::text) AND ((time_period_code)::text <= 'M12'::text)))),
            CONSTRAINT check_year_range CHECK (((year >= 2024) AND (year <= 2100)))
        );

        COMMENT ON COLUMN public.instructor_specialization_availability.instructor_id IS 'Instructor who sets this availability preference';

        COMMENT ON COLUMN public.instructor_specialization_availability.specialization_type IS 'LFA_PLAYER_PRE, LFA_PLAYER_YOUTH, LFA_PLAYER_AMATEUR, LFA_PLAYER_PRO';

        COMMENT ON COLUMN public.instructor_specialization_availability.time_period_code IS 'Q1-Q4 for quarterly, M01-M12 for monthly';

        COMMENT ON COLUMN public.instructor_specialization_availability.year IS 'Year for which this availability applies (e.g., 2025)';

        COMMENT ON COLUMN public.instructor_specialization_availability.location_city IS 'City where this availability applies (e.g., Budapest, Budaörs)';

        COMMENT ON COLUMN public.instructor_specialization_availability.is_available IS 'True if instructor is available for this specialization in this time period';

        COMMENT ON COLUMN public.instructor_specialization_availability.notes IS 'Optional notes from instructor about this availability';

        CREATE SEQUENCE public.instructor_specialization_availability_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_specialization_availability_id_seq OWNED BY public.instructor_specialization_availability.id;

        CREATE TABLE public.instructor_specializations (
            id integer NOT NULL,
            user_id integer NOT NULL,
            specialization character varying(50) NOT NULL,
            certified_at timestamp without time zone,
            certified_by integer,
            notes text,
            is_active boolean NOT NULL,
            created_at timestamp without time zone
        );

        CREATE SEQUENCE public.instructor_specializations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.instructor_specializations_id_seq OWNED BY public.instructor_specializations.id;

        CREATE TABLE public.internship_levels (
            id integer NOT NULL,
            name character varying(100) NOT NULL,
            required_xp integer NOT NULL,
            required_sessions integer NOT NULL,
            total_hours integer NOT NULL,
            description text,
            license_title character varying(255) NOT NULL
        );

        CREATE SEQUENCE public.internship_levels_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.internship_levels_id_seq OWNED BY public.internship_levels.id;

        CREATE TABLE public.invitation_codes (
            id integer NOT NULL,
            code character varying(50) NOT NULL,
            invited_name character varying(200) NOT NULL,
            invited_email character varying(200),
            bonus_credits integer NOT NULL,
            is_used boolean NOT NULL,
            used_by_user_id integer,
            used_at timestamp with time zone,
            created_by_admin_id integer,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            expires_at timestamp with time zone,
            notes text
        );

        COMMENT ON COLUMN public.invitation_codes.code IS 'Unique invitation code';

        COMMENT ON COLUMN public.invitation_codes.invited_name IS 'Name of the person/organization receiving the code';

        COMMENT ON COLUMN public.invitation_codes.invited_email IS 'Optional: Email restriction - only this email can use the code';

        COMMENT ON COLUMN public.invitation_codes.bonus_credits IS 'Bonus credits to grant when code is used';

        COMMENT ON COLUMN public.invitation_codes.is_used IS 'Whether the code has been used';

        COMMENT ON COLUMN public.invitation_codes.used_by_user_id IS 'User who redeemed this code';

        COMMENT ON COLUMN public.invitation_codes.used_at IS 'When the code was redeemed';

        COMMENT ON COLUMN public.invitation_codes.created_by_admin_id IS 'Admin who created this code';

        COMMENT ON COLUMN public.invitation_codes.expires_at IS 'Optional expiration date';

        COMMENT ON COLUMN public.invitation_codes.notes IS 'Admin notes about this invitation code';

        CREATE SEQUENCE public.invitation_codes_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.invitation_codes_id_seq OWNED BY public.invitation_codes.id;

        CREATE TABLE public.invoice_requests (
            id integer NOT NULL,
            user_id integer NOT NULL,
            payment_reference character varying(50) NOT NULL,
            amount_eur double precision NOT NULL,
            credit_amount integer NOT NULL,
            specialization character varying(50),
            coupon_code character varying(50),
            status character varying(20) NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            paid_at timestamp with time zone,
            verified_at timestamp with time zone
        );

        COMMENT ON COLUMN public.invoice_requests.payment_reference IS 'Unique payment reference: LFA-YYYYMMDD-HHMMSS-ID-HASH (max 30 chars, SWIFT compatible)';

        COMMENT ON COLUMN public.invoice_requests.amount_eur IS 'Amount in EUR';

        COMMENT ON COLUMN public.invoice_requests.credit_amount IS 'Credit amount';

        COMMENT ON COLUMN public.invoice_requests.specialization IS 'Specialization type';

        COMMENT ON COLUMN public.invoice_requests.coupon_code IS 'Applied coupon code (if any)';

        COMMENT ON COLUMN public.invoice_requests.paid_at IS 'When payment was made';

        COMMENT ON COLUMN public.invoice_requests.verified_at IS 'When admin verified payment';

        CREATE SEQUENCE public.invoice_requests_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.invoice_requests_id_seq OWNED BY public.invoice_requests.id;

        CREATE TABLE public.issued_certificates (
            id uuid NOT NULL,
            certificate_template_id uuid NOT NULL,
            user_id integer NOT NULL,
            unique_identifier character varying(100) NOT NULL,
            issue_date timestamp without time zone,
            completion_date timestamp without time zone,
            verification_hash character varying(256) NOT NULL,
            cert_metadata json,
            is_revoked boolean,
            revoked_at timestamp without time zone,
            revoked_reason text,
            created_at timestamp without time zone
        );

        CREATE TABLE public.license_metadata (
            id integer NOT NULL,
            specialization_type character varying(20) NOT NULL,
            level_code character varying(50) NOT NULL,
            level_number integer NOT NULL,
            title character varying(100) NOT NULL,
            title_en character varying(100),
            subtitle character varying(200),
            color_primary character varying(7) NOT NULL,
            color_secondary character varying(7),
            icon_emoji character varying(10),
            icon_symbol character varying(50),
            marketing_narrative text,
            cultural_context text,
            philosophy text,
            background_gradient character varying(200),
            css_class character varying(50),
            image_url character varying(500),
            advancement_criteria json,
            time_requirement_hours integer,
            project_requirements json,
            evaluation_criteria json,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        CREATE SEQUENCE public.license_metadata_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.license_metadata_id_seq OWNED BY public.license_metadata.id;

        CREATE TABLE public.license_progressions (
            id integer NOT NULL,
            user_license_id integer NOT NULL,
            from_level integer NOT NULL,
            to_level integer NOT NULL,
            advanced_by integer,
            advancement_reason text,
            requirements_met text,
            advanced_at timestamp without time zone
        );

        CREATE SEQUENCE public.license_progressions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.license_progressions_id_seq OWNED BY public.license_progressions.id;

        CREATE TABLE public.location_master_instructors (
            id integer NOT NULL,
            location_id integer NOT NULL,
            instructor_id integer NOT NULL,
            contract_start timestamp with time zone NOT NULL,
            contract_end timestamp with time zone NOT NULL,
            is_active boolean NOT NULL,
            offer_status public.masterofferstatus,
            offered_at timestamp with time zone,
            offer_deadline timestamp with time zone,
            accepted_at timestamp with time zone,
            declined_at timestamp with time zone,
            hiring_pathway character varying(20) NOT NULL,
            source_position_id integer,
            availability_override boolean NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            terminated_at timestamp with time zone
        );

        COMMENT ON COLUMN public.location_master_instructors.location_id IS 'Location for master instructor';

        COMMENT ON COLUMN public.location_master_instructors.instructor_id IS 'Master instructor user';

        COMMENT ON COLUMN public.location_master_instructors.contract_start IS 'Contract start date';

        COMMENT ON COLUMN public.location_master_instructors.contract_end IS 'Contract end date';

        COMMENT ON COLUMN public.location_master_instructors.is_active IS 'Only one active master per location';

        COMMENT ON COLUMN public.location_master_instructors.offer_status IS 'Offer workflow status: NULL=legacy, OFFERED=pending, ACCEPTED=active, DECLINED/EXPIRED=rejected';

        COMMENT ON COLUMN public.location_master_instructors.offered_at IS 'When offer was sent to instructor';

        COMMENT ON COLUMN public.location_master_instructors.offer_deadline IS 'Deadline for instructor to accept/decline offer';

        COMMENT ON COLUMN public.location_master_instructors.accepted_at IS 'When instructor accepted the offer';

        COMMENT ON COLUMN public.location_master_instructors.declined_at IS 'When instructor declined or offer expired';

        COMMENT ON COLUMN public.location_master_instructors.hiring_pathway IS 'Hiring method: DIRECT or JOB_POSTING';

        COMMENT ON COLUMN public.location_master_instructors.source_position_id IS 'Links to job posting if hired via JOB_POSTING pathway';

        COMMENT ON COLUMN public.location_master_instructors.availability_override IS 'True if admin sent offer despite availability mismatch';

        COMMENT ON COLUMN public.location_master_instructors.terminated_at IS 'When contract was terminated';

        CREATE SEQUENCE public.location_master_instructors_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.location_master_instructors_id_seq OWNED BY public.location_master_instructors.id;

        CREATE TABLE public.locations (
            id integer NOT NULL,
            name character varying(200) NOT NULL,
            city character varying(100) NOT NULL,
            postal_code character varying(20),
            country character varying(100) NOT NULL,
            country_code character varying(2),
            location_code character varying(10),
            venue character varying(200),
            address character varying(500),
            notes text,
            is_active boolean NOT NULL,
            location_type public.locationtype NOT NULL,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        COMMENT ON COLUMN public.locations.location_type IS 'Location capability: PARTNER (Tournament+Mini only) or CENTER (all types)';

        CREATE SEQUENCE public.locations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.locations_id_seq OWNED BY public.locations.id;

        CREATE TABLE public.messages (
            id integer NOT NULL,
            sender_id integer NOT NULL,
            recipient_id integer NOT NULL,
            subject character varying NOT NULL,
            message text NOT NULL,
            priority public.messagepriority,
            is_read boolean,
            is_edited boolean,
            created_at timestamp without time zone,
            read_at timestamp without time zone,
            edited_at timestamp without time zone
        );

        CREATE SEQUENCE public.messages_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;

        CREATE TABLE public.module_components (
            id uuid NOT NULL,
            module_id uuid NOT NULL,
            type character varying(50) NOT NULL,
            name character varying(255) NOT NULL,
            description text,
            order_in_module integer,
            estimated_minutes integer,
            is_mandatory boolean,
            component_data json,
            created_at timestamp without time zone
        );

        CREATE TABLE public.modules (
            id uuid NOT NULL,
            track_id uuid NOT NULL,
            semester_id integer,
            name character varying(255) NOT NULL,
            description text,
            order_in_track integer,
            learning_objectives json,
            estimated_hours integer,
            is_mandatory boolean,
            created_at timestamp without time zone
        );

        CREATE TABLE public.notifications (
            id integer NOT NULL,
            user_id integer NOT NULL,
            title character varying NOT NULL,
            message text NOT NULL,
            type public.notificationtype,
            is_read boolean,
            related_session_id integer,
            related_booking_id integer,
            created_at timestamp without time zone,
            read_at timestamp without time zone,
            link character varying(255),
            related_semester_id integer,
            related_request_id integer
        );

        CREATE SEQUENCE public.notifications_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;

        CREATE TABLE public.player_levels (
            id integer NOT NULL,
            name character varying(100) NOT NULL,
            color character varying(50) NOT NULL,
            required_xp integer NOT NULL,
            required_sessions integer NOT NULL,
            description text,
            license_title character varying(255) NOT NULL
        );

        CREATE SEQUENCE public.player_levels_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.player_levels_id_seq OWNED BY public.player_levels.id;

        CREATE TABLE public.position_applications (
            id integer NOT NULL,
            position_id integer NOT NULL,
            applicant_id integer NOT NULL,
            application_message text NOT NULL,
            status public.applicationstatus NOT NULL,
            reviewed_at timestamp with time zone,
            created_at timestamp with time zone DEFAULT now() NOT NULL
        );

        COMMENT ON COLUMN public.position_applications.position_id IS 'Position being applied to';

        COMMENT ON COLUMN public.position_applications.applicant_id IS 'Instructor applying';

        COMMENT ON COLUMN public.position_applications.application_message IS 'Cover letter / application message';

        COMMENT ON COLUMN public.position_applications.status IS 'PENDING, ACCEPTED, DECLINED';

        COMMENT ON COLUMN public.position_applications.reviewed_at IS 'When master reviewed application';

        CREATE SEQUENCE public.position_applications_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.position_applications_id_seq OWNED BY public.position_applications.id;

        CREATE TABLE public.project_enrollment_quizzes (
            id integer NOT NULL,
            project_id integer NOT NULL,
            user_id integer NOT NULL,
            quiz_attempt_id integer NOT NULL,
            enrollment_priority integer,
            enrollment_confirmed boolean,
            created_at timestamp without time zone
        );

        CREATE SEQUENCE public.project_enrollment_quizzes_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.project_enrollment_quizzes_id_seq OWNED BY public.project_enrollment_quizzes.id;

        CREATE TABLE public.project_enrollments (
            id integer NOT NULL,
            project_id integer NOT NULL,
            user_id integer NOT NULL,
            enrolled_at timestamp without time zone,
            status character varying(20),
            progress_status character varying(20),
            completion_percentage double precision,
            instructor_approved boolean,
            instructor_feedback text,
            enrollment_status character varying(20),
            quiz_passed boolean,
            final_grade character varying(5),
            completed_at timestamp without time zone
        );

        CREATE SEQUENCE public.project_enrollments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.project_enrollments_id_seq OWNED BY public.project_enrollments.id;

        CREATE TABLE public.project_milestone_progress (
            id integer NOT NULL,
            enrollment_id integer NOT NULL,
            milestone_id integer NOT NULL,
            status character varying(20),
            submitted_at timestamp without time zone,
            instructor_feedback text,
            instructor_approved_at timestamp without time zone,
            sessions_completed integer,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        CREATE SEQUENCE public.project_milestone_progress_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.project_milestone_progress_id_seq OWNED BY public.project_milestone_progress.id;

        CREATE TABLE public.project_milestones (
            id integer NOT NULL,
            project_id integer NOT NULL,
            title character varying(200) NOT NULL,
            description text,
            order_index integer NOT NULL,
            required_sessions integer,
            xp_reward integer,
            deadline date,
            is_required boolean,
            created_at timestamp without time zone
        );

        CREATE SEQUENCE public.project_milestones_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.project_milestones_id_seq OWNED BY public.project_milestones.id;

        CREATE TABLE public.project_quizzes (
            id integer NOT NULL,
            project_id integer NOT NULL,
            quiz_id integer NOT NULL,
            milestone_id integer,
            quiz_type character varying(50) NOT NULL,
            is_required boolean,
            minimum_score double precision,
            order_index integer,
            is_active boolean,
            created_at timestamp without time zone
        );

        CREATE SEQUENCE public.project_quizzes_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.project_quizzes_id_seq OWNED BY public.project_quizzes.id;

        CREATE TABLE public.project_sessions (
            id integer NOT NULL,
            project_id integer NOT NULL,
            session_id integer NOT NULL,
            milestone_id integer,
            is_required boolean,
            created_at timestamp without time zone
        );

        CREATE SEQUENCE public.project_sessions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.project_sessions_id_seq OWNED BY public.project_sessions.id;

        CREATE TABLE public.projects (
            id integer NOT NULL,
            title character varying(200) NOT NULL,
            description text,
            semester_id integer NOT NULL,
            instructor_id integer,
            max_participants integer,
            required_sessions integer,
            xp_reward integer,
            deadline date,
            status character varying(20),
            difficulty character varying(20),
            target_specialization public.specializationtype,
            mixed_specialization boolean,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        COMMENT ON COLUMN public.projects.target_specialization IS 'Target specialization for this project (null = all specializations)';

        COMMENT ON COLUMN public.projects.mixed_specialization IS 'Whether this project encourages collaboration between Player and Coach specializations';

        CREATE SEQUENCE public.projects_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;

        CREATE TABLE public.question_metadata (
            id integer NOT NULL,
            question_id integer NOT NULL,
            estimated_difficulty double precision,
            cognitive_load double precision,
            concept_tags character varying(500),
            prerequisite_concepts character varying(500),
            average_time_seconds double precision,
            global_success_rate double precision,
            last_analytics_update timestamp with time zone
        );

        CREATE SEQUENCE public.question_metadata_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.question_metadata_id_seq OWNED BY public.question_metadata.id;

        CREATE TABLE public.quiz_answer_options (
            id integer NOT NULL,
            question_id integer NOT NULL,
            option_text character varying(500) NOT NULL,
            is_correct boolean NOT NULL,
            order_index integer NOT NULL
        );

        CREATE SEQUENCE public.quiz_answer_options_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.quiz_answer_options_id_seq OWNED BY public.quiz_answer_options.id;

        CREATE TABLE public.quiz_attempts (
            id integer NOT NULL,
            user_id integer NOT NULL,
            quiz_id integer NOT NULL,
            started_at timestamp with time zone DEFAULT now(),
            completed_at timestamp with time zone,
            time_spent_minutes double precision,
            score double precision,
            total_questions integer NOT NULL,
            correct_answers integer NOT NULL,
            xp_awarded integer NOT NULL,
            passed boolean NOT NULL
        );

        CREATE SEQUENCE public.quiz_attempts_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.quiz_attempts_id_seq OWNED BY public.quiz_attempts.id;

        CREATE TABLE public.quiz_questions (
            id integer NOT NULL,
            quiz_id integer NOT NULL,
            question_text text NOT NULL,
            question_type public.questiontype NOT NULL,
            points integer NOT NULL,
            order_index integer NOT NULL,
            explanation text,
            created_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.quiz_questions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.quiz_questions_id_seq OWNED BY public.quiz_questions.id;

        CREATE TABLE public.quiz_user_answers (
            id integer NOT NULL,
            attempt_id integer NOT NULL,
            question_id integer NOT NULL,
            selected_option_id integer,
            answer_text character varying(1000),
            is_correct boolean NOT NULL,
            answered_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.quiz_user_answers_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.quiz_user_answers_id_seq OWNED BY public.quiz_user_answers.id;

        CREATE TABLE public.quizzes (
            id integer NOT NULL,
            title character varying(200) NOT NULL,
            description text,
            category public.quizcategory NOT NULL,
            difficulty public.quizdifficulty NOT NULL,
            time_limit_minutes integer NOT NULL,
            xp_reward integer NOT NULL,
            passing_score double precision NOT NULL,
            is_active boolean,
            created_at timestamp with time zone DEFAULT now(),
            updated_at timestamp with time zone
        );

        CREATE SEQUENCE public.quizzes_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.quizzes_id_seq OWNED BY public.quizzes.id;

        CREATE TABLE public.semester_enrollments (
            id integer NOT NULL,
            user_id integer NOT NULL,
            semester_id integer NOT NULL,
            user_license_id integer NOT NULL,
            request_status public.enrollmentstatus NOT NULL,
            requested_at timestamp with time zone NOT NULL,
            approved_at timestamp with time zone,
            approved_by integer,
            rejection_reason character varying,
            payment_reference_code character varying(50),
            payment_verified boolean NOT NULL,
            payment_verified_at timestamp with time zone,
            payment_verified_by integer,
            is_active boolean NOT NULL,
            enrolled_at timestamp with time zone NOT NULL,
            deactivated_at timestamp with time zone,
            age_category character varying(20),
            age_category_overridden boolean NOT NULL,
            age_category_overridden_at timestamp with time zone,
            age_category_overridden_by integer,
            created_at timestamp with time zone NOT NULL,
            updated_at timestamp with time zone NOT NULL,
            tournament_checked_in_at timestamp with time zone
        );

        COMMENT ON COLUMN public.semester_enrollments.user_id IS 'Student who is enrolled';

        COMMENT ON COLUMN public.semester_enrollments.semester_id IS 'Semester for this enrollment';

        COMMENT ON COLUMN public.semester_enrollments.user_license_id IS 'Link to UserLicense (tracks progress/levels)';

        COMMENT ON COLUMN public.semester_enrollments.request_status IS 'Enrollment request status: PENDING/APPROVED/REJECTED/WITHDRAWN';

        COMMENT ON COLUMN public.semester_enrollments.requested_at IS 'When student requested enrollment';

        COMMENT ON COLUMN public.semester_enrollments.approved_at IS 'When admin approved/rejected the request';

        COMMENT ON COLUMN public.semester_enrollments.approved_by IS 'Admin who approved/rejected';

        COMMENT ON COLUMN public.semester_enrollments.rejection_reason IS 'Reason for rejection (if rejected)';

        COMMENT ON COLUMN public.semester_enrollments.payment_reference_code IS 'Unique payment reference code for bank transfer (e.g., LFA-INT-2024S1-042-A7B9)';

        COMMENT ON COLUMN public.semester_enrollments.payment_verified IS 'Whether student paid for THIS specialization in THIS semester';

        COMMENT ON COLUMN public.semester_enrollments.payment_verified_at IS 'When payment was verified';

        COMMENT ON COLUMN public.semester_enrollments.payment_verified_by IS 'Admin user who verified payment';

        COMMENT ON COLUMN public.semester_enrollments.is_active IS 'Whether this enrollment is currently active (auto-set when approved)';

        COMMENT ON COLUMN public.semester_enrollments.enrolled_at IS 'When student enrolled in this spec for this semester';

        COMMENT ON COLUMN public.semester_enrollments.deactivated_at IS 'When enrollment was deactivated (if applicable)';

        COMMENT ON COLUMN public.semester_enrollments.age_category IS 'Age category at enrollment (PRE/YOUTH/AMATEUR/PRO)';

        COMMENT ON COLUMN public.semester_enrollments.age_category_overridden IS 'True if instructor manually changed category';

        COMMENT ON COLUMN public.semester_enrollments.age_category_overridden_at IS 'When age category was overridden by instructor';

        COMMENT ON COLUMN public.semester_enrollments.age_category_overridden_by IS 'Instructor who overrode the age category';

        COMMENT ON COLUMN public.semester_enrollments.tournament_checked_in_at IS 'Timestamp when player confirmed tournament attendance (pre-tournament check-in)';

        CREATE SEQUENCE public.semester_enrollments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.semester_enrollments_id_seq OWNED BY public.semester_enrollments.id;

        CREATE TABLE public.semester_instructors (
            semester_id integer NOT NULL,
            instructor_id integer NOT NULL
        );

        CREATE TABLE public.semesters (
            id integer NOT NULL,
            code character varying NOT NULL,
            name character varying NOT NULL,
            start_date date NOT NULL,
            end_date date NOT NULL,
            status public.semester_status NOT NULL,
            tournament_status character varying(50),
            winner_count integer,
            is_active boolean,
            enrollment_cost integer NOT NULL,
            created_at timestamp without time zone,
            updated_at timestamp without time zone,
            master_instructor_id integer,
            specialization_type character varying(50),
            age_group character varying(20),
            theme character varying(200),
            focus_description character varying(500),
            campus_id integer,
            location_id integer
        );

        COMMENT ON COLUMN public.semesters.status IS 'Current lifecycle phase of the semester';

        COMMENT ON COLUMN public.semesters.tournament_status IS 'Tournament-specific status: DRAFT, SEEKING_INSTRUCTOR, READY_FOR_ENROLLMENT, etc.';

        COMMENT ON COLUMN public.semesters.winner_count IS 'Number of winners for INDIVIDUAL_RANKING tournaments (E2E testing)';

        COMMENT ON COLUMN public.semesters.is_active IS 'DEPRECATED: Use status field instead. Kept for backward compatibility.';

        COMMENT ON COLUMN public.semesters.enrollment_cost IS 'Credit cost to enroll in this semester (admin adjustable)';

        COMMENT ON COLUMN public.semesters.master_instructor_id IS 'Master instructor who approves enrollment requests for this semester';

        COMMENT ON COLUMN public.semesters.specialization_type IS 'Specialization type (SEASON types: LFA_PLAYER_PRE/YOUTH/AMATEUR/PRO, GANCUJU_PLAYER, LFA_COACH, INTERNSHIP, OR user license for tournaments: LFA_FOOTBALL_PLAYER)';

        COMMENT ON COLUMN public.semesters.age_group IS 'Age group (PRE, YOUTH, AMATEUR, PRO)';

        COMMENT ON COLUMN public.semesters.theme IS 'Marketing theme (e.g., ''New Year Challenge'', ''Q1'', ''Fall'')';

        COMMENT ON COLUMN public.semesters.focus_description IS 'Focus description (e.g., ''Újévi fogadalmak, friss kezdés'')';

        COMMENT ON COLUMN public.semesters.campus_id IS 'FK to campuses table (most specific location - preferred)';

        COMMENT ON COLUMN public.semesters.location_id IS 'FK to locations table (less specific than campus_id, preferred over legacy location_city/venue/address)';

        CREATE SEQUENCE public.semesters_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.semesters_id_seq OWNED BY public.semesters.id;

        CREATE TABLE public.session_group_assignments (
            id integer NOT NULL,
            session_id integer NOT NULL,
            group_number integer NOT NULL,
            instructor_id integer NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            created_by integer
        );

        COMMENT ON COLUMN public.session_group_assignments.session_id IS 'Session these groups belong to';

        COMMENT ON COLUMN public.session_group_assignments.group_number IS 'Group number within session (1, 2, 3, 4...)';

        COMMENT ON COLUMN public.session_group_assignments.instructor_id IS 'Instructor leading this group';

        COMMENT ON COLUMN public.session_group_assignments.created_by IS 'Head coach who created this assignment';

        CREATE SEQUENCE public.session_group_assignments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.session_group_assignments_id_seq OWNED BY public.session_group_assignments.id;

        CREATE TABLE public.session_group_students (
            id integer NOT NULL,
            session_group_id integer NOT NULL,
            student_id integer NOT NULL,
            assigned_at timestamp with time zone DEFAULT now() NOT NULL
        );

        COMMENT ON COLUMN public.session_group_students.session_group_id IS 'Which group this student is in';

        COMMENT ON COLUMN public.session_group_students.student_id IS 'Student assigned to this group';

        CREATE SEQUENCE public.session_group_students_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.session_group_students_id_seq OWNED BY public.session_group_students.id;

        CREATE TABLE public.session_quizzes (
            id integer NOT NULL,
            session_id integer NOT NULL,
            quiz_id integer NOT NULL,
            is_required boolean,
            max_attempts integer,
            created_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.session_quizzes_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.session_quizzes_id_seq OWNED BY public.session_quizzes.id;

        CREATE TABLE public.sessions (
            id integer NOT NULL,
            title character varying NOT NULL,
            description text,
            date_start timestamp without time zone NOT NULL,
            date_end timestamp without time zone NOT NULL,
            session_type public.sessiontype NOT NULL,
            capacity integer,
            location character varying,
            meeting_link character varying,
            sport_type character varying,
            level character varying,
            instructor_name character varying,
            semester_id integer NOT NULL,
            group_id integer,
            instructor_id integer,
            target_specialization public.specializationtype,
            mixed_specialization boolean,
            actual_start_time timestamp without time zone,
            actual_end_time timestamp without time zone,
            session_status character varying(20),
            quiz_unlocked boolean,
            base_xp integer,
            credit_cost integer NOT NULL,
            is_tournament_game boolean,
            game_type character varying(100),
            game_results text,
            auto_generated boolean NOT NULL,
            tournament_phase public.tournament_phase_enum,
            tournament_round integer,
            tournament_match_number integer,
            ranking_mode character varying(50),
            group_identifier character varying(10),
            round_number integer,
            expected_participants integer,
            participant_filter character varying(50),
            pod_tier integer,
            match_format character varying(50),
            scoring_type character varying(50),
            structure_config jsonb,
            rounds_data jsonb DEFAULT '{}'::jsonb NOT NULL,
            participant_user_ids integer[],
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        COMMENT ON COLUMN public.sessions.target_specialization IS 'Target specialization for this session (null = all specializations)';

        COMMENT ON COLUMN public.sessions.mixed_specialization IS 'Whether this session is open to all specializations';

        COMMENT ON COLUMN public.sessions.actual_start_time IS 'Actual start time when instructor starts the session';

        COMMENT ON COLUMN public.sessions.actual_end_time IS 'Actual end time when instructor stops the session';

        COMMENT ON COLUMN public.sessions.session_status IS 'Session status: scheduled, in_progress, completed';

        COMMENT ON COLUMN public.sessions.quiz_unlocked IS 'Whether the quiz is unlocked for students (HYBRID sessions)';

        COMMENT ON COLUMN public.sessions.base_xp IS 'Base XP awarded for completing this session (HYBRID=100, ON-SITE=75, VIRTUAL=50)';

        COMMENT ON COLUMN public.sessions.credit_cost IS 'Number of credits required to book this session (default: 1, workshops may cost more)';

        COMMENT ON COLUMN public.sessions.is_tournament_game IS 'True if this session is a tournament game';

        COMMENT ON COLUMN public.sessions.game_type IS 'Type/name of tournament game (user-defined, e.g., ''Skills Challenge'')';

        COMMENT ON COLUMN public.sessions.game_results IS 'JSON array of game results: [{user_id: 1, score: 95, rank: 1}, ...]';

        COMMENT ON COLUMN public.sessions.auto_generated IS 'True if this session was auto-generated from tournament type config';

        COMMENT ON COLUMN public.sessions.tournament_phase IS 'Tournament phase: canonical TournamentPhase enum values (GROUP_STAGE, KNOCKOUT, etc.)';

        COMMENT ON COLUMN public.sessions.tournament_round IS 'Round number within the tournament (1, 2, 3, ...)';

        COMMENT ON COLUMN public.sessions.tournament_match_number IS 'Match number within the round (1, 2, 3, ...)';

        COMMENT ON COLUMN public.sessions.ranking_mode IS 'Ranking mode: ALL_PARTICIPANTS, GROUP_ISOLATED, TIERED, QUALIFIED_ONLY, PERFORMANCE_POD';

        COMMENT ON COLUMN public.sessions.group_identifier IS 'Group identifier for group stage sessions (A, B, C, D)';

        COMMENT ON COLUMN public.sessions.round_number IS 'Round number within the group/phase (1, 2, 3, ...)';

        COMMENT ON COLUMN public.sessions.expected_participants IS 'Expected number of participants for this session (used for validation)';

        COMMENT ON COLUMN public.sessions.participant_filter IS 'Participant filter logic: group_membership, top_group_qualifiers, dynamic_swiss_pairing';

        COMMENT ON COLUMN public.sessions.pod_tier IS 'Performance tier for Swiss System pods (1=top performers, 2=middle, etc.)';

        COMMENT ON COLUMN public.sessions.match_format IS 'Match format: INDIVIDUAL_RANKING, HEAD_TO_HEAD, TEAM_MATCH, TIME_BASED, SKILL_RATING';

        COMMENT ON COLUMN public.sessions.scoring_type IS 'Scoring type: PLACEMENT, WIN_LOSS, SCORE_BASED, TIME_BASED, SKILL_RATING';

        COMMENT ON COLUMN public.sessions.structure_config IS 'Match structure configuration (pairings, teams, performance criteria, etc.)';

        COMMENT ON COLUMN public.sessions.rounds_data IS 'Round-by-round results for INDIVIDUAL_RANKING tournaments. Structure: {''total_rounds'': 3, ''completed_rounds'': 1, ''round_results'': {''1'': {''user_123'': ''12.5s'', ''user_456'': ''13.2s''}}}';

        COMMENT ON COLUMN public.sessions.participant_user_ids IS 'Explicit list of user_ids participating in THIS MATCH (not tournament-wide). This fixes the architectural issue where participants were determined at runtime.';

        CREATE SEQUENCE public.sessions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.sessions_id_seq OWNED BY public.sessions.id;

        CREATE TABLE public.skill_point_conversion_rates (
            id integer NOT NULL,
            skill_category character varying(50) NOT NULL,
            xp_per_point integer NOT NULL,
            updated_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.skill_point_conversion_rates_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.skill_point_conversion_rates_id_seq OWNED BY public.skill_point_conversion_rates.id;

        CREATE TABLE public.skill_rewards (
            id integer NOT NULL,
            user_id integer NOT NULL,
            source_type character varying(20) NOT NULL,
            source_id integer NOT NULL,
            skill_name character varying(50) NOT NULL,
            points_awarded integer NOT NULL,
            created_at timestamp without time zone NOT NULL
        );

        CREATE SEQUENCE public.skill_rewards_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.skill_rewards_id_seq OWNED BY public.skill_rewards.id;

        CREATE TABLE public.specialization_progress (
            id integer NOT NULL,
            student_id integer NOT NULL,
            specialization_id character varying(50) NOT NULL,
            current_level integer,
            total_xp integer,
            completed_sessions integer,
            completed_projects integer,
            theory_hours_completed integer,
            practice_hours_completed integer,
            last_activity timestamp without time zone,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        CREATE SEQUENCE public.specialization_progress_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.specialization_progress_id_seq OWNED BY public.specialization_progress.id;

        CREATE TABLE public.specializations (
            id character varying(50) NOT NULL,
            is_active boolean NOT NULL,
            created_at timestamp without time zone NOT NULL
        );

        COMMENT ON COLUMN public.specializations.id IS 'Matches SpecializationType enum values';

        COMMENT ON COLUMN public.specializations.is_active IS 'Controls availability without code changes';

        COMMENT ON COLUMN public.specializations.created_at IS 'Audit trail for when specialization was created';

        CREATE TABLE public.student_performance_reviews (
            id integer NOT NULL,
            session_id integer NOT NULL,
            student_id integer NOT NULL,
            instructor_id integer NOT NULL,
            punctuality integer NOT NULL,
            engagement integer NOT NULL,
            focus integer NOT NULL,
            collaboration integer NOT NULL,
            attitude integer NOT NULL,
            comments text,
            created_at timestamp without time zone,
            updated_at timestamp without time zone,
            CONSTRAINT check_attitude_range CHECK (((attitude >= 1) AND (attitude <= 5))),
            CONSTRAINT check_collaboration_range CHECK (((collaboration >= 1) AND (collaboration <= 5))),
            CONSTRAINT check_engagement_range CHECK (((engagement >= 1) AND (engagement <= 5))),
            CONSTRAINT check_focus_range CHECK (((focus >= 1) AND (focus <= 5))),
            CONSTRAINT check_punctuality_range CHECK (((punctuality >= 1) AND (punctuality <= 5)))
        );

        CREATE SEQUENCE public.student_performance_reviews_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.student_performance_reviews_id_seq OWNED BY public.student_performance_reviews.id;

        CREATE TABLE public.system_events (
            id integer NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            level public.systemeventlevel NOT NULL,
            event_type character varying(100) NOT NULL,
            user_id integer,
            role character varying(50),
            payload_json jsonb,
            resolved boolean DEFAULT false NOT NULL
        );

        CREATE SEQUENCE public.system_events_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.system_events_id_seq OWNED BY public.system_events.id;

        CREATE TABLE public.team_members (
            id integer NOT NULL,
            team_id integer NOT NULL,
            user_id integer NOT NULL,
            role character varying(50),
            joined_at timestamp with time zone DEFAULT now(),
            is_active boolean
        );

        CREATE SEQUENCE public.team_members_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.team_members_id_seq OWNED BY public.team_members.id;

        CREATE TABLE public.teams (
            id integer NOT NULL,
            name character varying(100) NOT NULL,
            code character varying(20),
            captain_user_id integer,
            specialization_type character varying(50),
            created_at timestamp with time zone DEFAULT now(),
            is_active boolean
        );

        CREATE SEQUENCE public.teams_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;

        CREATE TABLE public.tournament_badges (
            id integer NOT NULL,
            user_id integer NOT NULL,
            semester_id integer NOT NULL,
            badge_type character varying(50) NOT NULL,
            badge_category character varying(50) NOT NULL,
            title character varying(200) NOT NULL,
            description text,
            icon character varying(10),
            rarity character varying(20) DEFAULT 'COMMON'::character varying NOT NULL,
            badge_metadata jsonb,
            earned_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.tournament_badges_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_badges_id_seq OWNED BY public.tournament_badges.id;

        CREATE TABLE public.tournament_configurations (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            tournament_type_id integer,
            participant_type character varying(50) NOT NULL,
            is_multi_day boolean NOT NULL,
            max_players integer,
            match_duration_minutes integer,
            break_duration_minutes integer,
            parallel_fields integer NOT NULL,
            scoring_type character varying(50) NOT NULL,
            measurement_unit character varying(50),
            ranking_direction character varying(10),
            number_of_rounds integer NOT NULL,
            assignment_type character varying(30),
            sessions_generated boolean NOT NULL,
            sessions_generated_at timestamp without time zone,
            enrollment_snapshot jsonb,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL,
            campus_schedule_overrides jsonb
        );

        COMMENT ON COLUMN public.tournament_configurations.semester_id IS 'Tournament this configuration belongs to (1:1 relationship)';

        COMMENT ON COLUMN public.tournament_configurations.tournament_type_id IS 'FK to tournament_types table (defines format: HEAD_TO_HEAD or INDIVIDUAL_RANKING)';

        COMMENT ON COLUMN public.tournament_configurations.participant_type IS 'Participant type: INDIVIDUAL, TEAM, MIXED';

        COMMENT ON COLUMN public.tournament_configurations.is_multi_day IS 'True if tournament spans multiple days';

        COMMENT ON COLUMN public.tournament_configurations.max_players IS 'Maximum tournament participants (explicit capacity, independent of session capacity sum)';

        COMMENT ON COLUMN public.tournament_configurations.match_duration_minutes IS 'Duration of each match in minutes (overrides tournament_type default)';

        COMMENT ON COLUMN public.tournament_configurations.break_duration_minutes IS 'Break time between matches in minutes (overrides tournament_type default)';

        COMMENT ON COLUMN public.tournament_configurations.parallel_fields IS 'Number of parallel fields/pitches available (1-4) for simultaneous matches';

        COMMENT ON COLUMN public.tournament_configurations.scoring_type IS 'Scoring type for INDIVIDUAL_RANKING: TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT. Ignored for HEAD_TO_HEAD.';

        COMMENT ON COLUMN public.tournament_configurations.measurement_unit IS 'Unit of measurement for INDIVIDUAL_RANKING results: seconds/minutes (TIME_BASED), meters/centimeters (DISTANCE_BASED), points/repetitions (SCORE_BASED). NULL for PLACEMENT or HEAD_TO_HEAD.';

        COMMENT ON COLUMN public.tournament_configurations.ranking_direction IS 'Ranking direction for INDIVIDUAL_RANKING: ASC (lowest wins, e.g. 100m sprint), DESC (highest wins, e.g. plank). HEAD_TO_HEAD always DESC. NULL for PLACEMENT.';

        COMMENT ON COLUMN public.tournament_configurations.number_of_rounds IS 'Number of rounds for INDIVIDUAL_RANKING tournaments (1-10). Each round is a separate session. HEAD_TO_HEAD ignores this.';

        COMMENT ON COLUMN public.tournament_configurations.assignment_type IS 'Tournament instructor assignment strategy: OPEN_ASSIGNMENT (admin assigns directly) or APPLICATION_BASED (instructors apply)';

        COMMENT ON COLUMN public.tournament_configurations.sessions_generated IS 'True if tournament sessions have been auto-generated (prevents duplicate generation)';

        COMMENT ON COLUMN public.tournament_configurations.sessions_generated_at IS 'Timestamp when sessions were auto-generated';

        COMMENT ON COLUMN public.tournament_configurations.enrollment_snapshot IS '📸 Snapshot of enrollment state before session generation (for regeneration if needed)';

        COMMENT ON COLUMN public.tournament_configurations.created_at IS 'When this configuration was created';

        COMMENT ON COLUMN public.tournament_configurations.updated_at IS 'When this configuration was last updated';

        COMMENT ON COLUMN public.tournament_configurations.campus_schedule_overrides IS 'Per-campus schedule overrides for multi-venue tournaments. Schema: {campus_id: {match_duration_minutes: int, break_duration_minutes: int, parallel_fields: int}}. Each campus can independently configure its own schedule parameters.';

        CREATE SEQUENCE public.tournament_configurations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_configurations_id_seq OWNED BY public.tournament_configurations.id;

        CREATE TABLE public.tournament_participations (
            id integer NOT NULL,
            user_id integer NOT NULL,
            semester_id integer NOT NULL,
            placement integer,
            skill_points_awarded jsonb,
            xp_awarded integer NOT NULL,
            credits_awarded integer NOT NULL,
            achieved_at timestamp with time zone DEFAULT now(),
            skill_rating_delta jsonb
        );

        COMMENT ON COLUMN public.tournament_participations.skill_rating_delta IS 'V3 EMA per-tournament rating delta: {"passing": 1.2, "dribbling": -0.4}. Isolated to this tournament only. Written at reward distribution time.';

        CREATE SEQUENCE public.tournament_participations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_participations_id_seq OWNED BY public.tournament_participations.id;

        CREATE TABLE public.tournament_rankings (
            id integer NOT NULL,
            tournament_id integer NOT NULL,
            user_id integer,
            team_id integer,
            participant_type character varying(50) NOT NULL,
            rank integer,
            points numeric(10,2),
            wins integer,
            losses integer,
            draws integer,
            goals_for integer,
            goals_against integer,
            updated_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.tournament_rankings_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_rankings_id_seq OWNED BY public.tournament_rankings.id;

        CREATE TABLE public.tournament_reward_configs (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            reward_policy_name character varying(100) NOT NULL,
            reward_policy_snapshot jsonb,
            reward_config jsonb,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        );

        COMMENT ON COLUMN public.tournament_reward_configs.semester_id IS 'Tournament this reward config belongs to (1:1 relationship)';

        COMMENT ON COLUMN public.tournament_reward_configs.reward_policy_name IS 'Name of the reward policy (Standard, Championship, Friendly, Custom)';

        COMMENT ON COLUMN public.tournament_reward_configs.reward_policy_snapshot IS 'Immutable snapshot of the reward policy at tournament creation time';

        COMMENT ON COLUMN public.tournament_reward_configs.reward_config IS 'Detailed reward configuration:
                - skill_mappings: List of skills with weights, categories, enabled flags
                - first_place, second_place, third_place: Placement-based rewards (badges, credits, XP)
                - top_25_percent: Dynamic rewards for top performers
                - participation: Participation rewards (badges, credits, XP)
                - template_name: Template name if using preset
                - custom_config: Whether this is a custom configuration
                ';

        COMMENT ON COLUMN public.tournament_reward_configs.created_at IS 'When this reward config was created';

        COMMENT ON COLUMN public.tournament_reward_configs.updated_at IS 'When this reward config was last updated';

        CREATE SEQUENCE public.tournament_reward_configs_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_reward_configs_id_seq OWNED BY public.tournament_reward_configs.id;

        CREATE TABLE public.tournament_rewards (
            id integer NOT NULL,
            tournament_id integer NOT NULL,
            "position" character varying(20) NOT NULL,
            xp_amount integer,
            credits_reward integer,
            badge_id integer
        );

        CREATE SEQUENCE public.tournament_rewards_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_rewards_id_seq OWNED BY public.tournament_rewards.id;

        CREATE TABLE public.tournament_skill_mappings (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            skill_name character varying(100) NOT NULL,
            skill_category character varying(50),
            weight numeric(3,2) DEFAULT 1.0 NOT NULL,
            created_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.tournament_skill_mappings_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_skill_mappings_id_seq OWNED BY public.tournament_skill_mappings.id;

        CREATE TABLE public.tournament_stats (
            id integer NOT NULL,
            tournament_id integer NOT NULL,
            total_participants integer,
            total_teams integer,
            total_matches integer,
            completed_matches integer,
            total_revenue integer,
            avg_attendance_rate numeric(5,2),
            created_at timestamp with time zone DEFAULT now(),
            updated_at timestamp with time zone DEFAULT now()
        );

        CREATE SEQUENCE public.tournament_stats_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_stats_id_seq OWNED BY public.tournament_stats.id;

        CREATE TABLE public.tournament_status_history (
            id integer NOT NULL,
            tournament_id integer NOT NULL,
            old_status character varying(50) NOT NULL,
            new_status character varying(50) NOT NULL,
            changed_by integer NOT NULL,
            reason text,
            extra_metadata json,
            created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
        );

        CREATE SEQUENCE public.tournament_status_history_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_status_history_id_seq OWNED BY public.tournament_status_history.id;

        CREATE TABLE public.tournament_team_enrollments (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            team_id integer NOT NULL,
            enrollment_date timestamp with time zone DEFAULT now(),
            payment_verified boolean,
            is_active boolean
        );

        CREATE SEQUENCE public.tournament_team_enrollments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_team_enrollments_id_seq OWNED BY public.tournament_team_enrollments.id;

        CREATE TABLE public.tournament_types (
            id integer NOT NULL,
            code character varying(50) NOT NULL,
            display_name character varying(100) NOT NULL,
            description text,
            min_players integer NOT NULL,
            max_players integer,
            requires_power_of_two boolean NOT NULL,
            session_duration_minutes integer NOT NULL,
            break_between_sessions_minutes integer NOT NULL,
            format character varying(50) DEFAULT 'INDIVIDUAL_RANKING'::character varying NOT NULL,
            config json NOT NULL
        );

        COMMENT ON COLUMN public.tournament_types.format IS 'Match format: INDIVIDUAL_RANKING (multi-player ranking) or HEAD_TO_HEAD (1v1 or team vs team score-based)';

        CREATE SEQUENCE public.tournament_types_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.tournament_types_id_seq OWNED BY public.tournament_types.id;

        CREATE TABLE public.tracks (
            id uuid NOT NULL,
            name character varying(255) NOT NULL,
            code character varying(50) NOT NULL,
            description text,
            duration_semesters integer,
            prerequisites json,
            is_active boolean,
            created_at timestamp without time zone
        );

        CREATE TABLE public.user_achievements (
            id integer NOT NULL,
            user_id integer NOT NULL,
            achievement_id integer,
            badge_type character varying NOT NULL,
            title character varying NOT NULL,
            description character varying,
            icon character varying,
            earned_at timestamp without time zone,
            semester_count integer,
            specialization_id character varying(50)
        );

        CREATE SEQUENCE public.user_achievements_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.user_achievements_id_seq OWNED BY public.user_achievements.id;

        CREATE TABLE public.user_licenses (
            id integer NOT NULL,
            user_id integer NOT NULL,
            specialization_type character varying(20) NOT NULL,
            current_level integer NOT NULL,
            max_achieved_level integer NOT NULL,
            started_at timestamp without time zone NOT NULL,
            last_advanced_at timestamp without time zone,
            instructor_notes text,
            payment_reference_code character varying(50),
            payment_verified boolean NOT NULL,
            payment_verified_at timestamp without time zone,
            onboarding_completed boolean NOT NULL,
            onboarding_completed_at timestamp without time zone,
            is_active boolean NOT NULL,
            issued_at timestamp without time zone,
            expires_at timestamp without time zone,
            last_renewed_at timestamp without time zone,
            renewal_cost integer NOT NULL,
            motivation_scores json,
            average_motivation_score double precision,
            motivation_last_assessed_at timestamp without time zone,
            motivation_assessed_by integer,
            football_skills json,
            skills_last_updated_at timestamp without time zone,
            skills_updated_by integer,
            credit_balance integer NOT NULL,
            credit_purchased integer NOT NULL,
            credit_expires_at timestamp without time zone,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        COMMENT ON COLUMN public.user_licenses.payment_reference_code IS 'Unique payment reference for bank transfer (e.g., INT-2025-002-X7K9)';

        COMMENT ON COLUMN public.user_licenses.payment_verified IS 'Whether admin verified payment received for this license';

        COMMENT ON COLUMN public.user_licenses.payment_verified_at IS 'When admin verified the payment';

        COMMENT ON COLUMN public.user_licenses.onboarding_completed IS 'Whether student completed basic onboarding for this specialization';

        COMMENT ON COLUMN public.user_licenses.onboarding_completed_at IS 'When student completed onboarding';

        COMMENT ON COLUMN public.user_licenses.is_active IS 'Whether this license is currently active (can be used for teaching/enrollment)';

        COMMENT ON COLUMN public.user_licenses.issued_at IS 'Official license issuance date (e.g., 2014-01-01 for Grand Master)';

        COMMENT ON COLUMN public.user_licenses.expires_at IS 'License expiration date (null = no expiration yet, perpetual until first renewal)';

        COMMENT ON COLUMN public.user_licenses.last_renewed_at IS 'When license was last renewed';

        COMMENT ON COLUMN public.user_licenses.renewal_cost IS 'Credit cost to renew this license (default: 1000 credits)';

        COMMENT ON COLUMN public.user_licenses.motivation_scores IS 'Motivation assessment scores (1-5 scale) - filled by admin/instructor';

        COMMENT ON COLUMN public.user_licenses.average_motivation_score IS 'Calculated average motivation score (1.0-5.0)';

        COMMENT ON COLUMN public.user_licenses.motivation_last_assessed_at IS 'When motivation was last assessed';

        COMMENT ON COLUMN public.user_licenses.motivation_assessed_by IS 'Admin/instructor who assessed motivation';

        COMMENT ON COLUMN public.user_licenses.football_skills IS '6 football skill percentages for LFA Player specializations (heading, shooting, crossing, passing, dribbling, ball_control)';

        COMMENT ON COLUMN public.user_licenses.skills_last_updated_at IS 'When skills were last updated';

        COMMENT ON COLUMN public.user_licenses.skills_updated_by IS 'Instructor who last updated skills';

        COMMENT ON COLUMN public.user_licenses.credit_balance IS 'Current credit balance available for enrollments';

        COMMENT ON COLUMN public.user_licenses.credit_purchased IS 'Total credits purchased (lifetime)';

        COMMENT ON COLUMN public.user_licenses.credit_expires_at IS 'Credit expiration date (2 years from purchase)';

        CREATE SEQUENCE public.user_licenses_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.user_licenses_id_seq OWNED BY public.user_licenses.id;

        CREATE TABLE public.user_module_progresses (
            id uuid NOT NULL,
            user_track_progress_id uuid NOT NULL,
            module_id uuid NOT NULL,
            started_at timestamp without time zone,
            completed_at timestamp without time zone,
            grade double precision,
            status public.moduleprogressstatus,
            attempts integer,
            time_spent_minutes integer,
            created_at timestamp without time zone
        );

        CREATE TABLE public.user_question_performance (
            id integer NOT NULL,
            user_id integer NOT NULL,
            question_id integer NOT NULL,
            total_attempts integer,
            correct_attempts integer,
            last_attempt_correct boolean,
            last_attempted_at timestamp with time zone,
            difficulty_weight double precision,
            next_review_at timestamp with time zone,
            mastery_level double precision
        );

        CREATE SEQUENCE public.user_question_performance_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.user_question_performance_id_seq OWNED BY public.user_question_performance.id;

        CREATE TABLE public.user_stats (
            id integer NOT NULL,
            user_id integer NOT NULL,
            semesters_participated integer,
            first_semester_date timestamp without time zone,
            current_streak integer,
            total_bookings integer,
            total_attended integer,
            total_cancelled integer,
            attendance_rate double precision,
            feedback_given integer,
            average_rating_given double precision,
            punctuality_score double precision,
            total_xp integer,
            level integer,
            created_at timestamp without time zone,
            updated_at timestamp without time zone
        );

        CREATE SEQUENCE public.user_stats_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.user_stats_id_seq OWNED BY public.user_stats.id;

        CREATE TABLE public.user_track_progresses (
            id uuid NOT NULL,
            user_id integer NOT NULL,
            track_id uuid NOT NULL,
            enrollment_date timestamp without time zone,
            current_semester integer,
            status public.trackprogressstatus,
            completion_percentage double precision,
            certificate_id uuid,
            started_at timestamp without time zone,
            completed_at timestamp without time zone,
            created_at timestamp without time zone
        );

        CREATE TABLE public.users (
            id integer NOT NULL,
            name character varying NOT NULL,
            nickname character varying,
            first_name character varying,
            last_name character varying,
            email character varying NOT NULL,
            password_hash character varying NOT NULL,
            role public.userrole NOT NULL,
            is_active boolean,
            onboarding_completed boolean,
            phone character varying,
            emergency_contact character varying,
            emergency_phone character varying,
            date_of_birth timestamp without time zone,
            medical_notes character varying,
            interests character varying,
            "position" character varying,
            nationality character varying,
            gender character varying,
            current_location character varying,
            street_address character varying,
            city character varying,
            postal_code character varying,
            country character varying,
            specialization public.specializationtype,
            payment_verified boolean NOT NULL,
            payment_verified_at timestamp without time zone,
            payment_verified_by integer,
            credit_balance integer NOT NULL,
            credit_purchased integer NOT NULL,
            credit_payment_reference character varying(50),
            xp_balance integer NOT NULL,
            nda_accepted boolean NOT NULL,
            nda_accepted_at timestamp without time zone,
            nda_ip_address character varying,
            parental_consent boolean NOT NULL,
            parental_consent_at timestamp without time zone,
            parental_consent_by character varying,
            created_at timestamp without time zone,
            updated_at timestamp without time zone,
            created_by integer,
            CONSTRAINT chk_credit_balance_non_negative CHECK ((credit_balance >= 0))
        );

        COMMENT ON COLUMN public.users.first_name IS 'User first name (given name)';

        COMMENT ON COLUMN public.users.last_name IS 'User last name (family name)';

        COMMENT ON COLUMN public.users.onboarding_completed IS 'Set to True when student completes FIRST license onboarding (motivation questionnaire). Note: UserLicense.onboarding_completed tracks EACH specialization separately.';

        COMMENT ON COLUMN public.users.nationality IS 'User''s nationality (e.g., Hungarian, American)';

        COMMENT ON COLUMN public.users.gender IS 'User''s gender (Male, Female, Other, Prefer not to say)';

        COMMENT ON COLUMN public.users.current_location IS 'User''s current location (e.g., Budapest, Hungary)';

        COMMENT ON COLUMN public.users.street_address IS 'Street address (e.g., Main Street 123)';

        COMMENT ON COLUMN public.users.city IS 'City name';

        COMMENT ON COLUMN public.users.postal_code IS 'Postal/ZIP code';

        COMMENT ON COLUMN public.users.country IS 'Country name';

        COMMENT ON COLUMN public.users.specialization IS 'User''s chosen specialization track (Player/Coach)';

        COMMENT ON COLUMN public.users.payment_verified IS 'Whether student has paid semester fees';

        COMMENT ON COLUMN public.users.payment_verified_at IS 'Timestamp when payment was verified';

        COMMENT ON COLUMN public.users.payment_verified_by IS 'Admin who verified the payment';

        COMMENT ON COLUMN public.users.credit_balance IS 'Current available credits (can be used across all specializations)';

        COMMENT ON COLUMN public.users.credit_purchased IS 'Total credits purchased by this user (for transaction history)';

        COMMENT ON COLUMN public.users.credit_payment_reference IS 'Unique payment reference code for credit purchases (közlemény)';

        COMMENT ON COLUMN public.users.xp_balance IS 'Current XP (Experience Points) - earned through training and tournaments';

        COMMENT ON COLUMN public.users.nda_accepted IS 'Whether student has accepted the NDA';

        COMMENT ON COLUMN public.users.nda_accepted_at IS 'Timestamp when NDA was accepted';

        COMMENT ON COLUMN public.users.nda_ip_address IS 'IP address from which NDA was accepted';

        COMMENT ON COLUMN public.users.parental_consent IS 'Whether parental consent has been given (required for users under 18 in LFA_COACH)';

        COMMENT ON COLUMN public.users.parental_consent_at IS 'Timestamp when parental consent was given';

        COMMENT ON COLUMN public.users.parental_consent_by IS 'Name of parent/guardian who gave consent';

        CREATE SEQUENCE public.users_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

        CREATE TABLE public.xp_transactions (
            id integer NOT NULL,
            user_id integer NOT NULL,
            transaction_type character varying(50) NOT NULL,
            amount integer NOT NULL,
            balance_after integer NOT NULL,
            description text,
            semester_id integer,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            idempotency_key character varying(255)
        );

        CREATE SEQUENCE public.xp_transactions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER SEQUENCE public.xp_transactions_id_seq OWNED BY public.xp_transactions.id;

        ALTER TABLE ONLY public.achievements ALTER COLUMN id SET DEFAULT nextval('public.achievements_id_seq'::regclass);

        ALTER TABLE ONLY public.adaptive_learning_sessions ALTER COLUMN id SET DEFAULT nextval('public.adaptive_learning_sessions_id_seq'::regclass);

        ALTER TABLE ONLY public.attendance ALTER COLUMN id SET DEFAULT nextval('public.attendance_id_seq'::regclass);

        ALTER TABLE ONLY public.attendance_history ALTER COLUMN id SET DEFAULT nextval('public.attendance_history_id_seq'::regclass);

        ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);

        ALTER TABLE ONLY public.belt_promotions ALTER COLUMN id SET DEFAULT nextval('public.belt_promotions_id_seq'::regclass);

        ALTER TABLE ONLY public.bookings ALTER COLUMN id SET DEFAULT nextval('public.bookings_id_seq'::regclass);

        ALTER TABLE ONLY public.campus_schedule_configs ALTER COLUMN id SET DEFAULT nextval('public.campus_schedule_configs_id_seq'::regclass);

        ALTER TABLE ONLY public.campuses ALTER COLUMN id SET DEFAULT nextval('public.campuses_id_seq'::regclass);

        ALTER TABLE ONLY public.coach_levels ALTER COLUMN id SET DEFAULT nextval('public.coach_levels_id_seq'::regclass);

        ALTER TABLE ONLY public.coupon_usages ALTER COLUMN id SET DEFAULT nextval('public.coupon_usages_id_seq'::regclass);

        ALTER TABLE ONLY public.coupons ALTER COLUMN id SET DEFAULT nextval('public.coupons_id_seq'::regclass);

        ALTER TABLE ONLY public.credit_transactions ALTER COLUMN id SET DEFAULT nextval('public.credit_transactions_id_seq'::regclass);

        ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);

        ALTER TABLE ONLY public.football_skill_assessments ALTER COLUMN id SET DEFAULT nextval('public.football_skill_assessments_id_seq'::regclass);

        ALTER TABLE ONLY public.game_configurations ALTER COLUMN id SET DEFAULT nextval('public.game_configurations_id_seq'::regclass);

        ALTER TABLE ONLY public.game_presets ALTER COLUMN id SET DEFAULT nextval('public.game_presets_id_seq'::regclass);

        ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_assignment_requests ALTER COLUMN id SET DEFAULT nextval('public.instructor_assignment_requests_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_assignments ALTER COLUMN id SET DEFAULT nextval('public.instructor_assignments_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_availability_windows ALTER COLUMN id SET DEFAULT nextval('public.instructor_availability_windows_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_positions ALTER COLUMN id SET DEFAULT nextval('public.instructor_positions_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_session_reviews ALTER COLUMN id SET DEFAULT nextval('public.instructor_session_reviews_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_specialization_availability ALTER COLUMN id SET DEFAULT nextval('public.instructor_specialization_availability_id_seq'::regclass);

        ALTER TABLE ONLY public.instructor_specializations ALTER COLUMN id SET DEFAULT nextval('public.instructor_specializations_id_seq'::regclass);

        ALTER TABLE ONLY public.internship_levels ALTER COLUMN id SET DEFAULT nextval('public.internship_levels_id_seq'::regclass);

        ALTER TABLE ONLY public.invitation_codes ALTER COLUMN id SET DEFAULT nextval('public.invitation_codes_id_seq'::regclass);

        ALTER TABLE ONLY public.invoice_requests ALTER COLUMN id SET DEFAULT nextval('public.invoice_requests_id_seq'::regclass);

        ALTER TABLE ONLY public.license_metadata ALTER COLUMN id SET DEFAULT nextval('public.license_metadata_id_seq'::regclass);

        ALTER TABLE ONLY public.license_progressions ALTER COLUMN id SET DEFAULT nextval('public.license_progressions_id_seq'::regclass);

        ALTER TABLE ONLY public.location_master_instructors ALTER COLUMN id SET DEFAULT nextval('public.location_master_instructors_id_seq'::regclass);

        ALTER TABLE ONLY public.locations ALTER COLUMN id SET DEFAULT nextval('public.locations_id_seq'::regclass);

        ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);

        ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);

        ALTER TABLE ONLY public.player_levels ALTER COLUMN id SET DEFAULT nextval('public.player_levels_id_seq'::regclass);

        ALTER TABLE ONLY public.position_applications ALTER COLUMN id SET DEFAULT nextval('public.position_applications_id_seq'::regclass);

        ALTER TABLE ONLY public.project_enrollment_quizzes ALTER COLUMN id SET DEFAULT nextval('public.project_enrollment_quizzes_id_seq'::regclass);

        ALTER TABLE ONLY public.project_enrollments ALTER COLUMN id SET DEFAULT nextval('public.project_enrollments_id_seq'::regclass);

        ALTER TABLE ONLY public.project_milestone_progress ALTER COLUMN id SET DEFAULT nextval('public.project_milestone_progress_id_seq'::regclass);

        ALTER TABLE ONLY public.project_milestones ALTER COLUMN id SET DEFAULT nextval('public.project_milestones_id_seq'::regclass);

        ALTER TABLE ONLY public.project_quizzes ALTER COLUMN id SET DEFAULT nextval('public.project_quizzes_id_seq'::regclass);

        ALTER TABLE ONLY public.project_sessions ALTER COLUMN id SET DEFAULT nextval('public.project_sessions_id_seq'::regclass);

        ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);

        ALTER TABLE ONLY public.question_metadata ALTER COLUMN id SET DEFAULT nextval('public.question_metadata_id_seq'::regclass);

        ALTER TABLE ONLY public.quiz_answer_options ALTER COLUMN id SET DEFAULT nextval('public.quiz_answer_options_id_seq'::regclass);

        ALTER TABLE ONLY public.quiz_attempts ALTER COLUMN id SET DEFAULT nextval('public.quiz_attempts_id_seq'::regclass);

        ALTER TABLE ONLY public.quiz_questions ALTER COLUMN id SET DEFAULT nextval('public.quiz_questions_id_seq'::regclass);

        ALTER TABLE ONLY public.quiz_user_answers ALTER COLUMN id SET DEFAULT nextval('public.quiz_user_answers_id_seq'::regclass);

        ALTER TABLE ONLY public.quizzes ALTER COLUMN id SET DEFAULT nextval('public.quizzes_id_seq'::regclass);

        ALTER TABLE ONLY public.semester_enrollments ALTER COLUMN id SET DEFAULT nextval('public.semester_enrollments_id_seq'::regclass);

        ALTER TABLE ONLY public.semesters ALTER COLUMN id SET DEFAULT nextval('public.semesters_id_seq'::regclass);

        ALTER TABLE ONLY public.session_group_assignments ALTER COLUMN id SET DEFAULT nextval('public.session_group_assignments_id_seq'::regclass);

        ALTER TABLE ONLY public.session_group_students ALTER COLUMN id SET DEFAULT nextval('public.session_group_students_id_seq'::regclass);

        ALTER TABLE ONLY public.session_quizzes ALTER COLUMN id SET DEFAULT nextval('public.session_quizzes_id_seq'::regclass);

        ALTER TABLE ONLY public.sessions ALTER COLUMN id SET DEFAULT nextval('public.sessions_id_seq'::regclass);

        ALTER TABLE ONLY public.skill_point_conversion_rates ALTER COLUMN id SET DEFAULT nextval('public.skill_point_conversion_rates_id_seq'::regclass);

        ALTER TABLE ONLY public.skill_rewards ALTER COLUMN id SET DEFAULT nextval('public.skill_rewards_id_seq'::regclass);

        ALTER TABLE ONLY public.specialization_progress ALTER COLUMN id SET DEFAULT nextval('public.specialization_progress_id_seq'::regclass);

        ALTER TABLE ONLY public.student_performance_reviews ALTER COLUMN id SET DEFAULT nextval('public.student_performance_reviews_id_seq'::regclass);

        ALTER TABLE ONLY public.system_events ALTER COLUMN id SET DEFAULT nextval('public.system_events_id_seq'::regclass);

        ALTER TABLE ONLY public.team_members ALTER COLUMN id SET DEFAULT nextval('public.team_members_id_seq'::regclass);

        ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_badges ALTER COLUMN id SET DEFAULT nextval('public.tournament_badges_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_configurations ALTER COLUMN id SET DEFAULT nextval('public.tournament_configurations_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_participations ALTER COLUMN id SET DEFAULT nextval('public.tournament_participations_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_rankings ALTER COLUMN id SET DEFAULT nextval('public.tournament_rankings_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_reward_configs ALTER COLUMN id SET DEFAULT nextval('public.tournament_reward_configs_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_rewards ALTER COLUMN id SET DEFAULT nextval('public.tournament_rewards_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_skill_mappings ALTER COLUMN id SET DEFAULT nextval('public.tournament_skill_mappings_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_stats ALTER COLUMN id SET DEFAULT nextval('public.tournament_stats_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_status_history ALTER COLUMN id SET DEFAULT nextval('public.tournament_status_history_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_team_enrollments ALTER COLUMN id SET DEFAULT nextval('public.tournament_team_enrollments_id_seq'::regclass);

        ALTER TABLE ONLY public.tournament_types ALTER COLUMN id SET DEFAULT nextval('public.tournament_types_id_seq'::regclass);

        ALTER TABLE ONLY public.user_achievements ALTER COLUMN id SET DEFAULT nextval('public.user_achievements_id_seq'::regclass);

        ALTER TABLE ONLY public.user_licenses ALTER COLUMN id SET DEFAULT nextval('public.user_licenses_id_seq'::regclass);

        ALTER TABLE ONLY public.user_question_performance ALTER COLUMN id SET DEFAULT nextval('public.user_question_performance_id_seq'::regclass);

        ALTER TABLE ONLY public.user_stats ALTER COLUMN id SET DEFAULT nextval('public.user_stats_id_seq'::regclass);

        ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);

        ALTER TABLE ONLY public.xp_transactions ALTER COLUMN id SET DEFAULT nextval('public.xp_transactions_id_seq'::regclass);

        ALTER TABLE ONLY public.achievements
            ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.adaptive_learning_sessions
            ADD CONSTRAINT adaptive_learning_sessions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.attendance_history
            ADD CONSTRAINT attendance_history_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT attendance_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.audit_logs
            ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.belt_promotions
            ADD CONSTRAINT belt_promotions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.bookings
            ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.campus_schedule_configs
            ADD CONSTRAINT campus_schedule_configs_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.campuses
            ADD CONSTRAINT campuses_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.certificate_templates
            ADD CONSTRAINT certificate_templates_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.coach_levels
            ADD CONSTRAINT coach_levels_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.coupon_usages
            ADD CONSTRAINT coupon_usages_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.coupons
            ADD CONSTRAINT coupons_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.credit_transactions
            ADD CONSTRAINT credit_transactions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.feedback
            ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.football_skill_assessments
            ADD CONSTRAINT football_skill_assessments_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.game_configurations
            ADD CONSTRAINT game_configurations_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.game_presets
            ADD CONSTRAINT game_presets_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.group_users
            ADD CONSTRAINT group_users_pkey PRIMARY KEY (group_id, user_id);

        ALTER TABLE ONLY public.groups
            ADD CONSTRAINT groups_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_assignment_requests
            ADD CONSTRAINT instructor_assignment_requests_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_assignments
            ADD CONSTRAINT instructor_assignments_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_availability_windows
            ADD CONSTRAINT instructor_availability_windows_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_positions
            ADD CONSTRAINT instructor_positions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_session_reviews
            ADD CONSTRAINT instructor_session_reviews_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_specialization_availability
            ADD CONSTRAINT instructor_specialization_availability_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_specializations
            ADD CONSTRAINT instructor_specializations_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.internship_levels
            ADD CONSTRAINT internship_levels_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.invitation_codes
            ADD CONSTRAINT invitation_codes_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.invoice_requests
            ADD CONSTRAINT invoice_requests_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.issued_certificates
            ADD CONSTRAINT issued_certificates_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.issued_certificates
            ADD CONSTRAINT issued_certificates_unique_identifier_key UNIQUE (unique_identifier);

        ALTER TABLE ONLY public.license_metadata
            ADD CONSTRAINT license_metadata_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.license_progressions
            ADD CONSTRAINT license_progressions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.location_master_instructors
            ADD CONSTRAINT location_master_instructors_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.locations
            ADD CONSTRAINT locations_city_key UNIQUE (city);

        ALTER TABLE ONLY public.locations
            ADD CONSTRAINT locations_location_code_key UNIQUE (location_code);

        ALTER TABLE ONLY public.locations
            ADD CONSTRAINT locations_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.messages
            ADD CONSTRAINT messages_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.module_components
            ADD CONSTRAINT module_components_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.modules
            ADD CONSTRAINT modules_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.notifications
            ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.player_levels
            ADD CONSTRAINT player_levels_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.position_applications
            ADD CONSTRAINT position_applications_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.project_enrollment_quizzes
            ADD CONSTRAINT project_enrollment_quizzes_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.project_enrollments
            ADD CONSTRAINT project_enrollments_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.project_milestone_progress
            ADD CONSTRAINT project_milestone_progress_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.project_milestones
            ADD CONSTRAINT project_milestones_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.project_quizzes
            ADD CONSTRAINT project_quizzes_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.project_sessions
            ADD CONSTRAINT project_sessions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.projects
            ADD CONSTRAINT projects_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.question_metadata
            ADD CONSTRAINT question_metadata_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.quiz_answer_options
            ADD CONSTRAINT quiz_answer_options_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.quiz_attempts
            ADD CONSTRAINT quiz_attempts_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.quiz_questions
            ADD CONSTRAINT quiz_questions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.quiz_user_answers
            ADD CONSTRAINT quiz_user_answers_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.quizzes
            ADD CONSTRAINT quizzes_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_payment_reference_code_key UNIQUE (payment_reference_code);

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.semester_instructors
            ADD CONSTRAINT semester_instructors_pkey PRIMARY KEY (semester_id, instructor_id);

        ALTER TABLE ONLY public.semesters
            ADD CONSTRAINT semesters_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.session_group_assignments
            ADD CONSTRAINT session_group_assignments_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.session_group_students
            ADD CONSTRAINT session_group_students_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.session_quizzes
            ADD CONSTRAINT session_quizzes_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.sessions
            ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.skill_point_conversion_rates
            ADD CONSTRAINT skill_point_conversion_rates_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.skill_point_conversion_rates
            ADD CONSTRAINT skill_point_conversion_rates_skill_category_key UNIQUE (skill_category);

        ALTER TABLE ONLY public.skill_rewards
            ADD CONSTRAINT skill_rewards_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.specialization_progress
            ADD CONSTRAINT specialization_progress_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.specializations
            ADD CONSTRAINT specializations_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.student_performance_reviews
            ADD CONSTRAINT student_performance_reviews_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.system_events
            ADD CONSTRAINT system_events_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.team_members
            ADD CONSTRAINT team_members_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.teams
            ADD CONSTRAINT teams_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_badges
            ADD CONSTRAINT tournament_badges_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_configurations
            ADD CONSTRAINT tournament_configurations_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_participations
            ADD CONSTRAINT tournament_participations_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_rankings
            ADD CONSTRAINT tournament_rankings_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_reward_configs
            ADD CONSTRAINT tournament_reward_configs_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_rewards
            ADD CONSTRAINT tournament_rewards_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_skill_mappings
            ADD CONSTRAINT tournament_skill_mappings_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_stats
            ADD CONSTRAINT tournament_stats_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_status_history
            ADD CONSTRAINT tournament_status_history_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_team_enrollments
            ADD CONSTRAINT tournament_team_enrollments_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tournament_types
            ADD CONSTRAINT tournament_types_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.tracks
            ADD CONSTRAINT tracks_code_key UNIQUE (code);

        ALTER TABLE ONLY public.tracks
            ADD CONSTRAINT tracks_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.instructor_specialization_availability
            ADD CONSTRAINT uix_instructor_spec_period_year_location UNIQUE (instructor_id, specialization_type, time_period_code, year, location_city);

        ALTER TABLE ONLY public.project_milestone_progress
            ADD CONSTRAINT unique_enrollment_milestone UNIQUE (enrollment_id, milestone_id);

        ALTER TABLE ONLY public.project_quizzes
            ADD CONSTRAINT unique_project_quiz_type UNIQUE (project_id, quiz_id, quiz_type);

        ALTER TABLE ONLY public.project_sessions
            ADD CONSTRAINT unique_project_session UNIQUE (project_id, session_id);

        ALTER TABLE ONLY public.project_enrollments
            ADD CONSTRAINT unique_project_user UNIQUE (project_id, user_id);

        ALTER TABLE ONLY public.project_enrollment_quizzes
            ADD CONSTRAINT unique_project_user_enrollment_quiz UNIQUE (project_id, user_id);

        ALTER TABLE ONLY public.question_metadata
            ADD CONSTRAINT unique_question_metadata UNIQUE (question_id);

        ALTER TABLE ONLY public.user_question_performance
            ADD CONSTRAINT unique_user_question UNIQUE (user_id, question_id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT uq_booking_attendance UNIQUE (booking_id);

        ALTER TABLE ONLY public.campus_schedule_configs
            ADD CONSTRAINT uq_campus_schedule_tournament_campus UNIQUE (tournament_id, campus_id);

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT uq_semester_enrollments_user_semester_license UNIQUE (user_id, semester_id, user_license_id);

        ALTER TABLE ONLY public.session_group_assignments
            ADD CONSTRAINT uq_session_group_number UNIQUE (session_id, group_number);

        ALTER TABLE ONLY public.session_group_students
            ADD CONSTRAINT uq_session_group_student UNIQUE (session_group_id, student_id);

        ALTER TABLE ONLY public.session_quizzes
            ADD CONSTRAINT uq_session_quiz UNIQUE (session_id, quiz_id);

        ALTER TABLE ONLY public.tournament_participations
            ADD CONSTRAINT uq_user_semester_participation UNIQUE (user_id, semester_id);

        ALTER TABLE ONLY public.user_achievements
            ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.user_licenses
            ADD CONSTRAINT user_licenses_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.user_module_progresses
            ADD CONSTRAINT user_module_progresses_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.user_question_performance
            ADD CONSTRAINT user_question_performance_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.user_stats
            ADD CONSTRAINT user_stats_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.user_stats
            ADD CONSTRAINT user_stats_user_id_key UNIQUE (user_id);

        ALTER TABLE ONLY public.user_track_progresses
            ADD CONSTRAINT user_track_progresses_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.users
            ADD CONSTRAINT users_credit_payment_reference_key UNIQUE (credit_payment_reference);

        ALTER TABLE ONLY public.users
            ADD CONSTRAINT users_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.xp_transactions
            ADD CONSTRAINT xp_transactions_pkey PRIMARY KEY (id);

        CREATE INDEX ix_achievements_category ON public.achievements USING btree (category);

        CREATE UNIQUE INDEX ix_achievements_code ON public.achievements USING btree (code);

        CREATE INDEX ix_achievements_id ON public.achievements USING btree (id);

        CREATE INDEX ix_achievements_is_active ON public.achievements USING btree (is_active);

        CREATE INDEX ix_adaptive_learning_sessions_id ON public.adaptive_learning_sessions USING btree (id);

        CREATE INDEX ix_attendance_history_id ON public.attendance_history USING btree (id);

        CREATE INDEX ix_attendance_id ON public.attendance USING btree (id);

        CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);

        CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);

        CREATE INDEX ix_audit_logs_timestamp ON public.audit_logs USING btree ("timestamp");

        CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);

        CREATE INDEX ix_belt_promotions_id ON public.belt_promotions USING btree (id);

        CREATE INDEX ix_belt_promotions_promoted_at ON public.belt_promotions USING btree (promoted_at);

        CREATE INDEX ix_belt_promotions_to_belt ON public.belt_promotions USING btree (to_belt);

        CREATE INDEX ix_belt_promotions_user_license_id ON public.belt_promotions USING btree (user_license_id);

        CREATE INDEX ix_bookings_enrollment_id ON public.bookings USING btree (enrollment_id);

        CREATE INDEX ix_bookings_id ON public.bookings USING btree (id);

        CREATE INDEX ix_campus_schedule_configs_campus_id ON public.campus_schedule_configs USING btree (campus_id);

        CREATE INDEX ix_campus_schedule_configs_id ON public.campus_schedule_configs USING btree (id);

        CREATE INDEX ix_campus_schedule_configs_tournament_id ON public.campus_schedule_configs USING btree (tournament_id);

        CREATE INDEX ix_campuses_id ON public.campuses USING btree (id);

        CREATE INDEX ix_coupon_usages_id ON public.coupon_usages USING btree (id);

        CREATE UNIQUE INDEX ix_coupons_code ON public.coupons USING btree (code);

        CREATE INDEX ix_coupons_id ON public.coupons USING btree (id);

        CREATE INDEX ix_credit_transactions_created_at ON public.credit_transactions USING btree (created_at);

        CREATE INDEX ix_credit_transactions_id ON public.credit_transactions USING btree (id);

        CREATE UNIQUE INDEX ix_credit_transactions_idempotency_key ON public.credit_transactions USING btree (idempotency_key);

        CREATE INDEX ix_credit_transactions_user_id ON public.credit_transactions USING btree (user_id);

        CREATE INDEX ix_credit_transactions_user_license_id ON public.credit_transactions USING btree (user_license_id);

        CREATE INDEX ix_feedback_id ON public.feedback USING btree (id);

        CREATE INDEX ix_football_skill_assessments_id ON public.football_skill_assessments USING btree (id);

        CREATE INDEX ix_game_configurations_game_preset_id ON public.game_configurations USING btree (game_preset_id);

        CREATE INDEX ix_game_configurations_id ON public.game_configurations USING btree (id);

        CREATE UNIQUE INDEX ix_game_configurations_semester_id ON public.game_configurations USING btree (semester_id);

        CREATE UNIQUE INDEX ix_game_presets_code ON public.game_presets USING btree (code);

        CREATE INDEX ix_game_presets_game_config ON public.game_presets USING btree (game_config);

        CREATE INDEX ix_game_presets_id ON public.game_presets USING btree (id);

        CREATE INDEX ix_game_presets_is_active ON public.game_presets USING btree (is_active);

        CREATE INDEX ix_game_presets_is_locked ON public.game_presets USING btree (is_locked);

        CREATE INDEX ix_game_presets_is_recommended ON public.game_presets USING btree (is_recommended);

        CREATE INDEX ix_groups_id ON public.groups USING btree (id);

        CREATE INDEX ix_instructor_assignment_requests_id ON public.instructor_assignment_requests USING btree (id);

        CREATE INDEX ix_instructor_assignments_id ON public.instructor_assignments USING btree (id);

        CREATE INDEX ix_instructor_availability_windows_id ON public.instructor_availability_windows USING btree (id);

        CREATE INDEX ix_instructor_positions_id ON public.instructor_positions USING btree (id);

        CREATE INDEX ix_instructor_session_reviews_id ON public.instructor_session_reviews USING btree (id);

        CREATE INDEX ix_instructor_specialization_availability_id ON public.instructor_specialization_availability USING btree (id);

        CREATE INDEX ix_instructor_specializations_id ON public.instructor_specializations USING btree (id);

        CREATE UNIQUE INDEX ix_invitation_codes_code ON public.invitation_codes USING btree (code);

        CREATE INDEX ix_invitation_codes_id ON public.invitation_codes USING btree (id);

        CREATE INDEX ix_invoice_requests_id ON public.invoice_requests USING btree (id);

        CREATE UNIQUE INDEX ix_invoice_requests_payment_reference ON public.invoice_requests USING btree (payment_reference);

        CREATE INDEX ix_license_metadata_id ON public.license_metadata USING btree (id);

        CREATE INDEX ix_license_progressions_id ON public.license_progressions USING btree (id);

        CREATE INDEX ix_location_master_instructors_id ON public.location_master_instructors USING btree (id);

        CREATE INDEX ix_locations_id ON public.locations USING btree (id);

        CREATE INDEX ix_messages_id ON public.messages USING btree (id);

        CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);

        CREATE INDEX ix_position_applications_id ON public.position_applications USING btree (id);

        CREATE INDEX ix_project_enrollment_quizzes_id ON public.project_enrollment_quizzes USING btree (id);

        CREATE INDEX ix_project_enrollments_id ON public.project_enrollments USING btree (id);

        CREATE INDEX ix_project_milestone_progress_id ON public.project_milestone_progress USING btree (id);

        CREATE INDEX ix_project_milestones_id ON public.project_milestones USING btree (id);

        CREATE INDEX ix_project_quizzes_id ON public.project_quizzes USING btree (id);

        CREATE INDEX ix_project_sessions_id ON public.project_sessions USING btree (id);

        CREATE INDEX ix_projects_id ON public.projects USING btree (id);

        CREATE INDEX ix_question_metadata_id ON public.question_metadata USING btree (id);

        CREATE INDEX ix_quiz_answer_options_id ON public.quiz_answer_options USING btree (id);

        CREATE INDEX ix_quiz_attempts_id ON public.quiz_attempts USING btree (id);

        CREATE INDEX ix_quiz_questions_id ON public.quiz_questions USING btree (id);

        CREATE INDEX ix_quiz_user_answers_id ON public.quiz_user_answers USING btree (id);

        CREATE INDEX ix_quizzes_id ON public.quizzes USING btree (id);

        CREATE INDEX ix_semester_enrollments_id ON public.semester_enrollments USING btree (id);

        CREATE INDEX ix_semester_enrollments_is_active ON public.semester_enrollments USING btree (is_active);

        CREATE INDEX ix_semester_enrollments_payment_verified ON public.semester_enrollments USING btree (payment_verified);

        CREATE INDEX ix_semester_enrollments_semester_id ON public.semester_enrollments USING btree (semester_id);

        CREATE INDEX ix_semester_enrollments_tournament_checked_in_at ON public.semester_enrollments USING btree (tournament_checked_in_at);

        CREATE INDEX ix_semester_enrollments_user_id ON public.semester_enrollments USING btree (user_id);

        CREATE INDEX ix_semester_enrollments_user_license_id ON public.semester_enrollments USING btree (user_license_id);

        CREATE INDEX ix_semesters_age_group ON public.semesters USING btree (age_group);

        CREATE INDEX ix_semesters_campus_id ON public.semesters USING btree (campus_id);

        CREATE UNIQUE INDEX ix_semesters_code ON public.semesters USING btree (code);

        CREATE INDEX ix_semesters_id ON public.semesters USING btree (id);

        CREATE INDEX ix_semesters_location_id ON public.semesters USING btree (location_id);

        CREATE INDEX ix_semesters_specialization_type ON public.semesters USING btree (specialization_type);

        CREATE INDEX ix_semesters_status ON public.semesters USING btree (status);

        CREATE INDEX ix_semesters_tournament_status ON public.semesters USING btree (tournament_status);

        CREATE INDEX ix_session_group_assignments_id ON public.session_group_assignments USING btree (id);

        CREATE INDEX ix_session_group_assignments_session_id ON public.session_group_assignments USING btree (session_id);

        CREATE INDEX ix_session_group_students_id ON public.session_group_students USING btree (id);

        CREATE INDEX ix_session_group_students_session_group_id ON public.session_group_students USING btree (session_group_id);

        CREATE INDEX ix_session_quizzes_id ON public.session_quizzes USING btree (id);

        CREATE INDEX ix_sessions_id ON public.sessions USING btree (id);

        CREATE INDEX ix_sessions_is_tournament_game ON public.sessions USING btree (is_tournament_game);

        CREATE INDEX ix_skill_point_conversion_rates_id ON public.skill_point_conversion_rates USING btree (id);

        CREATE INDEX ix_skill_rewards_created_at ON public.skill_rewards USING btree (created_at);

        CREATE INDEX ix_skill_rewards_id ON public.skill_rewards USING btree (id);

        CREATE INDEX ix_skill_rewards_source ON public.skill_rewards USING btree (source_type, source_id);

        CREATE INDEX ix_skill_rewards_user_id ON public.skill_rewards USING btree (user_id);

        CREATE INDEX ix_student_performance_reviews_id ON public.student_performance_reviews USING btree (id);

        CREATE INDEX ix_system_events_created_at ON public.system_events USING btree (created_at);

        CREATE INDEX ix_system_events_event_type ON public.system_events USING btree (event_type);

        CREATE INDEX ix_system_events_id ON public.system_events USING btree (id);

        CREATE INDEX ix_system_events_level ON public.system_events USING btree (level);

        CREATE INDEX ix_system_events_open_created ON public.system_events USING btree (created_at) WHERE (resolved = false);

        CREATE INDEX ix_system_events_resolved ON public.system_events USING btree (resolved);

        CREATE INDEX ix_system_events_resolved_created ON public.system_events USING btree (resolved, created_at);

        CREATE INDEX ix_system_events_user_event_type_created ON public.system_events USING btree (user_id, event_type, created_at);

        CREATE INDEX ix_system_events_user_id ON public.system_events USING btree (user_id);

        CREATE INDEX ix_team_members_id ON public.team_members USING btree (id);

        CREATE INDEX ix_team_members_team_id ON public.team_members USING btree (team_id);

        CREATE INDEX ix_team_members_user_id ON public.team_members USING btree (user_id);

        CREATE UNIQUE INDEX ix_teams_code ON public.teams USING btree (code);

        CREATE INDEX ix_teams_id ON public.teams USING btree (id);

        CREATE INDEX ix_tournament_badges_badge_category ON public.tournament_badges USING btree (badge_category);

        CREATE INDEX ix_tournament_badges_badge_type ON public.tournament_badges USING btree (badge_type);

        CREATE INDEX ix_tournament_badges_id ON public.tournament_badges USING btree (id);

        CREATE INDEX ix_tournament_badges_semester_id ON public.tournament_badges USING btree (semester_id);

        CREATE INDEX ix_tournament_badges_user_id ON public.tournament_badges USING btree (user_id);

        CREATE INDEX ix_tournament_configurations_id ON public.tournament_configurations USING btree (id);

        CREATE UNIQUE INDEX ix_tournament_configurations_semester_id ON public.tournament_configurations USING btree (semester_id);

        CREATE INDEX ix_tournament_configurations_tournament_type_id ON public.tournament_configurations USING btree (tournament_type_id);

        CREATE INDEX ix_tournament_participations_id ON public.tournament_participations USING btree (id);

        CREATE INDEX ix_tournament_participations_semester_id ON public.tournament_participations USING btree (semester_id);

        CREATE INDEX ix_tournament_participations_user_id ON public.tournament_participations USING btree (user_id);

        CREATE INDEX ix_tournament_rankings_id ON public.tournament_rankings USING btree (id);

        CREATE INDEX ix_tournament_rankings_tournament_id ON public.tournament_rankings USING btree (tournament_id);

        CREATE INDEX ix_tournament_reward_configs_id ON public.tournament_reward_configs USING btree (id);

        CREATE UNIQUE INDEX ix_tournament_reward_configs_semester_id ON public.tournament_reward_configs USING btree (semester_id);

        CREATE INDEX ix_tournament_rewards_id ON public.tournament_rewards USING btree (id);

        CREATE INDEX ix_tournament_rewards_tournament_id ON public.tournament_rewards USING btree (tournament_id);

        CREATE INDEX ix_tournament_skill_mappings_id ON public.tournament_skill_mappings USING btree (id);

        CREATE INDEX ix_tournament_skill_mappings_semester_id ON public.tournament_skill_mappings USING btree (semester_id);

        CREATE INDEX ix_tournament_stats_id ON public.tournament_stats USING btree (id);

        CREATE UNIQUE INDEX ix_tournament_stats_tournament_id ON public.tournament_stats USING btree (tournament_id);

        CREATE INDEX ix_tournament_status_history_id ON public.tournament_status_history USING btree (id);

        CREATE INDEX ix_tournament_status_history_tournament_id ON public.tournament_status_history USING btree (tournament_id);

        CREATE INDEX ix_tournament_team_enrollments_id ON public.tournament_team_enrollments USING btree (id);

        CREATE INDEX ix_tournament_team_enrollments_semester_id ON public.tournament_team_enrollments USING btree (semester_id);

        CREATE INDEX ix_tournament_team_enrollments_team_id ON public.tournament_team_enrollments USING btree (team_id);

        CREATE UNIQUE INDEX ix_tournament_types_code ON public.tournament_types USING btree (code);

        CREATE INDEX ix_tournament_types_id ON public.tournament_types USING btree (id);

        CREATE INDEX ix_user_achievements_id ON public.user_achievements USING btree (id);

        CREATE INDEX ix_user_licenses_id ON public.user_licenses USING btree (id);

        CREATE UNIQUE INDEX ix_user_licenses_payment_reference_code ON public.user_licenses USING btree (payment_reference_code);

        CREATE INDEX ix_user_question_performance_id ON public.user_question_performance USING btree (id);

        CREATE INDEX ix_user_stats_id ON public.user_stats USING btree (id);

        CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);

        CREATE INDEX ix_users_id ON public.users USING btree (id);

        CREATE INDEX ix_xp_transactions_created_at ON public.xp_transactions USING btree (created_at);

        CREATE INDEX ix_xp_transactions_id ON public.xp_transactions USING btree (id);

        CREATE INDEX ix_xp_transactions_idempotency_key ON public.xp_transactions USING btree (idempotency_key);

        CREATE INDEX ix_xp_transactions_user_id ON public.xp_transactions USING btree (user_id);

        CREATE UNIQUE INDEX uq_active_booking ON public.bookings USING btree (user_id, session_id) WHERE (status <> 'CANCELLED'::public.bookingstatus);

        CREATE UNIQUE INDEX uq_active_enrollment ON public.semester_enrollments USING btree (user_id, semester_id) WHERE (is_active = true);

        CREATE UNIQUE INDEX uq_user_tournament_badge ON public.tournament_badges USING btree (user_id, semester_id, badge_type);

        CREATE UNIQUE INDEX uq_waitlist_position ON public.bookings USING btree (session_id, waitlist_position) WHERE (status = 'WAITLISTED'::public.bookingstatus);

        CREATE UNIQUE INDEX uq_xp_transaction_idempotency ON public.xp_transactions USING btree (idempotency_key) WHERE (idempotency_key IS NOT NULL);

        ALTER TABLE ONLY public.adaptive_learning_sessions
            ADD CONSTRAINT adaptive_learning_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT attendance_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT attendance_change_requested_by_fkey FOREIGN KEY (change_requested_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.attendance_history
            ADD CONSTRAINT attendance_history_attendance_id_fkey FOREIGN KEY (attendance_id) REFERENCES public.attendance(id);

        ALTER TABLE ONLY public.attendance_history
            ADD CONSTRAINT attendance_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT attendance_marked_by_fkey FOREIGN KEY (marked_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT attendance_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.attendance
            ADD CONSTRAINT attendance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.audit_logs
            ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.belt_promotions
            ADD CONSTRAINT belt_promotions_promoted_by_fkey FOREIGN KEY (promoted_by) REFERENCES public.users(id) ON DELETE RESTRICT;

        ALTER TABLE ONLY public.belt_promotions
            ADD CONSTRAINT belt_promotions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.bookings
            ADD CONSTRAINT bookings_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.semester_enrollments(id);

        ALTER TABLE ONLY public.bookings
            ADD CONSTRAINT bookings_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.bookings
            ADD CONSTRAINT bookings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.campus_schedule_configs
            ADD CONSTRAINT campus_schedule_configs_campus_id_fkey FOREIGN KEY (campus_id) REFERENCES public.campuses(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.campus_schedule_configs
            ADD CONSTRAINT campus_schedule_configs_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.campuses
            ADD CONSTRAINT campuses_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.certificate_templates
            ADD CONSTRAINT certificate_templates_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);

        ALTER TABLE ONLY public.coupon_usages
            ADD CONSTRAINT coupon_usages_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.coupon_usages
            ADD CONSTRAINT coupon_usages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.credit_transactions
            ADD CONSTRAINT credit_transactions_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.semester_enrollments(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.credit_transactions
            ADD CONSTRAINT credit_transactions_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.credit_transactions
            ADD CONSTRAINT credit_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.credit_transactions
            ADD CONSTRAINT credit_transactions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.feedback
            ADD CONSTRAINT feedback_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.feedback
            ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.game_presets
            ADD CONSTRAINT fk_game_presets_created_by FOREIGN KEY (created_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.football_skill_assessments
            ADD CONSTRAINT football_skill_assessments_assessed_by_fkey FOREIGN KEY (assessed_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.football_skill_assessments
            ADD CONSTRAINT football_skill_assessments_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.game_configurations
            ADD CONSTRAINT game_configurations_game_preset_id_fkey FOREIGN KEY (game_preset_id) REFERENCES public.game_presets(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.game_configurations
            ADD CONSTRAINT game_configurations_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.group_users
            ADD CONSTRAINT group_users_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);

        ALTER TABLE ONLY public.group_users
            ADD CONSTRAINT group_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.groups
            ADD CONSTRAINT groups_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);

        ALTER TABLE ONLY public.instructor_assignment_requests
            ADD CONSTRAINT instructor_assignment_requests_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_assignment_requests
            ADD CONSTRAINT instructor_assignment_requests_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_assignment_requests
            ADD CONSTRAINT instructor_assignment_requests_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.instructor_assignment_requests
            ADD CONSTRAINT instructor_assignment_requests_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_assignments
            ADD CONSTRAINT instructor_assignments_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.instructor_assignments
            ADD CONSTRAINT instructor_assignments_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_assignments
            ADD CONSTRAINT instructor_assignments_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_availability_windows
            ADD CONSTRAINT instructor_availability_windows_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_positions
            ADD CONSTRAINT instructor_positions_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_positions
            ADD CONSTRAINT instructor_positions_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_session_reviews
            ADD CONSTRAINT instructor_session_reviews_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.instructor_session_reviews
            ADD CONSTRAINT instructor_session_reviews_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.instructor_session_reviews
            ADD CONSTRAINT instructor_session_reviews_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.instructor_specialization_availability
            ADD CONSTRAINT instructor_specialization_availability_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.instructor_specializations
            ADD CONSTRAINT instructor_specializations_certified_by_fkey FOREIGN KEY (certified_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.instructor_specializations
            ADD CONSTRAINT instructor_specializations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.invitation_codes
            ADD CONSTRAINT invitation_codes_created_by_admin_id_fkey FOREIGN KEY (created_by_admin_id) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.invitation_codes
            ADD CONSTRAINT invitation_codes_used_by_user_id_fkey FOREIGN KEY (used_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.invoice_requests
            ADD CONSTRAINT invoice_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.issued_certificates
            ADD CONSTRAINT issued_certificates_certificate_template_id_fkey FOREIGN KEY (certificate_template_id) REFERENCES public.certificate_templates(id);

        ALTER TABLE ONLY public.issued_certificates
            ADD CONSTRAINT issued_certificates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.license_progressions
            ADD CONSTRAINT license_progressions_advanced_by_fkey FOREIGN KEY (advanced_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.license_progressions
            ADD CONSTRAINT license_progressions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id);

        ALTER TABLE ONLY public.location_master_instructors
            ADD CONSTRAINT location_master_instructors_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.location_master_instructors
            ADD CONSTRAINT location_master_instructors_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.location_master_instructors
            ADD CONSTRAINT location_master_instructors_source_position_id_fkey FOREIGN KEY (source_position_id) REFERENCES public.instructor_positions(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.messages
            ADD CONSTRAINT messages_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.messages
            ADD CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.module_components
            ADD CONSTRAINT module_components_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.modules(id);

        ALTER TABLE ONLY public.modules
            ADD CONSTRAINT modules_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);

        ALTER TABLE ONLY public.modules
            ADD CONSTRAINT modules_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);

        ALTER TABLE ONLY public.notifications
            ADD CONSTRAINT notifications_related_booking_id_fkey FOREIGN KEY (related_booking_id) REFERENCES public.bookings(id);

        ALTER TABLE ONLY public.notifications
            ADD CONSTRAINT notifications_related_request_id_fkey FOREIGN KEY (related_request_id) REFERENCES public.instructor_assignment_requests(id);

        ALTER TABLE ONLY public.notifications
            ADD CONSTRAINT notifications_related_semester_id_fkey FOREIGN KEY (related_semester_id) REFERENCES public.semesters(id);

        ALTER TABLE ONLY public.notifications
            ADD CONSTRAINT notifications_related_session_id_fkey FOREIGN KEY (related_session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.notifications
            ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.position_applications
            ADD CONSTRAINT position_applications_applicant_id_fkey FOREIGN KEY (applicant_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.position_applications
            ADD CONSTRAINT position_applications_position_id_fkey FOREIGN KEY (position_id) REFERENCES public.instructor_positions(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.project_enrollment_quizzes
            ADD CONSTRAINT project_enrollment_quizzes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);

        ALTER TABLE ONLY public.project_enrollment_quizzes
            ADD CONSTRAINT project_enrollment_quizzes_quiz_attempt_id_fkey FOREIGN KEY (quiz_attempt_id) REFERENCES public.quiz_attempts(id);

        ALTER TABLE ONLY public.project_enrollment_quizzes
            ADD CONSTRAINT project_enrollment_quizzes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.project_enrollments
            ADD CONSTRAINT project_enrollments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);

        ALTER TABLE ONLY public.project_enrollments
            ADD CONSTRAINT project_enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.project_milestone_progress
            ADD CONSTRAINT project_milestone_progress_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.project_enrollments(id);

        ALTER TABLE ONLY public.project_milestone_progress
            ADD CONSTRAINT project_milestone_progress_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);

        ALTER TABLE ONLY public.project_milestones
            ADD CONSTRAINT project_milestones_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);

        ALTER TABLE ONLY public.project_quizzes
            ADD CONSTRAINT project_quizzes_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);

        ALTER TABLE ONLY public.project_quizzes
            ADD CONSTRAINT project_quizzes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);

        ALTER TABLE ONLY public.project_quizzes
            ADD CONSTRAINT project_quizzes_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);

        ALTER TABLE ONLY public.project_sessions
            ADD CONSTRAINT project_sessions_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);

        ALTER TABLE ONLY public.project_sessions
            ADD CONSTRAINT project_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);

        ALTER TABLE ONLY public.project_sessions
            ADD CONSTRAINT project_sessions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.projects
            ADD CONSTRAINT projects_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.projects
            ADD CONSTRAINT projects_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);

        ALTER TABLE ONLY public.question_metadata
            ADD CONSTRAINT question_metadata_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);

        ALTER TABLE ONLY public.quiz_answer_options
            ADD CONSTRAINT quiz_answer_options_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);

        ALTER TABLE ONLY public.quiz_attempts
            ADD CONSTRAINT quiz_attempts_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);

        ALTER TABLE ONLY public.quiz_attempts
            ADD CONSTRAINT quiz_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.quiz_questions
            ADD CONSTRAINT quiz_questions_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);

        ALTER TABLE ONLY public.quiz_user_answers
            ADD CONSTRAINT quiz_user_answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.quiz_attempts(id);

        ALTER TABLE ONLY public.quiz_user_answers
            ADD CONSTRAINT quiz_user_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);

        ALTER TABLE ONLY public.quiz_user_answers
            ADD CONSTRAINT quiz_user_answers_selected_option_id_fkey FOREIGN KEY (selected_option_id) REFERENCES public.quiz_answer_options(id);

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_age_category_overridden_by_fkey FOREIGN KEY (age_category_overridden_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_payment_verified_by_fkey FOREIGN KEY (payment_verified_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.semester_enrollments
            ADD CONSTRAINT semester_enrollments_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.semester_instructors
            ADD CONSTRAINT semester_instructors_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.semester_instructors
            ADD CONSTRAINT semester_instructors_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.semesters
            ADD CONSTRAINT semesters_campus_id_fkey FOREIGN KEY (campus_id) REFERENCES public.campuses(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.semesters
            ADD CONSTRAINT semesters_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.semesters
            ADD CONSTRAINT semesters_master_instructor_id_fkey FOREIGN KEY (master_instructor_id) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.session_group_assignments
            ADD CONSTRAINT session_group_assignments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.session_group_assignments
            ADD CONSTRAINT session_group_assignments_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.session_group_assignments
            ADD CONSTRAINT session_group_assignments_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.session_group_students
            ADD CONSTRAINT session_group_students_session_group_id_fkey FOREIGN KEY (session_group_id) REFERENCES public.session_group_assignments(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.session_group_students
            ADD CONSTRAINT session_group_students_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.session_quizzes
            ADD CONSTRAINT session_quizzes_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.session_quizzes
            ADD CONSTRAINT session_quizzes_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.sessions
            ADD CONSTRAINT sessions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);

        ALTER TABLE ONLY public.sessions
            ADD CONSTRAINT sessions_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.sessions
            ADD CONSTRAINT sessions_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);

        ALTER TABLE ONLY public.skill_rewards
            ADD CONSTRAINT skill_rewards_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.specialization_progress
            ADD CONSTRAINT specialization_progress_specialization_id_fkey FOREIGN KEY (specialization_id) REFERENCES public.specializations(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.specialization_progress
            ADD CONSTRAINT specialization_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.student_performance_reviews
            ADD CONSTRAINT student_performance_reviews_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.student_performance_reviews
            ADD CONSTRAINT student_performance_reviews_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);

        ALTER TABLE ONLY public.student_performance_reviews
            ADD CONSTRAINT student_performance_reviews_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.system_events
            ADD CONSTRAINT system_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.team_members
            ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.team_members
            ADD CONSTRAINT team_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.teams
            ADD CONSTRAINT teams_captain_user_id_fkey FOREIGN KEY (captain_user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.tournament_badges
            ADD CONSTRAINT tournament_badges_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_badges
            ADD CONSTRAINT tournament_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_configurations
            ADD CONSTRAINT tournament_configurations_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_configurations
            ADD CONSTRAINT tournament_configurations_tournament_type_id_fkey FOREIGN KEY (tournament_type_id) REFERENCES public.tournament_types(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.tournament_participations
            ADD CONSTRAINT tournament_participations_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_participations
            ADD CONSTRAINT tournament_participations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_rankings
            ADD CONSTRAINT tournament_rankings_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_rankings
            ADD CONSTRAINT tournament_rankings_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_rankings
            ADD CONSTRAINT tournament_rankings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_reward_configs
            ADD CONSTRAINT tournament_reward_configs_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_rewards
            ADD CONSTRAINT tournament_rewards_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_skill_mappings
            ADD CONSTRAINT tournament_skill_mappings_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_stats
            ADD CONSTRAINT tournament_stats_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_status_history
            ADD CONSTRAINT tournament_status_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.tournament_status_history
            ADD CONSTRAINT tournament_status_history_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id);

        ALTER TABLE ONLY public.tournament_team_enrollments
            ADD CONSTRAINT tournament_team_enrollments_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.tournament_team_enrollments
            ADD CONSTRAINT tournament_team_enrollments_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;

        ALTER TABLE ONLY public.user_achievements
            ADD CONSTRAINT user_achievements_achievement_id_fkey FOREIGN KEY (achievement_id) REFERENCES public.achievements(id);

        ALTER TABLE ONLY public.user_achievements
            ADD CONSTRAINT user_achievements_specialization_id_fkey FOREIGN KEY (specialization_id) REFERENCES public.specializations(id);

        ALTER TABLE ONLY public.user_achievements
            ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.user_licenses
            ADD CONSTRAINT user_licenses_motivation_assessed_by_fkey FOREIGN KEY (motivation_assessed_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.user_licenses
            ADD CONSTRAINT user_licenses_skills_updated_by_fkey FOREIGN KEY (skills_updated_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.user_licenses
            ADD CONSTRAINT user_licenses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.user_module_progresses
            ADD CONSTRAINT user_module_progresses_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.modules(id);

        ALTER TABLE ONLY public.user_module_progresses
            ADD CONSTRAINT user_module_progresses_user_track_progress_id_fkey FOREIGN KEY (user_track_progress_id) REFERENCES public.user_track_progresses(id);

        ALTER TABLE ONLY public.user_question_performance
            ADD CONSTRAINT user_question_performance_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);

        ALTER TABLE ONLY public.user_question_performance
            ADD CONSTRAINT user_question_performance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.user_stats
            ADD CONSTRAINT user_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.user_track_progresses
            ADD CONSTRAINT user_track_progresses_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.issued_certificates(id);

        ALTER TABLE ONLY public.user_track_progresses
            ADD CONSTRAINT user_track_progresses_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);

        ALTER TABLE ONLY public.user_track_progresses
            ADD CONSTRAINT user_track_progresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

        ALTER TABLE ONLY public.users
            ADD CONSTRAINT users_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.users
            ADD CONSTRAINT users_payment_verified_by_fkey FOREIGN KEY (payment_verified_by) REFERENCES public.users(id);

        ALTER TABLE ONLY public.xp_transactions
            ADD CONSTRAINT xp_transactions_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE SET NULL;

        ALTER TABLE ONLY public.xp_transactions
            ADD CONSTRAINT xp_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

    """)



def downgrade() -> None:
    """
    Drop all schema objects.
    Note: This is a complete schema wipe - use with extreme caution.
    """
    # Drop all tables (CASCADE will handle foreign keys)
    op.execute("""
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO postgres;
        GRANT ALL ON SCHEMA public TO public;
    """)
