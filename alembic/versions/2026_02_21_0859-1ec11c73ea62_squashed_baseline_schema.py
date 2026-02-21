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

        CREATE SEQUENCE public.attendance_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.campus_schedule_configs_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE TABLE public.coupon_usages (
            id integer NOT NULL,
            coupon_id integer NOT NULL,
            user_id integer NOT NULL,
            credits_awarded integer NOT NULL,
            used_at timestamp with time zone DEFAULT now() NOT NULL
        );

        CREATE SEQUENCE public.coupon_usages_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.coupons_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE TABLE public.game_configurations (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            game_preset_id integer,
            game_config jsonb,
            game_config_overrides jsonb,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        );

        CREATE SEQUENCE public.game_configurations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.game_presets_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.instructor_assignment_requests_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.instructor_assignments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.instructor_availability_windows_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.instructor_positions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.instructor_specialization_availability_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.invitation_codes_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.invoice_requests_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.location_master_instructors_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.locations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE TABLE public.position_applications (
            id integer NOT NULL,
            position_id integer NOT NULL,
            applicant_id integer NOT NULL,
            application_message text NOT NULL,
            status public.applicationstatus NOT NULL,
            reviewed_at timestamp with time zone,
            created_at timestamp with time zone DEFAULT now() NOT NULL
        );

        CREATE SEQUENCE public.position_applications_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.projects_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.semester_enrollments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.semesters_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        CREATE TABLE public.session_group_assignments (
            id integer NOT NULL,
            session_id integer NOT NULL,
            group_number integer NOT NULL,
            instructor_id integer NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            created_by integer
        );

        CREATE SEQUENCE public.session_group_assignments_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        CREATE TABLE public.session_group_students (
            id integer NOT NULL,
            session_group_id integer NOT NULL,
            student_id integer NOT NULL,
            assigned_at timestamp with time zone DEFAULT now() NOT NULL
        );

        CREATE SEQUENCE public.session_group_students_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.sessions_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE TABLE public.specializations (
            id character varying(50) NOT NULL,
            is_active boolean NOT NULL,
            created_at timestamp without time zone NOT NULL
        );

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

        CREATE SEQUENCE public.tournament_configurations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.tournament_participations_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE TABLE public.tournament_reward_configs (
            id integer NOT NULL,
            semester_id integer NOT NULL,
            reward_policy_name character varying(100) NOT NULL,
            reward_policy_snapshot jsonb,
            reward_config jsonb,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        );

        COMMENT ON COLUMN public.tournament_reward_configs.reward_config IS 'Detailed reward configuration:
                - skill_mappings: List of skills with weights, categories, enabled flags
                - first_place, second_place, third_place: Placement-based rewards (badges, credits, XP)
                - top_25_percent: Dynamic rewards for top performers
                - participation: Participation rewards (badges, credits, XP)
                - template_name: Template name if using preset
                - custom_config: Whether this is a custom configuration
                ';

        CREATE SEQUENCE public.tournament_reward_configs_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.tournament_types_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.user_licenses_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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

        CREATE SEQUENCE public.users_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

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
