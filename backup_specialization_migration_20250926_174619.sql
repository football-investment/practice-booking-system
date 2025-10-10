--
-- PostgreSQL database dump
--

\restrict vAbY5tKSvLMm6b8VyGhPAnyuZ6MhmRUasnqqkaQH6omwrGSaHMw7gZXvJV6BQfu

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
-- Name: attendancestatus; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.attendancestatus AS ENUM (
    'PRESENT',
    'ABSENT',
    'LATE',
    'EXCUSED'
);


ALTER TYPE public.attendancestatus OWNER TO "lovas.zoltan";

--
-- Name: bookingstatus; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.bookingstatus AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED',
    'WAITLISTED'
);


ALTER TYPE public.bookingstatus OWNER TO "lovas.zoltan";

--
-- Name: messagepriority; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.messagepriority AS ENUM (
    'LOW',
    'NORMAL',
    'HIGH',
    'URGENT'
);


ALTER TYPE public.messagepriority OWNER TO "lovas.zoltan";

--
-- Name: notificationtype; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.notificationtype AS ENUM (
    'BOOKING_CONFIRMED',
    'BOOKING_CANCELLED',
    'SESSION_REMINDER',
    'SESSION_CANCELLED',
    'WAITLIST_PROMOTED',
    'GENERAL'
);


ALTER TYPE public.notificationtype OWNER TO "lovas.zoltan";

--
-- Name: questiontype; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.questiontype AS ENUM (
    'MULTIPLE_CHOICE',
    'TRUE_FALSE',
    'FILL_IN_BLANK',
    'matching',
    'short_answer',
    'long_answer',
    'calculation',
    'scenario_based'
);


ALTER TYPE public.questiontype OWNER TO "lovas.zoltan";

--
-- Name: quizcategory; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.quizcategory AS ENUM (
    'GENERAL',
    'MARKETING',
    'ECONOMICS',
    'INFORMATICS',
    'SPORTS_PHYSIOLOGY',
    'NUTRITION'
);


ALTER TYPE public.quizcategory OWNER TO "lovas.zoltan";

--
-- Name: quizdifficulty; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.quizdifficulty AS ENUM (
    'EASY',
    'MEDIUM',
    'HARD'
);


ALTER TYPE public.quizdifficulty OWNER TO "lovas.zoltan";

--
-- Name: sessionmode; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.sessionmode AS ENUM (
    'ONLINE',
    'OFFLINE',
    'HYBRID'
);


ALTER TYPE public.sessionmode OWNER TO "lovas.zoltan";

--
-- Name: specializationtype; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.specializationtype AS ENUM (
    'PLAYER',
    'COACH',
    'INTERNSHIP'
);


ALTER TYPE public.specializationtype OWNER TO "lovas.zoltan";

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'INSTRUCTOR',
    'STUDENT'
);


ALTER TYPE public.userrole OWNER TO "lovas.zoltan";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: adaptive_learning_sessions; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.adaptive_learning_sessions OWNER TO "lovas.zoltan";

--
-- Name: adaptive_learning_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.adaptive_learning_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.adaptive_learning_sessions_id_seq OWNER TO "lovas.zoltan";

--
-- Name: adaptive_learning_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.adaptive_learning_sessions_id_seq OWNED BY public.adaptive_learning_sessions.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO "lovas.zoltan";

--
-- Name: attendance; Type: TABLE; Schema: public; Owner: lovas.zoltan
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
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.attendance OWNER TO "lovas.zoltan";

--
-- Name: attendance_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.attendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.attendance_id_seq OWNER TO "lovas.zoltan";

--
-- Name: attendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.attendance_id_seq OWNED BY public.attendance.id;


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: lovas.zoltan
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
    attended_status character varying(20)
);


ALTER TABLE public.bookings OWNER TO "lovas.zoltan";

--
-- Name: bookings_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.bookings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.bookings_id_seq OWNER TO "lovas.zoltan";

--
-- Name: bookings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.bookings_id_seq OWNED BY public.bookings.id;


--
-- Name: feedback; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.feedback OWNER TO "lovas.zoltan";

--
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.feedback_id_seq OWNER TO "lovas.zoltan";

--
-- Name: feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;


