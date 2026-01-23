--
-- PostgreSQL database dump
--

\restrict bMwg13hEs75GkGgiblkCkqHV351l8ExyVxhRBhjI0dYqjNwabYTcV5srZZHJ19J

-- Dumped from database version 14.19 (Homebrew)
-- Dumped by pg_dump version 14.19 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: applicationstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.applicationstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'DECLINED'
);


ALTER TYPE public.applicationstatus OWNER TO postgres;

--
-- Name: assignmentrequeststatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.assignmentrequeststatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'DECLINED',
    'CANCELLED',
    'EXPIRED'
);


ALTER TYPE public.assignmentrequeststatus OWNER TO postgres;

--
-- Name: attendancestatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.attendancestatus AS ENUM (
    'present',
    'absent',
    'late',
    'excused'
);


ALTER TYPE public.attendancestatus OWNER TO postgres;

--
-- Name: bookingstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.bookingstatus AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED',
    'WAITLISTED'
);


ALTER TYPE public.bookingstatus OWNER TO postgres;

--
-- Name: confirmationstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.confirmationstatus AS ENUM (
    'pending_confirmation',
    'confirmed',
    'disputed'
);


ALTER TYPE public.confirmationstatus OWNER TO postgres;

--
-- Name: coupontype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.coupontype AS ENUM (
    'BONUS_CREDITS',
    'PURCHASE_DISCOUNT_PERCENT',
    'PURCHASE_BONUS_CREDITS',
    'PERCENT',
    'FIXED',
    'CREDITS'
);


ALTER TYPE public.coupontype OWNER TO postgres;

--
-- Name: enrollmentstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.enrollmentstatus AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'WITHDRAWN'
);


ALTER TYPE public.enrollmentstatus OWNER TO postgres;

--
-- Name: locationtype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.locationtype AS ENUM (
    'PARTNER',
    'CENTER'
);


ALTER TYPE public.locationtype OWNER TO postgres;

--
-- Name: masterofferstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.masterofferstatus AS ENUM (
    'OFFERED',
    'ACCEPTED',
    'DECLINED',
    'EXPIRED'
);


ALTER TYPE public.masterofferstatus OWNER TO postgres;

--
-- Name: messagepriority; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.messagepriority AS ENUM (
    'LOW',
    'NORMAL',
    'HIGH',
    'URGENT'
);


ALTER TYPE public.messagepriority OWNER TO postgres;

--
-- Name: moduleprogressstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.moduleprogressstatus AS ENUM (
    'NOT_STARTED',
    'IN_PROGRESS',
    'COMPLETED',
    'FAILED'
);


ALTER TYPE public.moduleprogressstatus OWNER TO postgres;

--
-- Name: notificationtype; Type: TYPE; Schema: public; Owner: postgres
--

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


ALTER TYPE public.notificationtype OWNER TO postgres;

--
-- Name: positionstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.positionstatus AS ENUM (
    'OPEN',
    'FILLED',
    'CLOSED',
    'CANCELLED'
);


ALTER TYPE public.positionstatus OWNER TO postgres;

--
-- Name: questiontype; Type: TYPE; Schema: public; Owner: postgres
--

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


ALTER TYPE public.questiontype OWNER TO postgres;

--
-- Name: quizcategory; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.quizcategory AS ENUM (
    'GENERAL',
    'MARKETING',
    'ECONOMICS',
    'INFORMATICS',
    'SPORTS_PHYSIOLOGY',
    'NUTRITION',
    'LESSON'
);


ALTER TYPE public.quizcategory OWNER TO postgres;

--
-- Name: quizdifficulty; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.quizdifficulty AS ENUM (
    'EASY',
    'MEDIUM',
    'HARD'
);


ALTER TYPE public.quizdifficulty OWNER TO postgres;

--
-- Name: semester_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.semester_status AS ENUM (
    'DRAFT',
    'SEEKING_INSTRUCTOR',
    'INSTRUCTOR_ASSIGNED',
    'READY_FOR_ENROLLMENT',
    'ONGOING',
    'COMPLETED',
    'CANCELLED'
);


ALTER TYPE public.semester_status OWNER TO postgres;

--
-- Name: sessiontype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.sessiontype AS ENUM (
    'on_site',
    'virtual',
    'hybrid'
);


ALTER TYPE public.sessiontype OWNER TO postgres;

--
-- Name: specializationtype; Type: TYPE; Schema: public; Owner: postgres
--

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


ALTER TYPE public.specializationtype OWNER TO postgres;

--
-- Name: trackprogressstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.trackprogressstatus AS ENUM (
    'ENROLLED',
    'ACTIVE',
    'COMPLETED',
    'SUSPENDED',
    'DROPPED'
);


ALTER TYPE public.trackprogressstatus OWNER TO postgres;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'INSTRUCTOR',
    'STUDENT'
);


ALTER TYPE public.userrole OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: achievements; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.achievements OWNER TO postgres;

--
-- Name: achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.achievements_id_seq OWNER TO postgres;

--
-- Name: achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.achievements_id_seq OWNED BY public.achievements.id;


--
-- Name: adaptive_learning_sessions; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.adaptive_learning_sessions OWNER TO postgres;

--
-- Name: adaptive_learning_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.adaptive_learning_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.adaptive_learning_sessions_id_seq OWNER TO postgres;

--
-- Name: adaptive_learning_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.adaptive_learning_sessions_id_seq OWNED BY public.adaptive_learning_sessions.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: attendance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attendance (
    id integer NOT NULL,
    user_id integer NOT NULL,
    session_id integer NOT NULL,
    booking_id integer NOT NULL,
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


ALTER TABLE public.attendance OWNER TO postgres;

--
-- Name: COLUMN attendance.xp_earned; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.attendance.xp_earned IS 'XP earned for this attendance';


--
-- Name: attendance_history; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.attendance_history OWNER TO postgres;

--
-- Name: attendance_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attendance_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.attendance_history_id_seq OWNER TO postgres;

--
-- Name: attendance_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attendance_history_id_seq OWNED BY public.attendance_history.id;


--
-- Name: attendance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.attendance_id_seq OWNER TO postgres;

--
-- Name: attendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attendance_id_seq OWNED BY public.attendance.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.audit_logs_id_seq OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: belt_promotions; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.belt_promotions OWNER TO postgres;

--
-- Name: belt_promotions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.belt_promotions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.belt_promotions_id_seq OWNER TO postgres;

--
-- Name: belt_promotions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.belt_promotions_id_seq OWNED BY public.belt_promotions.id;


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.bookings OWNER TO postgres;

--
-- Name: bookings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bookings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.bookings_id_seq OWNER TO postgres;

--
-- Name: bookings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bookings_id_seq OWNED BY public.bookings.id;


--
-- Name: campuses; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.campuses OWNER TO postgres;

--
-- Name: campuses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.campuses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.campuses_id_seq OWNER TO postgres;

--
-- Name: campuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.campuses_id_seq OWNED BY public.campuses.id;


--
-- Name: certificate_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.certificate_templates (
    id uuid NOT NULL,
    track_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    design_template text,
    validation_rules json,
    created_at timestamp without time zone
);


ALTER TABLE public.certificate_templates OWNER TO postgres;

--
-- Name: coach_levels; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.coach_levels OWNER TO postgres;

--
-- Name: coach_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.coach_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.coach_levels_id_seq OWNER TO postgres;

--
-- Name: coach_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.coach_levels_id_seq OWNED BY public.coach_levels.id;


--
-- Name: coupon_usages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.coupon_usages (
    id integer NOT NULL,
    coupon_id integer NOT NULL,
    user_id integer NOT NULL,
    credits_awarded integer NOT NULL,
    used_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.coupon_usages OWNER TO postgres;

--
-- Name: COLUMN coupon_usages.credits_awarded; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.coupon_usages.credits_awarded IS 'Amount of credits awarded from this coupon';


--
-- Name: coupon_usages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.coupon_usages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.coupon_usages_id_seq OWNER TO postgres;

--
-- Name: coupon_usages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.coupon_usages_id_seq OWNED BY public.coupon_usages.id;


--
-- Name: coupons; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.coupons OWNER TO postgres;

--
-- Name: COLUMN coupons.requires_purchase; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.coupons.requires_purchase IS 'True if coupon can only be used during credit purchase';


--
-- Name: COLUMN coupons.requires_admin_approval; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.coupons.requires_admin_approval IS 'True if coupon requires admin approval after purchase';


--
-- Name: coupons_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.coupons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.coupons_id_seq OWNER TO postgres;

--
-- Name: coupons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.coupons_id_seq OWNED BY public.coupons.id;


--
-- Name: credit_transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.credit_transactions (
    id integer NOT NULL,
    user_id integer,
    user_license_id integer,
    transaction_type character varying(50) NOT NULL,
    amount integer NOT NULL,
    balance_after integer NOT NULL,
    description text,
    semester_id integer,
    enrollment_id integer,
    created_at timestamp without time zone NOT NULL,
    CONSTRAINT check_one_credit_reference CHECK ((((user_id IS NOT NULL) AND (user_license_id IS NULL)) OR ((user_id IS NULL) AND (user_license_id IS NOT NULL))))
);


ALTER TABLE public.credit_transactions OWNER TO postgres;

--
-- Name: credit_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.credit_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.credit_transactions_id_seq OWNER TO postgres;

--
-- Name: credit_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.credit_transactions_id_seq OWNED BY public.credit_transactions.id;


--
-- Name: feedback; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.feedback OWNER TO postgres;

--
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.feedback_id_seq OWNER TO postgres;

--
-- Name: feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;


--
-- Name: football_skill_assessments; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.football_skill_assessments OWNER TO postgres;

--
-- Name: football_skill_assessments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.football_skill_assessments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.football_skill_assessments_id_seq OWNER TO postgres;

--
-- Name: football_skill_assessments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.football_skill_assessments_id_seq OWNED BY public.football_skill_assessments.id;


--
-- Name: group_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_users (
    group_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.group_users OWNER TO postgres;

--
-- Name: groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    name character varying NOT NULL,
    description text,
    semester_id integer NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.groups OWNER TO postgres;

--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.groups_id_seq OWNER TO postgres;

--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: instructor_assignment_requests; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.instructor_assignment_requests OWNER TO postgres;

--
-- Name: COLUMN instructor_assignment_requests.semester_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.semester_id IS 'Semester needing an instructor';


--
-- Name: COLUMN instructor_assignment_requests.instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.instructor_id IS 'Instructor receiving the request';


--
-- Name: COLUMN instructor_assignment_requests.requested_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.requested_by IS 'Admin who sent the request';


--
-- Name: COLUMN instructor_assignment_requests.location_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.location_id IS 'Location for the assignment';


--
-- Name: COLUMN instructor_assignment_requests.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.status IS 'PENDING, ACCEPTED, DECLINED, CANCELLED, EXPIRED';


--
-- Name: COLUMN instructor_assignment_requests.responded_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.responded_at IS 'When instructor responded';


--
-- Name: COLUMN instructor_assignment_requests.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.expires_at IS 'Request expiration (optional)';


--
-- Name: COLUMN instructor_assignment_requests.request_message; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.request_message IS 'Message from admin to instructor';


--
-- Name: COLUMN instructor_assignment_requests.response_message; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.response_message IS 'Message from instructor (if declined, reason)';


--
-- Name: COLUMN instructor_assignment_requests.priority; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignment_requests.priority IS 'Higher number = higher priority (0-10)';


--
-- Name: instructor_assignment_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_assignment_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_assignment_requests_id_seq OWNER TO postgres;

--
-- Name: instructor_assignment_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_assignment_requests_id_seq OWNED BY public.instructor_assignment_requests.id;


--
-- Name: instructor_assignments; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.instructor_assignments OWNER TO postgres;

--
-- Name: COLUMN instructor_assignments.location_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.location_id IS 'Assignment location';


--
-- Name: COLUMN instructor_assignments.instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.instructor_id IS 'Assigned instructor';


--
-- Name: COLUMN instructor_assignments.specialization_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.specialization_type IS 'LFA_PLAYER, INTERNSHIP, etc.';


--
-- Name: COLUMN instructor_assignments.age_group; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.age_group IS 'PRE, YOUTH, AMATEUR, PRO';


--
-- Name: COLUMN instructor_assignments.year; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.year IS 'Year (e.g., 2026)';


--
-- Name: COLUMN instructor_assignments.time_period_start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.time_period_start IS 'Start period code (M01, Q1, etc.)';


--
-- Name: COLUMN instructor_assignments.time_period_end; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.time_period_end IS 'End period code (M06, Q2, etc.)';


--
-- Name: COLUMN instructor_assignments.is_master; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.is_master IS 'True if this is the master instructor';


--
-- Name: COLUMN instructor_assignments.assigned_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.assigned_by IS 'Master instructor who made assignment';


--
-- Name: COLUMN instructor_assignments.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.is_active IS 'Active assignment';


--
-- Name: COLUMN instructor_assignments.deactivated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_assignments.deactivated_at IS 'When assignment was deactivated';


--
-- Name: instructor_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_assignments_id_seq OWNER TO postgres;

--
-- Name: instructor_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_assignments_id_seq OWNED BY public.instructor_assignments.id;


--
-- Name: instructor_availability_windows; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.instructor_availability_windows OWNER TO postgres;

--
-- Name: COLUMN instructor_availability_windows.instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_availability_windows.instructor_id IS 'Instructor setting availability';


--
-- Name: COLUMN instructor_availability_windows.year; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_availability_windows.year IS 'Year (e.g., 2026)';


--
-- Name: COLUMN instructor_availability_windows.time_period; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_availability_windows.time_period IS 'Q1, Q2, Q3, Q4 or M01-M12';


--
-- Name: COLUMN instructor_availability_windows.is_available; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_availability_windows.is_available IS 'True if instructor is available for this window';


--
-- Name: COLUMN instructor_availability_windows.notes; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_availability_windows.notes IS 'Optional notes from instructor';


--
-- Name: instructor_availability_windows_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_availability_windows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_availability_windows_id_seq OWNER TO postgres;

--
-- Name: instructor_availability_windows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_availability_windows_id_seq OWNED BY public.instructor_availability_windows.id;


--
-- Name: instructor_positions; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.instructor_positions OWNER TO postgres;

--
-- Name: COLUMN instructor_positions.location_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.location_id IS 'Location for position';


--
-- Name: COLUMN instructor_positions.posted_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.posted_by IS 'Admin or master instructor who posted';


--
-- Name: COLUMN instructor_positions.is_master_position; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.is_master_position IS 'True if this is a master instructor opening, False for assistant positions';


--
-- Name: COLUMN instructor_positions.specialization_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.specialization_type IS 'LFA_PLAYER, INTERNSHIP, etc.';


--
-- Name: COLUMN instructor_positions.age_group; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.age_group IS 'PRE, YOUTH, AMATEUR, PRO';


--
-- Name: COLUMN instructor_positions.year; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.year IS 'Year (e.g., 2026)';


--
-- Name: COLUMN instructor_positions.time_period_start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.time_period_start IS 'Start period code (M01, Q1, etc.)';


--
-- Name: COLUMN instructor_positions.time_period_end; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.time_period_end IS 'End period code (M06, Q2, etc.)';


--
-- Name: COLUMN instructor_positions.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.description IS 'Job description and requirements';


--
-- Name: COLUMN instructor_positions.priority; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.priority IS '1=low, 5=medium, 10=high';


--
-- Name: COLUMN instructor_positions.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.status IS 'OPEN, FILLED, CLOSED, CANCELLED';


--
-- Name: COLUMN instructor_positions.application_deadline; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_positions.application_deadline IS 'Application deadline';


--
-- Name: instructor_positions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_positions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_positions_id_seq OWNER TO postgres;

--
-- Name: instructor_positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_positions_id_seq OWNED BY public.instructor_positions.id;


--
-- Name: instructor_session_reviews; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.instructor_session_reviews OWNER TO postgres;

--
-- Name: instructor_session_reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_session_reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_session_reviews_id_seq OWNER TO postgres;

--
-- Name: instructor_session_reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_session_reviews_id_seq OWNED BY public.instructor_session_reviews.id;


--
-- Name: instructor_specialization_availability; Type: TABLE; Schema: public; Owner: postgres
--

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
    CONSTRAINT check_time_period_code_format CHECK (((((time_period_code)::text ~~ 'Q_'::text) AND ((time_period_code)::text = ANY ((ARRAY['Q1'::character varying, 'Q2'::character varying, 'Q3'::character varying, 'Q4'::character varying])::text[]))) OR (((time_period_code)::text ~~ 'M__'::text) AND ((time_period_code)::text >= 'M01'::text) AND ((time_period_code)::text <= 'M12'::text)))),
    CONSTRAINT check_year_range CHECK (((year >= 2024) AND (year <= 2100)))
);


ALTER TABLE public.instructor_specialization_availability OWNER TO postgres;

--
-- Name: COLUMN instructor_specialization_availability.instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.instructor_id IS 'Instructor who sets this availability preference';


--
-- Name: COLUMN instructor_specialization_availability.specialization_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.specialization_type IS 'LFA_PLAYER_PRE, LFA_PLAYER_YOUTH, LFA_PLAYER_AMATEUR, LFA_PLAYER_PRO';


--
-- Name: COLUMN instructor_specialization_availability.time_period_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.time_period_code IS 'Q1-Q4 for quarterly, M01-M12 for monthly';


--
-- Name: COLUMN instructor_specialization_availability.year; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.year IS 'Year for which this availability applies (e.g., 2025)';


--
-- Name: COLUMN instructor_specialization_availability.location_city; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.location_city IS 'City where this availability applies (e.g., Budapest, Budaörs)';


--
-- Name: COLUMN instructor_specialization_availability.is_available; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.is_available IS 'True if instructor is available for this specialization in this time period';


--
-- Name: COLUMN instructor_specialization_availability.notes; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.instructor_specialization_availability.notes IS 'Optional notes from instructor about this availability';


--
-- Name: instructor_specialization_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_specialization_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_specialization_availability_id_seq OWNER TO postgres;

--
-- Name: instructor_specialization_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_specialization_availability_id_seq OWNED BY public.instructor_specialization_availability.id;


--
-- Name: instructor_specializations; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.instructor_specializations OWNER TO postgres;

--
-- Name: instructor_specializations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instructor_specializations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructor_specializations_id_seq OWNER TO postgres;

--
-- Name: instructor_specializations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instructor_specializations_id_seq OWNED BY public.instructor_specializations.id;


--
-- Name: internship_levels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.internship_levels (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    required_xp integer NOT NULL,
    required_sessions integer NOT NULL,
    total_hours integer NOT NULL,
    description text,
    license_title character varying(255) NOT NULL
);


ALTER TABLE public.internship_levels OWNER TO postgres;

--
-- Name: internship_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.internship_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.internship_levels_id_seq OWNER TO postgres;

--
-- Name: internship_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.internship_levels_id_seq OWNED BY public.internship_levels.id;


--
-- Name: invitation_codes; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.invitation_codes OWNER TO postgres;

--
-- Name: COLUMN invitation_codes.code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.code IS 'Unique invitation code';


--
-- Name: COLUMN invitation_codes.invited_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.invited_name IS 'Name of the person/organization receiving the code';


--
-- Name: COLUMN invitation_codes.invited_email; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.invited_email IS 'Optional: Email restriction - only this email can use the code';


--
-- Name: COLUMN invitation_codes.bonus_credits; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.bonus_credits IS 'Bonus credits to grant when code is used';


--
-- Name: COLUMN invitation_codes.is_used; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.is_used IS 'Whether the code has been used';


--
-- Name: COLUMN invitation_codes.used_by_user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.used_by_user_id IS 'User who redeemed this code';


--
-- Name: COLUMN invitation_codes.used_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.used_at IS 'When the code was redeemed';


--
-- Name: COLUMN invitation_codes.created_by_admin_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.created_by_admin_id IS 'Admin who created this code';


--
-- Name: COLUMN invitation_codes.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.expires_at IS 'Optional expiration date';


--
-- Name: COLUMN invitation_codes.notes; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invitation_codes.notes IS 'Admin notes about this invitation code';


--
-- Name: invitation_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.invitation_codes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.invitation_codes_id_seq OWNER TO postgres;

--
-- Name: invitation_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.invitation_codes_id_seq OWNED BY public.invitation_codes.id;


--
-- Name: invoice_requests; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.invoice_requests OWNER TO postgres;

--
-- Name: COLUMN invoice_requests.payment_reference; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.payment_reference IS 'Unique payment reference: LFA-YYYYMMDD-HHMMSS-ID-HASH (max 30 chars, SWIFT compatible)';


--
-- Name: COLUMN invoice_requests.amount_eur; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.amount_eur IS 'Amount in EUR';


--
-- Name: COLUMN invoice_requests.credit_amount; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.credit_amount IS 'Credit amount';


--
-- Name: COLUMN invoice_requests.specialization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.specialization IS 'Specialization type';


--
-- Name: COLUMN invoice_requests.coupon_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.coupon_code IS 'Applied coupon code (if any)';


--
-- Name: COLUMN invoice_requests.paid_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.paid_at IS 'When payment was made';


--
-- Name: COLUMN invoice_requests.verified_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.invoice_requests.verified_at IS 'When admin verified payment';


--
-- Name: invoice_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.invoice_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.invoice_requests_id_seq OWNER TO postgres;

--
-- Name: invoice_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.invoice_requests_id_seq OWNED BY public.invoice_requests.id;


--
-- Name: issued_certificates; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.issued_certificates OWNER TO postgres;

--
-- Name: license_metadata; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.license_metadata OWNER TO postgres;

--
-- Name: license_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.license_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.license_metadata_id_seq OWNER TO postgres;

--
-- Name: license_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.license_metadata_id_seq OWNED BY public.license_metadata.id;


--
-- Name: license_progressions; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.license_progressions OWNER TO postgres;

--
-- Name: license_progressions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.license_progressions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.license_progressions_id_seq OWNER TO postgres;

--
-- Name: license_progressions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.license_progressions_id_seq OWNED BY public.license_progressions.id;


--
-- Name: location_master_instructors; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.location_master_instructors OWNER TO postgres;

--
-- Name: COLUMN location_master_instructors.location_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.location_id IS 'Location for master instructor';


--
-- Name: COLUMN location_master_instructors.instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.instructor_id IS 'Master instructor user';


--
-- Name: COLUMN location_master_instructors.contract_start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.contract_start IS 'Contract start date';


--
-- Name: COLUMN location_master_instructors.contract_end; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.contract_end IS 'Contract end date';


--
-- Name: COLUMN location_master_instructors.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.is_active IS 'Only one active master per location';


--
-- Name: COLUMN location_master_instructors.offer_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.offer_status IS 'Offer workflow status: NULL=legacy, OFFERED=pending, ACCEPTED=active, DECLINED/EXPIRED=rejected';


--
-- Name: COLUMN location_master_instructors.offered_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.offered_at IS 'When offer was sent to instructor';


--
-- Name: COLUMN location_master_instructors.offer_deadline; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.offer_deadline IS 'Deadline for instructor to accept/decline offer';


--
-- Name: COLUMN location_master_instructors.accepted_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.accepted_at IS 'When instructor accepted the offer';


--
-- Name: COLUMN location_master_instructors.declined_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.declined_at IS 'When instructor declined or offer expired';


--
-- Name: COLUMN location_master_instructors.hiring_pathway; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.hiring_pathway IS 'Hiring method: DIRECT or JOB_POSTING';


--
-- Name: COLUMN location_master_instructors.source_position_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.source_position_id IS 'Links to job posting if hired via JOB_POSTING pathway';


--
-- Name: COLUMN location_master_instructors.availability_override; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.availability_override IS 'True if admin sent offer despite availability mismatch';


--
-- Name: COLUMN location_master_instructors.terminated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.location_master_instructors.terminated_at IS 'When contract was terminated';


--
-- Name: location_master_instructors_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.location_master_instructors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.location_master_instructors_id_seq OWNER TO postgres;

--
-- Name: location_master_instructors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.location_master_instructors_id_seq OWNED BY public.location_master_instructors.id;


--
-- Name: locations; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.locations OWNER TO postgres;

--
-- Name: COLUMN locations.location_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.locations.location_type IS 'Location capability: PARTNER (Tournament+Mini only) or CENTER (all types)';


--
-- Name: locations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.locations_id_seq OWNER TO postgres;

--
-- Name: locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.locations_id_seq OWNED BY public.locations.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.messages OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.messages_id_seq OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: module_components; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.module_components OWNER TO postgres;

--
-- Name: modules; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.modules OWNER TO postgres;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.notifications OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notifications_id_seq OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: player_levels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.player_levels (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    color character varying(50) NOT NULL,
    required_xp integer NOT NULL,
    required_sessions integer NOT NULL,
    description text,
    license_title character varying(255) NOT NULL
);


ALTER TABLE public.player_levels OWNER TO postgres;

--
-- Name: player_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.player_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.player_levels_id_seq OWNER TO postgres;

--
-- Name: player_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.player_levels_id_seq OWNED BY public.player_levels.id;


--
-- Name: position_applications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.position_applications (
    id integer NOT NULL,
    position_id integer NOT NULL,
    applicant_id integer NOT NULL,
    application_message text NOT NULL,
    status public.applicationstatus NOT NULL,
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.position_applications OWNER TO postgres;

--
-- Name: COLUMN position_applications.position_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.position_applications.position_id IS 'Position being applied to';


--
-- Name: COLUMN position_applications.applicant_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.position_applications.applicant_id IS 'Instructor applying';


--
-- Name: COLUMN position_applications.application_message; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.position_applications.application_message IS 'Cover letter / application message';


--
-- Name: COLUMN position_applications.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.position_applications.status IS 'PENDING, ACCEPTED, DECLINED';


--
-- Name: COLUMN position_applications.reviewed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.position_applications.reviewed_at IS 'When master reviewed application';


--
-- Name: position_applications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.position_applications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.position_applications_id_seq OWNER TO postgres;

--
-- Name: position_applications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.position_applications_id_seq OWNED BY public.position_applications.id;


--
-- Name: project_enrollment_quizzes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_enrollment_quizzes (
    id integer NOT NULL,
    project_id integer NOT NULL,
    user_id integer NOT NULL,
    quiz_attempt_id integer NOT NULL,
    enrollment_priority integer,
    enrollment_confirmed boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.project_enrollment_quizzes OWNER TO postgres;

--
-- Name: project_enrollment_quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_enrollment_quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_enrollment_quizzes_id_seq OWNER TO postgres;

--
-- Name: project_enrollment_quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_enrollment_quizzes_id_seq OWNED BY public.project_enrollment_quizzes.id;


--
-- Name: project_enrollments; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.project_enrollments OWNER TO postgres;

--
-- Name: project_enrollments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_enrollments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_enrollments_id_seq OWNER TO postgres;

--
-- Name: project_enrollments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_enrollments_id_seq OWNED BY public.project_enrollments.id;


--
-- Name: project_milestone_progress; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.project_milestone_progress OWNER TO postgres;

--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_milestone_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_milestone_progress_id_seq OWNER TO postgres;

--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_milestone_progress_id_seq OWNED BY public.project_milestone_progress.id;


--
-- Name: project_milestones; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.project_milestones OWNER TO postgres;

--
-- Name: project_milestones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_milestones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_milestones_id_seq OWNER TO postgres;

--
-- Name: project_milestones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_milestones_id_seq OWNED BY public.project_milestones.id;


--
-- Name: project_quizzes; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.project_quizzes OWNER TO postgres;

--
-- Name: project_quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_quizzes_id_seq OWNER TO postgres;

--
-- Name: project_quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_quizzes_id_seq OWNED BY public.project_quizzes.id;


--
-- Name: project_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_sessions (
    id integer NOT NULL,
    project_id integer NOT NULL,
    session_id integer NOT NULL,
    milestone_id integer,
    is_required boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.project_sessions OWNER TO postgres;

--
-- Name: project_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_sessions_id_seq OWNER TO postgres;

--
-- Name: project_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_sessions_id_seq OWNED BY public.project_sessions.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: COLUMN projects.target_specialization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.target_specialization IS 'Target specialization for this project (null = all specializations)';


--
-- Name: COLUMN projects.mixed_specialization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.mixed_specialization IS 'Whether this project encourages collaboration between Player and Coach specializations';


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.projects_id_seq OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: question_metadata; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.question_metadata OWNER TO postgres;

--
-- Name: question_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.question_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.question_metadata_id_seq OWNER TO postgres;

--
-- Name: question_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.question_metadata_id_seq OWNED BY public.question_metadata.id;


--
-- Name: quiz_answer_options; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quiz_answer_options (
    id integer NOT NULL,
    question_id integer NOT NULL,
    option_text character varying(500) NOT NULL,
    is_correct boolean NOT NULL,
    order_index integer NOT NULL
);


ALTER TABLE public.quiz_answer_options OWNER TO postgres;

--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quiz_answer_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_answer_options_id_seq OWNER TO postgres;

--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quiz_answer_options_id_seq OWNED BY public.quiz_answer_options.id;


--
-- Name: quiz_attempts; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.quiz_attempts OWNER TO postgres;

--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quiz_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_attempts_id_seq OWNER TO postgres;

--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quiz_attempts_id_seq OWNED BY public.quiz_attempts.id;


--
-- Name: quiz_questions; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.quiz_questions OWNER TO postgres;

--
-- Name: quiz_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quiz_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_questions_id_seq OWNER TO postgres;

--
-- Name: quiz_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quiz_questions_id_seq OWNED BY public.quiz_questions.id;


--
-- Name: quiz_user_answers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quiz_user_answers (
    id integer NOT NULL,
    attempt_id integer NOT NULL,
    question_id integer NOT NULL,
    selected_option_id integer,
    answer_text character varying(1000),
    is_correct boolean NOT NULL,
    answered_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.quiz_user_answers OWNER TO postgres;

--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quiz_user_answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_user_answers_id_seq OWNER TO postgres;

--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quiz_user_answers_id_seq OWNED BY public.quiz_user_answers.id;


--
-- Name: quizzes; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.quizzes OWNER TO postgres;

--
-- Name: quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quizzes_id_seq OWNER TO postgres;

--
-- Name: quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quizzes_id_seq OWNED BY public.quizzes.id;


--
-- Name: semester_enrollments; Type: TABLE; Schema: public; Owner: postgres
--

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
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.semester_enrollments OWNER TO postgres;

--
-- Name: COLUMN semester_enrollments.user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.user_id IS 'Student who is enrolled';


--
-- Name: COLUMN semester_enrollments.semester_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.semester_id IS 'Semester for this enrollment';


--
-- Name: COLUMN semester_enrollments.user_license_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.user_license_id IS 'Link to UserLicense (tracks progress/levels)';


--
-- Name: COLUMN semester_enrollments.request_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.request_status IS 'Enrollment request status: PENDING/APPROVED/REJECTED/WITHDRAWN';


--
-- Name: COLUMN semester_enrollments.requested_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.requested_at IS 'When student requested enrollment';


--
-- Name: COLUMN semester_enrollments.approved_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.approved_at IS 'When admin approved/rejected the request';


--
-- Name: COLUMN semester_enrollments.approved_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.approved_by IS 'Admin who approved/rejected';


--
-- Name: COLUMN semester_enrollments.rejection_reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.rejection_reason IS 'Reason for rejection (if rejected)';


--
-- Name: COLUMN semester_enrollments.payment_reference_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.payment_reference_code IS 'Unique payment reference code for bank transfer (e.g., LFA-INT-2024S1-042-A7B9)';


--
-- Name: COLUMN semester_enrollments.payment_verified; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.payment_verified IS 'Whether student paid for THIS specialization in THIS semester';


--
-- Name: COLUMN semester_enrollments.payment_verified_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.payment_verified_at IS 'When payment was verified';


--
-- Name: COLUMN semester_enrollments.payment_verified_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.payment_verified_by IS 'Admin user who verified payment';


--
-- Name: COLUMN semester_enrollments.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.is_active IS 'Whether this enrollment is currently active (auto-set when approved)';


--
-- Name: COLUMN semester_enrollments.enrolled_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.enrolled_at IS 'When student enrolled in this spec for this semester';


--
-- Name: COLUMN semester_enrollments.deactivated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.deactivated_at IS 'When enrollment was deactivated (if applicable)';


--
-- Name: COLUMN semester_enrollments.age_category; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.age_category IS 'Age category at enrollment (PRE/YOUTH/AMATEUR/PRO)';


--
-- Name: COLUMN semester_enrollments.age_category_overridden; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.age_category_overridden IS 'True if instructor manually changed category';


--
-- Name: COLUMN semester_enrollments.age_category_overridden_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.age_category_overridden_at IS 'When age category was overridden by instructor';


--
-- Name: COLUMN semester_enrollments.age_category_overridden_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semester_enrollments.age_category_overridden_by IS 'Instructor who overrode the age category';


--
-- Name: semester_enrollments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semester_enrollments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semester_enrollments_id_seq OWNER TO postgres;

--
-- Name: semester_enrollments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semester_enrollments_id_seq OWNED BY public.semester_enrollments.id;


--
-- Name: semester_instructors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semester_instructors (
    semester_id integer NOT NULL,
    instructor_id integer NOT NULL
);


ALTER TABLE public.semester_instructors OWNER TO postgres;

--
-- Name: semesters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semesters (
    id integer NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status public.semester_status NOT NULL,
    tournament_status character varying(50),
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
    location_id integer,
    location_city character varying(100),
    location_venue character varying(200),
    location_address character varying(500),
    tournament_type_id integer,
    tournament_type character varying(50),
    participant_type character varying(50),
    is_multi_day boolean,
    sessions_generated boolean NOT NULL,
    sessions_generated_at timestamp without time zone,
    assignment_type character varying(30),
    max_players integer,
    reward_policy_name character varying(100) NOT NULL,
    reward_policy_snapshot jsonb
);


ALTER TABLE public.semesters OWNER TO postgres;

--
-- Name: COLUMN semesters.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.status IS 'Current lifecycle phase of the semester';


--
-- Name: COLUMN semesters.tournament_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.tournament_status IS 'Tournament-specific status: DRAFT, SEEKING_INSTRUCTOR, READY_FOR_ENROLLMENT, etc.';


--
-- Name: COLUMN semesters.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.is_active IS 'DEPRECATED: Use status field instead. Kept for backward compatibility.';


--
-- Name: COLUMN semesters.enrollment_cost; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.enrollment_cost IS 'Credit cost to enroll in this semester (admin adjustable)';


--
-- Name: COLUMN semesters.master_instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.master_instructor_id IS 'Master instructor who approves enrollment requests for this semester';


--
-- Name: COLUMN semesters.specialization_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.specialization_type IS 'Specialization type (SEASON types: LFA_PLAYER_PRE/YOUTH/AMATEUR/PRO, GANCUJU_PLAYER, LFA_COACH, INTERNSHIP, OR user license for tournaments: LFA_FOOTBALL_PLAYER)';


--
-- Name: COLUMN semesters.age_group; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.age_group IS 'Age group (PRE, YOUTH, AMATEUR, PRO)';


--
-- Name: COLUMN semesters.theme; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.theme IS 'Marketing theme (e.g., ''New Year Challenge'', ''Q1'', ''Fall'')';


--
-- Name: COLUMN semesters.focus_description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.focus_description IS 'Focus description (e.g., ''Újévi fogadalmak, friss kezdés'')';


--
-- Name: COLUMN semesters.campus_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.campus_id IS 'FK to campuses table (most specific location - preferred)';


--
-- Name: COLUMN semesters.location_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.location_id IS 'FK to locations table (less specific than campus_id, preferred over legacy location_city/venue/address)';


--
-- Name: COLUMN semesters.location_city; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.location_city IS 'DEPRECATED: Use campus_id or location_id instead. City where semester takes place';


--
-- Name: COLUMN semesters.location_venue; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.location_venue IS 'DEPRECATED: Use campus_id or location_id instead. Venue/campus name';


--
-- Name: COLUMN semesters.location_address; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.location_address IS 'DEPRECATED: Use campus_id or location_id instead. Full address';


--
-- Name: COLUMN semesters.tournament_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.tournament_type_id IS 'FK to tournament_types table (for auto-generating session structure)';


--
-- Name: COLUMN semesters.tournament_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.tournament_type IS 'DEPRECATED: Use tournament_type_id instead. Tournament format: LEAGUE, KNOCKOUT, ROUND_ROBIN, CUSTOM';


--
-- Name: COLUMN semesters.participant_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.participant_type IS 'Participant type: INDIVIDUAL, TEAM, MIXED';


--
-- Name: COLUMN semesters.is_multi_day; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.is_multi_day IS 'True if tournament spans multiple days';


--
-- Name: COLUMN semesters.sessions_generated; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.sessions_generated IS 'True if tournament sessions have been auto-generated (prevents duplicate generation)';


--
-- Name: COLUMN semesters.sessions_generated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.sessions_generated_at IS 'Timestamp when sessions were auto-generated';


--
-- Name: COLUMN semesters.assignment_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.assignment_type IS 'Tournament instructor assignment strategy: OPEN_ASSIGNMENT (admin assigns directly) or APPLICATION_BASED (instructors apply)';


--
-- Name: COLUMN semesters.max_players; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.max_players IS 'Maximum tournament participants (explicit capacity, independent of session capacity sum)';


--
-- Name: COLUMN semesters.reward_policy_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.reward_policy_name IS 'Name of the reward policy applied to this tournament semester';


--
-- Name: COLUMN semesters.reward_policy_snapshot; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.semesters.reward_policy_snapshot IS 'Immutable snapshot of the reward policy at tournament creation time';


--
-- Name: semesters_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semesters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semesters_id_seq OWNER TO postgres;

--
-- Name: semesters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semesters_id_seq OWNED BY public.semesters.id;


--
-- Name: session_group_assignments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.session_group_assignments (
    id integer NOT NULL,
    session_id integer NOT NULL,
    group_number integer NOT NULL,
    instructor_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by integer
);


ALTER TABLE public.session_group_assignments OWNER TO postgres;

--
-- Name: COLUMN session_group_assignments.session_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.session_group_assignments.session_id IS 'Session these groups belong to';


--
-- Name: COLUMN session_group_assignments.group_number; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.session_group_assignments.group_number IS 'Group number within session (1, 2, 3, 4...)';


--
-- Name: COLUMN session_group_assignments.instructor_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.session_group_assignments.instructor_id IS 'Instructor leading this group';


--
-- Name: COLUMN session_group_assignments.created_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.session_group_assignments.created_by IS 'Head coach who created this assignment';


--
-- Name: session_group_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.session_group_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.session_group_assignments_id_seq OWNER TO postgres;

--
-- Name: session_group_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.session_group_assignments_id_seq OWNED BY public.session_group_assignments.id;


--
-- Name: session_group_students; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.session_group_students (
    id integer NOT NULL,
    session_group_id integer NOT NULL,
    student_id integer NOT NULL,
    assigned_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.session_group_students OWNER TO postgres;

--
-- Name: COLUMN session_group_students.session_group_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.session_group_students.session_group_id IS 'Which group this student is in';


--
-- Name: COLUMN session_group_students.student_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.session_group_students.student_id IS 'Student assigned to this group';


--
-- Name: session_group_students_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.session_group_students_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.session_group_students_id_seq OWNER TO postgres;

--
-- Name: session_group_students_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.session_group_students_id_seq OWNED BY public.session_group_students.id;


--
-- Name: session_quizzes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.session_quizzes (
    id integer NOT NULL,
    session_id integer NOT NULL,
    quiz_id integer NOT NULL,
    is_required boolean,
    max_attempts integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.session_quizzes OWNER TO postgres;

--
-- Name: session_quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.session_quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.session_quizzes_id_seq OWNER TO postgres;

--
-- Name: session_quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.session_quizzes_id_seq OWNED BY public.session_quizzes.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: postgres
--

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
    tournament_phase character varying(50),
    tournament_round integer,
    tournament_match_number integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.sessions OWNER TO postgres;

--
-- Name: COLUMN sessions.target_specialization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.target_specialization IS 'Target specialization for this session (null = all specializations)';


--
-- Name: COLUMN sessions.mixed_specialization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.mixed_specialization IS 'Whether this session is open to all specializations';


--
-- Name: COLUMN sessions.actual_start_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.actual_start_time IS 'Actual start time when instructor starts the session';


--
-- Name: COLUMN sessions.actual_end_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.actual_end_time IS 'Actual end time when instructor stops the session';


--
-- Name: COLUMN sessions.session_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.session_status IS 'Session status: scheduled, in_progress, completed';


--
-- Name: COLUMN sessions.quiz_unlocked; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.quiz_unlocked IS 'Whether the quiz is unlocked for students (HYBRID sessions)';


--
-- Name: COLUMN sessions.base_xp; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.base_xp IS 'Base XP awarded for completing this session (HYBRID=100, ON-SITE=75, VIRTUAL=50)';


--
-- Name: COLUMN sessions.credit_cost; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.credit_cost IS 'Number of credits required to book this session (default: 1, workshops may cost more)';


--
-- Name: COLUMN sessions.is_tournament_game; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.is_tournament_game IS 'True if this session is a tournament game';


--
-- Name: COLUMN sessions.game_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.game_type IS 'Type/name of tournament game (user-defined, e.g., ''Skills Challenge'')';


--
-- Name: COLUMN sessions.game_results; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.game_results IS 'JSON array of game results: [{user_id: 1, score: 95, rank: 1}, ...]';


--
-- Name: COLUMN sessions.auto_generated; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.auto_generated IS 'True if this session was auto-generated from tournament type config';


--
-- Name: COLUMN sessions.tournament_phase; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.tournament_phase IS 'Tournament phase: ''Group Stage'', ''Knockout Stage'', ''Finals''';


--
-- Name: COLUMN sessions.tournament_round; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.tournament_round IS 'Round number within the tournament (1, 2, 3, ...)';


--
-- Name: COLUMN sessions.tournament_match_number; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sessions.tournament_match_number IS 'Match number within the round (1, 2, 3, ...)';


--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sessions_id_seq OWNER TO postgres;

--
-- Name: sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sessions_id_seq OWNED BY public.sessions.id;


--
-- Name: specialization_progress; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.specialization_progress OWNER TO postgres;

--
-- Name: specialization_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.specialization_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.specialization_progress_id_seq OWNER TO postgres;

--
-- Name: specialization_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.specialization_progress_id_seq OWNED BY public.specialization_progress.id;


--
-- Name: specializations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.specializations (
    id character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.specializations OWNER TO postgres;

--
-- Name: COLUMN specializations.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.specializations.id IS 'Matches SpecializationType enum values';


--
-- Name: COLUMN specializations.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.specializations.is_active IS 'Controls availability without code changes';


--
-- Name: COLUMN specializations.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.specializations.created_at IS 'Audit trail for when specialization was created';


--
-- Name: student_performance_reviews; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.student_performance_reviews OWNER TO postgres;

--
-- Name: student_performance_reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.student_performance_reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.student_performance_reviews_id_seq OWNER TO postgres;

--
-- Name: student_performance_reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.student_performance_reviews_id_seq OWNED BY public.student_performance_reviews.id;


--
-- Name: team_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.team_members (
    id integer NOT NULL,
    team_id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(50),
    joined_at timestamp with time zone DEFAULT now(),
    is_active boolean
);


ALTER TABLE public.team_members OWNER TO postgres;

--
-- Name: team_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.team_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.team_members_id_seq OWNER TO postgres;

--
-- Name: team_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.team_members_id_seq OWNED BY public.team_members.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(20),
    captain_user_id integer,
    specialization_type character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    is_active boolean
);


ALTER TABLE public.teams OWNER TO postgres;

--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.teams_id_seq OWNER TO postgres;

--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: tournament_rankings; Type: TABLE; Schema: public; Owner: postgres
--

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
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.tournament_rankings OWNER TO postgres;

--
-- Name: tournament_rankings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournament_rankings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tournament_rankings_id_seq OWNER TO postgres;

--
-- Name: tournament_rankings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournament_rankings_id_seq OWNED BY public.tournament_rankings.id;


--
-- Name: tournament_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tournament_rewards (
    id integer NOT NULL,
    tournament_id integer NOT NULL,
    "position" character varying(20) NOT NULL,
    xp_amount integer,
    credits_reward integer,
    badge_id integer
);


ALTER TABLE public.tournament_rewards OWNER TO postgres;

--
-- Name: tournament_rewards_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournament_rewards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tournament_rewards_id_seq OWNER TO postgres;

--
-- Name: tournament_rewards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournament_rewards_id_seq OWNED BY public.tournament_rewards.id;


--
-- Name: tournament_stats; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.tournament_stats OWNER TO postgres;

--
-- Name: tournament_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournament_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tournament_stats_id_seq OWNER TO postgres;

--
-- Name: tournament_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournament_stats_id_seq OWNED BY public.tournament_stats.id;


--
-- Name: tournament_status_history; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.tournament_status_history OWNER TO postgres;

--
-- Name: tournament_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournament_status_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tournament_status_history_id_seq OWNER TO postgres;

--
-- Name: tournament_status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournament_status_history_id_seq OWNED BY public.tournament_status_history.id;


--
-- Name: tournament_team_enrollments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tournament_team_enrollments (
    id integer NOT NULL,
    semester_id integer NOT NULL,
    team_id integer NOT NULL,
    enrollment_date timestamp with time zone DEFAULT now(),
    payment_verified boolean,
    is_active boolean
);


ALTER TABLE public.tournament_team_enrollments OWNER TO postgres;

--
-- Name: tournament_team_enrollments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournament_team_enrollments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tournament_team_enrollments_id_seq OWNER TO postgres;

--
-- Name: tournament_team_enrollments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournament_team_enrollments_id_seq OWNED BY public.tournament_team_enrollments.id;


--
-- Name: tournament_types; Type: TABLE; Schema: public; Owner: postgres
--

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
    config json NOT NULL
);


ALTER TABLE public.tournament_types OWNER TO postgres;

--
-- Name: tournament_types_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournament_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tournament_types_id_seq OWNER TO postgres;

--
-- Name: tournament_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournament_types_id_seq OWNED BY public.tournament_types.id;


--
-- Name: tracks; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.tracks OWNER TO postgres;

--
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.user_achievements OWNER TO postgres;

--
-- Name: user_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_achievements_id_seq OWNER TO postgres;

--
-- Name: user_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_achievements_id_seq OWNED BY public.user_achievements.id;


--
-- Name: user_licenses; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.user_licenses OWNER TO postgres;

--
-- Name: COLUMN user_licenses.payment_reference_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.payment_reference_code IS 'Unique payment reference for bank transfer (e.g., INT-2025-002-X7K9)';


--
-- Name: COLUMN user_licenses.payment_verified; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.payment_verified IS 'Whether admin verified payment received for this license';


--
-- Name: COLUMN user_licenses.payment_verified_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.payment_verified_at IS 'When admin verified the payment';


--
-- Name: COLUMN user_licenses.onboarding_completed; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.onboarding_completed IS 'Whether student completed basic onboarding for this specialization';


--
-- Name: COLUMN user_licenses.onboarding_completed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.onboarding_completed_at IS 'When student completed onboarding';


--
-- Name: COLUMN user_licenses.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.is_active IS 'Whether this license is currently active (can be used for teaching/enrollment)';


--
-- Name: COLUMN user_licenses.issued_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.issued_at IS 'Official license issuance date (e.g., 2014-01-01 for Grand Master)';


--
-- Name: COLUMN user_licenses.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.expires_at IS 'License expiration date (null = no expiration yet, perpetual until first renewal)';


--
-- Name: COLUMN user_licenses.last_renewed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.last_renewed_at IS 'When license was last renewed';


--
-- Name: COLUMN user_licenses.renewal_cost; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.renewal_cost IS 'Credit cost to renew this license (default: 1000 credits)';


--
-- Name: COLUMN user_licenses.motivation_scores; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.motivation_scores IS 'Motivation assessment scores (1-5 scale) - filled by admin/instructor';


--
-- Name: COLUMN user_licenses.average_motivation_score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.average_motivation_score IS 'Calculated average motivation score (1.0-5.0)';


--
-- Name: COLUMN user_licenses.motivation_last_assessed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.motivation_last_assessed_at IS 'When motivation was last assessed';


--
-- Name: COLUMN user_licenses.motivation_assessed_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.motivation_assessed_by IS 'Admin/instructor who assessed motivation';


--
-- Name: COLUMN user_licenses.football_skills; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.football_skills IS '6 football skill percentages for LFA Player specializations (heading, shooting, crossing, passing, dribbling, ball_control)';


--
-- Name: COLUMN user_licenses.skills_last_updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.skills_last_updated_at IS 'When skills were last updated';


--
-- Name: COLUMN user_licenses.skills_updated_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.skills_updated_by IS 'Instructor who last updated skills';


--
-- Name: COLUMN user_licenses.credit_balance; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.credit_balance IS 'Current credit balance available for enrollments';


--
-- Name: COLUMN user_licenses.credit_purchased; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.credit_purchased IS 'Total credits purchased (lifetime)';


--
-- Name: COLUMN user_licenses.credit_expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_licenses.credit_expires_at IS 'Credit expiration date (2 years from purchase)';


--
-- Name: user_licenses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_licenses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_licenses_id_seq OWNER TO postgres;

--
-- Name: user_licenses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_licenses_id_seq OWNED BY public.user_licenses.id;


--
-- Name: user_module_progresses; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.user_module_progresses OWNER TO postgres;

--
-- Name: user_question_performance; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.user_question_performance OWNER TO postgres;

--
-- Name: user_question_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_question_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_question_performance_id_seq OWNER TO postgres;

--
-- Name: user_question_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_question_performance_id_seq OWNED BY public.user_question_performance.id;


--
-- Name: user_stats; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.user_stats OWNER TO postgres;

--
-- Name: user_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_stats_id_seq OWNER TO postgres;

--
-- Name: user_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_stats_id_seq OWNED BY public.user_stats.id;


--
-- Name: user_track_progresses; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.user_track_progresses OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

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
    nda_accepted boolean NOT NULL,
    nda_accepted_at timestamp without time zone,
    nda_ip_address character varying,
    parental_consent boolean NOT NULL,
    parental_consent_at timestamp without time zone,
    parental_consent_by character varying,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    created_by integer
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: COLUMN users.first_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.first_name IS 'User first name (given name)';


--
-- Name: COLUMN users.last_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.last_name IS 'User last name (family name)';


--
-- Name: COLUMN users.onboarding_completed; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.onboarding_completed IS 'Set to True when student completes FIRST license onboarding (motivation questionnaire). Note: UserLicense.onboarding_completed tracks EACH specialization separately.';


--
-- Name: COLUMN users.nationality; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.nationality IS 'User''s nationality (e.g., Hungarian, American)';


--
-- Name: COLUMN users.gender; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.gender IS 'User''s gender (Male, Female, Other, Prefer not to say)';


--
-- Name: COLUMN users.current_location; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.current_location IS 'User''s current location (e.g., Budapest, Hungary)';


--
-- Name: COLUMN users.street_address; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.street_address IS 'Street address (e.g., Main Street 123)';


--
-- Name: COLUMN users.city; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.city IS 'City name';


--
-- Name: COLUMN users.postal_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.postal_code IS 'Postal/ZIP code';


--
-- Name: COLUMN users.country; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.country IS 'Country name';


--
-- Name: COLUMN users.specialization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.specialization IS 'User''s chosen specialization track (Player/Coach)';


--
-- Name: COLUMN users.payment_verified; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.payment_verified IS 'Whether student has paid semester fees';


--
-- Name: COLUMN users.payment_verified_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.payment_verified_at IS 'Timestamp when payment was verified';


--
-- Name: COLUMN users.payment_verified_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.payment_verified_by IS 'Admin who verified the payment';


--
-- Name: COLUMN users.credit_balance; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.credit_balance IS 'Current available credits (can be used across all specializations)';


--
-- Name: COLUMN users.credit_purchased; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.credit_purchased IS 'Total credits purchased by this user (for transaction history)';


--
-- Name: COLUMN users.credit_payment_reference; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.credit_payment_reference IS 'Unique payment reference code for credit purchases (közlemény)';


--
-- Name: COLUMN users.nda_accepted; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.nda_accepted IS 'Whether student has accepted the NDA';


--
-- Name: COLUMN users.nda_accepted_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.nda_accepted_at IS 'Timestamp when NDA was accepted';


--
-- Name: COLUMN users.nda_ip_address; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.nda_ip_address IS 'IP address from which NDA was accepted';


--
-- Name: COLUMN users.parental_consent; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.parental_consent IS 'Whether parental consent has been given (required for users under 18 in LFA_COACH)';


--
-- Name: COLUMN users.parental_consent_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.parental_consent_at IS 'Timestamp when parental consent was given';


--
-- Name: COLUMN users.parental_consent_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.parental_consent_by IS 'Name of parent/guardian who gave consent';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: achievements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements ALTER COLUMN id SET DEFAULT nextval('public.achievements_id_seq'::regclass);


--
-- Name: adaptive_learning_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.adaptive_learning_sessions ALTER COLUMN id SET DEFAULT nextval('public.adaptive_learning_sessions_id_seq'::regclass);


--
-- Name: attendance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance ALTER COLUMN id SET DEFAULT nextval('public.attendance_id_seq'::regclass);


--
-- Name: attendance_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance_history ALTER COLUMN id SET DEFAULT nextval('public.attendance_history_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: belt_promotions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.belt_promotions ALTER COLUMN id SET DEFAULT nextval('public.belt_promotions_id_seq'::regclass);


--
-- Name: bookings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings ALTER COLUMN id SET DEFAULT nextval('public.bookings_id_seq'::regclass);


--
-- Name: campuses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campuses ALTER COLUMN id SET DEFAULT nextval('public.campuses_id_seq'::regclass);


--
-- Name: coach_levels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coach_levels ALTER COLUMN id SET DEFAULT nextval('public.coach_levels_id_seq'::regclass);


--
-- Name: coupon_usages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coupon_usages ALTER COLUMN id SET DEFAULT nextval('public.coupon_usages_id_seq'::regclass);


--
-- Name: coupons id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coupons ALTER COLUMN id SET DEFAULT nextval('public.coupons_id_seq'::regclass);


--
-- Name: credit_transactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_transactions ALTER COLUMN id SET DEFAULT nextval('public.credit_transactions_id_seq'::regclass);


--
-- Name: feedback id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);


--
-- Name: football_skill_assessments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.football_skill_assessments ALTER COLUMN id SET DEFAULT nextval('public.football_skill_assessments_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: instructor_assignment_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignment_requests ALTER COLUMN id SET DEFAULT nextval('public.instructor_assignment_requests_id_seq'::regclass);


--
-- Name: instructor_assignments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignments ALTER COLUMN id SET DEFAULT nextval('public.instructor_assignments_id_seq'::regclass);


--
-- Name: instructor_availability_windows id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_availability_windows ALTER COLUMN id SET DEFAULT nextval('public.instructor_availability_windows_id_seq'::regclass);


--
-- Name: instructor_positions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_positions ALTER COLUMN id SET DEFAULT nextval('public.instructor_positions_id_seq'::regclass);


--
-- Name: instructor_session_reviews id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_session_reviews ALTER COLUMN id SET DEFAULT nextval('public.instructor_session_reviews_id_seq'::regclass);


--
-- Name: instructor_specialization_availability id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specialization_availability ALTER COLUMN id SET DEFAULT nextval('public.instructor_specialization_availability_id_seq'::regclass);


--
-- Name: instructor_specializations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specializations ALTER COLUMN id SET DEFAULT nextval('public.instructor_specializations_id_seq'::regclass);


--
-- Name: internship_levels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.internship_levels ALTER COLUMN id SET DEFAULT nextval('public.internship_levels_id_seq'::regclass);


--
-- Name: invitation_codes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitation_codes ALTER COLUMN id SET DEFAULT nextval('public.invitation_codes_id_seq'::regclass);


--
-- Name: invoice_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoice_requests ALTER COLUMN id SET DEFAULT nextval('public.invoice_requests_id_seq'::regclass);


--
-- Name: license_metadata id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.license_metadata ALTER COLUMN id SET DEFAULT nextval('public.license_metadata_id_seq'::regclass);


--
-- Name: license_progressions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.license_progressions ALTER COLUMN id SET DEFAULT nextval('public.license_progressions_id_seq'::regclass);


--
-- Name: location_master_instructors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location_master_instructors ALTER COLUMN id SET DEFAULT nextval('public.location_master_instructors_id_seq'::regclass);


--
-- Name: locations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations ALTER COLUMN id SET DEFAULT nextval('public.locations_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: player_levels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_levels ALTER COLUMN id SET DEFAULT nextval('public.player_levels_id_seq'::regclass);


--
-- Name: position_applications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.position_applications ALTER COLUMN id SET DEFAULT nextval('public.position_applications_id_seq'::regclass);


--
-- Name: project_enrollment_quizzes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollment_quizzes ALTER COLUMN id SET DEFAULT nextval('public.project_enrollment_quizzes_id_seq'::regclass);


--
-- Name: project_enrollments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollments ALTER COLUMN id SET DEFAULT nextval('public.project_enrollments_id_seq'::regclass);


--
-- Name: project_milestone_progress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestone_progress ALTER COLUMN id SET DEFAULT nextval('public.project_milestone_progress_id_seq'::regclass);


--
-- Name: project_milestones id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestones ALTER COLUMN id SET DEFAULT nextval('public.project_milestones_id_seq'::regclass);


--
-- Name: project_quizzes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_quizzes ALTER COLUMN id SET DEFAULT nextval('public.project_quizzes_id_seq'::regclass);


--
-- Name: project_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_sessions ALTER COLUMN id SET DEFAULT nextval('public.project_sessions_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: question_metadata id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_metadata ALTER COLUMN id SET DEFAULT nextval('public.question_metadata_id_seq'::regclass);


--
-- Name: quiz_answer_options id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_answer_options ALTER COLUMN id SET DEFAULT nextval('public.quiz_answer_options_id_seq'::regclass);


--
-- Name: quiz_attempts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_attempts ALTER COLUMN id SET DEFAULT nextval('public.quiz_attempts_id_seq'::regclass);


--
-- Name: quiz_questions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_questions ALTER COLUMN id SET DEFAULT nextval('public.quiz_questions_id_seq'::regclass);


--
-- Name: quiz_user_answers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_user_answers ALTER COLUMN id SET DEFAULT nextval('public.quiz_user_answers_id_seq'::regclass);


--
-- Name: quizzes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quizzes ALTER COLUMN id SET DEFAULT nextval('public.quizzes_id_seq'::regclass);


--
-- Name: semester_enrollments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments ALTER COLUMN id SET DEFAULT nextval('public.semester_enrollments_id_seq'::regclass);


--
-- Name: semesters id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semesters ALTER COLUMN id SET DEFAULT nextval('public.semesters_id_seq'::regclass);


--
-- Name: session_group_assignments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_assignments ALTER COLUMN id SET DEFAULT nextval('public.session_group_assignments_id_seq'::regclass);


--
-- Name: session_group_students id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_students ALTER COLUMN id SET DEFAULT nextval('public.session_group_students_id_seq'::regclass);


--
-- Name: session_quizzes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_quizzes ALTER COLUMN id SET DEFAULT nextval('public.session_quizzes_id_seq'::regclass);


--
-- Name: sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions ALTER COLUMN id SET DEFAULT nextval('public.sessions_id_seq'::regclass);


--
-- Name: specialization_progress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialization_progress ALTER COLUMN id SET DEFAULT nextval('public.specialization_progress_id_seq'::regclass);


--
-- Name: student_performance_reviews id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_performance_reviews ALTER COLUMN id SET DEFAULT nextval('public.student_performance_reviews_id_seq'::regclass);


--
-- Name: team_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members ALTER COLUMN id SET DEFAULT nextval('public.team_members_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: tournament_rankings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rankings ALTER COLUMN id SET DEFAULT nextval('public.tournament_rankings_id_seq'::regclass);


--
-- Name: tournament_rewards id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rewards ALTER COLUMN id SET DEFAULT nextval('public.tournament_rewards_id_seq'::regclass);


--
-- Name: tournament_stats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_stats ALTER COLUMN id SET DEFAULT nextval('public.tournament_stats_id_seq'::regclass);


--
-- Name: tournament_status_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_status_history ALTER COLUMN id SET DEFAULT nextval('public.tournament_status_history_id_seq'::regclass);


--
-- Name: tournament_team_enrollments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_team_enrollments ALTER COLUMN id SET DEFAULT nextval('public.tournament_team_enrollments_id_seq'::regclass);


--
-- Name: tournament_types id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_types ALTER COLUMN id SET DEFAULT nextval('public.tournament_types_id_seq'::regclass);


--
-- Name: user_achievements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements ALTER COLUMN id SET DEFAULT nextval('public.user_achievements_id_seq'::regclass);


--
-- Name: user_licenses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_licenses ALTER COLUMN id SET DEFAULT nextval('public.user_licenses_id_seq'::regclass);


--
-- Name: user_question_performance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_question_performance ALTER COLUMN id SET DEFAULT nextval('public.user_question_performance_id_seq'::regclass);


--
-- Name: user_stats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_stats ALTER COLUMN id SET DEFAULT nextval('public.user_stats_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: achievements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.achievements (id, code, name, description, icon, xp_reward, category, requirements, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: adaptive_learning_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.adaptive_learning_sessions (id, user_id, category, started_at, ended_at, questions_presented, questions_correct, xp_earned, target_difficulty, performance_trend, session_time_limit_seconds, session_start_time) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
f7592a774d52
\.


--
-- Data for Name: attendance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attendance (id, user_id, session_id, booking_id, status, check_in_time, check_out_time, notes, marked_by, confirmation_status, student_confirmed_at, dispute_reason, pending_change_to, change_requested_by, change_requested_at, change_request_reason, xp_earned, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: attendance_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attendance_history (id, attendance_id, changed_by, change_type, old_value, new_value, reason, created_at) FROM stdin;
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (id, user_id, action, resource_type, resource_id, details, ip_address, user_agent, request_method, request_path, status_code, "timestamp") FROM stdin;
1	1	LOGIN	\N	\N	{"email": "admin@lfa.com", "role": "admin", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:46:42.46154+01
2	1	POST_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/admin/coupons	201	2026-01-17 11:46:42.695112+01
3	1	POST_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/admin/coupons	201	2026-01-17 11:46:42.710095+01
4	1	POST_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/admin/coupons	201	2026-01-17 11:46:42.722412+01
5	1	LOGIN	\N	\N	{"email": "admin@lfa.com", "role": "admin", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:46:49.223237+01
6	1	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:46:49.434394+01
7	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:46:49.511904+01
8	1	GET_/api/v1/admin/locations/2/campuses	location	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/2/campuses	200	2026-01-17 11:46:49.540138+01
9	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:46:51.802087+01
10	1	GET_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/invitation-codes	200	2026-01-17 11:46:51.831008+01
11	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:46:55.933057+01
12	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:46:55.997777+01
13	1	GET_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/invitation-codes	200	2026-01-17 11:46:56.019829+01
14	1	POST_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/admin/invitation-codes	200	2026-01-17 11:47:00.259119+01
15	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:47:09.389645+01
16	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:47:09.453588+01
17	1	GET_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/invitation-codes	200	2026-01-17 11:47:09.475877+01
18	1	POST_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/admin/invitation-codes	200	2026-01-17 11:47:13.663822+01
19	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:47:22.802554+01
20	1	GET_/api/v1/admin/coupons	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/coupons	200	2026-01-17 11:47:22.867252+01
21	1	GET_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/invitation-codes	200	2026-01-17 11:47:22.890657+01
22	1	POST_/api/v1/admin/invitation-codes	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/admin/invitation-codes	200	2026-01-17 11:47:27.078256+01
23	4	USER_CREATED	\N	\N	{"email": "pwt.k1sqx1@f1stteam.hu", "name": "Krist\\u00f3f Kis", "invitation_code": "INV-20260117-E7PMZN", "bonus_credits": 50, "registration_type": "invitation_code"}	\N	\N	\N	\N	\N	2026-01-17 11:48:01.56129+01
24	\N	POST_/api/v1/auth/register-with-invitation	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/auth/register-with-invitation	200	2026-01-17 11:48:01.567678+01
25	5	USER_CREATED	\N	\N	{"email": "pwt.p3t1k3@f1stteam.hu", "name": "P\\u00e9ter Pataki", "invitation_code": "INV-20260117-0G8HP1", "bonus_credits": 50, "registration_type": "invitation_code"}	\N	\N	\N	\N	\N	2026-01-17 11:48:32.444605+01
26	\N	POST_/api/v1/auth/register-with-invitation	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/auth/register-with-invitation	200	2026-01-17 11:48:32.451065+01
27	6	USER_CREATED	\N	\N	{"email": "pwt.V4lv3rd3jr@f1stteam.hu", "name": "Viktor Valverde", "invitation_code": "INV-20260117-TQSEC4", "bonus_credits": 50, "registration_type": "invitation_code"}	\N	\N	\N	\N	\N	2026-01-17 11:49:04.440787+01
28	\N	POST_/api/v1/auth/register-with-invitation	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/auth/register-with-invitation	200	2026-01-17 11:49:04.446933+01
29	4	LOGIN	\N	\N	{"email": "pwt.k1sqx1@f1stteam.hu", "role": "student", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:49:18.445516+01
30	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:18.651839+01
31	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:18.732679+01
32	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:27.164117+01
33	4	POST_/api/v1/coupons/apply	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/coupons/apply	200	2026-01-17 11:49:27.19462+01
34	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:27.205078+01
35	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:27.242958+01
36	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:38.792945+01
37	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:38.842577+01
38	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:41.35843+01
39	4	POST_/specialization/unlock	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/specialization/unlock	200	2026-01-17 11:49:41.391775+01
40	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:41.401162+01
41	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:41.468383+01
42	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:46.962122+01
43	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:47.01413+01
44	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:48.508494+01
45	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:48.55722+01
46	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:54.105228+01
47	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:54.935651+01
48	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:55.409498+01
49	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:55.983505+01
50	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:56.55007+01
51	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:57.115386+01
52	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:57.957165+01
53	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:58.671136+01
54	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:49:59.506269+01
55	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:00.209233+01
56	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:01.040342+01
57	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:01.748776+01
58	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:02.317444+01
59	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:02.887432+01
60	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:03.456754+01
61	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:04.292256+01
62	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:05.001267+01
63	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:05.577621+01
64	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:06.407014+01
65	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:07.116915+01
66	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:08.946348+01
67	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:08.999278+01
68	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:17.238457+01
69	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:20.810417+01
70	4	POST_/specialization/lfa-player/onboarding-submit	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/specialization/lfa-player/onboarding-submit	303	2026-01-17 11:50:20.838191+01
71	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:20.850741+01
72	4	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:20.918084+01
73	5	LOGIN	\N	\N	{"email": "pwt.p3t1k3@f1stteam.hu", "role": "student", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:50:36.728245+01
74	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:37.010577+01
75	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:37.09575+01
76	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:45.415808+01
77	5	POST_/api/v1/coupons/apply	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/coupons/apply	200	2026-01-17 11:50:45.449433+01
78	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:45.491168+01
79	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:45.530864+01
80	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:57.04103+01
81	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:57.093497+01
82	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:59.604046+01
83	5	POST_/specialization/unlock	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/specialization/unlock	200	2026-01-17 11:50:59.628277+01
84	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:59.641233+01
85	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:50:59.691244+01
86	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:05.192529+01
87	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:05.242748+01
88	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:06.749449+01
89	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:06.818047+01
90	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:12.337732+01
91	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:13.32479+01
92	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:14.28873+01
93	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:15.006736+01
94	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:15.56916+01
95	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:16.143014+01
96	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:16.709618+01
97	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:17.537888+01
98	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:18.251014+01
99	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:18.818856+01
100	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:19.638333+01
101	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:20.34844+01
102	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:20.910881+01
103	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:21.738976+01
104	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:22.452479+01
105	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:23.018282+01
106	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:23.579414+01
107	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:24.150683+01
108	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:25.98777+01
109	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:26.040989+01
110	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:34.235958+01
111	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:37.812952+01
119	6	POST_/api/v1/coupons/apply	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/coupons/apply	200	2026-01-17 11:52:00.829305+01
120	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:00.836995+01
121	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:00.883491+01
122	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:12.425139+01
123	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:12.471725+01
124	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:14.99304+01
159	6	POST_/specialization/lfa-player/onboarding-submit	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/specialization/lfa-player/onboarding-submit	303	2026-01-17 11:52:56.192379+01
160	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:56.202296+01
161	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:56.252897+01
163	1	LOGIN	\N	\N	{"email": "admin@lfa.com", "role": "admin", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:53:08.984549+01
164	1	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:53:09.189615+01
112	5	POST_/specialization/lfa-player/onboarding-submit	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/specialization/lfa-player/onboarding-submit	303	2026-01-17 11:51:37.841056+01
113	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:37.852203+01
114	5	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:37.90022+01
125	6	POST_/specialization/unlock	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/specialization/unlock	200	2026-01-17 11:52:15.023591+01
126	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:15.03333+01
127	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:15.079798+01
128	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:20.572789+01
129	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:20.61991+01
130	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:22.137192+01
131	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:22.188005+01
132	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:27.737043+01
133	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:28.46093+01
134	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:29.037656+01
135	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:29.604921+01
136	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:30.438883+01
137	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:31.423217+01
138	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:32.134999+01
139	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:32.711739+01
140	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:33.27597+01
141	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:34.105914+01
142	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:34.818054+01
143	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:35.387748+01
144	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:35.956719+01
145	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:36.52269+01
146	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:37.371227+01
147	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:38.080315+01
148	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:38.653745+01
149	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:39.484742+01
150	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:40.206851+01
151	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:40.771811+01
152	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:41.36388+01
153	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:41.922824+01
154	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:42.498769+01
155	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:44.327212+01
156	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:44.376382+01
162	6	GET_/api/v1/tournaments/available	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/tournaments/available	400	2026-01-17 11:52:56.285919+01
115	6	LOGIN	\N	\N	{"email": "pwt.V4lv3rd3jr@f1stteam.hu", "role": "student", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:51:52.106023+01
116	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:52.309337+01
117	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:51:52.378292+01
118	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:00.797311+01
157	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:52.558587+01
158	6	GET_/api/v1/users/me	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/me	200	2026-01-17 11:52:56.126631+01
165	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:53:09.259676+01
166	1	GET_/api/v1/admin/locations/2/campuses	location	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/2/campuses	200	2026-01-17 11:53:09.279362+01
167	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:53:21.591067+01
168	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:53:21.598313+01
169	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:53:21.61101+01
170	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:53:40.054497+01
171	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:53:40.064492+01
172	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:53:40.076636+01
173	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:53:46.748664+01
174	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:53:46.75892+01
175	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:53:46.767636+01
176	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:54:10.098474+01
177	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:54:10.108096+01
178	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:54:10.117822+01
179	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:54:10.13755+01
180	1	POST_/api/v1/tournaments/generate	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournaments/generate	201	2026-01-17 11:54:10.175528+01
181	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:54:10.227163+01
182	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:54:10.245861+01
183	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:54:10.253131+01
184	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:54:10.261963+01
185	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:54:10.281433+01
186	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:54:28.673768+01
187	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:54:28.695847+01
188	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:54:28.702658+01
189	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:54:28.713525+01
190	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:54:28.733766+01
191	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:54:36.236241+01
192	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:54:36.260856+01
193	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:54:36.269685+01
194	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:54:36.278369+01
195	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:54:36.296816+01
196	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:54:59.534046+01
197	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:54:59.552481+01
198	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:54:59.561216+01
199	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:54:59.568673+01
200	1	POST_/api/v1/tournament-types/2/estimate	tournament-type	2	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/2/estimate	200	2026-01-17 11:54:59.58675+01
201	1	POST_/api/v1/tournaments/generate	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournaments/generate	201	2026-01-17 11:54:59.614306+01
202	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:54:59.661072+01
203	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:54:59.677499+01
204	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:54:59.695116+01
205	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:54:59.701693+01
206	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:54:59.71082+01
207	1	POST_/api/v1/tournament-types/2/estimate	tournament-type	2	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/2/estimate	200	2026-01-17 11:54:59.728898+01
208	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:55:18.066054+01
209	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:55:18.083732+01
211	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:55:18.124096+01
212	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:55:18.132765+01
216	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:55:24.832041+01
219	1	POST_/api/v1/tournament-types/2/estimate	tournament-type	2	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/2/estimate	200	2026-01-17 11:55:24.867532+01
226	1	POST_/api/v1/tournaments/generate	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournaments/generate	201	2026-01-17 11:55:48.343663+01
227	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:55:48.39544+01
228	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:55:48.411825+01
229	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:55:48.427451+01
231	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:55:48.450761+01
232	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:55:48.460149+01
237	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:56:06.834459+01
240	1	POST_/api/v1/tournament-types/3/estimate	tournament-type	3	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/3/estimate	200	2026-01-17 11:56:06.868217+01
210	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:55:18.115759+01
213	1	POST_/api/v1/tournament-types/2/estimate	tournament-type	2	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/2/estimate	200	2026-01-17 11:55:18.151505+01
220	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:55:48.234892+01
221	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:55:48.252732+01
223	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:55:48.281861+01
224	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:55:48.293816+01
230	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:55:48.444018+01
233	1	POST_/api/v1/tournament-types/3/estimate	tournament-type	3	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/3/estimate	200	2026-01-17 11:55:48.477035+01
214	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:55:24.793707+01
215	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:55:24.812308+01
217	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:55:24.839869+01
218	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:55:24.84842+01
222	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:55:48.274411+01
225	1	POST_/api/v1/tournament-types/3/estimate	tournament-type	3	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/3/estimate	200	2026-01-17 11:55:48.315645+01
234	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:56:06.778459+01
235	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:56:06.796986+01
236	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:56:06.816041+01
238	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:56:06.842044+01
239	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:56:06.850489+01
241	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:56:13.475867+01
242	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:56:13.495692+01
243	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:56:13.51332+01
244	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:56:13.529815+01
245	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:56:13.53769+01
246	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:56:13.545457+01
247	1	POST_/api/v1/tournament-types/3/estimate	tournament-type	3	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/3/estimate	200	2026-01-17 11:56:13.563259+01
248	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:56:37.018628+01
249	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:56:37.035094+01
250	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:56:37.049493+01
251	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:56:37.06888+01
252	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:56:37.077148+01
253	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:56:37.085417+01
254	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:56:37.103461+01
255	1	POST_/api/v1/tournaments/generate	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournaments/generate	201	2026-01-17 11:56:37.131927+01
256	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:56:37.181029+01
257	1	GET_/api/v1/semesters/4/enrollments	semester	4	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/4/enrollments	404	2026-01-17 11:56:37.197518+01
258	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:56:37.211748+01
259	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:56:37.220148+01
260	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:56:37.235079+01
261	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:56:37.251987+01
262	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:56:37.259709+01
263	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:56:37.26749+01
264	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:56:37.286459+01
265	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:57:07.163528+01
266	1	GET_/api/v1/semesters/4/enrollments	semester	4	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/4/enrollments	404	2026-01-17 11:57:07.180783+01
267	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:57:07.193211+01
268	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:57:07.201352+01
269	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:57:07.216906+01
270	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:57:07.233974+01
271	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:57:07.240395+01
272	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:57:07.2485+01
273	1	POST_/api/v1/tournament-types/1/estimate	tournament-type	1	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/1/estimate	200	2026-01-17 11:57:07.26668+01
274	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:57:30.451655+01
275	1	GET_/api/v1/semesters/4/enrollments	semester	4	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/4/enrollments	404	2026-01-17 11:57:30.46799+01
276	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:57:30.480809+01
277	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:57:30.488438+01
278	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:57:30.503786+01
280	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:57:30.528078+01
281	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:57:30.535962+01
289	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:57:30.684349+01
290	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:57:30.700401+01
292	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:57:30.723771+01
293	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:57:30.731966+01
295	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:58:56.178695+01
296	1	GET_/api/v1/semesters/5/enrollments	semester	5	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/5/enrollments	404	2026-01-17 11:58:56.195839+01
297	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:58:56.206866+01
306	1	POST_/api/v1/tournaments/generate	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournaments/generate	201	2026-01-17 11:58:56.329809+01
307	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:58:56.383608+01
308	1	GET_/api/v1/semesters/6/enrollments	semester	6	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/6/enrollments	404	2026-01-17 11:58:56.397625+01
309	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:58:56.409218+01
314	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:58:56.457231+01
315	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:58:56.472279+01
317	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:58:56.495429+01
318	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:58:56.503029+01
279	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:57:30.520532+01
282	1	POST_/api/v1/tournament-types/2/estimate	tournament-type	2	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/2/estimate	200	2026-01-17 11:57:30.554198+01
287	1	GET_/api/v1/semesters/4/enrollments	semester	4	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/4/enrollments	404	2026-01-17 11:57:30.665872+01
288	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:57:30.677283+01
291	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:57:30.716159+01
294	1	POST_/api/v1/tournament-types/2/estimate	tournament-type	2	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/2/estimate	200	2026-01-17 11:57:30.748453+01
300	1	GET_/api/v1/semesters/1/enrollments	semester	1	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/1/enrollments	404	2026-01-17 11:58:56.236684+01
301	1	GET_/api/v1/semesters/3/enrollments	semester	3	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/3/enrollments	404	2026-01-17 11:58:56.251955+01
303	1	GET_/api/v1/admin/campuses/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses/	307	2026-01-17 11:58:56.275705+01
304	1	GET_/api/v1/admin/campuses	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/campuses	200	2026-01-17 11:58:56.283371+01
312	1	GET_/api/v1/semesters/4/enrollments	semester	4	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/4/enrollments	404	2026-01-17 11:58:56.437428+01
313	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:58:56.449989+01
316	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:58:56.488355+01
319	1	POST_/api/v1/tournament-types/3/estimate	tournament-type	3	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/3/estimate	200	2026-01-17 11:58:56.520735+01
320	1	LOGIN	\N	\N	{"email": "admin@lfa.com", "role": "admin", "success": true}	\N	\N	\N	\N	\N	2026-01-17 11:59:01.799553+01
283	1	POST_/api/v1/tournaments/generate	\N	\N	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournaments/generate	201	2026-01-17 11:57:30.581302+01
284	1	GET_/api/v1/semesters/2/enrollments	semester	2	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/2/enrollments	404	2026-01-17 11:57:30.630153+01
285	1	GET_/api/v1/semesters/5/enrollments	semester	5	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/5/enrollments	404	2026-01-17 11:57:30.644266+01
286	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:57:30.657909+01
298	1	GET_/api/v1/semesters/4/enrollments	semester	4	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/4/enrollments	404	2026-01-17 11:58:56.214568+01
299	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:58:56.229314+01
302	1	GET_/api/v1/admin/locations/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/admin/locations/	200	2026-01-17 11:58:56.268158+01
305	1	POST_/api/v1/tournament-types/3/estimate	tournament-type	3	null	127.0.0.1	python-requests/2.32.5	POST	/api/v1/tournament-types/3/estimate	200	2026-01-17 11:58:56.302461+01
310	1	GET_/api/v1/semesters/5/enrollments	semester	5	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/semesters/5/enrollments	404	2026-01-17 11:58:56.416666+01
311	1	GET_/api/v1/users/	\N	\N	null	127.0.0.1	python-requests/2.32.5	GET	/api/v1/users/	200	2026-01-17 11:58:56.429591+01
\.


--
-- Data for Name: belt_promotions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.belt_promotions (id, user_license_id, from_belt, to_belt, promoted_by, promoted_at, notes, exam_score, exam_notes) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bookings (id, user_id, session_id, status, waitlist_position, notes, created_at, updated_at, cancelled_at, attended_status, enrollment_id) FROM stdin;
\.


--
-- Data for Name: campuses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.campuses (id, location_id, name, venue, address, notes, is_active, created_at, updated_at) FROM stdin;
1	1	Budapest Main Campus	Budapest Sports Complex	Budapest Sports Street 1	\N	t	2026-01-17 10:46:42.070698	2026-01-17 10:46:42.070709
2	2	Vienna Main Campus	Vienna Sports Complex	Vienna Sports Street 1	\N	t	2026-01-17 10:46:42.072684	2026-01-17 10:46:42.072686
3	3	Bratislava Main Campus	Bratislava Sports Complex	Bratislava Sports Street 1	\N	t	2026-01-17 10:46:42.073672	2026-01-17 10:46:42.073673
\.


--
-- Data for Name: certificate_templates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.certificate_templates (id, track_id, title, description, design_template, validation_rules, created_at) FROM stdin;
\.


--
-- Data for Name: coach_levels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.coach_levels (id, name, required_xp, required_sessions, theory_hours, practice_hours, description, license_title) FROM stdin;
\.


--
-- Data for Name: coupon_usages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.coupon_usages (id, coupon_id, user_id, credits_awarded, used_at) FROM stdin;
1	1	4	50	2026-01-17 11:49:27.185408+01
2	2	5	50	2026-01-17 11:50:45.435164+01
3	3	6	50	2026-01-17 11:52:00.81991+01
\.


--
-- Data for Name: coupons; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.coupons (id, code, type, discount_value, description, is_active, expires_at, max_uses, current_uses, requires_purchase, requires_admin_approval, created_at, updated_at) FROM stdin;
1	E2E-BONUS-50-USER1	BONUS_CREDITS	50	E2E onboarding test: +50 bonus credits	t	\N	1	1	f	f	2026-01-17 11:46:42.684376+01	2026-01-17 11:49:27.18272+01
2	E2E-BONUS-50-USER2	BONUS_CREDITS	50	E2E onboarding test: +50 bonus credits	t	\N	1	1	f	f	2026-01-17 11:46:42.705672+01	2026-01-17 11:50:45.43329+01
3	E2E-BONUS-50-USER3	BONUS_CREDITS	50	E2E onboarding test: +50 bonus credits	t	\N	1	1	f	f	2026-01-17 11:46:42.718362+01	2026-01-17 11:52:00.817441+01
\.


--
-- Data for Name: credit_transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.credit_transactions (id, user_id, user_license_id, transaction_type, amount, balance_after, description, semester_id, enrollment_id, created_at) FROM stdin;
1	\N	22	PURCHASE	-100	0	Unlocked specialization: LFA_FOOTBALL_PLAYER	\N	\N	2026-01-17 10:49:41.382386
2	\N	23	PURCHASE	-100	0	Unlocked specialization: LFA_FOOTBALL_PLAYER	\N	\N	2026-01-17 10:50:59.620493
3	\N	24	PURCHASE	-100	0	Unlocked specialization: LFA_FOOTBALL_PLAYER	\N	\N	2026-01-17 10:52:15.016841
\.


--
-- Data for Name: feedback; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feedback (id, user_id, session_id, rating, instructor_rating, session_quality, would_recommend, comment, is_anonymous, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: football_skill_assessments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.football_skill_assessments (id, user_license_id, skill_name, points_earned, points_total, percentage, assessed_by, assessed_at, notes) FROM stdin;
\.


--
-- Data for Name: group_users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_users (group_id, user_id) FROM stdin;
\.


--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.groups (id, name, description, semester_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: instructor_assignment_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_assignment_requests (id, semester_id, instructor_id, requested_by, location_id, status, created_at, responded_at, expires_at, request_message, response_message, priority) FROM stdin;
\.


--
-- Data for Name: instructor_assignments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_assignments (id, location_id, instructor_id, specialization_type, age_group, year, time_period_start, time_period_end, is_master, assigned_by, is_active, created_at, deactivated_at) FROM stdin;
\.


--
-- Data for Name: instructor_availability_windows; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_availability_windows (id, instructor_id, year, time_period, is_available, created_at, updated_at, notes) FROM stdin;
\.


--
-- Data for Name: instructor_positions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_positions (id, location_id, posted_by, is_master_position, specialization_type, age_group, year, time_period_start, time_period_end, description, priority, status, application_deadline, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: instructor_session_reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_session_reviews (id, session_id, student_id, instructor_id, instructor_clarity, support_approachability, session_structure, relevance, environment, engagement_feeling, feedback_quality, satisfaction, comments, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: instructor_specialization_availability; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_specialization_availability (id, instructor_id, specialization_type, time_period_code, year, location_city, is_available, created_at, updated_at, notes) FROM stdin;
\.


--
-- Data for Name: instructor_specializations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.instructor_specializations (id, user_id, specialization, certified_at, certified_by, notes, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: internship_levels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.internship_levels (id, name, required_xp, required_sessions, total_hours, description, license_title) FROM stdin;
\.


--
-- Data for Name: invitation_codes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.invitation_codes (id, code, invited_name, invited_email, bonus_credits, is_used, used_by_user_id, used_at, created_by_admin_id, created_at, expires_at, notes) FROM stdin;
1	INV-20260117-E7PMZN	E2E Test - First Team Player 1 - Pre Category	\N	50	t	4	2026-01-17 11:48:01.557013+01	1	2026-01-17 11:47:00.251705+01	2026-01-24 11:47:00.24177+01	\N
2	INV-20260117-0G8HP1	E2E Test - First Team Player 2 - Youth Category	\N	50	t	5	2026-01-17 11:48:32.441635+01	1	2026-01-17 11:47:13.660448+01	2026-01-24 11:47:13.654371+01	\N
3	INV-20260117-TQSEC4	E2E Test - First Team Player 3 - Amateur Category	\N	50	t	6	2026-01-17 11:49:04.43571+01	1	2026-01-17 11:47:27.074074+01	2026-01-24 11:47:27.067195+01	\N
\.


--
-- Data for Name: invoice_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.invoice_requests (id, user_id, payment_reference, amount_eur, credit_amount, specialization, coupon_code, status, created_at, paid_at, verified_at) FROM stdin;
\.


--
-- Data for Name: issued_certificates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.issued_certificates (id, certificate_template_id, user_id, unique_identifier, issue_date, completion_date, verification_hash, cert_metadata, is_revoked, revoked_at, revoked_reason, created_at) FROM stdin;
\.


--
-- Data for Name: license_metadata; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.license_metadata (id, specialization_type, level_code, level_number, title, title_en, subtitle, color_primary, color_secondary, icon_emoji, icon_symbol, marketing_narrative, cultural_context, philosophy, background_gradient, css_class, image_url, advancement_criteria, time_requirement_hours, project_requirements, evaluation_criteria, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: license_progressions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.license_progressions (id, user_license_id, from_level, to_level, advanced_by, advancement_reason, requirements_met, advanced_at) FROM stdin;
\.


--
-- Data for Name: location_master_instructors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.location_master_instructors (id, location_id, instructor_id, contract_start, contract_end, is_active, offer_status, offered_at, offer_deadline, accepted_at, declined_at, hiring_pathway, source_position_id, availability_override, created_at, terminated_at) FROM stdin;
\.


--
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.locations (id, name, city, postal_code, country, country_code, location_code, venue, address, notes, is_active, location_type, created_at, updated_at) FROM stdin;
1	Budapest Center	Budapest	1011	Hungary	HU	BDPST	\N	Váci utca 123	\N	t	CENTER	2026-01-17 10:46:42.068798	2026-01-17 10:46:42.068811
2	Vienna Academy	Vienna	1010	Austria	AT	VIE	\N	Stephansplatz 1	\N	t	CENTER	2026-01-17 10:46:42.072176	2026-01-17 10:46:42.072178
3	Bratislava Training Center	Bratislava	81101	Slovakia	SK	BTS	\N	Hviezdoslavovo námestie 1	\N	t	PARTNER	2026-01-17 10:46:42.073198	2026-01-17 10:46:42.073199
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.messages (id, sender_id, recipient_id, subject, message, priority, is_read, is_edited, created_at, read_at, edited_at) FROM stdin;
\.


--
-- Data for Name: module_components; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.module_components (id, module_id, type, name, description, order_in_module, estimated_minutes, is_mandatory, component_data, created_at) FROM stdin;
\.


--
-- Data for Name: modules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.modules (id, track_id, semester_id, name, description, order_in_track, learning_objectives, estimated_hours, is_mandatory, created_at) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notifications (id, user_id, title, message, type, is_read, related_session_id, related_booking_id, created_at, read_at, link, related_semester_id, related_request_id) FROM stdin;
\.


--
-- Data for Name: player_levels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.player_levels (id, name, color, required_xp, required_sessions, description, license_title) FROM stdin;
\.


--
-- Data for Name: position_applications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.position_applications (id, position_id, applicant_id, application_message, status, reviewed_at, created_at) FROM stdin;
\.


--
-- Data for Name: project_enrollment_quizzes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_enrollment_quizzes (id, project_id, user_id, quiz_attempt_id, enrollment_priority, enrollment_confirmed, created_at) FROM stdin;
\.


--
-- Data for Name: project_enrollments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_enrollments (id, project_id, user_id, enrolled_at, status, progress_status, completion_percentage, instructor_approved, instructor_feedback, enrollment_status, quiz_passed, final_grade, completed_at) FROM stdin;
\.


--
-- Data for Name: project_milestone_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_milestone_progress (id, enrollment_id, milestone_id, status, submitted_at, instructor_feedback, instructor_approved_at, sessions_completed, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: project_milestones; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_milestones (id, project_id, title, description, order_index, required_sessions, xp_reward, deadline, is_required, created_at) FROM stdin;
\.


--
-- Data for Name: project_quizzes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_quizzes (id, project_id, quiz_id, milestone_id, quiz_type, is_required, minimum_score, order_index, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: project_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_sessions (id, project_id, session_id, milestone_id, is_required, created_at) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.projects (id, title, description, semester_id, instructor_id, max_participants, required_sessions, xp_reward, deadline, status, difficulty, target_specialization, mixed_specialization, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: question_metadata; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.question_metadata (id, question_id, estimated_difficulty, cognitive_load, concept_tags, prerequisite_concepts, average_time_seconds, global_success_rate, last_analytics_update) FROM stdin;
\.


--
-- Data for Name: quiz_answer_options; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quiz_answer_options (id, question_id, option_text, is_correct, order_index) FROM stdin;
\.


--
-- Data for Name: quiz_attempts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quiz_attempts (id, user_id, quiz_id, started_at, completed_at, time_spent_minutes, score, total_questions, correct_answers, xp_awarded, passed) FROM stdin;
\.


--
-- Data for Name: quiz_questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quiz_questions (id, quiz_id, question_text, question_type, points, order_index, explanation, created_at) FROM stdin;
\.


--
-- Data for Name: quiz_user_answers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quiz_user_answers (id, attempt_id, question_id, selected_option_id, answer_text, is_correct, answered_at) FROM stdin;
\.


--
-- Data for Name: quizzes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quizzes (id, title, description, category, difficulty, time_limit_minutes, xp_reward, passing_score, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: semester_enrollments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.semester_enrollments (id, user_id, semester_id, user_license_id, request_status, requested_at, approved_at, approved_by, rejection_reason, payment_reference_code, payment_verified, payment_verified_at, payment_verified_by, is_active, enrolled_at, deactivated_at, age_category, age_category_overridden, age_category_overridden_at, age_category_overridden_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: semester_instructors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.semester_instructors (semester_id, instructor_id) FROM stdin;
\.


--
-- Data for Name: semesters; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.semesters (id, code, name, start_date, end_date, status, tournament_status, is_active, enrollment_cost, created_at, updated_at, master_instructor_id, specialization_type, age_group, theme, focus_description, campus_id, location_id, location_city, location_venue, location_address, tournament_type_id, tournament_type, participant_type, is_multi_day, sessions_generated, sessions_generated_at, assignment_type, max_players, reward_policy_name, reward_policy_snapshot) FROM stdin;
1	TOURN-20260118-001	🇦🇹 AT - "Budapest HU League 20260117115304" - VIE	2026-01-18	2026-01-18	SEEKING_INSTRUCTOR	SEEKING_INSTRUCTOR	t	500	2026-01-17 11:54:10.163998	2026-01-17 11:54:10.164004	\N	LFA_FOOTBALL_PLAYER	AMATEUR	\N	\N	2	2	\N	\N	\N	1	\N	INDIVIDUAL	f	f	\N	APPLICATION_BASED	8	default	{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}
2	TOURN-20260118-002	🇭🇺 HU - "Vienna AT Knockout 20260117115304" - BDPST	2026-01-18	2026-01-18	SEEKING_INSTRUCTOR	SEEKING_INSTRUCTOR	t	500	2026-01-17 11:54:59.607946	2026-01-17 11:54:59.607949	\N	LFA_FOOTBALL_PLAYER	AMATEUR	\N	\N	1	1	\N	\N	\N	2	\N	INDIVIDUAL	f	f	\N	APPLICATION_BASED	8	default	{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}
3	TOURN-20260118-003	🇸🇰 SK - "Bratislava SK Group+KO 20260117115304" - BTS	2026-01-18	2026-01-18	SEEKING_INSTRUCTOR	SEEKING_INSTRUCTOR	t	500	2026-01-17 11:55:48.337033	2026-01-17 11:55:48.337036	\N	LFA_FOOTBALL_PLAYER	AMATEUR	\N	\N	3	3	\N	\N	\N	3	\N	INDIVIDUAL	f	f	\N	APPLICATION_BASED	8	default	{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}
4	TOURN-20260118-004	🇦🇹 AT - "Budapest HU League INV 20260117115304" - VIE	2026-01-18	2026-01-18	SEEKING_INSTRUCTOR	SEEKING_INSTRUCTOR	t	500	2026-01-17 11:56:37.126595	2026-01-17 11:56:37.126598	\N	LFA_FOOTBALL_PLAYER	AMATEUR	\N	\N	2	2	\N	\N	\N	1	\N	INDIVIDUAL	f	f	\N	OPEN_ASSIGNMENT	8	default	{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}
5	TOURN-20260118-005	🇦🇹 AT - "Vienna AT Knockout INV 20260117115304" - VIE	2026-01-18	2026-01-18	SEEKING_INSTRUCTOR	SEEKING_INSTRUCTOR	t	500	2026-01-17 11:57:30.575689	2026-01-17 11:57:30.575692	\N	LFA_FOOTBALL_PLAYER	AMATEUR	\N	\N	2	2	\N	\N	\N	2	\N	INDIVIDUAL	f	f	\N	OPEN_ASSIGNMENT	8	default	{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}
6	TOURN-20260118-006	🇦🇹 AT - "Bratislava SK Group+KO INV 20260117115304" - VIE	2026-01-18	2026-01-18	SEEKING_INSTRUCTOR	SEEKING_INSTRUCTOR	t	500	2026-01-17 11:58:56.323911	2026-01-17 11:58:56.323914	\N	LFA_FOOTBALL_PLAYER	AMATEUR	\N	\N	2	2	\N	\N	\N	3	\N	INDIVIDUAL	f	f	\N	OPEN_ASSIGNMENT	8	default	{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}
\.


--
-- Data for Name: session_group_assignments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.session_group_assignments (id, session_id, group_number, instructor_id, created_at, created_by) FROM stdin;
\.


--
-- Data for Name: session_group_students; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.session_group_students (id, session_group_id, student_id, assigned_at) FROM stdin;
\.


--
-- Data for Name: session_quizzes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.session_quizzes (id, session_id, quiz_id, is_required, max_attempts, created_at) FROM stdin;
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sessions (id, title, description, date_start, date_end, session_type, capacity, location, meeting_link, sport_type, level, instructor_name, semester_id, group_id, instructor_id, target_specialization, mixed_specialization, actual_start_time, actual_end_time, session_status, quiz_unlocked, base_xp, credit_cost, is_tournament_game, game_type, game_results, auto_generated, tournament_phase, tournament_round, tournament_match_number, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: specialization_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.specialization_progress (id, student_id, specialization_id, current_level, total_xp, completed_sessions, completed_projects, theory_hours_completed, practice_hours_completed, last_activity, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: specializations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.specializations (id, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: student_performance_reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_performance_reviews (id, session_id, student_id, instructor_id, punctuality, engagement, focus, collaboration, attitude, comments, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: team_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.team_members (id, team_id, user_id, role, joined_at, is_active) FROM stdin;
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teams (id, name, code, captain_user_id, specialization_type, created_at, is_active) FROM stdin;
\.


--
-- Data for Name: tournament_rankings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_rankings (id, tournament_id, user_id, team_id, participant_type, rank, points, wins, losses, draws, updated_at) FROM stdin;
\.


--
-- Data for Name: tournament_rewards; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_rewards (id, tournament_id, "position", xp_amount, credits_reward, badge_id) FROM stdin;
\.


--
-- Data for Name: tournament_stats; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_stats (id, tournament_id, total_participants, total_teams, total_matches, completed_matches, total_revenue, avg_attendance_rate, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tournament_status_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_status_history (id, tournament_id, old_status, new_status, changed_by, reason, extra_metadata, created_at) FROM stdin;
\.


--
-- Data for Name: tournament_team_enrollments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_team_enrollments (id, semester_id, team_id, enrollment_date, payment_verified, is_active) FROM stdin;
\.


--
-- Data for Name: tournament_types; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_types (id, code, display_name, description, min_players, max_players, requires_power_of_two, session_duration_minutes, break_between_sessions_minutes, config) FROM stdin;
1	league	League (Round Robin)	Every player plays against every other player once. Best for smaller groups with balanced competition.	4	16	f	90	15	{"code": "league", "display_name": "League (Round Robin)", "description": "Every player plays against every other player once. Best for smaller groups with balanced competition.", "min_players": 4, "max_players": 16, "requires_power_of_two": false, "session_duration_minutes": 90, "break_between_sessions_minutes": 15, "matches_calculation": "n * (n - 1) / 2", "rounds_calculation": "n - 1 if n is even else n", "session_naming_pattern": "Round {round_number} - Match {match_number}", "placement_rules": {"primary": "wins", "tiebreakers": ["goal_difference", "goals_scored", "head_to_head"]}, "config_notes": ["Each player plays every other player exactly once", "Total matches = n*(n-1)/2 where n = player count", "Can run multiple matches in parallel if fields available", "Fair format - everyone gets equal opportunities"]}
2	knockout	Single Elimination (Knockout)	Traditional knockout tournament - lose once and you're out. Fast and exciting.	4	64	t	90	15	{"code": "knockout", "display_name": "Single Elimination (Knockout)", "description": "Traditional knockout tournament - lose once and you're out. Fast and exciting.", "min_players": 4, "max_players": 64, "requires_power_of_two": true, "session_duration_minutes": 90, "break_between_sessions_minutes": 15, "matches_calculation": "n - 1", "rounds_calculation": "log2(n)", "session_naming_pattern": "{round_name} - Match {match_number}", "round_names": {"64": "Round of 64", "32": "Round of 32", "16": "Round of 16", "8": "Quarter-finals", "4": "Semi-finals", "2": "Final"}, "placement_rules": {"1": "Winner of final", "2": "Loser of final", "3": "Winners of 3rd place playoff (optional)", "4": "Loser of 3rd place playoff (optional)"}, "config_notes": ["Requires power-of-2 players (4, 8, 16, 32, 64)", "Total matches = n - 1", "Fastest tournament format", "Highly competitive - no second chances"], "third_place_playoff": true}
3	group_knockout	Group Stage + Knockout	Hybrid format - group stage followed by knockout playoffs. Best balance of fairness and excitement.	8	32	f	90	15	{"code": "group_knockout", "display_name": "Group Stage + Knockout", "description": "Hybrid format - group stage followed by knockout playoffs. Best balance of fairness and excitement.", "min_players": 8, "max_players": 32, "requires_power_of_two": false, "session_duration_minutes": 90, "break_between_sessions_minutes": 15, "matches_calculation": "group_matches + knockout_matches", "rounds_calculation": "group_rounds + knockout_rounds", "session_naming_pattern": "{phase} - {round_name} - Match {match_number}", "phases": [{"name": "Group Stage", "format": "round_robin_within_groups", "groups_count": "dynamic", "players_per_group": 4, "top_qualifiers_per_group": 2}, {"name": "Knockout Stage", "format": "single_elimination", "seeding": "group_winners_vs_runners_up"}], "group_configuration": {"8_players": {"groups": 2, "players_per_group": 4, "qualifiers": 2}, "12_players": {"groups": 3, "players_per_group": 4, "qualifiers": 2}, "16_players": {"groups": 4, "players_per_group": 4, "qualifiers": 2}, "24_players": {"groups": 6, "players_per_group": 4, "qualifiers": 2}, "32_players": {"groups": 8, "players_per_group": 4, "qualifiers": 2}}, "placement_rules": {"group_stage": {"primary": "wins", "tiebreakers": ["goal_difference", "goals_scored", "head_to_head"]}, "knockout_stage": {"1": "Winner of final", "2": "Loser of final", "3-4": "Losers of semi-finals"}}, "config_notes": ["Group stage ensures everyone plays multiple matches", "Knockout stage provides exciting conclusion", "Most popular format for medium-large tournaments", "Balances fairness with entertainment value"]}
4	swiss	Swiss System	Players with similar scores play each other. Fair and flexible format for any player count.	4	64	f	90	15	{"code": "swiss", "display_name": "Swiss System", "description": "Players with similar scores play each other. Fair and flexible format for any player count.", "min_players": 4, "max_players": 64, "requires_power_of_two": false, "session_duration_minutes": 90, "break_between_sessions_minutes": 15, "matches_calculation": "n * rounds / 2", "rounds_calculation": "ceil(log2(n))", "session_naming_pattern": "Round {round_number} - Match {match_number}", "pairing_algorithm": "swiss_pairing", "pairing_rules": ["Round 1: Random or seeded pairing", "Round 2+: Players with similar scores paired together", "Avoid repeat matchups if possible", "Handle odd number of players with byes"], "placement_rules": {"primary": "total_points", "tiebreakers": ["buchholz_score", "sonneborn_berger", "goal_difference", "goals_scored"]}, "config_notes": ["Flexible format - works with any player count", "Each round pairs players of similar strength", "Typical rounds = log2(players) rounded up", "Popular in chess, works well for football too", "No elimination - everyone plays all rounds"], "bye_handling": {"enabled": true, "points_awarded": 3, "max_byes_per_player": 1}}
\.


--
-- Data for Name: tracks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tracks (id, name, code, description, duration_semesters, prerequisites, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_achievements (id, user_id, achievement_id, badge_type, title, description, icon, earned_at, semester_count, specialization_id) FROM stdin;
\.


--
-- Data for Name: user_licenses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_licenses (id, user_id, specialization_type, current_level, max_achieved_level, started_at, last_advanced_at, instructor_notes, payment_reference_code, payment_verified, payment_verified_at, onboarding_completed, onboarding_completed_at, is_active, issued_at, expires_at, last_renewed_at, renewal_cost, motivation_scores, average_motivation_score, motivation_last_assessed_at, motivation_assessed_by, football_skills, skills_last_updated_at, skills_updated_by, credit_balance, credit_purchased, credit_expires_at, created_at, updated_at) FROM stdin;
1	3	LFA_FOOTBALL_PLAYER	1	1	2026-01-17 10:46:42.0583	\N	\N	\N	t	2026-01-17 10:46:42.058312	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060243	2026-01-17 11:46:42.060245
2	3	LFA_FOOTBALL_PLAYER	2	2	2026-01-17 10:46:42.058375	\N	\N	\N	t	2026-01-17 10:46:42.058376	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060246	2026-01-17 11:46:42.060246
3	3	LFA_FOOTBALL_PLAYER	3	3	2026-01-17 10:46:42.058405	\N	\N	\N	t	2026-01-17 10:46:42.058406	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060247	2026-01-17 11:46:42.060248
4	3	LFA_FOOTBALL_PLAYER	4	4	2026-01-17 10:46:42.058428	\N	\N	\N	t	2026-01-17 10:46:42.058428	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060248	2026-01-17 11:46:42.060249
5	3	LFA_FOOTBALL_PLAYER	5	5	2026-01-17 10:46:42.058448	\N	\N	\N	t	2026-01-17 10:46:42.058449	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060249	2026-01-17 11:46:42.06025
6	3	LFA_FOOTBALL_PLAYER	6	6	2026-01-17 10:46:42.058468	\N	\N	\N	t	2026-01-17 10:46:42.058469	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.06025	2026-01-17 11:46:42.060251
7	3	LFA_FOOTBALL_PLAYER	7	7	2026-01-17 10:46:42.058487	\N	\N	\N	t	2026-01-17 10:46:42.058488	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060251	2026-01-17 11:46:42.060252
8	3	LFA_FOOTBALL_PLAYER	8	8	2026-01-17 10:46:42.058507	\N	\N	\N	t	2026-01-17 10:46:42.058507	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060253	2026-01-17 11:46:42.060253
9	3	LFA_COACH	1	1	2026-01-17 10:46:42.058525	\N	\N	\N	t	2026-01-17 10:46:42.058526	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060254	2026-01-17 11:46:42.060254
10	3	LFA_COACH	2	2	2026-01-17 10:46:42.058545	\N	\N	\N	t	2026-01-17 10:46:42.058546	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060255	2026-01-17 11:46:42.060255
11	3	LFA_COACH	3	3	2026-01-17 10:46:42.058584	\N	\N	\N	t	2026-01-17 10:46:42.058585	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060256	2026-01-17 11:46:42.060256
12	3	LFA_COACH	4	4	2026-01-17 10:46:42.058604	\N	\N	\N	t	2026-01-17 10:46:42.058605	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060257	2026-01-17 11:46:42.060257
13	3	LFA_COACH	5	5	2026-01-17 10:46:42.058623	\N	\N	\N	t	2026-01-17 10:46:42.058624	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060258	2026-01-17 11:46:42.060258
14	3	LFA_COACH	6	6	2026-01-17 10:46:42.058642	\N	\N	\N	t	2026-01-17 10:46:42.058643	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060259	2026-01-17 11:46:42.060259
15	3	LFA_COACH	7	7	2026-01-17 10:46:42.058661	\N	\N	\N	t	2026-01-17 10:46:42.058662	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.06026	2026-01-17 11:46:42.06026
16	3	LFA_COACH	8	8	2026-01-17 10:46:42.058681	\N	\N	\N	t	2026-01-17 10:46:42.058681	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060261	2026-01-17 11:46:42.060261
17	3	INTERNSHIP	1	1	2026-01-17 10:46:42.058706	\N	\N	\N	t	2026-01-17 10:46:42.058707	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060262	2026-01-17 11:46:42.060262
18	3	INTERNSHIP	2	2	2026-01-17 10:46:42.058725	\N	\N	\N	t	2026-01-17 10:46:42.058726	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060263	2026-01-17 11:46:42.060263
19	3	INTERNSHIP	3	3	2026-01-17 10:46:42.058744	\N	\N	\N	t	2026-01-17 10:46:42.058745	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060264	2026-01-17 11:46:42.060264
20	3	INTERNSHIP	4	4	2026-01-17 10:46:42.058763	\N	\N	\N	t	2026-01-17 10:46:42.058764	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060265	2026-01-17 11:46:42.060265
21	3	INTERNSHIP	5	5	2026-01-17 10:46:42.058782	\N	\N	\N	t	2026-01-17 10:46:42.058783	t	\N	t	\N	\N	\N	1000	\N	\N	\N	\N	\N	\N	\N	0	0	\N	2026-01-17 11:46:42.060266	2026-01-17 11:46:42.060266
22	4	LFA_FOOTBALL_PLAYER	1	1	2026-01-17 10:49:41.379118	\N	\N	\N	t	2026-01-17 10:49:41.379121	t	2026-01-17 11:50:20.829153	t	\N	\N	\N	1000	{"position": "DEFENDER", "goals": "improve_skills", "motivation": "", "initial_self_assessment": {"heading": 10, "shooting": 4, "passing": 4, "dribbling": 9, "defending": 3, "physical": 6}, "average_skill_level": 60.0, "onboarding_completed_at": "2026-01-17T10:50:20.829114+00:00"}	60	2026-01-17 11:50:20.829145	4	\N	\N	\N	0	0	\N	2026-01-17 11:49:41.381315	2026-01-17 11:50:20.831956
23	5	LFA_FOOTBALL_PLAYER	1	1	2026-01-17 10:50:59.617834	\N	\N	\N	t	2026-01-17 10:50:59.617836	t	2026-01-17 11:51:37.831605	t	\N	\N	\N	1000	{"position": "MIDFIELDER", "goals": "improve_skills", "motivation": "", "initial_self_assessment": {"heading": 5, "shooting": 5, "passing": 1, "dribbling": 7, "defending": 7, "physical": 1}, "average_skill_level": 43.3, "onboarding_completed_at": "2026-01-17T10:51:37.831581+00:00"}	43.33333333333333	2026-01-17 11:51:37.831598	5	\N	\N	\N	0	0	\N	2026-01-17 11:50:59.619189	2026-01-17 11:51:37.835022
24	6	LFA_FOOTBALL_PLAYER	1	1	2026-01-17 10:52:15.014111	\N	\N	\N	t	2026-01-17 10:52:15.014113	t	2026-01-17 11:52:56.143624	t	\N	\N	\N	1000	{"position": "MIDFIELDER", "goals": "fitness_health", "motivation": "", "initial_self_assessment": {"heading": 8, "shooting": 5, "passing": 2, "dribbling": 1, "defending": 3, "physical": 10}, "average_skill_level": 48.3, "onboarding_completed_at": "2026-01-17T10:52:56.143599+00:00"}	48.33333333333333	2026-01-17 11:52:56.143617	6	\N	\N	\N	0	0	\N	2026-01-17 11:52:15.015758	2026-01-17 11:52:56.145746
\.


--
-- Data for Name: user_module_progresses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_module_progresses (id, user_track_progress_id, module_id, started_at, completed_at, grade, status, attempts, time_spent_minutes, created_at) FROM stdin;
\.


--
-- Data for Name: user_question_performance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_question_performance (id, user_id, question_id, total_attempts, correct_attempts, last_attempt_correct, last_attempted_at, difficulty_weight, next_review_at, mastery_level) FROM stdin;
\.


--
-- Data for Name: user_stats; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_stats (id, user_id, semesters_participated, first_semester_date, current_streak, total_bookings, total_attended, total_cancelled, attendance_rate, feedback_given, average_rating_given, punctuality_score, total_xp, level, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_track_progresses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_track_progresses (id, user_id, track_id, enrollment_date, current_semester, status, completion_percentage, certificate_id, started_at, completed_at, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, name, nickname, first_name, last_name, email, password_hash, role, is_active, onboarding_completed, phone, emergency_contact, emergency_phone, date_of_birth, medical_notes, interests, "position", nationality, gender, current_location, street_address, city, postal_code, country, specialization, payment_verified, payment_verified_at, payment_verified_by, credit_balance, credit_purchased, credit_payment_reference, nda_accepted, nda_accepted_at, nda_ip_address, parental_consent, parental_consent_at, parental_consent_by, created_at, updated_at, created_by) FROM stdin;
1	Admin User	\N	\N	\N	admin@lfa.com	$2b$10$zp0y6Hd6JONL3hQi0Qh78OScBZY7.sUAx6T.JL9mDX74tw4mPTR3C	ADMIN	t	t	\N	\N	\N	1990-01-01 00:00:00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N	0	0	\N	f	\N	\N	f	\N	\N	2026-01-17 10:46:41.887274	2026-01-17 11:46:41.993899	1
3	Grand Master	\N	\N	\N	grandmaster@lfa.com	$2b$10$1YOA9v2Enml7kcrqC5yTQedkv8rN21bt/qESlIirwYm4KgmrhXenO	INSTRUCTOR	t	t	\N	\N	\N	1985-01-01 00:00:00	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N	5000	0	\N	f	\N	\N	f	\N	\N	2026-01-17 10:46:42.056587	2026-01-17 11:46:42.05723	1
4	Kristóf Kis	Krisz	Kristóf	Kis	pwt.k1sqx1@f1stteam.hu	$2b$10$roKdtPu9HP.lEJG3GxuCAOHTsRe6D/t3yk5yQ2nhzQBUI9Iy6yg.S	STUDENT	t	t	+36201234567	\N	\N	2014-05-15 00:00:00	\N	\N	\N	Hungarian	Male	\N	Fő utca 12	Budapest	1011	Hungary	LFA_FOOTBALL_PLAYER	f	\N	\N	0	50	\N	f	\N	\N	f	\N	\N	2026-01-17 11:48:01.555284	2026-01-17 11:50:20.83102	\N
5	Péter Pataki	Peti	Péter	Pataki	pwt.p3t1k3@f1stteam.hu	$2b$10$sI99/l.xX9Fb/LIzJjX5MugUcOHBUzQY//EH5r8eX0YlOe9vAL9/e	STUDENT	t	t	+36302345678	\N	\N	2009-08-20 00:00:00	\N	\N	\N	Hungarian	Male	\N	Petőfi utca 34	Debrecen	4024	Hungary	LFA_FOOTBALL_PLAYER	f	\N	\N	0	50	\N	f	\N	\N	f	\N	\N	2026-01-17 11:48:32.436771	2026-01-17 11:51:37.834117	\N
6	Viktor Valverde	Viki	Viktor	Valverde	pwt.V4lv3rd3jr@f1stteam.hu	$2b$10$h0ncye75bO8fIN7vkP6qxu2IQUeqPGtr7bIF8mV9SJEIlkIoQFFue	STUDENT	t	t	+36703456789	\N	\N	2004-11-12 00:00:00	\N	\N	\N	Hungarian	Male	\N	Rákóczi út 56	Szeged	6720	Hungary	LFA_FOOTBALL_PLAYER	f	\N	\N	0	50	\N	f	\N	\N	f	\N	\N	2026-01-17 11:49:04.43324	2026-01-17 11:52:56.14527	\N
\.


--
-- Name: achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.achievements_id_seq', 1, false);


--
-- Name: adaptive_learning_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.adaptive_learning_sessions_id_seq', 1, false);


--
-- Name: attendance_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attendance_history_id_seq', 1, false);


--
-- Name: attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attendance_id_seq', 1, false);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 320, true);


--
-- Name: belt_promotions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.belt_promotions_id_seq', 1, false);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bookings_id_seq', 1, false);


--
-- Name: campuses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.campuses_id_seq', 1, false);


--
-- Name: coach_levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.coach_levels_id_seq', 1, false);


--
-- Name: coupon_usages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.coupon_usages_id_seq', 3, true);


--
-- Name: coupons_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.coupons_id_seq', 3, true);


--
-- Name: credit_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.credit_transactions_id_seq', 3, true);


--
-- Name: feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.feedback_id_seq', 1, false);


--
-- Name: football_skill_assessments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.football_skill_assessments_id_seq', 1, false);


--
-- Name: groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.groups_id_seq', 1, false);


--
-- Name: instructor_assignment_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_assignment_requests_id_seq', 1, false);


--
-- Name: instructor_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_assignments_id_seq', 1, false);


--
-- Name: instructor_availability_windows_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_availability_windows_id_seq', 1, false);


--
-- Name: instructor_positions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_positions_id_seq', 1, false);


--
-- Name: instructor_session_reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_session_reviews_id_seq', 1, false);


--
-- Name: instructor_specialization_availability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_specialization_availability_id_seq', 1, false);


--
-- Name: instructor_specializations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.instructor_specializations_id_seq', 1, false);


--
-- Name: internship_levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.internship_levels_id_seq', 1, false);


--
-- Name: invitation_codes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.invitation_codes_id_seq', 3, true);


--
-- Name: invoice_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.invoice_requests_id_seq', 1, false);


--
-- Name: license_metadata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.license_metadata_id_seq', 1, false);


--
-- Name: license_progressions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.license_progressions_id_seq', 1, false);


--
-- Name: location_master_instructors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.location_master_instructors_id_seq', 1, false);


--
-- Name: locations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.locations_id_seq', 1, false);


--
-- Name: messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.messages_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: player_levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.player_levels_id_seq', 1, false);


--
-- Name: position_applications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.position_applications_id_seq', 1, false);


--
-- Name: project_enrollment_quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_enrollment_quizzes_id_seq', 1, false);


--
-- Name: project_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_enrollments_id_seq', 1, false);


--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_milestone_progress_id_seq', 1, false);


--
-- Name: project_milestones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_milestones_id_seq', 1, false);


--
-- Name: project_quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_quizzes_id_seq', 1, false);


--
-- Name: project_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_sessions_id_seq', 1, false);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.projects_id_seq', 1, false);


--
-- Name: question_metadata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.question_metadata_id_seq', 1, false);


--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.quiz_answer_options_id_seq', 1, false);


--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.quiz_attempts_id_seq', 1, false);


--
-- Name: quiz_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.quiz_questions_id_seq', 1, false);


--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.quiz_user_answers_id_seq', 1, false);


--
-- Name: quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.quizzes_id_seq', 1, false);


--
-- Name: semester_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.semester_enrollments_id_seq', 1, false);


--
-- Name: semesters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.semesters_id_seq', 6, true);


--
-- Name: session_group_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.session_group_assignments_id_seq', 1, false);


--
-- Name: session_group_students_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.session_group_students_id_seq', 1, false);


--
-- Name: session_quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.session_quizzes_id_seq', 1, false);


--
-- Name: sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.sessions_id_seq', 1, false);


--
-- Name: specialization_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.specialization_progress_id_seq', 1, false);


--
-- Name: student_performance_reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.student_performance_reviews_id_seq', 1, false);


--
-- Name: team_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.team_members_id_seq', 1, false);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teams_id_seq', 1, false);


--
-- Name: tournament_rankings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_rankings_id_seq', 1, false);


--
-- Name: tournament_rewards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_rewards_id_seq', 1, false);


--
-- Name: tournament_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_stats_id_seq', 1, false);


--
-- Name: tournament_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_status_history_id_seq', 1, false);


--
-- Name: tournament_team_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_team_enrollments_id_seq', 1, false);


--
-- Name: tournament_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_types_id_seq', 4, true);


--
-- Name: user_achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_achievements_id_seq', 1, false);


--
-- Name: user_licenses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_licenses_id_seq', 24, true);


--
-- Name: user_question_performance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_question_performance_id_seq', 1, false);


--
-- Name: user_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_stats_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 6, true);


--
-- Name: achievements achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements
    ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);


--
-- Name: adaptive_learning_sessions adaptive_learning_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.adaptive_learning_sessions
    ADD CONSTRAINT adaptive_learning_sessions_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attendance_history attendance_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance_history
    ADD CONSTRAINT attendance_history_pkey PRIMARY KEY (id);


--
-- Name: attendance attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: belt_promotions belt_promotions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.belt_promotions
    ADD CONSTRAINT belt_promotions_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: campuses campuses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campuses
    ADD CONSTRAINT campuses_pkey PRIMARY KEY (id);


--
-- Name: certificate_templates certificate_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.certificate_templates
    ADD CONSTRAINT certificate_templates_pkey PRIMARY KEY (id);


--
-- Name: coach_levels coach_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coach_levels
    ADD CONSTRAINT coach_levels_pkey PRIMARY KEY (id);


--
-- Name: coupon_usages coupon_usages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_pkey PRIMARY KEY (id);


--
-- Name: coupons coupons_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coupons
    ADD CONSTRAINT coupons_pkey PRIMARY KEY (id);


--
-- Name: credit_transactions credit_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: football_skill_assessments football_skill_assessments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.football_skill_assessments
    ADD CONSTRAINT football_skill_assessments_pkey PRIMARY KEY (id);


--
-- Name: group_users group_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_users
    ADD CONSTRAINT group_users_pkey PRIMARY KEY (group_id, user_id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: instructor_assignment_requests instructor_assignment_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignment_requests
    ADD CONSTRAINT instructor_assignment_requests_pkey PRIMARY KEY (id);


--
-- Name: instructor_assignments instructor_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignments
    ADD CONSTRAINT instructor_assignments_pkey PRIMARY KEY (id);


--
-- Name: instructor_availability_windows instructor_availability_windows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_availability_windows
    ADD CONSTRAINT instructor_availability_windows_pkey PRIMARY KEY (id);


--
-- Name: instructor_positions instructor_positions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_positions
    ADD CONSTRAINT instructor_positions_pkey PRIMARY KEY (id);


--
-- Name: instructor_session_reviews instructor_session_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_session_reviews
    ADD CONSTRAINT instructor_session_reviews_pkey PRIMARY KEY (id);


--
-- Name: instructor_specialization_availability instructor_specialization_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specialization_availability
    ADD CONSTRAINT instructor_specialization_availability_pkey PRIMARY KEY (id);


--
-- Name: instructor_specializations instructor_specializations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specializations
    ADD CONSTRAINT instructor_specializations_pkey PRIMARY KEY (id);


--
-- Name: internship_levels internship_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.internship_levels
    ADD CONSTRAINT internship_levels_pkey PRIMARY KEY (id);


--
-- Name: invitation_codes invitation_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitation_codes
    ADD CONSTRAINT invitation_codes_pkey PRIMARY KEY (id);


--
-- Name: invoice_requests invoice_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoice_requests
    ADD CONSTRAINT invoice_requests_pkey PRIMARY KEY (id);


--
-- Name: issued_certificates issued_certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.issued_certificates
    ADD CONSTRAINT issued_certificates_pkey PRIMARY KEY (id);


--
-- Name: issued_certificates issued_certificates_unique_identifier_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.issued_certificates
    ADD CONSTRAINT issued_certificates_unique_identifier_key UNIQUE (unique_identifier);


--
-- Name: license_metadata license_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.license_metadata
    ADD CONSTRAINT license_metadata_pkey PRIMARY KEY (id);


--
-- Name: license_progressions license_progressions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.license_progressions
    ADD CONSTRAINT license_progressions_pkey PRIMARY KEY (id);


--
-- Name: location_master_instructors location_master_instructors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location_master_instructors
    ADD CONSTRAINT location_master_instructors_pkey PRIMARY KEY (id);


--
-- Name: locations locations_city_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_city_key UNIQUE (city);


--
-- Name: locations locations_location_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_location_code_key UNIQUE (location_code);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: module_components module_components_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.module_components
    ADD CONSTRAINT module_components_pkey PRIMARY KEY (id);


--
-- Name: modules modules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: player_levels player_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_levels
    ADD CONSTRAINT player_levels_pkey PRIMARY KEY (id);


--
-- Name: position_applications position_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.position_applications
    ADD CONSTRAINT position_applications_pkey PRIMARY KEY (id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_pkey PRIMARY KEY (id);


--
-- Name: project_enrollments project_enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT project_enrollments_pkey PRIMARY KEY (id);


--
-- Name: project_milestone_progress project_milestone_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT project_milestone_progress_pkey PRIMARY KEY (id);


--
-- Name: project_milestones project_milestones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestones
    ADD CONSTRAINT project_milestones_pkey PRIMARY KEY (id);


--
-- Name: project_quizzes project_quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_pkey PRIMARY KEY (id);


--
-- Name: project_sessions project_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: question_metadata question_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_metadata
    ADD CONSTRAINT question_metadata_pkey PRIMARY KEY (id);


--
-- Name: quiz_answer_options quiz_answer_options_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_answer_options
    ADD CONSTRAINT quiz_answer_options_pkey PRIMARY KEY (id);


--
-- Name: quiz_attempts quiz_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_pkey PRIMARY KEY (id);


--
-- Name: quiz_questions quiz_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_questions
    ADD CONSTRAINT quiz_questions_pkey PRIMARY KEY (id);


--
-- Name: quiz_user_answers quiz_user_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_pkey PRIMARY KEY (id);


--
-- Name: quizzes quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quizzes
    ADD CONSTRAINT quizzes_pkey PRIMARY KEY (id);


--
-- Name: semester_enrollments semester_enrollments_payment_reference_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_payment_reference_code_key UNIQUE (payment_reference_code);


--
-- Name: semester_enrollments semester_enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_pkey PRIMARY KEY (id);


--
-- Name: semester_instructors semester_instructors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_instructors
    ADD CONSTRAINT semester_instructors_pkey PRIMARY KEY (semester_id, instructor_id);


--
-- Name: semesters semesters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semesters
    ADD CONSTRAINT semesters_pkey PRIMARY KEY (id);


--
-- Name: session_group_assignments session_group_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_assignments
    ADD CONSTRAINT session_group_assignments_pkey PRIMARY KEY (id);


--
-- Name: session_group_students session_group_students_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_students
    ADD CONSTRAINT session_group_students_pkey PRIMARY KEY (id);


--
-- Name: session_quizzes session_quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_quizzes
    ADD CONSTRAINT session_quizzes_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: specialization_progress specialization_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialization_progress
    ADD CONSTRAINT specialization_progress_pkey PRIMARY KEY (id);


--
-- Name: specializations specializations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specializations
    ADD CONSTRAINT specializations_pkey PRIMARY KEY (id);


--
-- Name: student_performance_reviews student_performance_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_performance_reviews
    ADD CONSTRAINT student_performance_reviews_pkey PRIMARY KEY (id);


--
-- Name: team_members team_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_pkey PRIMARY KEY (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: tournament_rankings tournament_rankings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rankings
    ADD CONSTRAINT tournament_rankings_pkey PRIMARY KEY (id);


--
-- Name: tournament_rewards tournament_rewards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rewards
    ADD CONSTRAINT tournament_rewards_pkey PRIMARY KEY (id);


--
-- Name: tournament_stats tournament_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_stats
    ADD CONSTRAINT tournament_stats_pkey PRIMARY KEY (id);


--
-- Name: tournament_status_history tournament_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_status_history
    ADD CONSTRAINT tournament_status_history_pkey PRIMARY KEY (id);


--
-- Name: tournament_team_enrollments tournament_team_enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_team_enrollments
    ADD CONSTRAINT tournament_team_enrollments_pkey PRIMARY KEY (id);


--
-- Name: tournament_types tournament_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_types
    ADD CONSTRAINT tournament_types_pkey PRIMARY KEY (id);


--
-- Name: tracks tracks_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tracks
    ADD CONSTRAINT tracks_code_key UNIQUE (code);


--
-- Name: tracks tracks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tracks
    ADD CONSTRAINT tracks_pkey PRIMARY KEY (id);


--
-- Name: instructor_specialization_availability uix_instructor_spec_period_year_location; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specialization_availability
    ADD CONSTRAINT uix_instructor_spec_period_year_location UNIQUE (instructor_id, specialization_type, time_period_code, year, location_city);


--
-- Name: project_milestone_progress unique_enrollment_milestone; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT unique_enrollment_milestone UNIQUE (enrollment_id, milestone_id);


--
-- Name: project_quizzes unique_project_quiz_type; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT unique_project_quiz_type UNIQUE (project_id, quiz_id, quiz_type);


--
-- Name: project_sessions unique_project_session; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT unique_project_session UNIQUE (project_id, session_id);


--
-- Name: project_enrollments unique_project_user; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT unique_project_user UNIQUE (project_id, user_id);


--
-- Name: project_enrollment_quizzes unique_project_user_enrollment_quiz; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT unique_project_user_enrollment_quiz UNIQUE (project_id, user_id);


--
-- Name: question_metadata unique_question_metadata; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_metadata
    ADD CONSTRAINT unique_question_metadata UNIQUE (question_id);


--
-- Name: user_question_performance unique_user_question; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT unique_user_question UNIQUE (user_id, question_id);


--
-- Name: semester_enrollments uq_semester_enrollments_user_semester_license; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT uq_semester_enrollments_user_semester_license UNIQUE (user_id, semester_id, user_license_id);


--
-- Name: session_group_assignments uq_session_group_number; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_assignments
    ADD CONSTRAINT uq_session_group_number UNIQUE (session_id, group_number);


--
-- Name: session_group_students uq_session_group_student; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_students
    ADD CONSTRAINT uq_session_group_student UNIQUE (session_group_id, student_id);


--
-- Name: session_quizzes uq_session_quiz; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_quizzes
    ADD CONSTRAINT uq_session_quiz UNIQUE (session_id, quiz_id);


--
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (id);


--
-- Name: user_licenses user_licenses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_pkey PRIMARY KEY (id);


--
-- Name: user_module_progresses user_module_progresses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_module_progresses
    ADD CONSTRAINT user_module_progresses_pkey PRIMARY KEY (id);


--
-- Name: user_question_performance user_question_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT user_question_performance_pkey PRIMARY KEY (id);


--
-- Name: user_stats user_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_stats
    ADD CONSTRAINT user_stats_pkey PRIMARY KEY (id);


--
-- Name: user_stats user_stats_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_stats
    ADD CONSTRAINT user_stats_user_id_key UNIQUE (user_id);


--
-- Name: user_track_progresses user_track_progresses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_track_progresses
    ADD CONSTRAINT user_track_progresses_pkey PRIMARY KEY (id);


--
-- Name: users users_credit_payment_reference_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_credit_payment_reference_key UNIQUE (credit_payment_reference);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_achievements_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_achievements_category ON public.achievements USING btree (category);


--
-- Name: ix_achievements_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_achievements_code ON public.achievements USING btree (code);


--
-- Name: ix_achievements_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_achievements_id ON public.achievements USING btree (id);


--
-- Name: ix_achievements_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_achievements_is_active ON public.achievements USING btree (is_active);


--
-- Name: ix_adaptive_learning_sessions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_adaptive_learning_sessions_id ON public.adaptive_learning_sessions USING btree (id);


--
-- Name: ix_attendance_history_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attendance_history_id ON public.attendance_history USING btree (id);


--
-- Name: ix_attendance_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attendance_id ON public.attendance USING btree (id);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);


--
-- Name: ix_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_timestamp ON public.audit_logs USING btree ("timestamp");


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_belt_promotions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_belt_promotions_id ON public.belt_promotions USING btree (id);


--
-- Name: ix_belt_promotions_promoted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_belt_promotions_promoted_at ON public.belt_promotions USING btree (promoted_at);


--
-- Name: ix_belt_promotions_to_belt; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_belt_promotions_to_belt ON public.belt_promotions USING btree (to_belt);


--
-- Name: ix_belt_promotions_user_license_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_belt_promotions_user_license_id ON public.belt_promotions USING btree (user_license_id);


--
-- Name: ix_bookings_enrollment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_enrollment_id ON public.bookings USING btree (enrollment_id);


--
-- Name: ix_bookings_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_id ON public.bookings USING btree (id);


--
-- Name: ix_campuses_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_campuses_id ON public.campuses USING btree (id);


--
-- Name: ix_coupon_usages_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_coupon_usages_id ON public.coupon_usages USING btree (id);


--
-- Name: ix_coupons_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_coupons_code ON public.coupons USING btree (code);


--
-- Name: ix_coupons_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_coupons_id ON public.coupons USING btree (id);


--
-- Name: ix_credit_transactions_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credit_transactions_created_at ON public.credit_transactions USING btree (created_at);


--
-- Name: ix_credit_transactions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credit_transactions_id ON public.credit_transactions USING btree (id);


--
-- Name: ix_credit_transactions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credit_transactions_user_id ON public.credit_transactions USING btree (user_id);


--
-- Name: ix_credit_transactions_user_license_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credit_transactions_user_license_id ON public.credit_transactions USING btree (user_license_id);


--
-- Name: ix_feedback_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_feedback_id ON public.feedback USING btree (id);


--
-- Name: ix_football_skill_assessments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_football_skill_assessments_id ON public.football_skill_assessments USING btree (id);


--
-- Name: ix_groups_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_groups_id ON public.groups USING btree (id);


--
-- Name: ix_instructor_assignment_requests_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_assignment_requests_id ON public.instructor_assignment_requests USING btree (id);


--
-- Name: ix_instructor_assignments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_assignments_id ON public.instructor_assignments USING btree (id);


--
-- Name: ix_instructor_availability_windows_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_availability_windows_id ON public.instructor_availability_windows USING btree (id);


--
-- Name: ix_instructor_positions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_positions_id ON public.instructor_positions USING btree (id);


--
-- Name: ix_instructor_session_reviews_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_session_reviews_id ON public.instructor_session_reviews USING btree (id);


--
-- Name: ix_instructor_specialization_availability_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_specialization_availability_id ON public.instructor_specialization_availability USING btree (id);


--
-- Name: ix_instructor_specializations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_instructor_specializations_id ON public.instructor_specializations USING btree (id);


--
-- Name: ix_invitation_codes_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_invitation_codes_code ON public.invitation_codes USING btree (code);


--
-- Name: ix_invitation_codes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invitation_codes_id ON public.invitation_codes USING btree (id);


--
-- Name: ix_invoice_requests_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_invoice_requests_id ON public.invoice_requests USING btree (id);


--
-- Name: ix_invoice_requests_payment_reference; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_invoice_requests_payment_reference ON public.invoice_requests USING btree (payment_reference);


--
-- Name: ix_license_metadata_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_license_metadata_id ON public.license_metadata USING btree (id);


--
-- Name: ix_license_progressions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_license_progressions_id ON public.license_progressions USING btree (id);


--
-- Name: ix_location_master_instructors_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_location_master_instructors_id ON public.location_master_instructors USING btree (id);


--
-- Name: ix_locations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_locations_id ON public.locations USING btree (id);


--
-- Name: ix_messages_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_messages_id ON public.messages USING btree (id);


--
-- Name: ix_notifications_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);


--
-- Name: ix_position_applications_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_position_applications_id ON public.position_applications USING btree (id);


--
-- Name: ix_project_enrollment_quizzes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_project_enrollment_quizzes_id ON public.project_enrollment_quizzes USING btree (id);


--
-- Name: ix_project_enrollments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_project_enrollments_id ON public.project_enrollments USING btree (id);


--
-- Name: ix_project_milestone_progress_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_project_milestone_progress_id ON public.project_milestone_progress USING btree (id);


--
-- Name: ix_project_milestones_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_project_milestones_id ON public.project_milestones USING btree (id);


--
-- Name: ix_project_quizzes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_project_quizzes_id ON public.project_quizzes USING btree (id);


--
-- Name: ix_project_sessions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_project_sessions_id ON public.project_sessions USING btree (id);


--
-- Name: ix_projects_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_projects_id ON public.projects USING btree (id);


--
-- Name: ix_question_metadata_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_question_metadata_id ON public.question_metadata USING btree (id);


--
-- Name: ix_quiz_answer_options_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quiz_answer_options_id ON public.quiz_answer_options USING btree (id);


--
-- Name: ix_quiz_attempts_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quiz_attempts_id ON public.quiz_attempts USING btree (id);


--
-- Name: ix_quiz_questions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quiz_questions_id ON public.quiz_questions USING btree (id);


--
-- Name: ix_quiz_user_answers_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quiz_user_answers_id ON public.quiz_user_answers USING btree (id);


--
-- Name: ix_quizzes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quizzes_id ON public.quizzes USING btree (id);


--
-- Name: ix_semester_enrollments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semester_enrollments_id ON public.semester_enrollments USING btree (id);


--
-- Name: ix_semester_enrollments_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semester_enrollments_is_active ON public.semester_enrollments USING btree (is_active);


--
-- Name: ix_semester_enrollments_payment_verified; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semester_enrollments_payment_verified ON public.semester_enrollments USING btree (payment_verified);


--
-- Name: ix_semester_enrollments_semester_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semester_enrollments_semester_id ON public.semester_enrollments USING btree (semester_id);


--
-- Name: ix_semester_enrollments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semester_enrollments_user_id ON public.semester_enrollments USING btree (user_id);


--
-- Name: ix_semester_enrollments_user_license_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semester_enrollments_user_license_id ON public.semester_enrollments USING btree (user_license_id);


--
-- Name: ix_semesters_age_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_age_group ON public.semesters USING btree (age_group);


--
-- Name: ix_semesters_campus_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_campus_id ON public.semesters USING btree (campus_id);


--
-- Name: ix_semesters_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_semesters_code ON public.semesters USING btree (code);


--
-- Name: ix_semesters_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_id ON public.semesters USING btree (id);


--
-- Name: ix_semesters_location_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_location_id ON public.semesters USING btree (location_id);


--
-- Name: ix_semesters_specialization_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_specialization_type ON public.semesters USING btree (specialization_type);


--
-- Name: ix_semesters_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_status ON public.semesters USING btree (status);


--
-- Name: ix_semesters_tournament_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semesters_tournament_status ON public.semesters USING btree (tournament_status);


--
-- Name: ix_session_group_assignments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_session_group_assignments_id ON public.session_group_assignments USING btree (id);


--
-- Name: ix_session_group_assignments_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_session_group_assignments_session_id ON public.session_group_assignments USING btree (session_id);


--
-- Name: ix_session_group_students_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_session_group_students_id ON public.session_group_students USING btree (id);


--
-- Name: ix_session_group_students_session_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_session_group_students_session_group_id ON public.session_group_students USING btree (session_group_id);


--
-- Name: ix_session_quizzes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_session_quizzes_id ON public.session_quizzes USING btree (id);


--
-- Name: ix_sessions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_sessions_id ON public.sessions USING btree (id);


--
-- Name: ix_sessions_is_tournament_game; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_sessions_is_tournament_game ON public.sessions USING btree (is_tournament_game);


--
-- Name: ix_student_performance_reviews_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_student_performance_reviews_id ON public.student_performance_reviews USING btree (id);


--
-- Name: ix_team_members_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_team_members_id ON public.team_members USING btree (id);


--
-- Name: ix_team_members_team_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_team_members_team_id ON public.team_members USING btree (team_id);


--
-- Name: ix_team_members_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_team_members_user_id ON public.team_members USING btree (user_id);


--
-- Name: ix_teams_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_teams_code ON public.teams USING btree (code);


--
-- Name: ix_teams_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teams_id ON public.teams USING btree (id);


--
-- Name: ix_tournament_rankings_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_rankings_id ON public.tournament_rankings USING btree (id);


--
-- Name: ix_tournament_rankings_tournament_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_rankings_tournament_id ON public.tournament_rankings USING btree (tournament_id);


--
-- Name: ix_tournament_rewards_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_rewards_id ON public.tournament_rewards USING btree (id);


--
-- Name: ix_tournament_rewards_tournament_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_rewards_tournament_id ON public.tournament_rewards USING btree (tournament_id);


--
-- Name: ix_tournament_stats_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_stats_id ON public.tournament_stats USING btree (id);


--
-- Name: ix_tournament_stats_tournament_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tournament_stats_tournament_id ON public.tournament_stats USING btree (tournament_id);


--
-- Name: ix_tournament_status_history_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_status_history_id ON public.tournament_status_history USING btree (id);


--
-- Name: ix_tournament_status_history_tournament_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_status_history_tournament_id ON public.tournament_status_history USING btree (tournament_id);


--
-- Name: ix_tournament_team_enrollments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_team_enrollments_id ON public.tournament_team_enrollments USING btree (id);


--
-- Name: ix_tournament_team_enrollments_semester_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_team_enrollments_semester_id ON public.tournament_team_enrollments USING btree (semester_id);


--
-- Name: ix_tournament_team_enrollments_team_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_team_enrollments_team_id ON public.tournament_team_enrollments USING btree (team_id);


--
-- Name: ix_tournament_types_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tournament_types_code ON public.tournament_types USING btree (code);


--
-- Name: ix_tournament_types_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournament_types_id ON public.tournament_types USING btree (id);


--
-- Name: ix_user_achievements_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_achievements_id ON public.user_achievements USING btree (id);


--
-- Name: ix_user_licenses_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_licenses_id ON public.user_licenses USING btree (id);


--
-- Name: ix_user_licenses_payment_reference_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_licenses_payment_reference_code ON public.user_licenses USING btree (payment_reference_code);


--
-- Name: ix_user_question_performance_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_question_performance_id ON public.user_question_performance USING btree (id);


--
-- Name: ix_user_stats_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_stats_id ON public.user_stats USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: adaptive_learning_sessions adaptive_learning_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.adaptive_learning_sessions
    ADD CONSTRAINT adaptive_learning_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: attendance attendance_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: attendance attendance_change_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_change_requested_by_fkey FOREIGN KEY (change_requested_by) REFERENCES public.users(id);


--
-- Name: attendance_history attendance_history_attendance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance_history
    ADD CONSTRAINT attendance_history_attendance_id_fkey FOREIGN KEY (attendance_id) REFERENCES public.attendance(id);


--
-- Name: attendance_history attendance_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance_history
    ADD CONSTRAINT attendance_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);


--
-- Name: attendance attendance_marked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_marked_by_fkey FOREIGN KEY (marked_by) REFERENCES public.users(id);


--
-- Name: attendance attendance_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: attendance attendance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: belt_promotions belt_promotions_promoted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.belt_promotions
    ADD CONSTRAINT belt_promotions_promoted_by_fkey FOREIGN KEY (promoted_by) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: belt_promotions belt_promotions_user_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.belt_promotions
    ADD CONSTRAINT belt_promotions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;


--
-- Name: bookings bookings_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.semester_enrollments(id);


--
-- Name: bookings bookings_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: bookings bookings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: campuses campuses_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.campuses
    ADD CONSTRAINT campuses_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: certificate_templates certificate_templates_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.certificate_templates
    ADD CONSTRAINT certificate_templates_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: coupon_usages coupon_usages_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id) ON DELETE CASCADE;


--
-- Name: coupon_usages coupon_usages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: credit_transactions credit_transactions_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.semester_enrollments(id) ON DELETE SET NULL;


--
-- Name: credit_transactions credit_transactions_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE SET NULL;


--
-- Name: credit_transactions credit_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: credit_transactions credit_transactions_user_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;


--
-- Name: feedback feedback_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: feedback feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: football_skill_assessments football_skill_assessments_assessed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.football_skill_assessments
    ADD CONSTRAINT football_skill_assessments_assessed_by_fkey FOREIGN KEY (assessed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: football_skill_assessments football_skill_assessments_user_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.football_skill_assessments
    ADD CONSTRAINT football_skill_assessments_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;


--
-- Name: group_users group_users_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_users
    ADD CONSTRAINT group_users_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: group_users group_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_users
    ADD CONSTRAINT group_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: groups groups_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: instructor_assignment_requests instructor_assignment_requests_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignment_requests
    ADD CONSTRAINT instructor_assignment_requests_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: instructor_assignment_requests instructor_assignment_requests_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignment_requests
    ADD CONSTRAINT instructor_assignment_requests_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: instructor_assignment_requests instructor_assignment_requests_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignment_requests
    ADD CONSTRAINT instructor_assignment_requests_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: instructor_assignment_requests instructor_assignment_requests_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignment_requests
    ADD CONSTRAINT instructor_assignment_requests_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: instructor_assignments instructor_assignments_assigned_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignments
    ADD CONSTRAINT instructor_assignments_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: instructor_assignments instructor_assignments_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignments
    ADD CONSTRAINT instructor_assignments_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: instructor_assignments instructor_assignments_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_assignments
    ADD CONSTRAINT instructor_assignments_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: instructor_availability_windows instructor_availability_windows_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_availability_windows
    ADD CONSTRAINT instructor_availability_windows_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: instructor_positions instructor_positions_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_positions
    ADD CONSTRAINT instructor_positions_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: instructor_positions instructor_positions_posted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_positions
    ADD CONSTRAINT instructor_positions_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: instructor_session_reviews instructor_session_reviews_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_session_reviews
    ADD CONSTRAINT instructor_session_reviews_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);


--
-- Name: instructor_session_reviews instructor_session_reviews_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_session_reviews
    ADD CONSTRAINT instructor_session_reviews_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: instructor_session_reviews instructor_session_reviews_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_session_reviews
    ADD CONSTRAINT instructor_session_reviews_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: instructor_specialization_availability instructor_specialization_availability_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specialization_availability
    ADD CONSTRAINT instructor_specialization_availability_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: instructor_specializations instructor_specializations_certified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specializations
    ADD CONSTRAINT instructor_specializations_certified_by_fkey FOREIGN KEY (certified_by) REFERENCES public.users(id);


--
-- Name: instructor_specializations instructor_specializations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instructor_specializations
    ADD CONSTRAINT instructor_specializations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: invitation_codes invitation_codes_created_by_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitation_codes
    ADD CONSTRAINT invitation_codes_created_by_admin_id_fkey FOREIGN KEY (created_by_admin_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitation_codes invitation_codes_used_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitation_codes
    ADD CONSTRAINT invitation_codes_used_by_user_id_fkey FOREIGN KEY (used_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invoice_requests invoice_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoice_requests
    ADD CONSTRAINT invoice_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: issued_certificates issued_certificates_certificate_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.issued_certificates
    ADD CONSTRAINT issued_certificates_certificate_template_id_fkey FOREIGN KEY (certificate_template_id) REFERENCES public.certificate_templates(id);


--
-- Name: issued_certificates issued_certificates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.issued_certificates
    ADD CONSTRAINT issued_certificates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: license_progressions license_progressions_advanced_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.license_progressions
    ADD CONSTRAINT license_progressions_advanced_by_fkey FOREIGN KEY (advanced_by) REFERENCES public.users(id);


--
-- Name: license_progressions license_progressions_user_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.license_progressions
    ADD CONSTRAINT license_progressions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id);


--
-- Name: location_master_instructors location_master_instructors_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location_master_instructors
    ADD CONSTRAINT location_master_instructors_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: location_master_instructors location_master_instructors_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location_master_instructors
    ADD CONSTRAINT location_master_instructors_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: location_master_instructors location_master_instructors_source_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location_master_instructors
    ADD CONSTRAINT location_master_instructors_source_position_id_fkey FOREIGN KEY (source_position_id) REFERENCES public.instructor_positions(id) ON DELETE SET NULL;


--
-- Name: messages messages_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.users(id);


--
-- Name: messages messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: module_components module_components_module_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.module_components
    ADD CONSTRAINT module_components_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.modules(id);


--
-- Name: modules modules_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: modules modules_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: notifications notifications_related_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_booking_id_fkey FOREIGN KEY (related_booking_id) REFERENCES public.bookings(id);


--
-- Name: notifications notifications_related_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_request_id_fkey FOREIGN KEY (related_request_id) REFERENCES public.instructor_assignment_requests(id);


--
-- Name: notifications notifications_related_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_semester_id_fkey FOREIGN KEY (related_semester_id) REFERENCES public.semesters(id);


--
-- Name: notifications notifications_related_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_session_id_fkey FOREIGN KEY (related_session_id) REFERENCES public.sessions(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: position_applications position_applications_applicant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.position_applications
    ADD CONSTRAINT position_applications_applicant_id_fkey FOREIGN KEY (applicant_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: position_applications position_applications_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.position_applications
    ADD CONSTRAINT position_applications_position_id_fkey FOREIGN KEY (position_id) REFERENCES public.instructor_positions(id) ON DELETE CASCADE;


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_quiz_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_quiz_attempt_id_fkey FOREIGN KEY (quiz_attempt_id) REFERENCES public.quiz_attempts(id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_enrollments project_enrollments_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT project_enrollments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_enrollments project_enrollments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT project_enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_milestone_progress project_milestone_progress_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT project_milestone_progress_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.project_enrollments(id);


--
-- Name: project_milestone_progress project_milestone_progress_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT project_milestone_progress_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);


--
-- Name: project_milestones project_milestones_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_milestones
    ADD CONSTRAINT project_milestones_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_quizzes project_quizzes_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);


--
-- Name: project_quizzes project_quizzes_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_quizzes project_quizzes_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);


--
-- Name: project_sessions project_sessions_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);


--
-- Name: project_sessions project_sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_sessions project_sessions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: projects projects_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);


--
-- Name: projects projects_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: question_metadata question_metadata_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_metadata
    ADD CONSTRAINT question_metadata_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: quiz_answer_options quiz_answer_options_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_answer_options
    ADD CONSTRAINT quiz_answer_options_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: quiz_attempts quiz_attempts_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);


--
-- Name: quiz_attempts quiz_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: quiz_questions quiz_questions_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_questions
    ADD CONSTRAINT quiz_questions_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);


--
-- Name: quiz_user_answers quiz_user_answers_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.quiz_attempts(id);


--
-- Name: quiz_user_answers quiz_user_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: quiz_user_answers quiz_user_answers_selected_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_selected_option_id_fkey FOREIGN KEY (selected_option_id) REFERENCES public.quiz_answer_options(id);


--
-- Name: semester_enrollments semester_enrollments_age_category_overridden_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_age_category_overridden_by_fkey FOREIGN KEY (age_category_overridden_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semester_enrollments semester_enrollments_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semester_enrollments semester_enrollments_payment_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_payment_verified_by_fkey FOREIGN KEY (payment_verified_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semester_enrollments semester_enrollments_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: semester_enrollments semester_enrollments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: semester_enrollments semester_enrollments_user_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_enrollments
    ADD CONSTRAINT semester_enrollments_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id) ON DELETE CASCADE;


--
-- Name: semester_instructors semester_instructors_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_instructors
    ADD CONSTRAINT semester_instructors_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: semester_instructors semester_instructors_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semester_instructors
    ADD CONSTRAINT semester_instructors_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: semesters semesters_campus_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semesters
    ADD CONSTRAINT semesters_campus_id_fkey FOREIGN KEY (campus_id) REFERENCES public.campuses(id) ON DELETE SET NULL;


--
-- Name: semesters semesters_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semesters
    ADD CONSTRAINT semesters_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE SET NULL;


--
-- Name: semesters semesters_master_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semesters
    ADD CONSTRAINT semesters_master_instructor_id_fkey FOREIGN KEY (master_instructor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semesters semesters_tournament_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semesters
    ADD CONSTRAINT semesters_tournament_type_id_fkey FOREIGN KEY (tournament_type_id) REFERENCES public.tournament_types(id) ON DELETE SET NULL;


--
-- Name: session_group_assignments session_group_assignments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_assignments
    ADD CONSTRAINT session_group_assignments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: session_group_assignments session_group_assignments_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_assignments
    ADD CONSTRAINT session_group_assignments_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_group_assignments session_group_assignments_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_assignments
    ADD CONSTRAINT session_group_assignments_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: session_group_students session_group_students_session_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_students
    ADD CONSTRAINT session_group_students_session_group_id_fkey FOREIGN KEY (session_group_id) REFERENCES public.session_group_assignments(id) ON DELETE CASCADE;


--
-- Name: session_group_students session_group_students_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_group_students
    ADD CONSTRAINT session_group_students_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_quizzes session_quizzes_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_quizzes
    ADD CONSTRAINT session_quizzes_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id) ON DELETE CASCADE;


--
-- Name: session_quizzes session_quizzes_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_quizzes
    ADD CONSTRAINT session_quizzes_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: sessions sessions_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);


--
-- Name: sessions sessions_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: specialization_progress specialization_progress_specialization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialization_progress
    ADD CONSTRAINT specialization_progress_specialization_id_fkey FOREIGN KEY (specialization_id) REFERENCES public.specializations(id) ON DELETE CASCADE;


--
-- Name: specialization_progress specialization_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialization_progress
    ADD CONSTRAINT specialization_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_performance_reviews student_performance_reviews_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_performance_reviews
    ADD CONSTRAINT student_performance_reviews_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);


--
-- Name: student_performance_reviews student_performance_reviews_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_performance_reviews
    ADD CONSTRAINT student_performance_reviews_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: student_performance_reviews student_performance_reviews_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_performance_reviews
    ADD CONSTRAINT student_performance_reviews_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: team_members team_members_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: teams teams_captain_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_captain_user_id_fkey FOREIGN KEY (captain_user_id) REFERENCES public.users(id);


--
-- Name: tournament_rankings tournament_rankings_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rankings
    ADD CONSTRAINT tournament_rankings_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: tournament_rankings tournament_rankings_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rankings
    ADD CONSTRAINT tournament_rankings_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: tournament_rankings tournament_rankings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rankings
    ADD CONSTRAINT tournament_rankings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tournament_rewards tournament_rewards_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_rewards
    ADD CONSTRAINT tournament_rewards_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: tournament_stats tournament_stats_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_stats
    ADD CONSTRAINT tournament_stats_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: tournament_status_history tournament_status_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_status_history
    ADD CONSTRAINT tournament_status_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);


--
-- Name: tournament_status_history tournament_status_history_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_status_history
    ADD CONSTRAINT tournament_status_history_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.semesters(id);


--
-- Name: tournament_team_enrollments tournament_team_enrollments_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_team_enrollments
    ADD CONSTRAINT tournament_team_enrollments_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id) ON DELETE CASCADE;


--
-- Name: tournament_team_enrollments tournament_team_enrollments_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_team_enrollments
    ADD CONSTRAINT tournament_team_enrollments_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: user_achievements user_achievements_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_achievement_id_fkey FOREIGN KEY (achievement_id) REFERENCES public.achievements(id);


--
-- Name: user_achievements user_achievements_specialization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_specialization_id_fkey FOREIGN KEY (specialization_id) REFERENCES public.specializations(id);


--
-- Name: user_achievements user_achievements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_licenses user_licenses_motivation_assessed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_motivation_assessed_by_fkey FOREIGN KEY (motivation_assessed_by) REFERENCES public.users(id);


--
-- Name: user_licenses user_licenses_skills_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_skills_updated_by_fkey FOREIGN KEY (skills_updated_by) REFERENCES public.users(id);


--
-- Name: user_licenses user_licenses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_module_progresses user_module_progresses_module_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_module_progresses
    ADD CONSTRAINT user_module_progresses_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.modules(id);


--
-- Name: user_module_progresses user_module_progresses_user_track_progress_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_module_progresses
    ADD CONSTRAINT user_module_progresses_user_track_progress_id_fkey FOREIGN KEY (user_track_progress_id) REFERENCES public.user_track_progresses(id);


--
-- Name: user_question_performance user_question_performance_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT user_question_performance_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: user_question_performance user_question_performance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT user_question_performance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_stats user_stats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_stats
    ADD CONSTRAINT user_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_track_progresses user_track_progresses_certificate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_track_progresses
    ADD CONSTRAINT user_track_progresses_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.issued_certificates(id);


--
-- Name: user_track_progresses user_track_progresses_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_track_progresses
    ADD CONSTRAINT user_track_progresses_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: user_track_progresses user_track_progresses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_track_progresses
    ADD CONSTRAINT user_track_progresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: users users_payment_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_payment_verified_by_fkey FOREIGN KEY (payment_verified_by) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict bMwg13hEs75GkGgiblkCkqHV351l8ExyVxhRBhjI0dYqjNwabYTcV5srZZHJ19J