--
-- Name: group_users; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.group_users (
    group_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.group_users OWNER TO "lovas.zoltan";

--
-- Name: groups; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    name character varying NOT NULL,
    description text,
    semester_id integer NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.groups OWNER TO "lovas.zoltan";

--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.groups_id_seq OWNER TO "lovas.zoltan";

--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: license_metadata; Type: TABLE; Schema: public; Owner: lovas.zoltan
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
    advancement_criteria jsonb,
    time_requirement_hours integer,
    project_requirements jsonb,
    evaluation_criteria jsonb,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.license_metadata OWNER TO "lovas.zoltan";

--
-- Name: license_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.license_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.license_metadata_id_seq OWNER TO "lovas.zoltan";

--
-- Name: license_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.license_metadata_id_seq OWNED BY public.license_metadata.id;


--
-- Name: license_progressions; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.license_progressions (
    id integer NOT NULL,
    user_license_id integer NOT NULL,
    from_level integer NOT NULL,
    to_level integer NOT NULL,
    advanced_by integer,
    advancement_reason text,
    requirements_met text,
    advanced_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.license_progressions OWNER TO "lovas.zoltan";

--
-- Name: license_progressions_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.license_progressions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.license_progressions_id_seq OWNER TO "lovas.zoltan";

--
-- Name: license_progressions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.license_progressions_id_seq OWNED BY public.license_progressions.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.messages OWNER TO "lovas.zoltan";

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.messages_id_seq OWNER TO "lovas.zoltan";

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: lovas.zoltan
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
    read_at timestamp without time zone
);


ALTER TABLE public.notifications OWNER TO "lovas.zoltan";

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notifications_id_seq OWNER TO "lovas.zoltan";

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: project_enrollment_quizzes; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.project_enrollment_quizzes OWNER TO "lovas.zoltan";

--
-- Name: project_enrollment_quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.project_enrollment_quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_enrollment_quizzes_id_seq OWNER TO "lovas.zoltan";

--
-- Name: project_enrollment_quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.project_enrollment_quizzes_id_seq OWNED BY public.project_enrollment_quizzes.id;


--
-- Name: project_enrollments; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.project_enrollments OWNER TO "lovas.zoltan";

--
-- Name: project_enrollments_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.project_enrollments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_enrollments_id_seq OWNER TO "lovas.zoltan";

--
-- Name: project_enrollments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.project_enrollments_id_seq OWNED BY public.project_enrollments.id;


--
-- Name: project_milestone_progress; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.project_milestone_progress OWNER TO "lovas.zoltan";

--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.project_milestone_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_milestone_progress_id_seq OWNER TO "lovas.zoltan";

--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.project_milestone_progress_id_seq OWNED BY public.project_milestone_progress.id;


--
-- Name: project_milestones; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.project_milestones OWNER TO "lovas.zoltan";

--
-- Name: project_milestones_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.project_milestones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_milestones_id_seq OWNER TO "lovas.zoltan";

--
-- Name: project_milestones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.project_milestones_id_seq OWNED BY public.project_milestones.id;


--
-- Name: project_quizzes; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.project_quizzes OWNER TO "lovas.zoltan";

--
-- Name: project_quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.project_quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_quizzes_id_seq OWNER TO "lovas.zoltan";

--
-- Name: project_quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.project_quizzes_id_seq OWNED BY public.project_quizzes.id;


--
-- Name: project_sessions; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.project_sessions (
    id integer NOT NULL,
    project_id integer NOT NULL,
    session_id integer NOT NULL,
    milestone_id integer,
    is_required boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.project_sessions OWNER TO "lovas.zoltan";

--
-- Name: project_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.project_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_sessions_id_seq OWNER TO "lovas.zoltan";

--
-- Name: project_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.project_sessions_id_seq OWNED BY public.project_sessions.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: lovas.zoltan
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
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    target_specialization public.specializationtype,
    mixed_specialization boolean DEFAULT false
);


ALTER TABLE public.projects OWNER TO "lovas.zoltan";

--
-- Name: COLUMN projects.target_specialization; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.projects.target_specialization IS 'Target specialization for this project (null = all specializations)';


--
-- Name: COLUMN projects.mixed_specialization; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.projects.mixed_specialization IS 'Whether this project encourages collaboration between Player and Coach specializations';


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.projects_id_seq OWNER TO "lovas.zoltan";

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: question_metadata; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.question_metadata OWNER TO "lovas.zoltan";

--
-- Name: question_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.question_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.question_metadata_id_seq OWNER TO "lovas.zoltan";

--
-- Name: question_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.question_metadata_id_seq OWNED BY public.question_metadata.id;


--
-- Name: quiz_answer_options; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.quiz_answer_options (
    id integer NOT NULL,
    question_id integer NOT NULL,
    option_text character varying(500) NOT NULL,
    is_correct boolean NOT NULL,
    order_index integer NOT NULL
);


ALTER TABLE public.quiz_answer_options OWNER TO "lovas.zoltan";

--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.quiz_answer_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_answer_options_id_seq OWNER TO "lovas.zoltan";

--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.quiz_answer_options_id_seq OWNED BY public.quiz_answer_options.id;


--
-- Name: quiz_attempts; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.quiz_attempts OWNER TO "lovas.zoltan";

--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.quiz_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_attempts_id_seq OWNER TO "lovas.zoltan";

--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.quiz_attempts_id_seq OWNED BY public.quiz_attempts.id;


--
-- Name: quiz_questions; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.quiz_questions OWNER TO "lovas.zoltan";

--
-- Name: quiz_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.quiz_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_questions_id_seq OWNER TO "lovas.zoltan";

--
-- Name: quiz_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.quiz_questions_id_seq OWNED BY public.quiz_questions.id;


--
-- Name: quiz_user_answers; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.quiz_user_answers OWNER TO "lovas.zoltan";

--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.quiz_user_answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quiz_user_answers_id_seq OWNER TO "lovas.zoltan";

--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.quiz_user_answers_id_seq OWNED BY public.quiz_user_answers.id;


--
-- Name: quizzes; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.quizzes OWNER TO "lovas.zoltan";

--
-- Name: quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quizzes_id_seq OWNER TO "lovas.zoltan";

--
-- Name: quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.quizzes_id_seq OWNED BY public.quizzes.id;


--
-- Name: semesters; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.semesters (
    id integer NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.semesters OWNER TO "lovas.zoltan";

--
-- Name: semesters_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.semesters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semesters_id_seq OWNER TO "lovas.zoltan";

--
-- Name: semesters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.semesters_id_seq OWNED BY public.semesters.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.sessions (
    id integer NOT NULL,
    title character varying NOT NULL,
    description text,
    date_start timestamp without time zone NOT NULL,
    date_end timestamp without time zone NOT NULL,
    mode public.sessionmode,
    capacity integer,
    location character varying,
    meeting_link character varying,
    sport_type character varying,
    level character varying,
    instructor_name character varying,
    semester_id integer NOT NULL,
    group_id integer,
    instructor_id integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    target_specialization public.specializationtype,
    mixed_specialization boolean DEFAULT false
);


ALTER TABLE public.sessions OWNER TO "lovas.zoltan";

--
-- Name: COLUMN sessions.target_specialization; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.sessions.target_specialization IS 'Target specialization for this session (null = all specializations)';


--
-- Name: COLUMN sessions.mixed_specialization; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.sessions.mixed_specialization IS 'Whether this session is open to all specializations';


--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sessions_id_seq OWNER TO "lovas.zoltan";

--
-- Name: sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.sessions_id_seq OWNED BY public.sessions.id;


--
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.user_achievements (
    id integer NOT NULL,
    user_id integer NOT NULL,
    badge_type character varying NOT NULL,
    title character varying NOT NULL,
    description character varying,
    icon character varying,
    earned_at timestamp without time zone,
    semester_count integer
);


ALTER TABLE public.user_achievements OWNER TO "lovas.zoltan";

--
-- Name: user_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.user_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_achievements_id_seq OWNER TO "lovas.zoltan";

--
-- Name: user_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.user_achievements_id_seq OWNED BY public.user_achievements.id;


--
-- Name: user_licenses; Type: TABLE; Schema: public; Owner: lovas.zoltan
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
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.user_licenses OWNER TO "lovas.zoltan";

--
-- Name: user_licenses_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.user_licenses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_licenses_id_seq OWNER TO "lovas.zoltan";

--
-- Name: user_licenses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.user_licenses_id_seq OWNED BY public.user_licenses.id;


--
-- Name: user_question_performance; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.user_question_performance OWNER TO "lovas.zoltan";

--
-- Name: user_question_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.user_question_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_question_performance_id_seq OWNER TO "lovas.zoltan";

--
-- Name: user_question_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.user_question_performance_id_seq OWNED BY public.user_question_performance.id;


--
-- Name: user_stats; Type: TABLE; Schema: public; Owner: lovas.zoltan
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


ALTER TABLE public.user_stats OWNER TO "lovas.zoltan";

--
-- Name: user_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.user_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_stats_id_seq OWNER TO "lovas.zoltan";

--
-- Name: user_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.user_stats_id_seq OWNED BY public.user_stats.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: lovas.zoltan
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying NOT NULL,
    nickname character varying,
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
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    created_by integer,
    specialization public.specializationtype,
    payment_verified boolean NOT NULL,
    payment_verified_at timestamp without time zone,
    payment_verified_by integer,
    "position" character varying
);


ALTER TABLE public.users OWNER TO "lovas.zoltan";

--
-- Name: COLUMN users.specialization; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.users.specialization IS 'User''s chosen specialization track (Player/Coach)';


--
-- Name: COLUMN users.payment_verified; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.users.payment_verified IS 'Whether student has paid semester fees';


--
-- Name: COLUMN users.payment_verified_at; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.users.payment_verified_at IS 'Timestamp when payment was verified';


--
-- Name: COLUMN users.payment_verified_by; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.users.payment_verified_by IS 'Admin who verified the payment';


--
-- Name: COLUMN users."position"; Type: COMMENT; Schema: public; Owner: lovas.zoltan
--

COMMENT ON COLUMN public.users."position" IS 'Football position: goalkeeper, defender, midfielder, forward, coach';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: lovas.zoltan
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO "lovas.zoltan";

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lovas.zoltan
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: adaptive_learning_sessions id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.adaptive_learning_sessions ALTER COLUMN id SET DEFAULT nextval('public.adaptive_learning_sessions_id_seq'::regclass);


--
-- Name: attendance id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.attendance ALTER COLUMN id SET DEFAULT nextval('public.attendance_id_seq'::regclass);


--
-- Name: bookings id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.bookings ALTER COLUMN id SET DEFAULT nextval('public.bookings_id_seq'::regclass);


--
-- Name: feedback id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: license_metadata id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_metadata ALTER COLUMN id SET DEFAULT nextval('public.license_metadata_id_seq'::regclass);


--
-- Name: license_progressions id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_progressions ALTER COLUMN id SET DEFAULT nextval('public.license_progressions_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: project_enrollment_quizzes id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollment_quizzes ALTER COLUMN id SET DEFAULT nextval('public.project_enrollment_quizzes_id_seq'::regclass);


--
-- Name: project_enrollments id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollments ALTER COLUMN id SET DEFAULT nextval('public.project_enrollments_id_seq'::regclass);


--
-- Name: project_milestone_progress id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestone_progress ALTER COLUMN id SET DEFAULT nextval('public.project_milestone_progress_id_seq'::regclass);


--
-- Name: project_milestones id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestones ALTER COLUMN id SET DEFAULT nextval('public.project_milestones_id_seq'::regclass);


--
-- Name: project_quizzes id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_quizzes ALTER COLUMN id SET DEFAULT nextval('public.project_quizzes_id_seq'::regclass);


--
-- Name: project_sessions id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions ALTER COLUMN id SET DEFAULT nextval('public.project_sessions_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: question_metadata id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.question_metadata ALTER COLUMN id SET DEFAULT nextval('public.question_metadata_id_seq'::regclass);


--
-- Name: quiz_answer_options id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_answer_options ALTER COLUMN id SET DEFAULT nextval('public.quiz_answer_options_id_seq'::regclass);


--
-- Name: quiz_attempts id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_attempts ALTER COLUMN id SET DEFAULT nextval('public.quiz_attempts_id_seq'::regclass);


--
-- Name: quiz_questions id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_questions ALTER COLUMN id SET DEFAULT nextval('public.quiz_questions_id_seq'::regclass);


--
-- Name: quiz_user_answers id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_user_answers ALTER COLUMN id SET DEFAULT nextval('public.quiz_user_answers_id_seq'::regclass);


--
-- Name: quizzes id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quizzes ALTER COLUMN id SET DEFAULT nextval('public.quizzes_id_seq'::regclass);


--
-- Name: semesters id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.semesters ALTER COLUMN id SET DEFAULT nextval('public.semesters_id_seq'::regclass);


--
-- Name: sessions id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.sessions ALTER COLUMN id SET DEFAULT nextval('public.sessions_id_seq'::regclass);


--
-- Name: user_achievements id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_achievements ALTER COLUMN id SET DEFAULT nextval('public.user_achievements_id_seq'::regclass);


--
-- Name: user_licenses id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_licenses ALTER COLUMN id SET DEFAULT nextval('public.user_licenses_id_seq'::regclass);


--
-- Name: user_question_performance id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_question_performance ALTER COLUMN id SET DEFAULT nextval('public.user_question_performance_id_seq'::regclass);


--
-- Name: user_stats id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_stats ALTER COLUMN id SET DEFAULT nextval('public.user_stats_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: adaptive_learning_sessions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.adaptive_learning_sessions (id, user_id, category, started_at, ended_at, questions_presented, questions_correct, xp_earned, target_difficulty, performance_trend, session_time_limit_seconds, session_start_time) FROM stdin;
1	3	GENERAL	2025-09-17 07:28:22.430893+02	\N	0	0	0	0.3	0	\N	\N
2	3	ECONOMICS	2025-09-17 07:31:53.452733+02	\N	0	0	0	0.3	0	\N	\N
3	3	ECONOMICS	2025-09-17 07:35:00.973095+02	\N	0	0	0	0.3	0	\N	\N
4	3	ECONOMICS	2025-09-17 07:36:11.752712+02	\N	0	0	0	0.3	0	\N	\N
5	3	GENERAL	2025-09-17 07:40:26.070373+02	\N	0	0	0	0.3	0	\N	\N
6	3	GENERAL	2025-09-17 07:40:50.345567+02	\N	0	0	0	0.3	0	\N	\N
8	3	GENERAL	2025-09-17 07:42:55.782471+02	\N	0	0	0	0.3	0	\N	\N
9	3	MARKETING	2025-09-17 07:43:25.304043+02	\N	0	0	0	0.3	0	\N	\N
10	3	GENERAL	2025-09-17 07:44:50.981129+02	\N	0	0	0	0.3	0	\N	\N
11	3	GENERAL	2025-09-17 07:56:04.292007+02	\N	0	0	0	0.3	0	\N	\N
12	3	GENERAL	2025-09-17 07:57:57.487185+02	\N	0	0	0	0.3	0	\N	\N
13	3	GENERAL	2025-09-17 07:58:12.823082+02	\N	0	0	0	0.3	0	\N	\N
14	3	GENERAL	2025-09-17 08:00:59.602432+02	\N	0	0	0	0.3	0	\N	\N
15	3	GENERAL	2025-09-17 08:09:20.02537+02	\N	0	0	0	0.3	0	\N	\N
16	3	GENERAL	2025-09-17 08:13:15.669994+02	\N	1	1	52	0.325	0	\N	\N
44	3	GENERAL	2025-09-17 09:29:05.248648+02	2025-09-17 09:29:05.310175+02	2	2	104	0.5545977011494253	0	1800	2025-09-17 09:29:05.255439+02
17	3	GENERAL	2025-09-17 08:15:35.032212+02	\N	1	1	52	0.725	0	\N	\N
18	3	GENERAL	2025-09-17 08:16:50.831244+02	\N	1	1	52	0.725	0	\N	\N
45	3	GENERAL	2025-09-17 09:30:29.631212+02	\N	1	1	52	0.5271505376344087	0	1800	2025-09-17 09:30:29.639199+02
37	3	GENERAL	2025-09-17 09:14:24.754934+02	2025-09-17 09:14:24.820966+02	2	0	10	0.6366228070175438	0	1800	2025-09-17 09:14:24.761421+02
19	3	GENERAL	2025-09-17 08:20:48.581+02	\N	2	2	104	0.75	0	\N	\N
38	3	GENERAL	2025-09-17 09:15:03.120581+02	\N	1	1	52	0.5154761904761904	0	1800	2025-09-17 09:15:03.128379+02
39	3	GENERAL	2025-09-17 09:16:32.685332+02	2025-09-17 09:16:38.659394+02	0	0	0	0.4956439393939394	0	1800	2025-09-17 09:16:32.688032+02
40	3	GENERAL	2025-09-17 09:16:50.900092+02	\N	0	0	0	0.4956439393939394	0	1800	2025-09-17 09:16:50.903332+02
84	3	SPORTS_PHYSIOLOGY	2025-09-17 12:20:25.9448+02	2025-09-17 12:20:27.436185+02	0	0	0	0.3	0	1800	2025-09-17 12:20:25.948158+02
91	3	GENERAL	2025-09-17 12:57:20.028147+02	2025-09-17 12:57:26.014204+02	0	0	0	0.5045458074534162	0	1800	2025-09-17 12:57:20.031506+02
20	3	GENERAL	2025-09-17 08:27:37.108085+02	2025-09-17 08:29:52.581861+02	5	2	102	0.6749999999999999	-0.19	\N	\N
21	3	GENERAL	2025-09-17 08:34:13.495576+02	\N	0	0	0	0.48714285714285716	0	\N	\N
22	3	GENERAL	2025-09-17 08:39:54.351713+02	\N	0	0	0	0.48714285714285716	0	\N	\N
92	3	GENERAL	2025-09-17 15:50:06.586241+02	\N	0	0	0	0.5045458074534162	0	1800	2025-09-17 15:50:06.58977+02
41	3	GENERAL	2025-09-17 09:21:47.100729+02	2025-09-17 09:21:47.224657+02	2	0	10	0.44564393939393937	0	1800	2025-09-17 09:21:47.111715+02
23	3	GENERAL	2025-09-17 08:40:29.734045+02	\N	2	2	103	0.5371428571428571	0	\N	\N
24	3	GENERAL	2025-09-17 08:52:38.053716+02	\N	0	0	0	0.4875	0	1800	2025-09-17 08:52:38.061708+02
25	3	GENERAL	2025-09-17 08:55:55.973302+02	\N	0	0	0	0.4875	0	1800	2025-09-17 08:55:55.993875+02
26	3	GENERAL	2025-09-17 08:56:19.374062+02	\N	0	0	0	0.4875	0	1800	2025-09-17 08:56:19.379169+02
27	3	GENERAL	2025-09-17 08:58:30.50028+02	\N	0	0	0	0.4875	0	10	2025-09-17 08:58:30.509477+02
28	3	GENERAL	2025-09-17 08:58:50.096915+02	\N	0	0	0	0.4875	0	10	2025-09-17 08:58:50.103379+02
29	3	GENERAL	2025-09-17 08:59:13.466367+02	\N	0	0	0	0.4875	0	10	2025-09-17 08:59:13.472465+02
30	3	GENERAL	2025-09-17 08:59:39.805962+02	\N	0	0	0	0.4875	0	10	2025-09-17 08:59:39.812402+02
31	3	GENERAL	2025-09-17 09:00:10.298079+02	\N	0	0	0	0.4875	0	10	2025-09-17 09:00:10.30999+02
32	3	GENERAL	2025-09-17 09:00:41.92966+02	\N	0	0	0	0.4875	0	10	2025-09-17 09:00:41.935565+02
33	3	GENERAL	2025-09-17 09:02:24.652005+02	\N	0	0	0	0.4875	0	1800	2025-09-17 09:02:24.657508+02
35	3	GENERAL	2025-09-17 09:05:40.345193+02	\N	0	0	0	0.4875	0	10	2025-09-17 09:05:40.351505+02
93	3	MARKETING	2025-09-17 16:01:58.444238+02	\N	0	0	0	0.3	0	1800	2025-09-17 16:01:58.447209+02
46	3	GENERAL	2025-09-17 09:32:32.66376+02	2025-09-17 09:32:34.317104+02	3	1	62	0.4764583333333333	-0.1	1800	2025-09-17 09:32:32.671326+02
100	3	GENERAL	2025-09-17 16:33:35.287107+02	\N	0	0	0	0.504077380952381	0	180	2025-09-17 16:33:35.310318+02
94	3	GENERAL	2025-09-17 16:02:28.165519+02	\N	1	1	35	0.5295458074534162	0	1800	2025-09-17 16:02:28.168823+02
95	3	GENERAL	2025-09-17 16:18:16.449757+02	\N	0	0	0	0.5043844984802431	0	1800	2025-09-17 16:18:16.453612+02
96	3	GENERAL	2025-09-17 16:18:25.414879+02	\N	0	0	0	0.5043844984802431	0	1800	2025-09-17 16:18:25.418022+02
97	3	GENERAL	2025-09-17 16:19:38.298995+02	\N	0	0	0	0.5043844984802431	0	1800	2025-09-17 16:19:38.306006+02
42	3	GENERAL	2025-09-17 09:22:28.397154+02	2025-09-17 09:22:33.579665+02	5	1	72	0.4239583333333332	-0.30000000000000004	1800	2025-09-17 09:22:28.404698+02
43	3	GENERAL	2025-09-17 09:24:15.605125+02	\N	0	0	0	0.5045977011494253	0	1800	2025-09-17 09:24:15.608734+02
101	3	GENERAL	2025-09-17 16:37:10.139884+02	\N	0	0	0	0.504077380952381	0	180	2025-09-17 16:37:10.144697+02
34	3	GENERAL	2025-09-17 09:02:36.862305+02	2025-09-17 09:08:19.235322+02	7	7	347	0.6625000000000001	0.5	1800	2025-09-17 09:02:36.866077+02
36	3	ECONOMICS	2025-09-17 09:09:38.550296+02	\N	0	0	0	0.3	0	1800	2025-09-17 09:09:38.569556+02
47	3	GENERAL	2025-09-17 09:33:16.887576+02	\N	4	2	114	0.5023214285714286	-0.09000000000000001	1800	2025-09-17 09:33:16.893501+02
85	3	GENERAL	2025-09-17 12:20:38.135332+02	\N	6	5	265	0.6037896825396827	0.4	1800	2025-09-17 12:20:38.139083+02
86	3	GENERAL	2025-09-17 12:31:13.067211+02	\N	0	0	0	0.5045458074534162	0	1800	2025-09-17 12:31:13.070587+02
87	3	GENERAL	2025-09-17 12:42:26.719318+02	\N	0	0	0	0.5045458074534162	0	1800	2025-09-17 12:42:26.723977+02
48	3	GENERAL	2025-09-17 11:07:37.699823+02	2025-09-17 11:07:38.777147+02	1	0	5	0.47811927655677655	0	1800	2025-09-17 11:07:37.710873+02
49	3	GENERAL	2025-09-17 11:11:54.076041+02	\N	0	0	0	0.5037896825396826	0	1800	2025-09-17 11:11:54.078761+02
82	3	GENERAL	2025-09-17 12:05:21.476602+02	\N	0	0	0	0.5037896825396826	0	1800	2025-09-17 12:05:21.484234+02
83	3	GENERAL	2025-09-17 12:15:13.398107+02	\N	0	0	0	0.5037896825396826	0	1800	2025-09-17 12:15:13.401621+02
88	3	GENERAL	2025-09-17 12:51:02.412802+02	\N	0	0	0	0.5045458074534162	0	1800	2025-09-17 12:51:02.416609+02
89	3	GENERAL	2025-09-17 12:56:47.985737+02	\N	0	0	0	0.5045458074534162	0	1800	2025-09-17 12:56:47.989242+02
90	3	GENERAL	2025-09-17 12:57:03.582299+02	\N	0	0	0	0.5045458074534162	0	1800	2025-09-17 12:57:03.584698+02
98	3	GENERAL	2025-09-17 16:22:15.677461+02	\N	1	1	40	0.5293844984802432	0	1800	2025-09-17 16:22:15.693927+02
99	3	GENERAL	2025-09-17 16:26:23.962625+02	\N	0	0	0	0.504077380952381	0	180	2025-09-17 16:26:23.967482+02
102	3	GENERAL	2025-09-17 16:37:38.072505+02	\N	0	0	0	0.504077380952381	0	180	2025-09-17 16:37:38.075189+02
103	3	GENERAL	2025-09-17 16:42:01.88434+02	\N	0	0	0	0.504077380952381	0	180	2025-09-17 16:42:01.886863+02
104	3	GENERAL	2025-09-17 16:55:22.27423+02	\N	0	0	0	0.504077380952381	0	180	2025-09-17 16:55:22.282646+02
106	3	GENERAL	2025-09-17 16:56:38.883435+02	\N	0	0	0	0.5050212585034014	0	180	2025-09-17 16:56:38.888707+02
105	3	GENERAL	2025-09-17 16:55:36.497758+02	\N	1	1	52	0.529077380952381	0	180	2025-09-17 16:55:36.501041+02
107	3	GENERAL	2025-09-17 17:02:24.428738+02	2025-09-17 17:06:40.65169+02	5	4	211	0.5800212585034015	0.2	180	2025-09-17 17:02:24.430987+02
109	3	GENERAL	2025-09-17 17:10:07.194801+02	\N	0	0	0	0.5028689836149514	0	180	2025-09-17 17:10:07.203142+02
108	3	GENERAL	2025-09-17 17:06:45.564422+02	\N	8	5	274	0.5538920454545455	-0.21870000000000006	180	2025-09-17 17:06:45.569555+02
110	3	GENERAL	2025-09-17 17:13:37.104581+02	\N	0	0	0	0.5028689836149514	0	180	2025-09-17 17:13:37.11351+02
111	3	GENERAL	2025-09-17 17:15:27.973653+02	\N	0	0	0	0.5028689836149514	0	180	2025-09-17 17:15:27.97758+02
112	3	GENERAL	2025-09-17 17:15:51.372733+02	\N	0	0	0	0.5028689836149514	0	180	2025-09-17 17:15:51.375565+02
114	3	GENERAL	2025-09-17 17:22:37.840555+02	\N	3	1	62	0.47786898361495134	-0.1	180	2025-09-17 17:22:37.84659+02
115	3	GENERAL	2025-09-17 17:24:58.668827+02	\N	0	0	0	0.5050680569430569	0	180	2025-09-17 17:24:58.671964+02
113	3	GENERAL	2025-09-17 17:19:02.2417+02	\N	0	0	0	0.5028689836149514	0	180	2025-09-17 17:19:02.247238+02
116	3	GENERAL	2025-09-17 17:27:23.899138+02	\N	0	0	0	0.5050680569430569	0	180	2025-09-17 17:27:23.902694+02
117	3	GENERAL	2025-09-17 17:31:33.273099+02	\N	0	0	0	0.5050680569430569	0	180	2025-09-17 17:31:33.376839+02
118	3	GENERAL	2025-09-17 17:33:10.355499+02	\N	0	0	0	0.5050680569430569	0	180	2025-09-17 17:33:10.358812+02
166	3	GENERAL	2025-09-19 16:26:37.752305+02	\N	0	0	0	0.5035622401247402	0	180	2025-09-19 16:26:37.756275+02
119	3	GENERAL	2025-09-17 17:39:34.688983+02	\N	1	1	35	0.5300680569430569	0	180	2025-09-17 17:39:34.692573+02
120	3	GENERAL	2025-09-17 17:42:09.264206+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 17:42:10.557912+02
121	3	GENERAL	2025-09-17 17:51:57.484529+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 17:51:57.514115+02
122	3	GENERAL	2025-09-17 17:57:53.302379+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 17:57:53.304105+02
123	3	GENERAL	2025-09-17 17:59:35.783604+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 17:59:35.785317+02
124	3	GENERAL	2025-09-17 18:02:55.352189+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:02:55.367964+02
125	3	GENERAL	2025-09-17 18:06:24.496144+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:06:24.498902+02
126	3	GENERAL	2025-09-17 18:07:07.547056+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:07:07.55128+02
127	3	GENERAL	2025-09-17 18:08:09.611165+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:08:09.61877+02
128	3	GENERAL	2025-09-17 18:11:58.37131+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:11:58.391014+02
129	3	GENERAL	2025-09-17 18:16:27.074372+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:16:27.076062+02
130	3	GENERAL	2025-09-17 18:17:05.62274+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:17:05.626485+02
131	3	GENERAL	2025-09-17 18:18:31.172601+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:18:31.178724+02
132	3	GENERAL	2025-09-17 18:21:02.005541+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:21:02.014418+02
133	3	GENERAL	2025-09-17 18:25:19.578111+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:25:19.581656+02
134	3	GENERAL	2025-09-17 18:26:57.125785+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:26:57.127683+02
135	3	GENERAL	2025-09-17 18:30:12.346561+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:30:12.348351+02
136	3	GENERAL	2025-09-17 18:32:56.831175+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:32:56.83379+02
137	3	GENERAL	2025-09-17 18:35:21.381469+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:35:21.383788+02
138	3	GENERAL	2025-09-17 18:36:02.465957+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:36:02.470457+02
139	3	GENERAL	2025-09-17 18:38:57.398434+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:38:57.401606+02
140	3	GENERAL	2025-09-17 18:42:02.187989+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:42:02.20927+02
141	3	GENERAL	2025-09-17 18:43:13.966754+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:43:13.970219+02
142	3	GENERAL	2025-09-17 18:46:38.65048+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:46:38.654109+02
143	3	GENERAL	2025-09-17 18:49:59.303005+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:49:59.305491+02
144	3	GENERAL	2025-09-17 18:53:03.270036+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:53:03.275219+02
145	3	GENERAL	2025-09-17 18:59:47.930923+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 18:59:47.934678+02
146	3	GENERAL	2025-09-17 19:02:54.605389+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:02:54.609013+02
147	3	GENERAL	2025-09-17 19:04:05.135495+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:04:05.138086+02
148	3	GENERAL	2025-09-17 19:06:29.885185+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:06:29.887505+02
149	3	GENERAL	2025-09-17 19:09:14.929988+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:09:14.934534+02
150	3	GENERAL	2025-09-17 19:09:45.26945+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:09:45.272639+02
151	3	GENERAL	2025-09-17 19:12:50.885953+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:12:50.888119+02
152	3	GENERAL	2025-09-17 19:17:58.590794+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-17 19:17:58.593514+02
153	3	GENERAL	2025-09-19 15:36:19.446203+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 15:36:19.481593+02
154	3	GENERAL	2025-09-19 15:39:53.704111+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 15:39:53.708896+02
155	3	GENERAL	2025-09-19 15:49:49.648673+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 15:49:49.650681+02
156	3	GENERAL	2025-09-19 15:53:01.846463+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 15:53:01.851341+02
157	3	GENERAL	2025-09-19 15:55:33.877569+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 15:55:33.881114+02
158	3	GENERAL	2025-09-19 15:58:00.307015+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 15:58:00.310479+02
159	3	GENERAL	2025-09-19 16:02:25.674632+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 16:02:25.679898+02
160	3	GENERAL	2025-09-19 16:03:38.771609+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 16:03:38.775062+02
161	3	GENERAL	2025-09-19 16:04:36.755794+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 16:04:36.760186+02
162	3	GENERAL	2025-09-19 16:07:01.953074+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 16:07:01.955033+02
163	3	GENERAL	2025-09-19 16:08:36.00079+02	\N	0	0	0	0.5045319264069265	0	180	2025-09-19 16:08:36.004891+02
167	3	GENERAL	2025-09-19 16:28:14.652674+02	\N	0	0	0	0.5035622401247402	0	180	2025-09-19 16:28:14.656151+02
168	3	GENERAL	2025-09-19 16:51:34.500454+02	\N	0	0	0	0.5035622401247402	0	180	2025-09-19 16:51:34.508098+02
169	3	GENERAL	2025-09-19 16:51:50.898976+02	\N	7	5	269	0.5785622401247402	0.18100000000000002	180	2025-09-19 16:51:50.901903+02
170	3	GENERAL	2025-09-19 16:58:27.659743+02	\N	0	0	0	0.5050352733686067	0	180	2025-09-19 16:58:27.662679+02
171	3	GENERAL	2025-09-19 17:00:13.194775+02	\N	0	0	0	0.5050352733686067	0	180	2025-09-19 17:00:13.208446+02
172	3	GENERAL	2025-09-19 17:00:18.330389+02	\N	0	0	0	0.5050352733686067	0	180	2025-09-19 17:00:18.334378+02
164	3	GENERAL	2025-09-19 16:11:20.915324+02	\N	4	4	175	0.6045319264069265	0.2	180	2025-09-19 16:11:20.918234+02
173	3	GENERAL	2025-09-19 17:00:29.738203+02	\N	0	0	0	0.5050352733686067	0	180	2025-09-19 17:00:29.741024+02
180	14	GENERAL	2025-09-20 14:51:23.637645+02	2025-09-20 14:51:34.960711+02	1	1	49	0.325	0	180	2025-09-20 14:51:23.646249+02
176	3	GENERAL	2025-09-19 17:15:15.372053+02	\N	4	4	207	0.6051693533990983	0.2	180	2025-09-19 17:15:15.375854+02
177	3	GENERAL	2025-09-19 17:16:00.50187+02	\N	0	0	0	0.5048160264980118	0	180	2025-09-19 17:16:00.503636+02
178	3	GENERAL	2025-09-19 17:16:05.715988+02	\N	0	0	0	0.5048160264980118	0	180	2025-09-19 17:16:05.719897+02
179	3	GENERAL	2025-09-19 17:17:42.053733+02	\N	0	0	0	0.5048160264980118	0	180	2025-09-19 17:17:42.060818+02
165	3	GENERAL	2025-09-19 16:23:05.024445+02	\N	4	3	160	0.5546565934065935	0.1	180	2025-09-19 16:23:05.037131+02
175	3	GENERAL	2025-09-19 17:06:40.889611+02	\N	10	10	501	0.8306250000000003	0.7999999999999999	180	2025-09-19 17:06:40.894812+02
174	3	GENERAL	2025-09-19 17:03:48.449169+02	\N	15	14	714	0.9	1	180	2025-09-19 17:03:48.456382+02
182	14	GENERAL	2025-09-23 23:42:16.131855+02	\N	0	0	0	0.7	0	180	2025-09-23 23:42:16.143562+02
181	14	GENERAL	2025-09-21 19:19:38.084074+02	\N	0	0	0	0.7	0	180	2025-09-21 19:19:38.101587+02
183	14	GENERAL	2025-09-23 23:46:21.960479+02	\N	0	0	0	0.7	0	180	2025-09-23 23:46:21.970852+02
184	14	GENERAL	2025-09-23 23:46:33.263196+02	\N	0	0	0	0.7	0	180	2025-09-23 23:46:33.266618+02
185	14	GENERAL	2025-09-23 23:49:11.469441+02	2025-09-23 23:50:22.786829+02	6	5	260	0.8	0.30000000000000004	180	2025-09-23 23:49:11.473753+02
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.alembic_version (version_num) FROM stdin;
gancuju_license_system
\.


--
-- Data for Name: attendance; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.attendance (id, user_id, session_id, booking_id, status, check_in_time, check_out_time, notes, marked_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.bookings (id, user_id, session_id, status, waitlist_position, notes, created_at, updated_at, cancelled_at, attended_status) FROM stdin;
1	14	1	CONFIRMED	\N	\N	2025-09-18 11:17:35.784484	\N	\N	\N
2	14	2	CONFIRMED	\N	\N	2025-09-19 11:17:35.784484	\N	\N	\N
3	14	3	CONFIRMED	\N	\N	2025-09-20 11:17:35.784484	\N	\N	\N
\.


--
-- Data for Name: feedback; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.feedback (id, user_id, session_id, rating, instructor_rating, session_quality, would_recommend, comment, is_anonymous, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: group_users; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.group_users (group_id, user_id) FROM stdin;
\.


--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.groups (id, name, description, semester_id, created_at, updated_at) FROM stdin;
6	FC Barcelona Academy	Barcelona ifjúsági akadémia	11	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
7	Real Madrid Cantera	Real Madrid utánpótlás	11	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
8	PSG Development	PSG fejlesztési program	12	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
9	Manchester City Youth	Man City ifjúsági csapat	13	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
10	Liverpool Academy	Liverpool akadémia	14	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
\.


--
-- Data for Name: license_metadata; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.license_metadata (id, specialization_type, level_code, level_number, title, title_en, subtitle, color_primary, color_secondary, icon_emoji, icon_symbol, marketing_narrative, cultural_context, philosophy, background_gradient, css_class, image_url, advancement_criteria, time_requirement_hours, project_requirements, evaluation_criteria, created_at, updated_at) FROM stdin;
1	COACH	coach_lfa_pre_assistant	1	LFA Pre Football Asszisztens Edző	LFA Pre Football Assistant Coach	Kezdő edzői szint	#8B7355	#D2B48C	🥉	\N	LFA szakmai fejlődési útvonal - kezdő edzői szint	\N	\N	linear-gradient(135deg, #8B7355, #D2B48C)	coach-pre	\N	\N	40	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
2	COACH	coach_lfa_pre_head	2	LFA Pre Football Vezetőedző	LFA Pre Football Head Coach	Pre kategória vezetői szint	#A0522D	#DEB887	🏆	\N	LFA szakmai fejlődési útvonal - pre kategória vezetői szint	\N	\N	linear-gradient(135deg, #A0522D, #DEB887)	coach-pre-head	\N	\N	80	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
3	COACH	coach_lfa_youth_assistant	3	LFA Youth Football Asszisztens Edző	LFA Youth Football Assistant Coach	Utánpótlás edzői szint	#228B22	#90EE90	⚽	\N	LFA szakmai fejlődési útvonal - utánpótlás edzői szint	\N	\N	linear-gradient(135deg, #228B22, #90EE90)	coach-youth	\N	\N	120	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
4	COACH	coach_lfa_youth_head	4	LFA Youth Football Vezetőedző	LFA Youth Football Head Coach	Utánpótlás vezetői szint	#32CD32	#98FB98	🌟	\N	LFA szakmai fejlődési útvonal - utánpótlás vezetői szint	\N	\N	linear-gradient(135deg, #32CD32, #98FB98)	coach-youth-head	\N	\N	160	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
5	COACH	coach_lfa_amateur_assistant	5	LFA Amateur Football Asszisztens Edző	LFA Amateur Football Assistant Coach	Amateur edzői szint	#4169E1	#87CEEB	🎯	\N	LFA szakmai fejlődési útvonal - amateur edzői szint	\N	\N	linear-gradient(135deg, #4169E1, #87CEEB)	coach-amateur	\N	\N	200	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
6	COACH	coach_lfa_amateur_head	6	LFA Amateur Football Vezetőedző	LFA Amateur Football Head Coach	Amateur vezetői szint	#1E90FF	#B0E0E6	👑	\N	LFA szakmai fejlődési útvonal - amateur vezetői szint	\N	\N	linear-gradient(135deg, #1E90FF, #B0E0E6)	coach-amateur-head	\N	\N	250	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
7	COACH	coach_lfa_pro_assistant	7	LFA PRO Football Asszisztens Edző	LFA PRO Football Assistant Coach	Profi edzői szint	#8A2BE2	#DDA0DD	💎	\N	LFA szakmai fejlődési útvonal - profi edzői szint	\N	\N	linear-gradient(135deg, #8A2BE2, #DDA0DD)	coach-pro	\N	\N	300	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
8	COACH	coach_lfa_pro_head	8	LFA PRO Football Vezetőedző	LFA PRO Football Head Coach	Profi vezetői szint	#9932CC	#E6E6FA	🏅	\N	LFA szakmai fejlődési útvonal - profi vezetői szint	\N	\N	linear-gradient(135deg, #9932CC, #E6E6FA)	coach-pro-head	\N	\N	400	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
10	PLAYER	player_morning_dew	2	Hajnali Harmat	Morning Dew	Frissítő energia és új technikák	#FFD700	#FFFFE0	💛	\N	Mint a hajnali harmat frissíti a bambuszerdőt, úgy hoz új energiát képességeidbe ez a szint.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #FFD700, #FFFFE0)	player-yellow	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
11	PLAYER	player_flexible_reed	3	Rugalmas Nád	Flexible Reed	Harmónia és alkalmazkodóképesség	#228B22	#98FB98	💚	\N	A szélben táncoló nád tanítása - tested és elméd megtanul áramlani a játékban.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #228B22, #98FB98)	player-green	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
12	PLAYER	player_sky_river	4	Égi Folyó	Sky River	Folyékony játék és intuíció	#4169E1	#87CEFA	💙	\N	Játékod folyékonnyá válik, mint a nagy kínai folyók áramlása. Az intuíció és reflexek felgyorsulnak.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #4169E1, #87CEFA)	player-blue	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
13	PLAYER	player_strong_root	5	Erős Gyökér	Strong Root	Mély tudás és mentorálás	#8B4513	#DEB887	🤎	\N	A tradíció őrzőjévé válsz. Tudásodat megosztva a 4000 éves lánc újabb szemévé válsz.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #8B4513, #DEB887)	player-brown	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
14	PLAYER	player_winter_moon	6	Téli Hold	Winter Moon	Oktatási kiválóság és versenyeredmények	#2F4F4F	#A9A9A9	🩶	\N	A Téli Hold fénye még a legsötétebb éjszakát is megvilágítja - ahogy te is feltárod a rejtett dimenziókat.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #2F4F4F, #A9A9A9)	player-gray	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
15	PLAYER	player_midnight_guardian	7	Éjfél Őrzője	Midnight Guardian	Módszertani szakértelem és licensz	#000000	#404040	🖤	\N	Beavatás a legmélyebb titkokba. Játékod művészetnek tűnik, módszertaned évezredes tudást ötvöz.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #000000, #404040)	player-black	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
16	PLAYER	player_dragon_wisdom	8	Sárkány Bölcsesség	Dragon Wisdom	Innováció és legendás státusz	#DC143C	#FFB6C1	❤️	\N	A GānCuju™️©️ legmagasabb csúcsa. Élő legendává válsz, tradíció és innováció tökéletes egyensúlyában.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #DC143C, #FFB6C1)	player-red	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
18	INTERNSHIP	intern_mid_level	2	Mid-level Intern	Mid-level Intern	Növekvő technikai kompetencia	#FF6347	#FFA07A	📈	\N	Nemzetközi IT karrierpálya - növekvő technikai kompetencia	\N	\N	linear-gradient(135deg, #FF6347, #FFA07A)	intern-mid	\N	\N	160	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
19	INTERNSHIP	intern_senior	3	Senior Intern	Senior Intern	Haladó szakmai készségek	#9932CC	#DDA0DD	🎯	\N	Nemzetközi IT karrierpálya - haladó szakmai készségek	\N	\N	linear-gradient(135deg, #9932CC, #DDA0DD)	intern-senior	\N	\N	240	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
20	INTERNSHIP	intern_lead	4	Lead Intern	Lead Intern	Vezetői szerepkör és projektirányítás	#FF8C00	#FFE4B5	👑	\N	Nemzetközi IT karrierpálya - vezetői szerepkör és projektirányítás	\N	\N	linear-gradient(135deg, #FF8C00, #FFE4B5)	intern-lead	\N	\N	320	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
21	INTERNSHIP	intern_principal	5	Principal Intern	Principal Intern	Strategiai szintű technikai vezetés	#B22222	#F0E68C	🚀	\N	Nemzetközi IT karrierpálya - strategiai szintű technikai vezetés	\N	\N	linear-gradient(135deg, #B22222, #F0E68C)	intern-principal	\N	\N	400	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 16:19:59.345162
9	PLAYER	player_bamboo_student	1	GānCuju™️©️ Player - Alapszint	GānCuju™️©️ Player - Foundation Level	Player specializáció kezdő szint	#F8F8FF	#E6E6FA	🤍	\N	A fiatal bambusz hajlik, de nem törik. Itt kezdődik a 4000 éves hagyomány utazása.	GānCuju™️©️ - 4000 éves kínai labdajáték hagyományain alapuló modern képzési rendszer	\N	linear-gradient(135deg, #F8F8FF, #E6E6FA)	player-white	\N	\N	\N	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 17:05:17.431943
17	INTERNSHIP	intern_junior	1	LFA Gyakornok - Alapszint	LFA Intern - Foundation Level	Gyakornoki program kezdő szint	#20B2AA	#AFEEEE	🔰	\N	Nemzetközi IT karrierpálya - it karrier első lépései	\N	\N	linear-gradient(135deg, #20B2AA, #AFEEEE)	intern-junior	\N	\N	80	\N	\N	2025-09-20 16:19:59.345162	2025-09-20 17:05:17.442676
\.


--
-- Data for Name: license_progressions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.license_progressions (id, user_license_id, from_level, to_level, advanced_by, advancement_reason, requirements_met, advanced_at) FROM stdin;
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.messages (id, sender_id, recipient_id, subject, message, priority, is_read, is_edited, created_at, read_at, edited_at) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.notifications (id, user_id, title, message, type, is_read, related_session_id, related_booking_id, created_at, read_at) FROM stdin;
\.


--
-- Data for Name: project_enrollment_quizzes; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_enrollment_quizzes (id, project_id, user_id, quiz_attempt_id, enrollment_priority, enrollment_confirmed, created_at) FROM stdin;
\.


--
-- Data for Name: project_enrollments; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_enrollments (id, project_id, user_id, enrolled_at, status, progress_status, completion_percentage, instructor_approved, instructor_feedback, enrollment_status, quiz_passed, final_grade, completed_at) FROM stdin;
\.


--
-- Data for Name: project_milestone_progress; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_milestone_progress (id, enrollment_id, milestone_id, status, submitted_at, instructor_feedback, instructor_approved_at, sessions_completed, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: project_milestones; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_milestones (id, project_id, title, description, order_index, required_sessions, xp_reward, deadline, is_required, created_at) FROM stdin;
1	1	Pozíciós Játék Alapjai	A Barcelona-stílusú pozíciós játék elsajátítása. 4-3-3 formáció, labdabirtoklás és rövidpassz-játék alapjai.	1	3	50	2025-09-21	t	2025-09-20 08:58:39.842415
2	1	Tiki-Taka Mesterfokon	Gyors labdacserék, mozgás labda nélkül és a térnyerés művészete. Guardiola személyes coaching-ja.	2	4	75	2025-09-22	t	2025-09-20 08:58:39.842415
3	1	Mérkőzés Alkalmazás	A tanult elemek alkalmazása valós mérkőzés helyzetekben. 11 vs 11 taktikai szimuláció.	3	5	100	2025-09-22	t	2025-09-20 08:58:39.842415
4	2	Galácticos Mentalitás	A Real Madrid történelmi nagyságának megértése és a bajnoki mentalitás kialakítása.	1	2	40	2025-09-21	t	2025-09-20 08:58:39.842415
5	2	Technikai Excelencia	Kiváló technikai készségek fejlesztése: labdavezetés, lövés, fejjáték. Ancelotti módszertana.	2	4	80	2025-09-22	t	2025-09-20 08:58:39.842415
6	2	Champions League Szimuláció	Nagy tétű mérkőzések szimulációja. Nyomás alatt játék és döntő pillanatok kezelése.	3	4	90	2025-09-22	t	2025-09-20 08:58:39.842415
7	3	Fizikai Kondíció Alapok	Klopp-féle intenzív fizikai felkészítés. Állóképesség, gyorsaság és robbanékonyság fejlesztése.	1	4	60	2025-09-21	t	2025-09-20 08:58:39.842415
8	3	Gégenpress Taktika	A Liverpool jellegzetes préselő játékstílusának elsajátítása. Intenzív labdaszerzés és gyors átmenet.	2	5	80	2025-09-22	t	2025-09-20 08:58:39.842415
9	3	You'll Never Walk Alone	Csapatszellem és mentális erősség fejlesztése. A Liverpool kultúra és értékek megértése.	3	3	70	2025-09-22	t	2025-09-20 08:58:39.842415
10	3	Anfield Atmosphere	Nagy tömeg előtti játék és a támogatók erejének hasznosítása. Hazai pálya előny maximalizálása.	4	3	90	2025-09-22	f	2025-09-20 08:58:39.842415
\.


--
-- Data for Name: project_quizzes; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_quizzes (id, project_id, quiz_id, milestone_id, quiz_type, is_required, minimum_score, order_index, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: project_sessions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_sessions (id, project_id, session_id, milestone_id, is_required, created_at) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.projects (id, title, description, semester_id, instructor_id, max_participants, required_sessions, xp_reward, deadline, status, difficulty, created_at, updated_at, target_specialization, mixed_specialization) FROM stdin;
1	Barcelona Academy - Fiatal Tehetségek Programja	Átfogó fejlesztési program a Barcelona módszertan alapján. A projekt során elsajátítod a pozíciós játékot, a labdabirtoklás művészetét és a tiki-taka stílust. Guardiola személyes mentorálásával.	2	17	8	12	500	2025-09-22	ACTIVE	ADVANCED	2025-09-20 08:58:39.842415	2025-09-21 09:43:15.399923	\N	f
2	Real Madrid Cantera - Excelencia Program	A Real Madrid hagyományos értékei alapján épülő fejlesztési program. Technikai készségek, taktikai tudás és mentális erősség fejlesztése. Ancelotti vezetésével a galácticos örökségét viszed tovább.	2	18	10	10	450	2025-09-22	ACTIVE	INTERMEDIATE	2025-09-20 08:58:39.842415	2025-09-21 09:43:15.39993	\N	f
3	Liverpool Academy - Mentality Monsters Training	Klopp-féle intenzív fejlesztési program a "Mentality Monsters" filozófia alapján. Fizikai erőnlét, gégenpress taktika és csapatszellem fejlesztése. Heavy metal futball a gyakorlatban.	2	19	12	15	600	2025-09-22	ACTIVE	ADVANCED	2025-09-20 08:58:39.842415	2025-09-21 09:43:15.399931	\N	f
4	Cross-Semester Speciális Program	Speciális fejlesztési program különböző szemeszterek közötti interakciók tesztelésére. Ez a projekt NEM elérhető a LIVE-TEST-2025 szemeszterből.	2	19	5	8	300	2025-08-31	ACTIVE	INTERMEDIATE	2025-09-20 08:58:39.842415	2025-09-21 09:43:15.399932	\N	f
5	Player Performance Analytics	Analysis of individual player statistics and improvement areas	15	18	8	6	150	2025-11-19	ACTIVE	intermediate	2025-09-20 10:37:14.856971	2025-09-21 09:43:15.402385	PLAYER	f
6	Coaching Certification Program	Complete certification pathway for aspiring football coaches	15	18	6	8	200	2025-11-19	ACTIVE	advanced	2025-09-20 10:37:14.856983	2025-09-21 09:43:15.402391	COACH	f
7	Team Building & Communication	Joint project focusing on team dynamics and leadership	2	18	12	4	120	2025-11-19	ACTIVE	beginner	2025-09-20 10:37:14.856984	2025-09-21 09:43:15.403218	\N	t
8	Youth Player Development	Specialized training methods for young football talent	15	18	10	7	180	2025-11-19	ACTIVE	intermediate	2025-09-20 10:37:14.856986	2025-09-21 09:43:15.403593	PLAYER	f
9	Strategic Game Analysis	Advanced tactical analysis and game planning techniques	2	18	8	10	250	2025-11-19	ACTIVE	advanced	2025-09-20 10:37:14.856987	2025-09-21 09:43:15.403842	COACH	f
\.


--
-- Data for Name: question_metadata; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.question_metadata (id, question_id, estimated_difficulty, cognitive_load, concept_tags, prerequisite_concepts, average_time_seconds, global_success_rate, last_analytics_update) FROM stdin;
8	8	0.5	0.5	["general", "basic"]	[]	34.24934111580365	0.6904010016960443	2025-09-19 17:07:29.467202+02
1	1	0.5	0.5	["general", "basic"]	[]	33.17728988779172	0.7730926594997292	2025-09-19 17:15:38.799267+02
2	2	0.5	0.5	["general", "basic"]	[]	29.652813331901875	0.5715812110024594	2025-09-23 23:49:31.91211+02
3	3	0.5	0.5	["general", "basic"]	[]	26.832115439209865	0.7314435262841238	2025-09-23 23:49:40.085187+02
6	6	0.5	0.5	["general", "basic"]	[]	47.01051306629023	0.7840625058283291	2025-09-23 23:49:55.668484+02
7	7	0.42999999999999994	0.5	["general", "basic"]	[]	33.32405466845469	0.853697506265341	2025-09-23 23:50:02.499171+02
4	4	0.47	0.5	["general", "basic"]	[]	42.113997650172536	0.8203789182284864	2025-09-23 23:50:08.086614+02
5	5	0.47	0.5	["general", "basic"]	[]	38.21239776257242	0.8203789182284864	2025-09-23 23:50:14.235469+02
\.


--
-- Data for Name: quiz_answer_options; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_answer_options (id, question_id, option_text, is_correct, order_index) FROM stdin;
1	1	London	f	0
2	1	Berlin	f	0
3	1	Paris	t	0
4	1	Madrid	f	0
5	2	Venus	f	0
6	2	Mercury	t	0
7	2	Earth	f	0
8	2	Mars	f	0
9	3	True	f	0
10	3	False	t	0
11	4	3	f	0
12	4	4	t	0
13	4	5	f	0
14	4	6	f	0
15	5	True	t	0
16	5	False	f	0
17	6	5	f	0
18	6	6	f	0
19	6	7	t	0
20	6	8	f	0
21	7	True	t	0
22	7	False	f	0
23	8	Atlantic Ocean	f	0
24	8	Indian Ocean	f	0
25	8	Arctic Ocean	f	0
26	8	Pacific Ocean	t	0
\.


--
-- Data for Name: quiz_attempts; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_attempts (id, user_id, quiz_id, started_at, completed_at, time_spent_minutes, score, total_questions, correct_answers, xp_awarded, passed) FROM stdin;
3	14	1	2025-09-21 19:19:57.945147+02	\N	\N	\N	8	0	0	f
4	14	1	2025-09-21 19:19:57.956958+02	\N	\N	\N	8	0	0	f
\.


--
-- Data for Name: quiz_questions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_questions (id, quiz_id, question_text, question_type, points, order_index, explanation, created_at) FROM stdin;
1	1	What is the capital of France?	MULTIPLE_CHOICE	10	0	This is the explanation for question 1.	2025-09-17 07:37:59.094014+02
2	1	Which planet is closest to the Sun?	MULTIPLE_CHOICE	10	0	This is the explanation for question 2.	2025-09-17 07:37:59.100371+02
3	1	The Earth is flat.	TRUE_FALSE	10	0	This is the explanation for question 3.	2025-09-17 07:37:59.111601+02
4	1	What is 2 + 2?	MULTIPLE_CHOICE	10	0	This is the explanation for question 4.	2025-09-17 07:37:59.114306+02
5	1	Programming is fun.	TRUE_FALSE	10	0	This is the explanation for question 5.	2025-09-17 07:37:59.116138+02
6	1	How many continents are there?	MULTIPLE_CHOICE	10	0	This is the explanation for question 6.	2025-09-17 07:37:59.118109+02
7	1	Water boils at 100 degrees Celsius.	TRUE_FALSE	10	0	This is the explanation for question 7.	2025-09-17 07:37:59.120731+02
8	1	What is the largest ocean?	MULTIPLE_CHOICE	10	0	This is the explanation for question 8.	2025-09-17 07:37:59.125162+02
\.


--
-- Data for Name: quiz_user_answers; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_user_answers (id, attempt_id, question_id, selected_option_id, answer_text, is_correct, answered_at) FROM stdin;
\.


--
-- Data for Name: quizzes; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quizzes (id, title, description, category, difficulty, time_limit_minutes, xp_reward, passing_score, is_active, created_at, updated_at) FROM stdin;
1	General Knowledge Quiz	Basic general knowledge questions for adaptive learning	GENERAL	MEDIUM	10	50	70	t	2025-09-17 07:37:59.084008+02	\N
\.


--
-- Data for Name: semesters; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.semesters (id, code, name, start_date, end_date, is_active, created_at, updated_at) FROM stdin;
12	DEMO-PAST-2025	Demo Múltbeli Szemeszter	2025-07-01	2025-07-31	f	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
13	DEMO-FUTURE-2026	Demo Jövőbeli Szemeszter	2026-01-15	2026-01-17	f	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535
11	LIVE-TEST-2025	Éles Teszt Szemeszter 2025.09.20-22	2025-09-20	2025-09-22	f	2025-09-20 08:56:33.777535	2025-09-21 09:42:31.578261
14	CROSS-TEST-2025	Cross-Semester Teszt	2025-08-01	2025-08-31	f	2025-09-20 08:56:33.777535	2025-09-21 09:42:31.578267
17	TEST2025	TESZT SZEMESZTER 2025.09.25	2025-10-09	2025-12-31	t	2025-09-25 16:47:06.092213	2025-09-25 16:47:06.092218
2	2025/1	Fall 2025	2025-09-01	2025-12-20	f	2025-09-17 07:12:03.709919	2025-09-25 16:47:22.994524
15	2025-test-oct	Teszt Szemeszter 2025.10.01-10	2025-10-01	2025-10-10	f	2025-09-21 09:42:19.593919	2025-09-25 16:47:22.994532
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.sessions (id, title, description, date_start, date_end, mode, capacity, location, meeting_link, sport_type, level, instructor_name, semester_id, group_id, instructor_id, created_at, updated_at, target_specialization, mixed_specialization) FROM stdin;
1	Taktikai Alapok - 4-3-3 Formáció	A modern futball alapformációjának elsajátítása Guardiola módszerével. Pozíciós játék, labdabirtoklás és nyomás után visszaszerzés.	2025-09-20 09:00:00	2025-09-20 10:30:00	OFFLINE	25	Puskás Aréna - Edzőpálya 1	\N	Taktikai Edzés	Haladó	Pep Guardiola	11	6	17	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
2	Labdabirtoklás és Passzolás	Technikai elemek fejlesztése Ancelotti-stílusú gyakorlatokkal. Rövid és hosszú passzok, első érintés, védelem alatti labdavezetés.	2025-09-20 11:00:00	2025-09-20 12:30:00	OFFLINE	20	Telki Edzőközpont - Műfüves pálya	\N	Technikai Edzés	Középhaladó	Carlo Ancelotti	11	7	18	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
3	Online Taktikai Elemzés	Videós taktikai elemzés élő mérkőzésekből - interaktív online session. Real-time elemzés, játékos mozgások értékelése.	2025-09-20 16:00:00	2025-09-20 17:00:00	ONLINE	50	\N	https://meet.lfa.test/tactical-analysis-sep20	Taktikai Elemzés	Minden szint	Pep Guardiola	11	6	17	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
4	Kondicionálás és Erőnlét	Klopp-féle intenzív fizikai felkészítés és állóképesség fejlesztés. Intervall edzés, gyorsaság, robbanékonyság.	2025-09-21 08:30:00	2025-09-21 10:00:00	OFFLINE	30	NB1 Fitness Center - Erősítő terem	\N	Kondicionális Edzés	Haladó	Jürgen Klopp	11	7	19	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
5	Hybrid Taktikai Workshop	Vegyes online-offline taktikai megbeszélés élő demonstrációval. Elméleti háttér és gyakorlati alkalmazás.	2025-09-21 13:00:00	2025-09-21 14:30:00	HYBRID	40	Magyar Labdarúgó Szövetség - Nagyterem	https://meet.lfa.test/hybrid-workshop-sep21	Workshop	Középhaladó	Pep Guardiola	11	6	17	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
6	Mérkőzés Szimulációs Edzés	Teljes mérkőzés szimulációs gyakorlat - záró edzés. 11 vs 11, taktikai variációk, játékhelyzetek elemzése.	2025-09-22 09:00:00	2025-09-22 11:00:00	OFFLINE	22	Bozsik Aréna - Főpálya	\N	Mérkőzés Szimuláció	Profi	Carlo Ancelotti	11	7	18	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
7	Cross-Semester Speciális Edzés	Speciális edzés különböző szemeszterek közötti kapcsolatok tesztelésére. Csak Mbappé számára elérhető.	2025-09-21 15:00:00	2025-09-21 16:00:00	OFFLINE	15	Liverpool Training Ground	\N	Speciális Edzés	Teszt	Jürgen Klopp	14	10	19	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	f
8	Player Technical Skills Training	Advanced ball control, passing, and shooting techniques for players	2025-09-27 20:37:14.854114	2025-09-27 22:07:14.854114	OFFLINE	16	Field A	\N	football	intermediate	\N	2	\N	18	2025-09-20 10:37:14.876101	2025-09-20 10:37:14.876107	PLAYER	f
9	Coaching Methodology Workshop	Session planning, player psychology, and tactical analysis for coaches	2025-09-29 21:37:14.854114	2025-09-29 23:07:14.854114	OFFLINE	12	Conference Room	\N	programming	advanced	\N	2	\N	18	2025-09-20 10:37:14.876109	2025-09-20 10:37:14.87611	COACH	f
10	Mixed Training: Strategy & Practice	Combined session where coaches and players work together on tactics	2025-10-01 22:37:14.854114	2025-10-02 00:07:14.854114	OFFLINE	20	Main Field	\N	football	all levels	\N	2	\N	18	2025-09-20 10:37:14.876111	2025-09-20 10:37:14.876111	\N	t
11	Player Fitness & Conditioning	Physical preparation and endurance training for competitive players	2025-10-03 23:37:14.854114	2025-10-04 01:07:14.854114	OFFLINE	14	Gym	\N	fitness	intermediate	\N	2	\N	18	2025-09-20 10:37:14.876112	2025-09-20 10:37:14.876113	PLAYER	f
12	Coach Education: Youth Development	Specialized techniques for working with young players	2025-10-06 00:37:14.854114	2025-10-06 02:07:14.854114	OFFLINE	10	Classroom B	\N	programming	beginner	\N	2	\N	18	2025-09-20 10:37:14.876114	2025-09-20 10:37:14.876114	COACH	f
13	General Football Skills (Open)	Basic football skills open to all participants	2025-10-08 01:37:14.854114	2025-10-08 03:07:14.854114	OFFLINE	18	Field B	\N	football	beginner	\N	2	\N	18	2025-09-20 10:37:14.876115	2025-09-20 10:37:14.876115	\N	f
14	LFA Teszt Szekció - Player Track	Specializáció teszt edzés játékosoknak	2025-10-02 10:00:00	2025-10-02 12:00:00	OFFLINE	15	LFA Training Center	\N	Football	All Levels	\N	15	\N	18	2025-09-21 09:44:32.905498	2025-09-21 09:44:32.905511	PLAYER	f
15	LFA Teszt Szekció - Coach Track	Vezetőedzői képzés specializáció teszt	2025-10-03 14:00:00	2025-10-03 16:00:00	OFFLINE	10	LFA Training Center	\N	Football	All Levels	\N	15	\N	18	2025-09-21 09:44:32.905513	2025-09-21 09:44:32.905514	COACH	f
16	LFA Teszt Szekció - Internship	Gyakorlati képzés specializáció teszt	2025-10-05 09:00:00	2025-10-05 12:00:00	OFFLINE	8	LFA Training Center	\N	Football	All Levels	\N	15	\N	18	2025-09-21 09:44:32.905515	2025-09-21 09:44:32.905515	INTERNSHIP	f
17	LFA Multi-Track Teszt Szekció	Összes specializáció tesztelése	2025-10-08 16:00:00	2025-10-08 18:00:00	OFFLINE	20	LFA Training Center	\N	Football	All Levels	\N	15	\N	18	2025-09-21 09:44:32.905516	2025-09-21 09:44:32.905517	\N	t
18	LFA Szemeszter Záró Teszt	Végleges onboarding és specializáció teszt	2025-10-10 11:00:00	2025-10-10 12:00:00	OFFLINE	25	LFA Training Center	\N	Football	All Levels	\N	15	\N	18	2025-09-21 09:44:32.905518	2025-09-21 09:44:32.905518	\N	f
\.


--
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.user_achievements (id, user_id, badge_type, title, description, icon, earned_at, semester_count) FROM stdin;
1	3	first_quiz_completed	🧠 First Quiz Master	Completed your very first quiz successfully!	🧠	2025-09-19 17:10:39.082458	\N
\.


--
-- Data for Name: user_licenses; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.user_licenses (id, user_id, specialization_type, current_level, max_achieved_level, started_at, last_advanced_at, instructor_notes, created_at, updated_at) FROM stdin;
1	2	PLAYER	1	1	2025-09-20 16:44:02.308506	\N	\N	2025-09-20 16:44:02.309231	2025-09-20 16:44:02.309233
2	2	COACH	1	1	2025-09-20 16:44:39.154351	\N	\N	2025-09-20 16:44:39.155131	2025-09-20 16:44:39.155133
3	2	INTERNSHIP	1	1	2025-09-20 16:44:50.688203	\N	\N	2025-09-20 16:44:50.689219	2025-09-20 16:44:50.689221
4	27	PLAYER	1	1	2025-09-20 16:56:46.69242	\N	\N	2025-09-20 16:56:46.693059	2025-09-20 16:56:46.693061
\.


--
-- Data for Name: user_question_performance; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.user_question_performance (id, user_id, question_id, total_attempts, correct_attempts, last_attempt_correct, last_attempted_at, difficulty_weight, next_review_at, mastery_level) FROM stdin;
5	3	2	22	10	t	2025-09-19 17:07:24.898015+02	1.1749394042330261	2025-10-07 03:57:59.413117+02	0.8250605957669739
7	3	8	13	8	t	2025-09-19 17:07:29.466495+02	1.1997537279999997	2025-10-05 17:27:09.86754+02	0.8002462720000003
8	3	4	9	9	t	2025-09-19 17:07:34.583946+02	1.1342177279999999	2025-10-09 19:27:19.12392+02	0.8657822720000001
4	3	5	9	9	t	2025-09-19 17:07:56.510027+02	1.1342177279999999	2025-10-09 19:27:41.050009+02	0.8657822720000001
2	3	3	17	12	t	2025-09-19 17:08:16.305949+02	1.1740070311480524	2025-10-07 05:20:11.056152+02	0.8259929688519476
1	3	1	16	13	t	2025-09-19 17:15:38.798762+02	1.1141139524550654	2025-10-11 06:23:39.118468+02	0.8858860475449346
3	3	6	12	10	t	2025-09-19 17:15:44.217715+02	1.1383281459199999	2025-10-09 12:46:08.233571+02	0.8616718540800001
6	3	7	12	12	t	2025-09-19 17:15:52.964693+02	1.068719476736	2025-10-14 22:30:19.365415+02	0.931280523264
10	14	2	1	0	f	2025-09-23 23:49:31.911278+02	2	2025-09-24 23:49:31.911294+02	0
11	14	3	1	1	t	2025-09-23 23:49:40.084487+02	1.8	2025-09-25 23:49:40.084508+02	0.2
12	14	6	1	1	t	2025-09-23 23:49:55.667907+02	1.8	2025-09-25 23:49:55.667924+02	0.2
9	14	7	2	2	t	2025-09-23 23:50:02.498509+02	1.64	2025-09-27 11:24:24.773197+02	0.36000000000000004
13	14	4	1	1	t	2025-09-23 23:50:08.085807+02	1.8	2025-09-25 23:50:08.085825+02	0.2
14	14	5	1	1	t	2025-09-23 23:50:14.234542+02	1.8	2025-09-25 23:50:14.234558+02	0.2
\.


--
-- Data for Name: user_stats; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.user_stats (id, user_id, semesters_participated, first_semester_date, current_streak, total_bookings, total_attended, total_cancelled, attendance_rate, feedback_given, average_rating_given, punctuality_score, total_xp, level, created_at, updated_at) FROM stdin;
3	16	0	\N	0	0	0	0	0	0	0	0	0	1	2025-09-23 18:28:37.000142	2025-09-26 08:23:47.777183
1	3	0	\N	0	0	0	0	0	0	0	0	1073	1	2025-09-17 07:20:37.707441	2025-09-19 17:17:37.22756
2	14	1	2025-09-20 00:00:00	0	3	0	0	0	0	0	0	760	1	2025-09-20 10:50:26.572983	2025-09-26 10:13:13.305131
4	36	0	\N	0	0	0	0	0	0	0	0	0	1	2025-09-25 08:50:43.587633	2025-09-25 09:10:40.043462
5	39	0	\N	0	0	0	0	0	0	0	0	0	1	2025-09-26 08:46:28.286551	2025-09-26 09:58:56.469366
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.users (id, name, nickname, email, password_hash, role, is_active, onboarding_completed, phone, emergency_contact, emergency_phone, date_of_birth, medical_notes, interests, created_at, updated_at, created_by, specialization, payment_verified, payment_verified_at, payment_verified_by, "position") FROM stdin;
36	Test Onboarding User	\N	test.onboarding@lfa.com	$2b$12$v7exMniISMNiSDC/5EP1relMTKWsmIgFVUbHMqrZmw2kia.d79eja	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-21 11:10:08.085577	2025-09-25 09:15:36.827484	\N	\N	f	\N	\N	\N
37	Emma Test Student	\N	emma.newcomer@student.devstudio.com	$2b$12$rXcuB/pd8db8n0eyj0P8J.ISerBYGsPX1hfK2Tnai.MOCmbd6wCw.	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-25 16:47:36.637156	2025-09-25 16:47:36.637161	\N	\N	f	\N	\N	\N
38	Layout Test Student	\N	layout.test@student.devstudio.com	$2b$12$BSTsG2q.hvu6vCGcuZVVjuqZx2Y7gGKCHU68pYBEqC8Ir6XGWBhSq	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-25 19:10:51.300736	2025-09-25 19:10:51.30074	\N	\N	f	\N	\N	\N
2	George Student	\N	george@student.devstudio.com	$2b$12$z5dtNRAgg4CG4POPmebEMOwilaYzbou9W5W2aLs4WjqcXnBNL5XuW	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-16 21:11:01.177941	2025-09-20 14:35:34.634118	\N	\N	f	\N	\N	midfielder
3	George Clooney	\N	george.clooney@student.devstudio.com	$2b$12$Rwp.7iVjBvy0s68llQ2KE.QNx8hi1AzG1FQuKxrlVOJ2zJ47y5j6a	STUDENT	t	f	\N	\N	0620667553	2000-01-01 00:00:00	\N	["Dance"]	2025-09-16 21:13:47.778671	2025-09-21 09:42:57.912187	\N	\N	t	2025-09-20 14:29:50.906804	24	midfielder
15	Neymar Jr.	\N	neymar@lfa.com	$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-21 09:42:57.91451	\N	\N	f	\N	\N	midfielder
16	Kylian Mbappé	\N	mbappe@lfa.com	$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m	STUDENT	t	f	\N	\N	\N	2004-01-01 00:00:00	\N	\N	2025-09-20 08:56:33.777535	2025-09-21 09:42:57.914512	\N	\N	f	\N	\N	midfielder
18	Carlo Ancelotti	\N	ancelotti@lfa.com	$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m	INSTRUCTOR	t	\N	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	\N	f	\N	\N	coach
19	Jürgen Klopp	\N	klopp@lfa.com	$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m	INSTRUCTOR	t	\N	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-20 08:56:33.777535	\N	\N	f	\N	\N	coach
1	System Administrator	\N	admin@yourcompany.com	$2b$12$d.8VRvyC.XpT7J62UY2pqeT4nBhoNzUMAFJWg5iKTjB16ExQkHH..	ADMIN	t	f	\N	\N	\N	\N	\N	\N	2025-09-16 20:55:44.855685	2025-09-20 14:00:09.77656	\N	\N	f	\N	\N	\N
20	Diego Maradona	\N	maradona@lfa.com	$2b$12$sfofxMF5/RXEYLlsoGUBbeSmfEr4anmnG8r3EARI7CxwZybpPE5pm	ADMIN	t	\N	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-20 14:00:11.705087	\N	\N	f	\N	\N	\N
21	Pelé	\N	pele@lfa.com	$2b$12$TQ8uPj2RjYpZz/Vyhx99meSipSwkbzyZWXoeQKcSvGSd5Eh5sOP7m	ADMIN	t	\N	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-20 14:00:13.646688	\N	\N	f	\N	\N	\N
24	Test Admin	\N	admin@test.com	$2b$12$/4PUC.fwURk7mtaqVjOKDO6Vq5C3MLdvtGuiByK5bVD9e9ieboBOG	ADMIN	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 14:02:06.623423	2025-09-20 14:02:06.62343	\N	\N	f	\N	\N	\N
14	Cristiano Ronaldo	\N	ronaldo@lfa.com	$2b$12$BVNqmGU0gk/Rdy0SNwaIYuYrLYIpGHxPXek.S2S4bY1hajrRerLhK	STUDENT	t	f	\N	\N	+36308876653	1985-02-05 00:00:00	\N	["Football","Fitness","Running","Swimming","Tennis"]	2025-09-20 08:56:33.777535	2025-09-25 20:11:48.75474	\N	\N	f	2025-09-20 14:46:08.651113	24	\N
39	Test Student	\N	test.student@devstudio.com	$2b$12$jnXN18zlgNSMULgv/ySR5O0OtIfUXy0E27KJDk1yc57lLjXf9ZkcK	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-26 08:43:38.649687	2025-09-26 08:43:38.649691	\N	\N	f	\N	\N	\N
22	Alex Player	\N	alex.player@lfa.com	$2b$12$tEZGy53frqBUWpIL3IQMJeGQfn9ds51Ip7l4EJsQytH0KndCg60j.	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 10:37:25.859255	2025-09-20 10:37:25.85926	\N	PLAYER	f	\N	\N	midfielder
23	Maria Coach	\N	maria.coach@lfa.com	$2b$12$6r1diLW9//3/PZQdqNtI2O6BqX0cbRSYKkHbCOr5Tt8tn.Fuylypm	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 10:37:25.859262	2025-09-20 10:37:25.859263	\N	COACH	f	\N	\N	midfielder
25	Test Student No Payment	\N	test.student.nopayment@devstudio.com	$2b$12$rzN7fKXvJNn4KX6iQS6w..opgjG5ry8QMWCU3uRUFXo6aV.Blo2na	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 14:10:22.672442	2025-09-20 14:10:22.672448	\N	\N	f	\N	\N	midfielder
26	Test Student Verified Payment	\N	test.student.verified@devstudio.com	$2b$12$vrVjxHG/g0LyyG7CZLvMeOGsDBV.AX6PcVA28cKUTAFKJTe2aTo2G	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 14:23:14.735784	2025-09-20 14:30:00.741216	\N	\N	f	\N	\N	midfielder
27	Coach Test User	\N	coach.test@student.devstudio.com	$2b$12$oEMNAHm0wfLEO98olxUROO4SEzvgXSQe0QE/NVo.wLMt7pSj254BW	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 16:56:46.651737	2025-09-20 16:56:46.651741	\N	\N	f	\N	\N	midfielder
28	Első Szemeszter Hallgató	\N	first.semester@student.devstudio.com	$2b$12$HfMckFzZXxD..cdM9zWUQOjKDv1ABqjQLJtfL2.vEcviRv7rZrARK	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 17:18:03.316227	2025-09-20 17:18:03.316232	\N	\N	f	\N	\N	midfielder
13	Lionel Messi	\N	messi@lfa.com	$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-21 09:42:57.913515	\N	PLAYER	f	\N	\N	midfielder
34	Teszt Október Hallgató	\N	teszt.oktober@lfa.com	$2b$12$RqS4C6/yk6K9PJBShBiz6.eHnrrgiKJO44W7yPOvntVM.MwiapdNa	STUDENT	t	f	\N	\N	\N	\N	\N	\N	2025-09-21 09:45:08.643555	2025-09-21 09:45:08.643563	\N	\N	f	\N	\N	midfielder
17	Pep Guardiola	\N	guardiola@lfa.com	$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m	INSTRUCTOR	t	\N	\N	\N	\N	\N	\N	\N	2025-09-20 08:56:33.777535	2025-09-20 10:01:00.183479	\N	COACH	f	\N	\N	coach
\.


--
-- Name: adaptive_learning_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.adaptive_learning_sessions_id_seq', 185, true);


--
-- Name: attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.attendance_id_seq', 1, false);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.bookings_id_seq', 3, true);


--
-- Name: feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.feedback_id_seq', 1, false);


--
-- Name: groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.groups_id_seq', 10, true);


--
-- Name: license_metadata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.license_metadata_id_seq', 21, true);


--
-- Name: license_progressions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.license_progressions_id_seq', 1, false);


--
-- Name: messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.messages_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: project_enrollment_quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_enrollment_quizzes_id_seq', 1, false);


--
-- Name: project_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_enrollments_id_seq', 1, false);


--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_milestone_progress_id_seq', 1, false);


--
-- Name: project_milestones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_milestones_id_seq', 10, true);


--
-- Name: project_quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_quizzes_id_seq', 1, false);


--
-- Name: project_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_sessions_id_seq', 1, false);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.projects_id_seq', 9, true);


--
-- Name: question_metadata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.question_metadata_id_seq', 8, true);


--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_answer_options_id_seq', 26, true);


--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_attempts_id_seq', 4, true);


--
-- Name: quiz_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_questions_id_seq', 8, true);


--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_user_answers_id_seq', 8, true);


--
-- Name: quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quizzes_id_seq', 1, true);


--
-- Name: semesters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.semesters_id_seq', 17, true);


--
-- Name: sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.sessions_id_seq', 18, true);


--
-- Name: user_achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.user_achievements_id_seq', 1, true);


--
-- Name: user_licenses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.user_licenses_id_seq', 4, true);


--
-- Name: user_question_performance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.user_question_performance_id_seq', 14, true);


--
-- Name: user_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.user_stats_id_seq', 5, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.users_id_seq', 39, true);


--
-- Name: adaptive_learning_sessions adaptive_learning_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.adaptive_learning_sessions
    ADD CONSTRAINT adaptive_learning_sessions_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attendance attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: group_users group_users_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.group_users
    ADD CONSTRAINT group_users_pkey PRIMARY KEY (group_id, user_id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: license_metadata license_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_metadata
    ADD CONSTRAINT license_metadata_pkey PRIMARY KEY (id);


--
-- Name: license_metadata license_metadata_specialization_type_level_code_key; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_metadata
    ADD CONSTRAINT license_metadata_specialization_type_level_code_key UNIQUE (specialization_type, level_code);


--
-- Name: license_metadata license_metadata_specialization_type_level_number_key; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_metadata
    ADD CONSTRAINT license_metadata_specialization_type_level_number_key UNIQUE (specialization_type, level_number);


--
-- Name: license_progressions license_progressions_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_progressions
    ADD CONSTRAINT license_progressions_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_pkey PRIMARY KEY (id);


--
-- Name: project_enrollments project_enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT project_enrollments_pkey PRIMARY KEY (id);


--
-- Name: project_milestone_progress project_milestone_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT project_milestone_progress_pkey PRIMARY KEY (id);


--
-- Name: project_milestones project_milestones_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestones
    ADD CONSTRAINT project_milestones_pkey PRIMARY KEY (id);


--
-- Name: project_quizzes project_quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_pkey PRIMARY KEY (id);


--
-- Name: project_sessions project_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: question_metadata question_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.question_metadata
    ADD CONSTRAINT question_metadata_pkey PRIMARY KEY (id);


--
-- Name: quiz_answer_options quiz_answer_options_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_answer_options
    ADD CONSTRAINT quiz_answer_options_pkey PRIMARY KEY (id);


--
-- Name: quiz_attempts quiz_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_pkey PRIMARY KEY (id);


--
-- Name: quiz_questions quiz_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_questions
    ADD CONSTRAINT quiz_questions_pkey PRIMARY KEY (id);


--
-- Name: quiz_user_answers quiz_user_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_pkey PRIMARY KEY (id);


--
-- Name: quizzes quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quizzes
    ADD CONSTRAINT quizzes_pkey PRIMARY KEY (id);


--
-- Name: semesters semesters_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.semesters
    ADD CONSTRAINT semesters_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: project_milestone_progress unique_enrollment_milestone; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT unique_enrollment_milestone UNIQUE (enrollment_id, milestone_id);


--
-- Name: project_quizzes unique_project_quiz_type; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT unique_project_quiz_type UNIQUE (project_id, quiz_id, quiz_type);


--
-- Name: project_sessions unique_project_session; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT unique_project_session UNIQUE (project_id, session_id);


--
-- Name: project_enrollments unique_project_user; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT unique_project_user UNIQUE (project_id, user_id);


--
-- Name: project_enrollment_quizzes unique_project_user_enrollment_quiz; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT unique_project_user_enrollment_quiz UNIQUE (project_id, user_id);


--
-- Name: question_metadata unique_question_metadata; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.question_metadata
    ADD CONSTRAINT unique_question_metadata UNIQUE (question_id);


--
-- Name: user_question_performance unique_user_question; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT unique_user_question UNIQUE (user_id, question_id);


--
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (id);


--
-- Name: user_licenses user_licenses_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_pkey PRIMARY KEY (id);


--
-- Name: user_licenses user_licenses_user_id_specialization_type_key; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_user_id_specialization_type_key UNIQUE (user_id, specialization_type);


--
-- Name: user_question_performance user_question_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT user_question_performance_pkey PRIMARY KEY (id);


--
-- Name: user_stats user_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_stats
    ADD CONSTRAINT user_stats_pkey PRIMARY KEY (id);


--
-- Name: user_stats user_stats_user_id_key; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_stats
    ADD CONSTRAINT user_stats_user_id_key UNIQUE (user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_adaptive_learning_sessions_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_adaptive_learning_sessions_id ON public.adaptive_learning_sessions USING btree (id);


--
-- Name: ix_attendance_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_attendance_id ON public.attendance USING btree (id);


--
-- Name: ix_bookings_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_bookings_id ON public.bookings USING btree (id);


--
-- Name: ix_feedback_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_feedback_id ON public.feedback USING btree (id);


--
-- Name: ix_groups_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_groups_id ON public.groups USING btree (id);


--
-- Name: ix_messages_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_messages_id ON public.messages USING btree (id);


--
-- Name: ix_notifications_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);


--
-- Name: ix_project_enrollment_quizzes_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_enrollment_quizzes_id ON public.project_enrollment_quizzes USING btree (id);


--
-- Name: ix_project_enrollments_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_enrollments_id ON public.project_enrollments USING btree (id);


--
-- Name: ix_project_milestone_progress_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_milestone_progress_id ON public.project_milestone_progress USING btree (id);


--
-- Name: ix_project_milestones_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_milestones_id ON public.project_milestones USING btree (id);


--
-- Name: ix_project_quizzes_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_quizzes_id ON public.project_quizzes USING btree (id);


--
-- Name: ix_project_sessions_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_sessions_id ON public.project_sessions USING btree (id);


--
-- Name: ix_projects_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_projects_id ON public.projects USING btree (id);


--
-- Name: ix_question_metadata_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_question_metadata_id ON public.question_metadata USING btree (id);


--
-- Name: ix_quiz_answer_options_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_quiz_answer_options_id ON public.quiz_answer_options USING btree (id);


--
-- Name: ix_quiz_attempts_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_quiz_attempts_id ON public.quiz_attempts USING btree (id);


--
-- Name: ix_quiz_questions_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_quiz_questions_id ON public.quiz_questions USING btree (id);


--
-- Name: ix_quiz_user_answers_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_quiz_user_answers_id ON public.quiz_user_answers USING btree (id);


--
-- Name: ix_quizzes_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_quizzes_id ON public.quizzes USING btree (id);


--
-- Name: ix_semesters_code; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE UNIQUE INDEX ix_semesters_code ON public.semesters USING btree (code);


--
-- Name: ix_semesters_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_semesters_id ON public.semesters USING btree (id);


--
-- Name: ix_sessions_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_sessions_id ON public.sessions USING btree (id);


--
-- Name: ix_user_achievements_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_user_achievements_id ON public.user_achievements USING btree (id);


--
-- Name: ix_user_question_performance_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_user_question_performance_id ON public.user_question_performance USING btree (id);


--
-- Name: ix_user_stats_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_user_stats_id ON public.user_stats USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: adaptive_learning_sessions adaptive_learning_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.adaptive_learning_sessions
    ADD CONSTRAINT adaptive_learning_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: attendance attendance_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: attendance attendance_marked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_marked_by_fkey FOREIGN KEY (marked_by) REFERENCES public.users(id);


--
-- Name: attendance attendance_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: attendance attendance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: bookings bookings_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: bookings bookings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: feedback feedback_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: feedback feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users fk_users_payment_verified_by; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_payment_verified_by FOREIGN KEY (payment_verified_by) REFERENCES public.users(id);


--
-- Name: group_users group_users_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.group_users
    ADD CONSTRAINT group_users_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: group_users group_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.group_users
    ADD CONSTRAINT group_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: groups groups_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: license_progressions license_progressions_advanced_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_progressions
    ADD CONSTRAINT license_progressions_advanced_by_fkey FOREIGN KEY (advanced_by) REFERENCES public.users(id);


--
-- Name: license_progressions license_progressions_user_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.license_progressions
    ADD CONSTRAINT license_progressions_user_license_id_fkey FOREIGN KEY (user_license_id) REFERENCES public.user_licenses(id);


--
-- Name: messages messages_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.users(id);


--
-- Name: messages messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_related_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_booking_id_fkey FOREIGN KEY (related_booking_id) REFERENCES public.bookings(id);


--
-- Name: notifications notifications_related_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_session_id_fkey FOREIGN KEY (related_session_id) REFERENCES public.sessions(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_quiz_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_quiz_attempt_id_fkey FOREIGN KEY (quiz_attempt_id) REFERENCES public.quiz_attempts(id);


--
-- Name: project_enrollment_quizzes project_enrollment_quizzes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollment_quizzes
    ADD CONSTRAINT project_enrollment_quizzes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_enrollments project_enrollments_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT project_enrollments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_enrollments project_enrollments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_enrollments
    ADD CONSTRAINT project_enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_milestone_progress project_milestone_progress_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT project_milestone_progress_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.project_enrollments(id);


--
-- Name: project_milestone_progress project_milestone_progress_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestone_progress
    ADD CONSTRAINT project_milestone_progress_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);


--
-- Name: project_milestones project_milestones_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_milestones
    ADD CONSTRAINT project_milestones_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_quizzes project_quizzes_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);


--
-- Name: project_quizzes project_quizzes_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_quizzes project_quizzes_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_quizzes
    ADD CONSTRAINT project_quizzes_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);


--
-- Name: project_sessions project_sessions_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.project_milestones(id);


--
-- Name: project_sessions project_sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_sessions project_sessions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions
    ADD CONSTRAINT project_sessions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id);


--
-- Name: projects projects_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);


--
-- Name: projects projects_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: question_metadata question_metadata_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.question_metadata
    ADD CONSTRAINT question_metadata_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: quiz_answer_options quiz_answer_options_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_answer_options
    ADD CONSTRAINT quiz_answer_options_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: quiz_attempts quiz_attempts_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);


--
-- Name: quiz_attempts quiz_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: quiz_questions quiz_questions_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_questions
    ADD CONSTRAINT quiz_questions_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id);


--
-- Name: quiz_user_answers quiz_user_answers_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.quiz_attempts(id);


--
-- Name: quiz_user_answers quiz_user_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: quiz_user_answers quiz_user_answers_selected_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.quiz_user_answers
    ADD CONSTRAINT quiz_user_answers_selected_option_id_fkey FOREIGN KEY (selected_option_id) REFERENCES public.quiz_answer_options(id);


--
-- Name: sessions sessions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: sessions sessions_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.users(id);


--
-- Name: sessions sessions_semester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_semester_id_fkey FOREIGN KEY (semester_id) REFERENCES public.semesters(id);


--
-- Name: user_achievements user_achievements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_licenses user_licenses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_licenses
    ADD CONSTRAINT user_licenses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_question_performance user_question_performance_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT user_question_performance_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.quiz_questions(id);


--
-- Name: user_question_performance user_question_performance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_question_performance
    ADD CONSTRAINT user_question_performance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_stats user_stats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_stats
    ADD CONSTRAINT user_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict vAbY5tKSvLMm6b8VyGhPAnyuZ6MhmRUasnqqkaQH6omwrGSaHMw7gZXvJV6BQfu

