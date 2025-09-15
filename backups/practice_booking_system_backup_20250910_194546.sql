--
-- PostgreSQL database dump
--

\restrict cCEhO5k1xLEP19eFcN2kUdztN30q8RKsowl0h7cgFR9cPI9XIeXEz0bFBF22zHw

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
    'FILL_IN_BLANK'
);


ALTER TYPE public.questiontype OWNER TO "lovas.zoltan";

--
-- Name: quizcategory; Type: TYPE; Schema: public; Owner: lovas.zoltan
--

CREATE TYPE public.quizcategory AS ENUM (
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
    comment text,
    is_anonymous boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    instructor_rating double precision,
    session_quality double precision,
    would_recommend boolean,
    CONSTRAINT rating_range CHECK (((rating >= (1.0)::double precision) AND (rating <= (5.0)::double precision)))
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
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.projects OWNER TO "lovas.zoltan";

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
    semester_id integer NOT NULL,
    group_id integer,
    instructor_id integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    sport_type character varying(100) DEFAULT 'General'::character varying,
    level character varying(50) DEFAULT 'All Levels'::character varying,
    instructor_name character varying(200)
);


ALTER TABLE public.sessions OWNER TO "lovas.zoltan";

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
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    role public.userrole NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    created_by integer
);


ALTER TABLE public.users OWNER TO "lovas.zoltan";

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
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


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
-- Name: project_sessions id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.project_sessions ALTER COLUMN id SET DEFAULT nextval('public.project_sessions_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


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
-- Name: user_stats id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_stats ALTER COLUMN id SET DEFAULT nextval('public.user_stats_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.alembic_version (version_num) FROM stdin;
3e6ac10683c0
\.


--
-- Data for Name: attendance; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.attendance (id, user_id, session_id, booking_id, status, check_in_time, check_out_time, notes, marked_by, created_at, updated_at) FROM stdin;
1067	109	170	1204	PRESENT	\N	\N	Test attendance for session 1	\N	2025-09-06 10:15:38.272612	2025-09-06 10:15:38.272614
1068	109	171	1205	PRESENT	\N	\N	Test attendance for session 2	\N	2025-09-06 10:15:38.272615	2025-09-06 10:15:38.272615
1073	97	219	1286	PRESENT	2025-09-06 21:01:17.450272	\N	\N	\N	2025-09-06 23:01:04.302359	2025-09-06 23:01:17.451334
1070	109	175	1208	PRESENT	\N	\N	\N	\N	2025-09-06 13:05:46.373007	2025-09-06 13:05:46.373011
1074	97	222	1289	PRESENT	2025-09-06 21:09:51.063681	\N	\N	\N	2025-09-06 23:09:51.066752	2025-09-06 23:09:51.066754
1071	109	176	1209	PRESENT	\N	\N	\N	\N	2025-09-06 13:08:44.942304	2025-09-06 13:08:44.942305
1072	109	181	1212	PRESENT	2025-09-05 13:16:19.029495	\N	\N	\N	2025-09-06 13:16:19.029942	2025-09-06 13:16:19.029944
752	97	117	851	PRESENT	2025-03-03 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793273	2025-08-27 20:57:54.793276
753	103	117	852	LATE	2025-03-03 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793278	2025-08-27 20:57:54.793278
754	105	117	853	LATE	2025-03-03 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793279	2025-08-27 20:57:54.793279
755	102	117	854	PRESENT	2025-03-03 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.79328	2025-08-27 20:57:54.79328
756	99	117	855	PRESENT	2025-03-03 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793281	2025-08-27 20:57:54.793281
757	104	117	856	PRESENT	2025-03-03 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793282	2025-08-27 20:57:54.793282
758	101	117	857	PRESENT	2025-03-03 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793283	2025-08-27 20:57:54.793283
759	98	117	858	PRESENT	2025-03-03 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793283	2025-08-27 20:57:54.793284
760	100	117	859	PRESENT	2025-03-03 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793284	2025-08-27 20:57:54.793285
761	106	118	860	PRESENT	2025-03-05 14:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793285	2025-08-27 20:57:54.793286
762	98	118	861	LATE	2025-03-05 14:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793286	2025-08-27 20:57:54.793287
763	103	118	862	PRESENT	2025-03-05 14:05:00	\N		\N	2025-08-27 20:57:54.793287	2025-08-27 20:57:54.793287
764	105	118	863	LATE	2025-03-05 14:13:00	\N		\N	2025-08-27 20:57:54.793288	2025-08-27 20:57:54.793288
765	99	118	864	PRESENT	2025-03-05 14:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793289	2025-08-27 20:57:54.793289
766	101	118	865	PRESENT	2025-03-05 14:05:00	\N		\N	2025-08-27 20:57:54.79329	2025-08-27 20:57:54.79329
767	104	118	867	PRESENT	2025-03-05 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793291	2025-08-27 20:57:54.793291
768	106	119	868	PRESENT	2025-03-14 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793291	2025-08-27 20:57:54.793292
769	104	119	869	LATE	2025-03-14 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793292	2025-08-27 20:57:54.793293
770	102	119	870	PRESENT	2025-03-14 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793293	2025-08-27 20:57:54.793294
771	101	119	872	PRESENT	2025-03-14 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793294	2025-08-27 20:57:54.793295
772	100	119	873	LATE	2025-03-14 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793295	2025-08-27 20:57:54.793295
773	99	119	874	PRESENT	2025-03-14 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793296	2025-08-27 20:57:54.793296
774	99	120	876	PRESENT	2025-03-10 09:05:00	\N		\N	2025-08-27 20:57:54.793297	2025-08-27 20:57:54.793297
775	104	120	877	PRESENT	2025-03-10 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793298	2025-08-27 20:57:54.793298
776	106	120	878	PRESENT	2025-03-10 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793299	2025-08-27 20:57:54.793299
777	98	120	879	PRESENT	2025-03-10 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793299	2025-08-27 20:57:54.7933
778	100	120	880	LATE	2025-03-10 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.7933	2025-08-27 20:57:54.793301
779	97	120	881	PRESENT	2025-03-10 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793301	2025-08-27 20:57:54.793302
780	97	121	883	PRESENT	2025-03-19 14:01:00	\N		\N	2025-08-27 20:57:54.793302	2025-08-27 20:57:54.793303
781	104	121	884	LATE	2025-03-19 14:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793303	2025-08-27 20:57:54.793304
782	102	121	885	PRESENT	2025-03-19 14:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793304	2025-08-27 20:57:54.793304
783	106	121	886	PRESENT	2025-03-19 14:13:00	\N		\N	2025-08-27 20:57:54.793305	2025-08-27 20:57:54.793305
784	105	121	887	PRESENT	2025-03-19 14:07:00	\N		\N	2025-08-27 20:57:54.793306	2025-08-27 20:57:54.793306
785	100	121	888	PRESENT	2025-03-19 14:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793307	2025-08-27 20:57:54.793307
786	99	121	889	PRESENT	2025-03-19 14:00:00	\N		\N	2025-08-27 20:57:54.793308	2025-08-27 20:57:54.793308
787	105	122	890	LATE	2025-03-21 09:02:00	\N		\N	2025-08-27 20:57:54.793308	2025-08-27 20:57:54.793309
788	99	122	891	PRESENT	2025-03-21 09:09:00	\N		\N	2025-08-27 20:57:54.793309	2025-08-27 20:57:54.79331
789	106	122	892	PRESENT	2025-03-21 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.79331	2025-08-27 20:57:54.793311
790	98	122	893	PRESENT	2025-03-21 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793311	2025-08-27 20:57:54.793311
791	101	122	894	LATE	2025-03-21 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793312	2025-08-27 20:57:54.793312
792	104	122	895	PRESENT	2025-03-21 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793313	2025-08-27 20:57:54.793313
793	103	122	896	PRESENT	2025-03-21 09:07:00	\N		\N	2025-08-27 20:57:54.793314	2025-08-27 20:57:54.793314
794	97	122	897	PRESENT	2025-03-21 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793315	2025-08-27 20:57:54.793315
795	99	123	898	PRESENT	2025-03-24 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793315	2025-08-27 20:57:54.793316
796	98	123	899	LATE	2025-03-24 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793316	2025-08-27 20:57:54.793317
797	97	123	900	LATE	2025-03-24 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793317	2025-08-27 20:57:54.793318
798	103	123	901	PRESENT	2025-03-24 09:15:00	\N		\N	2025-08-27 20:57:54.793318	2025-08-27 20:57:54.793318
799	100	123	902	PRESENT	2025-03-24 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793319	2025-08-27 20:57:54.793319
800	101	123	903	PRESENT	2025-03-24 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.79332	2025-08-27 20:57:54.79332
801	106	123	904	PRESENT	2025-03-24 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793321	2025-08-27 20:57:54.793321
802	102	123	905	LATE	2025-03-24 09:03:00	\N		\N	2025-08-27 20:57:54.793322	2025-08-27 20:57:54.793322
803	100	124	906	PRESENT	2025-03-26 14:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793322	2025-08-27 20:57:54.793323
804	104	124	908	PRESENT	2025-03-26 14:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793323	2025-08-27 20:57:54.793324
805	97	124	909	PRESENT	2025-03-26 14:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793324	2025-08-27 20:57:54.793325
806	106	124	910	LATE	2025-03-26 14:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793325	2025-08-27 20:57:54.793326
807	105	124	911	LATE	2025-03-26 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793326	2025-08-27 20:57:54.793326
808	102	124	913	PRESENT	2025-03-26 14:05:00	\N		\N	2025-08-27 20:57:54.793327	2025-08-27 20:57:54.793327
809	98	124	914	PRESENT	2025-03-26 14:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793328	2025-08-27 20:57:54.793328
810	98	125	915	PRESENT	2025-04-04 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793329	2025-08-27 20:57:54.793329
811	104	125	916	PRESENT	2025-04-04 09:15:00	\N		\N	2025-08-27 20:57:54.79333	2025-08-27 20:57:54.79333
812	103	125	917	LATE	2025-04-04 09:02:00	\N		\N	2025-08-27 20:57:54.79333	2025-08-27 20:57:54.793331
813	99	125	918	PRESENT	2025-04-04 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793331	2025-08-27 20:57:54.793332
814	100	125	919	LATE	2025-04-04 09:01:00	\N		\N	2025-08-27 20:57:54.793332	2025-08-27 20:57:54.793333
815	106	125	920	PRESENT	2025-04-04 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793333	2025-08-27 20:57:54.793334
816	101	125	921	PRESENT	2025-04-04 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793334	2025-08-27 20:57:54.793334
817	105	126	922	PRESENT	2025-04-07 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793335	2025-08-27 20:57:54.793335
818	98	126	923	PRESENT	2025-04-07 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793336	2025-08-27 20:57:54.793336
819	102	126	924	LATE	2025-04-07 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793337	2025-08-27 20:57:54.793337
820	106	126	926	PRESENT	2025-04-07 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793338	2025-08-27 20:57:54.793338
821	100	126	927	PRESENT	2025-04-07 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793339	2025-08-27 20:57:54.793339
822	103	126	928	PRESENT	2025-04-07 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793339	2025-08-27 20:57:54.79334
823	101	126	929	PRESENT	2025-04-07 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.79334	2025-08-27 20:57:54.793341
824	106	127	931	LATE	2025-04-09 14:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793341	2025-08-27 20:57:54.793342
825	103	127	932	LATE	2025-04-09 14:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793342	2025-08-27 20:57:54.793342
826	97	127	933	LATE	2025-04-09 14:04:00	\N		\N	2025-08-27 20:57:54.793343	2025-08-27 20:57:54.793343
827	99	127	934	PRESENT	2025-04-09 14:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793344	2025-08-27 20:57:54.793344
828	102	127	935	LATE	2025-04-09 14:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793345	2025-08-27 20:57:54.793345
829	100	127	936	PRESENT	2025-04-09 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793346	2025-08-27 20:57:54.793346
830	101	127	937	PRESENT	2025-04-09 14:04:00	\N		\N	2025-08-27 20:57:54.793347	2025-08-27 20:57:54.793347
831	102	128	938	PRESENT	2025-04-18 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793347	2025-08-27 20:57:54.793348
832	100	128	939	PRESENT	2025-04-18 09:06:00	\N		\N	2025-08-27 20:57:54.793348	2025-08-27 20:57:54.793349
833	106	128	940	LATE	2025-04-18 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793349	2025-08-27 20:57:54.79335
834	97	128	941	PRESENT	2025-04-18 09:11:00	\N		\N	2025-08-27 20:57:54.79335	2025-08-27 20:57:54.79335
835	101	128	942	PRESENT	2025-04-18 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793351	2025-08-27 20:57:54.793351
836	103	128	944	PRESENT	2025-04-18 09:07:00	\N		\N	2025-08-27 20:57:54.793352	2025-08-27 20:57:54.793352
837	98	128	945	PRESENT	2025-04-18 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793353	2025-08-27 20:57:54.793353
838	105	129	948	PRESENT	2025-04-14 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793354	2025-08-27 20:57:54.793354
839	98	129	949	PRESENT	2025-04-14 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793355	2025-08-27 20:57:54.793355
840	101	129	950	PRESENT	2025-04-14 09:03:00	\N		\N	2025-08-27 20:57:54.793355	2025-08-27 20:57:54.793356
841	100	129	951	PRESENT	2025-04-14 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793356	2025-08-27 20:57:54.793357
842	97	129	952	PRESENT	2025-04-14 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793357	2025-08-27 20:57:54.793358
843	99	129	953	LATE	2025-04-14 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793358	2025-08-27 20:57:54.793358
844	98	130	954	PRESENT	2025-04-23 14:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793359	2025-08-27 20:57:54.793359
845	99	130	955	PRESENT	2025-04-23 14:14:00	\N		\N	2025-08-27 20:57:54.79336	2025-08-27 20:57:54.79336
846	100	130	956	LATE	2025-04-23 14:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793361	2025-08-27 20:57:54.793361
847	103	130	957	LATE	2025-04-23 14:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793362	2025-08-27 20:57:54.793362
848	101	130	958	PRESENT	2025-04-23 14:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793363	2025-08-27 20:57:54.793363
849	104	130	959	PRESENT	2025-04-23 14:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793363	2025-08-27 20:57:54.793364
850	105	130	960	PRESENT	2025-04-23 14:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793364	2025-08-27 20:57:54.793365
851	97	130	961	PRESENT	2025-04-23 14:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793365	2025-08-27 20:57:54.793366
852	102	131	962	PRESENT	2025-05-02 09:06:00	\N		\N	2025-08-27 20:57:54.793366	2025-08-27 20:57:54.793366
853	105	131	963	LATE	2025-05-02 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793367	2025-08-27 20:57:54.793367
854	100	131	964	PRESENT	2025-05-02 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793368	2025-08-27 20:57:54.793368
855	101	131	965	PRESENT	2025-05-02 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793369	2025-08-27 20:57:54.793369
856	104	131	967	PRESENT	2025-05-02 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.79337	2025-08-27 20:57:54.79337
857	98	131	968	PRESENT	2025-05-02 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.79337	2025-08-27 20:57:54.793371
858	99	132	969	LATE	2025-04-28 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793371	2025-08-27 20:57:54.793372
859	104	132	970	PRESENT	2025-04-28 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793372	2025-08-27 20:57:54.793373
860	106	132	971	LATE	2025-04-28 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793373	2025-08-27 20:57:54.793374
861	97	132	972	LATE	2025-04-28 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793374	2025-08-27 20:57:54.793374
862	101	132	973	PRESENT	2025-04-28 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793375	2025-08-27 20:57:54.793375
863	102	132	975	PRESENT	2025-04-28 09:07:00	\N		\N	2025-08-27 20:57:54.793376	2025-08-27 20:57:54.793376
864	97	133	976	PRESENT	2025-05-07 14:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793377	2025-08-27 20:57:54.793377
865	102	133	977	PRESENT	2025-05-07 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793378	2025-08-27 20:57:54.793378
866	105	133	978	PRESENT	2025-05-07 14:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793378	2025-08-27 20:57:54.793379
867	101	133	979	PRESENT	2025-05-07 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793379	2025-08-27 20:57:54.79338
868	99	133	980	LATE	2025-05-07 14:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.79338	2025-08-27 20:57:54.793381
869	100	133	981	PRESENT	2025-05-07 14:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793381	2025-08-27 20:57:54.793381
870	106	133	983	LATE	2025-05-07 14:04:00	\N		\N	2025-08-27 20:57:54.793382	2025-08-27 20:57:54.793382
871	104	133	984	PRESENT	2025-05-07 14:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793383	2025-08-27 20:57:54.793383
872	101	134	986	PRESENT	2025-05-09 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793384	2025-08-27 20:57:54.793384
873	100	134	987	PRESENT	2025-05-09 09:13:00	\N		\N	2025-08-27 20:57:54.793385	2025-08-27 20:57:54.793385
874	105	134	988	PRESENT	2025-05-09 09:02:00	\N		\N	2025-08-27 20:57:54.793385	2025-08-27 20:57:54.793386
875	99	134	989	PRESENT	2025-05-09 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793386	2025-08-27 20:57:54.793387
876	106	134	990	LATE	2025-05-09 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793387	2025-08-27 20:57:54.793388
877	103	134	991	PRESENT	2025-05-09 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793388	2025-08-27 20:57:54.793388
878	98	134	992	PRESENT	2025-05-09 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793389	2025-08-27 20:57:54.793389
879	105	135	993	PRESENT	2025-05-12 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.79339	2025-08-27 20:57:54.79339
880	98	135	995	PRESENT	2025-05-12 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793391	2025-08-27 20:57:54.793391
881	103	135	996	LATE	2025-05-12 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793392	2025-08-27 20:57:54.793392
882	100	135	997	PRESENT	2025-05-12 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793392	2025-08-27 20:57:54.793393
883	106	135	998	LATE	2025-05-12 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793393	2025-08-27 20:57:54.793394
884	101	135	999	PRESENT	2025-05-12 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793394	2025-08-27 20:57:54.793395
885	99	135	1000	PRESENT	2025-05-12 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793395	2025-08-27 20:57:54.793396
886	106	136	1001	LATE	2025-05-21 14:15:00	\N		\N	2025-08-27 20:57:54.793396	2025-08-27 20:57:54.793396
887	97	136	1002	PRESENT	2025-05-21 14:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793397	2025-08-27 20:57:54.793397
888	99	136	1003	LATE	2025-05-21 14:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793398	2025-08-27 20:57:54.793398
889	100	136	1004	PRESENT	2025-05-21 14:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793399	2025-08-27 20:57:54.793399
890	104	136	1005	PRESENT	2025-05-21 14:14:00	\N		\N	2025-08-27 20:57:54.7934	2025-08-27 20:57:54.7934
891	98	136	1006	PRESENT	2025-05-21 14:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.7934	2025-08-27 20:57:54.793401
892	102	136	1007	LATE	2025-05-21 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793401	2025-08-27 20:57:54.793402
893	105	136	1008	PRESENT	2025-05-21 14:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793402	2025-08-27 20:57:54.793403
894	101	137	1010	PRESENT	2025-05-23 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793403	2025-08-27 20:57:54.793403
895	102	137	1011	PRESENT	2025-05-23 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793404	2025-08-27 20:57:54.793404
896	98	137	1012	PRESENT	2025-05-23 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793405	2025-08-27 20:57:54.793405
897	97	137	1013	LATE	2025-05-23 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793406	2025-08-27 20:57:54.793406
898	99	137	1015	PRESENT	2025-05-23 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793407	2025-08-27 20:57:54.793407
899	103	137	1016	PRESENT	2025-05-23 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793407	2025-08-27 20:57:54.793408
900	101	138	1018	PRESENT	2025-05-26 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793408	2025-08-27 20:57:54.793409
901	106	138	1019	PRESENT	2025-05-26 09:07:00	\N		\N	2025-08-27 20:57:54.793409	2025-08-27 20:57:54.79341
902	97	138	1020	PRESENT	2025-05-26 09:05:00	\N		\N	2025-08-27 20:57:54.79341	2025-08-27 20:57:54.79341
903	98	138	1021	PRESENT	2025-05-26 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793411	2025-08-27 20:57:54.793411
904	104	138	1022	PRESENT	2025-05-26 09:03:00	\N		\N	2025-08-27 20:57:54.793412	2025-08-27 20:57:54.793412
905	99	138	1023	PRESENT	2025-05-26 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793413	2025-08-27 20:57:54.793413
906	97	139	1024	PRESENT	2025-05-28 14:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793414	2025-08-27 20:57:54.793414
907	101	139	1025	PRESENT	2025-05-28 14:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793414	2025-08-27 20:57:54.793415
908	106	139	1026	PRESENT	2025-05-28 14:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793415	2025-08-27 20:57:54.793416
909	103	139	1027	LATE	2025-05-28 14:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793416	2025-08-27 20:57:54.793417
910	105	139	1028	LATE	2025-05-28 14:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793417	2025-08-27 20:57:54.793418
911	99	139	1029	PRESENT	2025-05-28 14:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793418	2025-08-27 20:57:54.793418
912	100	139	1030	PRESENT	2025-05-28 14:06:00	\N		\N	2025-08-27 20:57:54.793419	2025-08-27 20:57:54.793419
913	104	140	1031	PRESENT	2025-06-06 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.79342	2025-08-27 20:57:54.79342
914	103	140	1032	PRESENT	2025-06-06 09:12:00	\N		\N	2025-08-27 20:57:54.793421	2025-08-27 20:57:54.793421
915	100	140	1033	PRESENT	2025-06-06 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793422	2025-08-27 20:57:54.793422
916	97	140	1034	PRESENT	2025-06-06 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793422	2025-08-27 20:57:54.793423
917	105	140	1035	PRESENT	2025-06-06 09:14:00	\N		\N	2025-08-27 20:57:54.793423	2025-08-27 20:57:54.793424
918	101	140	1036	LATE	2025-06-06 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793424	2025-08-27 20:57:54.793425
919	102	140	1037	PRESENT	2025-06-06 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793425	2025-08-27 20:57:54.793425
920	99	140	1038	PRESENT	2025-06-06 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793426	2025-08-27 20:57:54.793426
921	98	140	1039	PRESENT	2025-06-06 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793427	2025-08-27 20:57:54.793427
922	98	141	1040	LATE	2025-06-02 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793428	2025-08-27 20:57:54.793428
923	106	141	1041	LATE	2025-06-02 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793429	2025-08-27 20:57:54.793429
924	102	141	1042	LATE	2025-06-02 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793429	2025-08-27 20:57:54.79343
925	101	141	1043	PRESENT	2025-06-02 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.79343	2025-08-27 20:57:54.793431
926	105	141	1044	PRESENT	2025-06-02 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793431	2025-08-27 20:57:54.793432
927	104	141	1045	PRESENT	2025-06-02 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793432	2025-08-27 20:57:54.793432
928	100	141	1046	PRESENT	2025-06-02 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793433	2025-08-27 20:57:54.793433
929	97	141	1047	PRESENT	2025-06-02 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793434	2025-08-27 20:57:54.793434
930	106	142	1048	PRESENT	2025-06-04 14:09:00	\N		\N	2025-08-27 20:57:54.793435	2025-08-27 20:57:54.793435
931	105	142	1049	PRESENT	2025-06-04 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793436	2025-08-27 20:57:54.793436
932	99	142	1051	PRESENT	2025-06-04 14:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793436	2025-08-27 20:57:54.793437
933	103	142	1052	LATE	2025-06-04 14:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793437	2025-08-27 20:57:54.793438
934	102	142	1053	PRESENT	2025-06-04 14:15:00	\N		\N	2025-08-27 20:57:54.793438	2025-08-27 20:57:54.793439
935	101	142	1054	PRESENT	2025-06-04 14:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793439	2025-08-27 20:57:54.793439
936	103	143	1055	PRESENT	2025-07-02 09:11:00	\N		\N	2025-08-27 20:57:54.79344	2025-08-27 20:57:54.79344
937	98	143	1056	PRESENT	2025-07-02 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793441	2025-08-27 20:57:54.793441
938	105	143	1057	PRESENT	2025-07-02 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793442	2025-08-27 20:57:54.793442
939	100	143	1059	LATE	2025-07-02 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793443	2025-08-27 20:57:54.793443
940	106	143	1060	PRESENT	2025-07-02 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793443	2025-08-27 20:57:54.793444
941	102	143	1061	LATE	2025-07-02 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793444	2025-08-27 20:57:54.793445
942	99	143	1062	PRESENT	2025-07-02 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793445	2025-08-27 20:57:54.793446
943	102	144	1063	PRESENT	2025-07-04 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793446	2025-08-27 20:57:54.793447
944	106	144	1064	LATE	2025-07-04 09:04:00	\N		\N	2025-08-27 20:57:54.793447	2025-08-27 20:57:54.793447
945	97	144	1065	PRESENT	2025-07-04 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793448	2025-08-27 20:57:54.793448
946	104	144	1066	PRESENT	2025-07-04 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793449	2025-08-27 20:57:54.793449
947	98	144	1067	PRESENT	2025-07-04 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.79345	2025-08-27 20:57:54.79345
948	105	144	1069	LATE	2025-07-04 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793451	2025-08-27 20:57:54.793451
949	100	144	1070	PRESENT	2025-07-04 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793451	2025-08-27 20:57:54.793452
950	105	145	1071	PRESENT	2025-07-09 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793452	2025-08-27 20:57:54.793453
951	101	145	1072	PRESENT	2025-07-09 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793453	2025-08-27 20:57:54.793454
952	99	145	1073	PRESENT	2025-07-09 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793454	2025-08-27 20:57:54.793454
953	102	145	1074	PRESENT	2025-07-09 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793455	2025-08-27 20:57:54.793455
954	98	145	1075	PRESENT	2025-07-09 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793456	2025-08-27 20:57:54.793456
955	106	145	1076	PRESENT	2025-07-09 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793457	2025-08-27 20:57:54.793457
956	104	145	1077	PRESENT	2025-07-09 09:03:00	\N		\N	2025-08-27 20:57:54.793458	2025-08-27 20:57:54.793458
957	97	145	1078	LATE	2025-07-09 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793459	2025-08-27 20:57:54.793459
958	103	146	1079	PRESENT	2025-07-11 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793459	2025-08-27 20:57:54.79346
959	98	146	1080	PRESENT	2025-07-11 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.79346	2025-08-27 20:57:54.793461
960	100	146	1081	PRESENT	2025-07-11 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793461	2025-08-27 20:57:54.793462
961	101	146	1082	PRESENT	2025-07-11 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793462	2025-08-27 20:57:54.793463
962	104	146	1083	LATE	2025-07-11 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793463	2025-08-27 20:57:54.793463
963	102	146	1084	PRESENT	2025-07-11 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793464	2025-08-27 20:57:54.793464
964	97	146	1085	PRESENT	2025-07-11 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793465	2025-08-27 20:57:54.793465
965	105	146	1086	LATE	2025-07-11 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793466	2025-08-27 20:57:54.793466
966	103	147	1087	PRESENT	2025-07-16 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793467	2025-08-27 20:57:54.793467
967	106	147	1088	PRESENT	2025-07-16 09:07:00	\N	Participated actively	\N	2025-08-27 20:57:54.793467	2025-08-27 20:57:54.793468
968	105	147	1089	LATE	2025-07-16 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793468	2025-08-27 20:57:54.793469
969	99	147	1090	PRESENT	2025-07-16 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793469	2025-08-27 20:57:54.79347
970	97	147	1091	PRESENT	2025-07-16 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.79347	2025-08-27 20:57:54.79347
971	102	147	1092	LATE	2025-07-16 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793471	2025-08-27 20:57:54.793471
972	100	147	1093	PRESENT	2025-07-16 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793472	2025-08-27 20:57:54.793472
973	100	148	1094	LATE	2025-07-18 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793473	2025-08-27 20:57:54.793473
974	101	148	1096	PRESENT	2025-07-18 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793474	2025-08-27 20:57:54.793474
975	105	148	1097	PRESENT	2025-07-18 09:15:00	\N		\N	2025-08-27 20:57:54.793475	2025-08-27 20:57:54.793475
976	102	148	1098	PRESENT	2025-07-18 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793476	2025-08-27 20:57:54.793476
977	98	148	1099	PRESENT	2025-07-18 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793476	2025-08-27 20:57:54.793477
978	104	149	1101	LATE	2025-07-23 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793477	2025-08-27 20:57:54.793478
979	97	149	1102	PRESENT	2025-07-23 09:06:00	\N		\N	2025-08-27 20:57:54.793478	2025-08-27 20:57:54.793479
980	105	149	1103	PRESENT	2025-07-23 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793479	2025-08-27 20:57:54.79348
981	106	149	1104	LATE	2025-07-23 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.79348	2025-08-27 20:57:54.79348
982	98	149	1105	PRESENT	2025-07-23 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793481	2025-08-27 20:57:54.793481
983	102	149	1106	PRESENT	2025-07-23 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793482	2025-08-27 20:57:54.793482
984	101	149	1107	PRESENT	2025-07-23 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793483	2025-08-27 20:57:54.793483
985	103	150	1108	LATE	2025-07-25 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793484	2025-08-27 20:57:54.793484
986	101	150	1109	PRESENT	2025-07-25 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793484	2025-08-27 20:57:54.793485
987	100	150	1110	PRESENT	2025-07-25 09:12:00	\N		\N	2025-08-27 20:57:54.793485	2025-08-27 20:57:54.793486
988	106	150	1111	PRESENT	2025-07-25 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793486	2025-08-27 20:57:54.793487
989	105	150	1112	LATE	2025-07-25 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793487	2025-08-27 20:57:54.793488
990	102	150	1113	PRESENT	2025-07-25 09:15:00	\N		\N	2025-08-27 20:57:54.793488	2025-08-27 20:57:54.793488
991	104	150	1114	LATE	2025-07-25 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793489	2025-08-27 20:57:54.793489
992	97	150	1115	PRESENT	2025-07-25 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.79349	2025-08-27 20:57:54.79349
993	101	151	1116	LATE	2025-07-30 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793491	2025-08-27 20:57:54.793491
994	104	151	1117	LATE	2025-07-30 09:15:00	\N		\N	2025-08-27 20:57:54.793492	2025-08-27 20:57:54.793492
995	97	151	1118	PRESENT	2025-07-30 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793492	2025-08-27 20:57:54.793493
996	106	151	1119	PRESENT	2025-07-30 09:08:00	\N		\N	2025-08-27 20:57:54.793493	2025-08-27 20:57:54.793494
997	100	151	1121	LATE	2025-07-30 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793494	2025-08-27 20:57:54.793495
998	102	151	1122	PRESENT	2025-07-30 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793495	2025-08-27 20:57:54.793495
999	98	151	1123	PRESENT	2025-07-30 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793496	2025-08-27 20:57:54.793496
1000	105	152	1124	PRESENT	2025-08-01 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793497	2025-08-27 20:57:54.793497
1001	101	152	1126	LATE	2025-08-01 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793498	2025-08-27 20:57:54.793498
1002	98	152	1127	PRESENT	2025-08-01 09:09:00	\N		\N	2025-08-27 20:57:54.793499	2025-08-27 20:57:54.793499
1003	97	152	1128	LATE	2025-08-01 09:08:00	\N		\N	2025-08-27 20:57:54.7935	2025-08-27 20:57:54.7935
1004	100	152	1129	PRESENT	2025-08-01 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.7935	2025-08-27 20:57:54.793501
1005	102	152	1130	LATE	2025-08-01 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793501	2025-08-27 20:57:54.793502
1006	99	152	1131	PRESENT	2025-08-01 09:10:00	\N		\N	2025-08-27 20:57:54.793502	2025-08-27 20:57:54.793503
1007	104	152	1132	PRESENT	2025-08-01 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793503	2025-08-27 20:57:54.793504
1008	98	153	1133	LATE	2025-08-06 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793504	2025-08-27 20:57:54.793504
1009	103	153	1134	LATE	2025-08-06 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793505	2025-08-27 20:57:54.793505
1010	102	153	1135	PRESENT	2025-08-06 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793506	2025-08-27 20:57:54.793506
1011	97	153	1136	PRESENT	2025-08-06 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793507	2025-08-27 20:57:54.793507
1012	100	153	1137	LATE	2025-08-06 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793508	2025-08-27 20:57:54.793508
1013	101	153	1138	PRESENT	2025-08-06 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793509	2025-08-27 20:57:54.793509
1014	99	153	1139	PRESENT	2025-08-06 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793509	2025-08-27 20:57:54.79351
1015	98	154	1140	LATE	2025-08-08 09:01:00	\N		\N	2025-08-27 20:57:54.79351	2025-08-27 20:57:54.793511
1016	100	154	1141	PRESENT	2025-08-08 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793511	2025-08-27 20:57:54.793512
1017	101	154	1142	LATE	2025-08-08 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793512	2025-08-27 20:57:54.793513
1018	97	154	1143	LATE	2025-08-08 09:10:00	\N		\N	2025-08-27 20:57:54.793513	2025-08-27 20:57:54.793513
1019	99	154	1144	PRESENT	2025-08-08 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793514	2025-08-27 20:57:54.793514
1020	106	154	1145	PRESENT	2025-08-08 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793515	2025-08-27 20:57:54.793515
1021	104	154	1146	LATE	2025-08-08 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793516	2025-08-27 20:57:54.793516
1022	105	154	1147	PRESENT	2025-08-08 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.793517	2025-08-27 20:57:54.793517
1023	104	155	1148	PRESENT	2025-08-13 09:11:00	\N	Participated actively	\N	2025-08-27 20:57:54.793518	2025-08-27 20:57:54.793518
1024	102	155	1149	PRESENT	2025-08-13 09:00:00	\N		\N	2025-08-27 20:57:54.793518	2025-08-27 20:57:54.793519
1025	99	155	1150	LATE	2025-08-13 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.793519	2025-08-27 20:57:54.79352
1026	103	155	1151	PRESENT	2025-08-13 09:06:00	\N	Participated actively	\N	2025-08-27 20:57:54.79352	2025-08-27 20:57:54.793521
1027	98	155	1152	LATE	2025-08-13 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793521	2025-08-27 20:57:54.793521
1028	100	155	1153	LATE	2025-08-13 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793522	2025-08-27 20:57:54.793522
1029	106	155	1154	PRESENT	2025-08-13 09:02:00	\N	Participated actively	\N	2025-08-27 20:57:54.793523	2025-08-27 20:57:54.793523
1030	101	155	1155	PRESENT	2025-08-13 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793524	2025-08-27 20:57:54.793524
1031	101	156	1156	LATE	2025-08-15 09:14:00	\N		\N	2025-08-27 20:57:54.793525	2025-08-27 20:57:54.793525
1032	104	156	1157	LATE	2025-08-15 09:00:00	\N		\N	2025-08-27 20:57:54.793525	2025-08-27 20:57:54.793526
1033	100	156	1158	PRESENT	2025-08-15 09:04:00	\N	Participated actively	\N	2025-08-27 20:57:54.793526	2025-08-27 20:57:54.793527
1034	99	156	1159	PRESENT	2025-08-15 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793527	2025-08-27 20:57:54.793528
1035	102	156	1161	PRESENT	2025-08-15 09:14:00	\N		\N	2025-08-27 20:57:54.793528	2025-08-27 20:57:54.793528
1036	98	156	1162	LATE	2025-08-15 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793529	2025-08-27 20:57:54.793529
1037	103	156	1163	PRESENT	2025-08-15 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.79353	2025-08-27 20:57:54.79353
1038	106	157	1164	PRESENT	2025-08-20 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793531	2025-08-27 20:57:54.793531
1039	105	157	1166	PRESENT	2025-08-20 09:10:00	\N	Participated actively	\N	2025-08-27 20:57:54.793532	2025-08-27 20:57:54.793532
1040	97	157	1167	PRESENT	2025-08-20 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793532	2025-08-27 20:57:54.793533
1041	99	157	1168	PRESENT	2025-08-20 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793533	2025-08-27 20:57:54.793534
1042	102	157	1170	PRESENT	2025-08-20 09:08:00	\N		\N	2025-08-27 20:57:54.793534	2025-08-27 20:57:54.793535
1043	103	157	1171	LATE	2025-08-20 09:05:00	\N		\N	2025-08-27 20:57:54.793535	2025-08-27 20:57:54.793536
1044	104	158	1172	PRESENT	2025-08-22 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793536	2025-08-27 20:57:54.793536
1045	105	158	1173	PRESENT	2025-08-22 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793537	2025-08-27 20:57:54.793537
1046	99	158	1174	LATE	2025-08-22 09:15:00	\N	Participated actively	\N	2025-08-27 20:57:54.793538	2025-08-27 20:57:54.793538
1047	98	158	1175	PRESENT	2025-08-22 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793539	2025-08-27 20:57:54.793539
1048	102	158	1176	LATE	2025-08-22 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793539	2025-08-27 20:57:54.79354
1049	97	158	1177	PRESENT	2025-08-22 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.79354	2025-08-27 20:57:54.793541
1050	106	158	1178	LATE	2025-08-22 09:15:00	\N		\N	2025-08-27 20:57:54.793541	2025-08-27 20:57:54.793542
1051	103	158	1179	PRESENT	2025-08-22 09:00:00	\N		\N	2025-08-27 20:57:54.793542	2025-08-27 20:57:54.793543
1052	106	159	1180	PRESENT	2025-08-20 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793543	2025-08-27 20:57:54.793543
1053	102	159	1181	LATE	2025-08-20 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793544	2025-08-27 20:57:54.793544
1054	105	159	1182	PRESENT	2025-08-20 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793545	2025-08-27 20:57:54.793545
1055	99	159	1184	LATE	2025-08-20 09:09:00	\N	Participated actively	\N	2025-08-27 20:57:54.793546	2025-08-27 20:57:54.793546
1056	100	159	1185	PRESENT	2025-08-20 09:12:00	\N	Participated actively	\N	2025-08-27 20:57:54.793547	2025-08-27 20:57:54.793547
1057	97	159	1186	PRESENT	2025-08-20 09:00:00	\N	Participated actively	\N	2025-08-27 20:57:54.793547	2025-08-27 20:57:54.793548
1058	103	159	1187	PRESENT	2025-08-20 09:14:00	\N	Participated actively	\N	2025-08-27 20:57:54.793548	2025-08-27 20:57:54.793549
1059	98	160	1188	LATE	2025-08-22 09:13:00	\N	Participated actively	\N	2025-08-27 20:57:54.793549	2025-08-27 20:57:54.79355
1060	104	160	1189	PRESENT	2025-08-22 09:05:00	\N	Participated actively	\N	2025-08-27 20:57:54.79355	2025-08-27 20:57:54.79355
1061	101	160	1190	PRESENT	2025-08-22 09:01:00	\N	Participated actively	\N	2025-08-27 20:57:54.793551	2025-08-27 20:57:54.793551
1062	103	160	1191	PRESENT	2025-08-22 09:01:00	\N		\N	2025-08-27 20:57:54.793552	2025-08-27 20:57:54.793552
1063	102	160	1192	PRESENT	2025-08-22 09:03:00	\N	Participated actively	\N	2025-08-27 20:57:54.793553	2025-08-27 20:57:54.793553
1064	100	160	1193	PRESENT	2025-08-22 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793554	2025-08-27 20:57:54.793554
1065	99	160	1194	PRESENT	2025-08-22 09:08:00	\N	Participated actively	\N	2025-08-27 20:57:54.793554	2025-08-27 20:57:54.793555
1066	106	160	1195	PRESENT	2025-08-22 09:03:00	\N		\N	2025-08-27 20:57:54.793555	2025-08-27 20:57:54.793556
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.bookings (id, user_id, session_id, status, waitlist_position, notes, created_at, updated_at, cancelled_at, attended_status) FROM stdin;
1196	2	163	CONFIRMED	\N	\N	2025-08-31 15:04:13.411329	2025-08-31 15:04:13.41133	\N	\N
1197	97	161	CANCELLED	\N	Testing auto-promotion	2025-08-31 19:25:06.556249	2025-08-31 21:25:28.41994	2025-08-31 19:25:28.414198	\N
1198	98	161	CANCELLED	\N	Testing second auto-promotion	2025-08-31 19:25:06.556321	2025-08-31 21:26:19.725826	2025-08-31 19:26:19.72445	\N
1199	99	161	CANCELLED	\N	Testing empty waitlist	2025-08-31 19:25:06.556348	2025-08-31 21:26:57.204882	2025-08-31 19:26:57.2042	\N
1201	97	163	CONFIRMED	\N	\N	2025-09-02 14:10:38.11803	2025-09-02 14:10:38.118039	\N	\N
1204	109	170	CONFIRMED	\N	\N	2025-09-06 10:15:38.260907	2025-09-06 10:15:38.26091	\N	present
1205	109	171	CONFIRMED	\N	\N	2025-09-06 10:15:38.260911	2025-09-06 10:15:38.260911	\N	present
1206	109	172	CONFIRMED	\N	\N	2025-09-06 10:15:38.260912	2025-09-06 10:15:38.260913	\N	\N
1207	109	173	CONFIRMED	\N	\N	2025-09-06 10:15:38.260913	2025-09-06 10:15:38.260914	\N	\N
1213	109	184	CONFIRMED	\N	\N	2025-09-06 13:57:25.98787	2025-09-06 13:57:25.987872	\N	\N
1214	110	184	CONFIRMED	\N	\N	2025-09-06 13:57:41.201082	2025-09-06 13:57:41.201083	\N	\N
1203	97	169	CANCELLED	\N	\N	2025-09-02 17:46:22.466092	2025-09-06 18:48:28.044577	2025-09-06 18:48:28.039788	\N
1246	97	169	CANCELLED	\N	\N	2025-09-06 18:54:31.30107	2025-09-06 18:54:35.709626	2025-09-06 18:54:35.704285	\N
1249	97	169	CANCELLED	\N	\N	2025-09-06 19:04:15.766638	2025-09-06 19:04:37.648105	2025-09-06 19:04:37.645782	\N
1251	97	169	CANCELLED	\N	\N	2025-09-06 19:06:32.858585	2025-09-06 19:12:17.997917	2025-09-06 19:12:17.99116	\N
1285	97	169	CONFIRMED	\N	\N	2025-09-06 19:16:16.822424	2025-09-06 19:16:16.822428	\N	\N
1286	97	219	CONFIRMED	\N	\N	2025-09-06 21:27:20.07039	\N	\N	\N
1287	97	221	CONFIRMED	\N	\N	2025-09-06 21:27:20.07039	\N	\N	\N
1290	97	223	CONFIRMED	\N	Live session for testing check-in	2025-09-07 07:20:30.80421	2025-09-07 07:20:30.804212	\N	\N
1291	106	226	CONFIRMED	\N	\N	2025-09-07 08:57:49.829347	2025-09-07 08:57:49.829352	\N	\N
1292	113	169	WAITLISTED	1	\N	2025-09-08 16:19:13.670398	2025-09-08 16:19:13.670401	\N	\N
1293	113	227	CONFIRMED	\N	\N	2025-09-09 17:56:25.461332	2025-09-09 17:56:25.461335	\N	\N
1294	114	169	CANCELLED	2	Test booking	2025-09-09 22:56:32.413425	2025-09-09 22:56:51.612152	2025-09-09 22:56:51.611149	\N
1200	98	161	CANCELLED	1	Testing waitlisted cancellation	2025-08-31 19:27:05.927492	2025-08-31 21:27:17.26272	2025-08-31 19:27:17.262555	\N
1202	97	168	CONFIRMED	\N	\N	2025-09-02 14:10:42.904285	2025-09-02 14:10:42.904291	\N	\N
1208	109	175	CONFIRMED	\N	\N	2025-09-03 13:05:38.856232	2025-09-06 13:05:38.857302	\N	\N
1247	97	169	CANCELLED	\N	\N	2025-09-06 18:55:23.067233	2025-09-06 18:59:40.009382	2025-09-06 18:59:40.003414	\N
1248	97	169	CANCELLED	\N	\N	2025-09-06 19:01:44.947897	2025-09-06 19:01:52.136489	2025-09-06 19:01:52.132711	\N
1250	97	169	CANCELLED	\N	\N	2025-09-06 19:06:20.044907	2025-09-06 19:06:31.346388	2025-09-06 19:06:31.342063	\N
1209	109	176	CONFIRMED	\N	\N	2025-09-06 13:08:44.936074	2025-09-06 13:08:44.936077	\N	\N
1252	97	169	CANCELLED	\N	\N	2025-09-06 19:12:48.778713	2025-09-06 19:12:53.128998	2025-09-06 19:12:53.126249	\N
1289	97	222	CONFIRMED	\N	\N	2025-09-06 23:04:51.154805	\N	\N	\N
851	97	117	CONFIRMED	\N	Enrolled for Web Development Fundamentals	2025-02-22 09:00:00	2025-08-27 20:57:54.750751	\N	\N
852	103	117	CONFIRMED	\N	Enrolled for Web Development Fundamentals	2025-02-28 09:00:00	2025-08-27 20:57:54.750754	\N	\N
853	105	117	CONFIRMED	\N	Enrolled for Web Development Fundamentals	2025-02-27 09:00:00	2025-08-27 20:57:54.750755	\N	\N
854	102	117	CONFIRMED	\N	Enrolled for Web Development Fundamentals	2025-02-28 09:00:00	2025-08-27 20:57:54.750756	\N	\N
855	99	117	WAITLISTED	\N	Enrolled for Web Development Fundamentals	2025-02-24 09:00:00	2025-08-27 20:57:54.750756	\N	\N
856	104	117	WAITLISTED	\N	Enrolled for Web Development Fundamentals	2025-02-17 09:00:00	2025-08-27 20:57:54.750757	\N	\N
857	101	117	CONFIRMED	\N	Enrolled for Web Development Fundamentals	2025-02-19 09:00:00	2025-08-27 20:57:54.750757	\N	\N
858	98	117	WAITLISTED	\N	Enrolled for Web Development Fundamentals	2025-02-28 09:00:00	2025-08-27 20:57:54.750758	\N	\N
859	100	117	CONFIRMED	\N	Enrolled for Web Development Fundamentals	2025-03-02 09:00:00	2025-08-27 20:57:54.750758	\N	\N
860	106	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-03-01 14:00:00	2025-08-27 20:57:54.750758	\N	\N
861	98	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-02-23 14:00:00	2025-08-27 20:57:54.750759	\N	\N
862	103	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-02-28 14:00:00	2025-08-27 20:57:54.750759	\N	\N
863	105	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-02-19 14:00:00	2025-08-27 20:57:54.75076	\N	\N
864	99	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-03-02 14:00:00	2025-08-27 20:57:54.75076	\N	\N
865	101	118	WAITLISTED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-02-21 14:00:00	2025-08-27 20:57:54.750761	\N	\N
866	100	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-02-27 14:00:00	2025-08-27 20:57:54.750761	\N	\N
867	104	118	CONFIRMED	\N	Enrolled for HTML5 & CSS3 Modern Techniques	2025-02-20 14:00:00	2025-08-27 20:57:54.750762	\N	\N
868	106	119	CONFIRMED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-06 09:00:00	2025-08-27 20:57:54.750762	\N	\N
869	104	119	CONFIRMED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-03 09:00:00	2025-08-27 20:57:54.750762	\N	\N
870	102	119	CONFIRMED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-03 09:00:00	2025-08-27 20:57:54.750763	\N	\N
871	103	119	CONFIRMED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-13 09:00:00	2025-08-27 20:57:54.750763	\N	\N
872	101	119	CONFIRMED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-02 09:00:00	2025-08-27 20:57:54.750764	\N	\N
873	100	119	CONFIRMED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-08 09:00:00	2025-08-27 20:57:54.750764	\N	\N
874	99	119	WAITLISTED	\N	Enrolled for JavaScript ES6+ Essentials	2025-03-02 09:00:00	2025-08-27 20:57:54.750765	\N	\N
875	103	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-02-28 09:00:00	2025-08-27 20:57:54.750765	\N	\N
876	99	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-03-04 09:00:00	2025-08-27 20:57:54.750765	\N	\N
877	104	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-03-06 09:00:00	2025-08-27 20:57:54.750766	\N	\N
878	106	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-03-07 09:00:00	2025-08-27 20:57:54.750766	\N	\N
879	98	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-03-02 09:00:00	2025-08-27 20:57:54.750767	\N	\N
880	100	120	WAITLISTED	\N	Enrolled for Git Version Control Workflow	2025-02-25 09:00:00	2025-08-27 20:57:54.750767	\N	\N
881	97	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-02-27 09:00:00	2025-08-27 20:57:54.750768	\N	\N
882	101	120	CONFIRMED	\N	Enrolled for Git Version Control Workflow	2025-03-05 09:00:00	2025-08-27 20:57:54.750768	\N	\N
883	97	121	WAITLISTED	\N	Enrolled for React.js Component Architecture	2025-03-07 14:00:00	2025-08-27 20:57:54.750769	\N	\N
884	104	121	CONFIRMED	\N	Enrolled for React.js Component Architecture	2025-03-08 14:00:00	2025-08-27 20:57:54.750769	\N	\N
885	102	121	WAITLISTED	\N	Enrolled for React.js Component Architecture	2025-03-14 14:00:00	2025-08-27 20:57:54.750769	\N	\N
886	106	121	CONFIRMED	\N	Enrolled for React.js Component Architecture	2025-03-18 14:00:00	2025-08-27 20:57:54.75077	\N	\N
887	105	121	CONFIRMED	\N	Enrolled for React.js Component Architecture	2025-03-16 14:00:00	2025-08-27 20:57:54.75077	\N	\N
888	100	121	CONFIRMED	\N	Enrolled for React.js Component Architecture	2025-03-11 14:00:00	2025-08-27 20:57:54.750771	\N	\N
889	99	121	CONFIRMED	\N	Enrolled for React.js Component Architecture	2025-03-05 14:00:00	2025-08-27 20:57:54.750771	\N	\N
890	105	122	CONFIRMED	\N	Enrolled for State Management with Redux	2025-03-20 09:00:00	2025-08-27 20:57:54.750772	\N	\N
891	99	122	CONFIRMED	\N	Enrolled for State Management with Redux	2025-03-14 09:00:00	2025-08-27 20:57:54.750772	\N	\N
892	106	122	WAITLISTED	\N	Enrolled for State Management with Redux	2025-03-13 09:00:00	2025-08-27 20:57:54.750772	\N	\N
893	98	122	WAITLISTED	\N	Enrolled for State Management with Redux	2025-03-14 09:00:00	2025-08-27 20:57:54.750773	\N	\N
894	101	122	CONFIRMED	\N	Enrolled for State Management with Redux	2025-03-14 09:00:00	2025-08-27 20:57:54.750773	\N	\N
895	104	122	CONFIRMED	\N	Enrolled for State Management with Redux	2025-03-14 09:00:00	2025-08-27 20:57:54.750774	\N	\N
896	103	122	CONFIRMED	\N	Enrolled for State Management with Redux	2025-03-07 09:00:00	2025-08-27 20:57:54.750774	\N	\N
897	97	122	WAITLISTED	\N	Enrolled for State Management with Redux	2025-03-08 09:00:00	2025-08-27 20:57:54.750775	\N	\N
898	99	123	CONFIRMED	\N	Enrolled for Vue.js Alternative Framework	2025-03-11 09:00:00	2025-08-27 20:57:54.750775	\N	\N
899	98	123	CONFIRMED	\N	Enrolled for Vue.js Alternative Framework	2025-03-17 09:00:00	2025-08-27 20:57:54.750776	\N	\N
900	97	123	WAITLISTED	\N	Enrolled for Vue.js Alternative Framework	2025-03-23 09:00:00	2025-08-27 20:57:54.750776	\N	\N
901	103	123	CONFIRMED	\N	Enrolled for Vue.js Alternative Framework	2025-03-18 09:00:00	2025-08-27 20:57:54.750776	\N	\N
902	100	123	WAITLISTED	\N	Enrolled for Vue.js Alternative Framework	2025-03-17 09:00:00	2025-08-27 20:57:54.750777	\N	\N
903	101	123	WAITLISTED	\N	Enrolled for Vue.js Alternative Framework	2025-03-20 09:00:00	2025-08-27 20:57:54.750777	\N	\N
904	106	123	CONFIRMED	\N	Enrolled for Vue.js Alternative Framework	2025-03-18 09:00:00	2025-08-27 20:57:54.750778	\N	\N
905	102	123	CONFIRMED	\N	Enrolled for Vue.js Alternative Framework	2025-03-20 09:00:00	2025-08-27 20:57:54.750778	\N	\N
906	100	124	WAITLISTED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-14 14:00:00	2025-08-27 20:57:54.750779	\N	\N
907	99	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-17 14:00:00	2025-08-27 20:57:54.750779	\N	\N
908	104	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-18 14:00:00	2025-08-27 20:57:54.75078	\N	\N
909	97	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-13 14:00:00	2025-08-27 20:57:54.75078	\N	\N
910	106	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-23 14:00:00	2025-08-27 20:57:54.75078	\N	\N
911	105	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-24 14:00:00	2025-08-27 20:57:54.750781	\N	\N
912	101	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-20 14:00:00	2025-08-27 20:57:54.750781	\N	\N
913	102	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-20 14:00:00	2025-08-27 20:57:54.750782	\N	\N
914	98	124	CONFIRMED	\N	Enrolled for Responsive Design & Bootstrap	2025-03-13 14:00:00	2025-08-27 20:57:54.750782	\N	\N
915	98	125	CONFIRMED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-03-26 09:00:00	2025-08-27 20:57:54.750783	\N	\N
916	104	125	CONFIRMED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-03-29 09:00:00	2025-08-27 20:57:54.750783	\N	\N
917	103	125	WAITLISTED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-03-25 09:00:00	2025-08-27 20:57:54.750783	\N	\N
918	99	125	CONFIRMED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-03-24 09:00:00	2025-08-27 20:57:54.750784	\N	\N
919	100	125	WAITLISTED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-03-30 09:00:00	2025-08-27 20:57:54.750784	\N	\N
920	106	125	WAITLISTED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-04-01 09:00:00	2025-08-27 20:57:54.750785	\N	\N
921	101	125	CONFIRMED	\N	Enrolled for Frontend Testing (Jest, Cypress)	2025-03-22 09:00:00	2025-08-27 20:57:54.750785	\N	\N
922	105	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-03-29 09:00:00	2025-08-27 20:57:54.750786	\N	\N
923	98	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-03-28 09:00:00	2025-08-27 20:57:54.750786	\N	\N
924	102	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-04-02 09:00:00	2025-08-27 20:57:54.750786	\N	\N
925	99	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-04-03 09:00:00	2025-08-27 20:57:54.750787	\N	\N
926	106	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-04-06 09:00:00	2025-08-27 20:57:54.750787	\N	\N
927	100	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-03-28 09:00:00	2025-08-27 20:57:54.750788	\N	\N
928	103	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-04-02 09:00:00	2025-08-27 20:57:54.750788	\N	\N
929	101	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-03-25 09:00:00	2025-08-27 20:57:54.750789	\N	\N
930	97	126	CONFIRMED	\N	Enrolled for Node.js Server Development	2025-04-06 09:00:00	2025-08-27 20:57:54.750789	\N	\N
931	106	127	WAITLISTED	\N	Enrolled for Express.js API Design	2025-04-03 14:00:00	2025-08-27 20:57:54.750789	\N	\N
932	103	127	CONFIRMED	\N	Enrolled for Express.js API Design	2025-03-27 14:00:00	2025-08-27 20:57:54.75079	\N	\N
933	97	127	CONFIRMED	\N	Enrolled for Express.js API Design	2025-04-06 14:00:00	2025-08-27 20:57:54.75079	\N	\N
934	99	127	CONFIRMED	\N	Enrolled for Express.js API Design	2025-04-03 14:00:00	2025-08-27 20:57:54.750791	\N	\N
935	102	127	CONFIRMED	\N	Enrolled for Express.js API Design	2025-03-31 14:00:00	2025-08-27 20:57:54.750791	\N	\N
936	100	127	CONFIRMED	\N	Enrolled for Express.js API Design	2025-04-06 14:00:00	2025-08-27 20:57:54.750792	\N	\N
937	101	127	CONFIRMED	\N	Enrolled for Express.js API Design	2025-03-31 14:00:00	2025-08-27 20:57:54.750792	\N	\N
938	102	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-16 09:00:00	2025-08-27 20:57:54.750792	\N	\N
939	100	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-13 09:00:00	2025-08-27 20:57:54.750793	\N	\N
940	106	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-08 09:00:00	2025-08-27 20:57:54.750793	\N	\N
941	97	128	WAITLISTED	\N	Enrolled for Database Design & PostgreSQL	2025-04-09 09:00:00	2025-08-27 20:57:54.750794	\N	\N
942	101	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-10 09:00:00	2025-08-27 20:57:54.750794	\N	\N
1212	109	181	CONFIRMED	\N	\N	2025-09-06 13:16:19.028266	2025-09-06 13:16:19.028268	\N	\N
943	105	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-06 09:00:00	2025-08-27 20:57:54.750795	\N	\N
944	103	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-13 09:00:00	2025-08-27 20:57:54.750795	\N	\N
945	98	128	CONFIRMED	\N	Enrolled for Database Design & PostgreSQL	2025-04-08 09:00:00	2025-08-27 20:57:54.750795	\N	\N
946	102	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-09 09:00:00	2025-08-27 20:57:54.750796	\N	\N
947	104	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-05 09:00:00	2025-08-27 20:57:54.750796	\N	\N
948	105	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-05 09:00:00	2025-08-27 20:57:54.750797	\N	\N
949	98	129	WAITLISTED	\N	Enrolled for Authentication & JWT Security	2025-04-04 09:00:00	2025-08-27 20:57:54.750797	\N	\N
950	101	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-13 09:00:00	2025-08-27 20:57:54.750798	\N	\N
951	100	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-02 09:00:00	2025-08-27 20:57:54.750798	\N	\N
952	97	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-03 09:00:00	2025-08-27 20:57:54.750798	\N	\N
953	99	129	CONFIRMED	\N	Enrolled for Authentication & JWT Security	2025-04-04 09:00:00	2025-08-27 20:57:54.750799	\N	\N
954	98	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-09 14:00:00	2025-08-27 20:57:54.750799	\N	\N
955	99	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-16 14:00:00	2025-08-27 20:57:54.7508	\N	\N
956	100	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-19 14:00:00	2025-08-27 20:57:54.7508	\N	\N
957	103	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-18 14:00:00	2025-08-27 20:57:54.750801	\N	\N
958	101	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-15 14:00:00	2025-08-27 20:57:54.750801	\N	\N
959	104	130	WAITLISTED	\N	Enrolled for RESTful API Best Practices	2025-04-17 14:00:00	2025-08-27 20:57:54.750801	\N	\N
960	105	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-21 14:00:00	2025-08-27 20:57:54.750802	\N	\N
961	97	130	CONFIRMED	\N	Enrolled for RESTful API Best Practices	2025-04-10 14:00:00	2025-08-27 20:57:54.750802	\N	\N
962	102	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-26 09:00:00	2025-08-27 20:57:54.750803	\N	\N
963	105	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-19 09:00:00	2025-08-27 20:57:54.750803	\N	\N
964	100	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-24 09:00:00	2025-08-27 20:57:54.750804	\N	\N
965	101	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-18 09:00:00	2025-08-27 20:57:54.750804	\N	\N
966	97	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-20 09:00:00	2025-08-27 20:57:54.750804	\N	\N
967	104	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-20 09:00:00	2025-08-27 20:57:54.750805	\N	\N
968	98	131	CONFIRMED	\N	Enrolled for Python Django Framework	2025-04-28 09:00:00	2025-08-27 20:57:54.750805	\N	\N
969	99	132	WAITLISTED	\N	Enrolled for GraphQL vs REST APIs	2025-04-16 09:00:00	2025-08-27 20:57:54.750806	\N	\N
970	104	132	CONFIRMED	\N	Enrolled for GraphQL vs REST APIs	2025-04-20 09:00:00	2025-08-27 20:57:54.750806	\N	\N
971	106	132	CONFIRMED	\N	Enrolled for GraphQL vs REST APIs	2025-04-24 09:00:00	2025-08-27 20:57:54.750807	\N	\N
972	97	132	CONFIRMED	\N	Enrolled for GraphQL vs REST APIs	2025-04-14 09:00:00	2025-08-27 20:57:54.750807	\N	\N
973	101	132	WAITLISTED	\N	Enrolled for GraphQL vs REST APIs	2025-04-27 09:00:00	2025-08-27 20:57:54.750807	\N	\N
974	103	132	CONFIRMED	\N	Enrolled for GraphQL vs REST APIs	2025-04-16 09:00:00	2025-08-27 20:57:54.750808	\N	\N
975	102	132	WAITLISTED	\N	Enrolled for GraphQL vs REST APIs	2025-04-23 09:00:00	2025-08-27 20:57:54.750808	\N	\N
976	97	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-04-23 14:00:00	2025-08-27 20:57:54.750809	\N	\N
977	102	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-04-24 14:00:00	2025-08-27 20:57:54.750809	\N	\N
978	105	133	WAITLISTED	\N	Enrolled for Microservices Architecture	2025-04-30 14:00:00	2025-08-27 20:57:54.75081	\N	\N
979	101	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-05-04 14:00:00	2025-08-27 20:57:54.75081	\N	\N
980	99	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-04-30 14:00:00	2025-08-27 20:57:54.75081	\N	\N
981	100	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-05-05 14:00:00	2025-08-27 20:57:54.750811	\N	\N
982	98	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-04-26 14:00:00	2025-08-27 20:57:54.750811	\N	\N
983	106	133	WAITLISTED	\N	Enrolled for Microservices Architecture	2025-04-24 14:00:00	2025-08-27 20:57:54.750812	\N	\N
984	104	133	CONFIRMED	\N	Enrolled for Microservices Architecture	2025-05-01 14:00:00	2025-08-27 20:57:54.750812	\N	\N
985	102	134	CONFIRMED	\N	Enrolled for Docker Containerization	2025-04-25 09:00:00	2025-08-27 20:57:54.750813	\N	\N
986	101	134	WAITLISTED	\N	Enrolled for Docker Containerization	2025-04-27 09:00:00	2025-08-27 20:57:54.750813	\N	\N
987	100	134	CONFIRMED	\N	Enrolled for Docker Containerization	2025-04-26 09:00:00	2025-08-27 20:57:54.750814	\N	\N
988	105	134	WAITLISTED	\N	Enrolled for Docker Containerization	2025-04-29 09:00:00	2025-08-27 20:57:54.750814	\N	\N
989	99	134	CONFIRMED	\N	Enrolled for Docker Containerization	2025-05-05 09:00:00	2025-08-27 20:57:54.750814	\N	\N
990	106	134	CONFIRMED	\N	Enrolled for Docker Containerization	2025-05-02 09:00:00	2025-08-27 20:57:54.750815	\N	\N
991	103	134	CONFIRMED	\N	Enrolled for Docker Containerization	2025-05-02 09:00:00	2025-08-27 20:57:54.750815	\N	\N
992	98	134	WAITLISTED	\N	Enrolled for Docker Containerization	2025-05-06 09:00:00	2025-08-27 20:57:54.750816	\N	\N
993	105	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-04-29 09:00:00	2025-08-27 20:57:54.750816	\N	\N
994	104	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-05-10 09:00:00	2025-08-27 20:57:54.750817	\N	\N
995	98	135	WAITLISTED	\N	Enrolled for AWS Cloud Deployment	2025-05-10 09:00:00	2025-08-27 20:57:54.750817	\N	\N
996	103	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-05-09 09:00:00	2025-08-27 20:57:54.750817	\N	\N
997	100	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-05-01 09:00:00	2025-08-27 20:57:54.750818	\N	\N
998	106	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-05-06 09:00:00	2025-08-27 20:57:54.750818	\N	\N
999	101	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-05-09 09:00:00	2025-08-27 20:57:54.750819	\N	\N
1000	99	135	CONFIRMED	\N	Enrolled for AWS Cloud Deployment	2025-05-04 09:00:00	2025-08-27 20:57:54.750819	\N	\N
1001	106	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-16 14:00:00	2025-08-27 20:57:54.75082	\N	\N
1002	97	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-17 14:00:00	2025-08-27 20:57:54.75082	\N	\N
1003	99	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-11 14:00:00	2025-08-27 20:57:54.75082	\N	\N
1004	100	136	WAITLISTED	\N	Enrolled for Project Planning & Architecture	2025-05-08 14:00:00	2025-08-27 20:57:54.750821	\N	\N
1005	104	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-14 14:00:00	2025-08-27 20:57:54.750821	\N	\N
1006	98	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-13 14:00:00	2025-08-27 20:57:54.750822	\N	\N
1007	102	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-12 14:00:00	2025-08-27 20:57:54.750822	\N	\N
1008	105	136	CONFIRMED	\N	Enrolled for Project Planning & Architecture	2025-05-20 14:00:00	2025-08-27 20:57:54.750823	\N	\N
1009	104	137	CONFIRMED	\N	Enrolled for Agile Development Workshop	2025-05-15 09:00:00	2025-08-27 20:57:54.750823	\N	\N
1010	101	137	CONFIRMED	\N	Enrolled for Agile Development Workshop	2025-05-10 09:00:00	2025-08-27 20:57:54.750823	\N	\N
1011	102	137	WAITLISTED	\N	Enrolled for Agile Development Workshop	2025-05-12 09:00:00	2025-08-27 20:57:54.750824	\N	\N
1012	98	137	WAITLISTED	\N	Enrolled for Agile Development Workshop	2025-05-12 09:00:00	2025-08-27 20:57:54.750824	\N	\N
1013	97	137	CONFIRMED	\N	Enrolled for Agile Development Workshop	2025-05-09 09:00:00	2025-08-27 20:57:54.750825	\N	\N
1014	105	137	CONFIRMED	\N	Enrolled for Agile Development Workshop	2025-05-19 09:00:00	2025-08-27 20:57:54.750825	\N	\N
1015	99	137	CONFIRMED	\N	Enrolled for Agile Development Workshop	2025-05-18 09:00:00	2025-08-27 20:57:54.750826	\N	\N
1016	103	137	WAITLISTED	\N	Enrolled for Agile Development Workshop	2025-05-18 09:00:00	2025-08-27 20:57:54.750826	\N	\N
1017	100	138	WAITLISTED	\N	Enrolled for Code Review & Quality Assurance	2025-05-19 09:00:00	2025-08-27 20:57:54.750826	\N	\N
1018	101	138	CONFIRMED	\N	Enrolled for Code Review & Quality Assurance	2025-05-24 09:00:00	2025-08-27 20:57:54.750827	\N	\N
1019	106	138	CONFIRMED	\N	Enrolled for Code Review & Quality Assurance	2025-05-13 09:00:00	2025-08-27 20:57:54.750827	\N	\N
1020	97	138	CONFIRMED	\N	Enrolled for Code Review & Quality Assurance	2025-05-18 09:00:00	2025-08-27 20:57:54.750828	\N	\N
1021	98	138	WAITLISTED	\N	Enrolled for Code Review & Quality Assurance	2025-05-21 09:00:00	2025-08-27 20:57:54.750828	\N	\N
1022	104	138	CONFIRMED	\N	Enrolled for Code Review & Quality Assurance	2025-05-22 09:00:00	2025-08-27 20:57:54.750829	\N	\N
1023	99	138	CONFIRMED	\N	Enrolled for Code Review & Quality Assurance	2025-05-20 09:00:00	2025-08-27 20:57:54.750829	\N	\N
1024	97	139	WAITLISTED	\N	Enrolled for Unit Testing Best Practices	2025-05-20 14:00:00	2025-08-27 20:57:54.750829	\N	\N
1025	101	139	CONFIRMED	\N	Enrolled for Unit Testing Best Practices	2025-05-24 14:00:00	2025-08-27 20:57:54.75083	\N	\N
1026	106	139	CONFIRMED	\N	Enrolled for Unit Testing Best Practices	2025-05-19 14:00:00	2025-08-27 20:57:54.75083	\N	\N
1027	103	139	CONFIRMED	\N	Enrolled for Unit Testing Best Practices	2025-05-19 14:00:00	2025-08-27 20:57:54.750831	\N	\N
1028	105	139	CONFIRMED	\N	Enrolled for Unit Testing Best Practices	2025-05-20 14:00:00	2025-08-27 20:57:54.750831	\N	\N
1029	99	139	CONFIRMED	\N	Enrolled for Unit Testing Best Practices	2025-05-17 14:00:00	2025-08-27 20:57:54.750832	\N	\N
1030	100	139	WAITLISTED	\N	Enrolled for Unit Testing Best Practices	2025-05-25 14:00:00	2025-08-27 20:57:54.750832	\N	\N
1031	104	140	CONFIRMED	\N	Enrolled for Final Project Presentations	2025-05-27 09:00:00	2025-08-27 20:57:54.750832	\N	\N
1032	103	140	CONFIRMED	\N	Enrolled for Final Project Presentations	2025-05-30 09:00:00	2025-08-27 20:57:54.750833	\N	\N
1033	100	140	CONFIRMED	\N	Enrolled for Final Project Presentations	2025-05-24 09:00:00	2025-08-27 20:57:54.750833	\N	\N
1034	97	140	CONFIRMED	\N	Enrolled for Final Project Presentations	2025-05-24 09:00:00	2025-08-27 20:57:54.750834	\N	\N
1035	105	140	CONFIRMED	\N	Enrolled for Final Project Presentations	2025-05-25 09:00:00	2025-08-27 20:57:54.750834	\N	\N
1036	101	140	WAITLISTED	\N	Enrolled for Final Project Presentations	2025-05-24 09:00:00	2025-08-27 20:57:54.750835	\N	\N
1037	102	140	WAITLISTED	\N	Enrolled for Final Project Presentations	2025-05-29 09:00:00	2025-08-27 20:57:54.750835	\N	\N
1038	99	140	WAITLISTED	\N	Enrolled for Final Project Presentations	2025-05-26 09:00:00	2025-08-27 20:57:54.750835	\N	\N
1039	98	140	CONFIRMED	\N	Enrolled for Final Project Presentations	2025-05-24 09:00:00	2025-08-27 20:57:54.750836	\N	\N
1040	98	141	WAITLISTED	\N	Enrolled for Career Development Workshop	2025-05-23 09:00:00	2025-08-27 20:57:54.750836	\N	\N
1041	106	141	WAITLISTED	\N	Enrolled for Career Development Workshop	2025-05-24 09:00:00	2025-08-27 20:57:54.750837	\N	\N
1042	102	141	CONFIRMED	\N	Enrolled for Career Development Workshop	2025-05-21 09:00:00	2025-08-27 20:57:54.750837	\N	\N
1043	101	141	WAITLISTED	\N	Enrolled for Career Development Workshop	2025-05-30 09:00:00	2025-08-27 20:57:54.750838	\N	\N
1044	105	141	CONFIRMED	\N	Enrolled for Career Development Workshop	2025-05-29 09:00:00	2025-08-27 20:57:54.750838	\N	\N
1045	104	141	WAITLISTED	\N	Enrolled for Career Development Workshop	2025-05-20 09:00:00	2025-08-27 20:57:54.750838	\N	\N
1046	100	141	CONFIRMED	\N	Enrolled for Career Development Workshop	2025-05-31 09:00:00	2025-08-27 20:57:54.750839	\N	\N
1047	97	141	CONFIRMED	\N	Enrolled for Career Development Workshop	2025-05-31 09:00:00	2025-08-27 20:57:54.750839	\N	\N
1048	106	142	WAITLISTED	\N	Enrolled for Industry Networking Event	2025-05-29 14:00:00	2025-08-27 20:57:54.75084	\N	\N
1049	105	142	CONFIRMED	\N	Enrolled for Industry Networking Event	2025-06-01 14:00:00	2025-08-27 20:57:54.75084	\N	\N
1050	104	142	CONFIRMED	\N	Enrolled for Industry Networking Event	2025-05-25 14:00:00	2025-08-27 20:57:54.750841	\N	\N
1051	99	142	CONFIRMED	\N	Enrolled for Industry Networking Event	2025-05-24 14:00:00	2025-08-27 20:57:54.750841	\N	\N
1052	103	142	CONFIRMED	\N	Enrolled for Industry Networking Event	2025-06-03 14:00:00	2025-08-27 20:57:54.750841	\N	\N
1053	102	142	CONFIRMED	\N	Enrolled for Industry Networking Event	2025-05-28 14:00:00	2025-08-27 20:57:54.750842	\N	\N
1054	101	142	CONFIRMED	\N	Enrolled for Industry Networking Event	2025-06-01 14:00:00	2025-08-27 20:57:54.750842	\N	\N
1055	103	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-24 09:00:00	2025-08-27 20:57:54.750843	\N	\N
1056	98	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-26 09:00:00	2025-08-27 20:57:54.750843	\N	\N
1057	105	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-25 09:00:00	2025-08-27 20:57:54.750844	\N	\N
1058	97	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-20 09:00:00	2025-08-27 20:57:54.750844	\N	\N
1059	100	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-18 09:00:00	2025-08-27 20:57:54.750844	\N	\N
1060	106	143	WAITLISTED	\N	Enrolled for Real Client Project Briefing	2025-06-27 09:00:00	2025-08-27 20:57:54.750845	\N	\N
1061	102	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-26 09:00:00	2025-08-27 20:57:54.750845	\N	\N
1062	99	143	CONFIRMED	\N	Enrolled for Real Client Project Briefing	2025-06-24 09:00:00	2025-08-27 20:57:54.750846	\N	\N
1063	102	144	CONFIRMED	\N	Enrolled for Technical Requirements Analysis	2025-06-23 09:00:00	2025-08-27 20:57:54.750846	\N	\N
1064	106	144	WAITLISTED	\N	Enrolled for Technical Requirements Analysis	2025-06-24 09:00:00	2025-08-27 20:57:54.750847	\N	\N
1065	97	144	WAITLISTED	\N	Enrolled for Technical Requirements Analysis	2025-07-03 09:00:00	2025-08-27 20:57:54.750847	\N	\N
1066	104	144	CONFIRMED	\N	Enrolled for Technical Requirements Analysis	2025-06-25 09:00:00	2025-08-27 20:57:54.750847	\N	\N
1067	98	144	CONFIRMED	\N	Enrolled for Technical Requirements Analysis	2025-06-23 09:00:00	2025-08-27 20:57:54.750848	\N	\N
1068	99	144	CONFIRMED	\N	Enrolled for Technical Requirements Analysis	2025-06-23 09:00:00	2025-08-27 20:57:54.750848	\N	\N
1069	105	144	WAITLISTED	\N	Enrolled for Technical Requirements Analysis	2025-06-30 09:00:00	2025-08-27 20:57:54.750849	\N	\N
1070	100	144	WAITLISTED	\N	Enrolled for Technical Requirements Analysis	2025-06-25 09:00:00	2025-08-27 20:57:54.750849	\N	\N
1071	105	145	CONFIRMED	\N	Enrolled for System Architecture Design	2025-07-06 09:00:00	2025-08-27 20:57:54.75085	\N	\N
1072	101	145	CONFIRMED	\N	Enrolled for System Architecture Design	2025-07-01 09:00:00	2025-08-27 20:57:54.75085	\N	\N
1073	99	145	CONFIRMED	\N	Enrolled for System Architecture Design	2025-07-04 09:00:00	2025-08-27 20:57:54.75085	\N	\N
1074	102	145	CONFIRMED	\N	Enrolled for System Architecture Design	2025-07-05 09:00:00	2025-08-27 20:57:54.750851	\N	\N
1075	98	145	WAITLISTED	\N	Enrolled for System Architecture Design	2025-07-06 09:00:00	2025-08-27 20:57:54.750851	\N	\N
1076	106	145	CONFIRMED	\N	Enrolled for System Architecture Design	2025-06-27 09:00:00	2025-08-27 20:57:54.750852	\N	\N
1077	104	145	WAITLISTED	\N	Enrolled for System Architecture Design	2025-06-26 09:00:00	2025-08-27 20:57:54.750852	\N	\N
1078	97	145	CONFIRMED	\N	Enrolled for System Architecture Design	2025-06-30 09:00:00	2025-08-27 20:57:54.750853	\N	\N
1079	103	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-07-03 09:00:00	2025-08-27 20:57:54.750853	\N	\N
1080	98	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-07-04 09:00:00	2025-08-27 20:57:54.750853	\N	\N
1081	100	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-07-03 09:00:00	2025-08-27 20:57:54.750854	\N	\N
1082	101	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-07-09 09:00:00	2025-08-27 20:57:54.750854	\N	\N
1083	104	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-07-03 09:00:00	2025-08-27 20:57:54.750855	\N	\N
1084	102	146	WAITLISTED	\N	Enrolled for Database Schema Planning	2025-07-10 09:00:00	2025-08-27 20:57:54.750855	\N	\N
1085	97	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-07-10 09:00:00	2025-08-27 20:57:54.750856	\N	\N
1086	105	146	CONFIRMED	\N	Enrolled for Database Schema Planning	2025-06-30 09:00:00	2025-08-27 20:57:54.750856	\N	\N
1087	103	147	WAITLISTED	\N	Enrolled for Frontend Prototype Development	2025-07-07 09:00:00	2025-08-27 20:57:54.750856	\N	\N
1088	106	147	CONFIRMED	\N	Enrolled for Frontend Prototype Development	2025-07-09 09:00:00	2025-08-27 20:57:54.750857	\N	\N
1089	105	147	CONFIRMED	\N	Enrolled for Frontend Prototype Development	2025-07-08 09:00:00	2025-08-27 20:57:54.750857	\N	\N
1090	99	147	CONFIRMED	\N	Enrolled for Frontend Prototype Development	2025-07-14 09:00:00	2025-08-27 20:57:54.750858	\N	\N
1091	97	147	WAITLISTED	\N	Enrolled for Frontend Prototype Development	2025-07-03 09:00:00	2025-08-27 20:57:54.750858	\N	\N
1092	102	147	CONFIRMED	\N	Enrolled for Frontend Prototype Development	2025-07-13 09:00:00	2025-08-27 20:57:54.750859	\N	\N
1093	100	147	WAITLISTED	\N	Enrolled for Frontend Prototype Development	2025-07-13 09:00:00	2025-08-27 20:57:54.750859	\N	\N
1094	100	148	CONFIRMED	\N	Enrolled for Backend API Implementation	2025-07-17 09:00:00	2025-08-27 20:57:54.750859	\N	\N
1095	104	148	CONFIRMED	\N	Enrolled for Backend API Implementation	2025-07-12 09:00:00	2025-08-27 20:57:54.75086	\N	\N
1096	101	148	CONFIRMED	\N	Enrolled for Backend API Implementation	2025-07-07 09:00:00	2025-08-27 20:57:54.75086	\N	\N
1097	105	148	WAITLISTED	\N	Enrolled for Backend API Implementation	2025-07-08 09:00:00	2025-08-27 20:57:54.750861	\N	\N
1098	102	148	CONFIRMED	\N	Enrolled for Backend API Implementation	2025-07-17 09:00:00	2025-08-27 20:57:54.750861	\N	\N
1099	98	148	WAITLISTED	\N	Enrolled for Backend API Implementation	2025-07-07 09:00:00	2025-08-27 20:57:54.750862	\N	\N
1100	97	148	WAITLISTED	\N	Enrolled for Backend API Implementation	2025-07-10 09:00:00	2025-08-27 20:57:54.750862	\N	\N
1101	104	149	CONFIRMED	\N	Enrolled for Mobile App Development Sprint	2025-07-17 09:00:00	2025-08-27 20:57:54.750863	\N	\N
1102	97	149	CONFIRMED	\N	Enrolled for Mobile App Development Sprint	2025-07-20 09:00:00	2025-08-27 20:57:54.750863	\N	\N
1103	105	149	WAITLISTED	\N	Enrolled for Mobile App Development Sprint	2025-07-22 09:00:00	2025-08-27 20:57:54.750863	\N	\N
1104	106	149	CONFIRMED	\N	Enrolled for Mobile App Development Sprint	2025-07-21 09:00:00	2025-08-27 20:57:54.750864	\N	\N
1105	98	149	CONFIRMED	\N	Enrolled for Mobile App Development Sprint	2025-07-15 09:00:00	2025-08-27 20:57:54.750864	\N	\N
1106	102	149	WAITLISTED	\N	Enrolled for Mobile App Development Sprint	2025-07-10 09:00:00	2025-08-27 20:57:54.750866	\N	\N
1107	101	149	CONFIRMED	\N	Enrolled for Mobile App Development Sprint	2025-07-10 09:00:00	2025-08-27 20:57:54.750866	\N	\N
1108	103	150	CONFIRMED	\N	Enrolled for DevOps Pipeline Setup	2025-07-15 09:00:00	2025-08-27 20:57:54.750867	\N	\N
1109	101	150	WAITLISTED	\N	Enrolled for DevOps Pipeline Setup	2025-07-19 09:00:00	2025-08-27 20:57:54.750867	\N	\N
1110	100	150	WAITLISTED	\N	Enrolled for DevOps Pipeline Setup	2025-07-12 09:00:00	2025-08-27 20:57:54.750867	\N	\N
1111	106	150	CONFIRMED	\N	Enrolled for DevOps Pipeline Setup	2025-07-16 09:00:00	2025-08-27 20:57:54.750868	\N	\N
1112	105	150	WAITLISTED	\N	Enrolled for DevOps Pipeline Setup	2025-07-23 09:00:00	2025-08-27 20:57:54.750868	\N	\N
1113	102	150	CONFIRMED	\N	Enrolled for DevOps Pipeline Setup	2025-07-23 09:00:00	2025-08-27 20:57:54.750869	\N	\N
1114	104	150	CONFIRMED	\N	Enrolled for DevOps Pipeline Setup	2025-07-23 09:00:00	2025-08-27 20:57:54.750869	\N	\N
1115	97	150	CONFIRMED	\N	Enrolled for DevOps Pipeline Setup	2025-07-19 09:00:00	2025-08-27 20:57:54.75087	\N	\N
1116	101	151	CONFIRMED	\N	Enrolled for Testing & Quality Assurance	2025-07-18 09:00:00	2025-08-27 20:57:54.75087	\N	\N
1117	104	151	CONFIRMED	\N	Enrolled for Testing & Quality Assurance	2025-07-26 09:00:00	2025-08-27 20:57:54.75087	\N	\N
1118	97	151	CONFIRMED	\N	Enrolled for Testing & Quality Assurance	2025-07-18 09:00:00	2025-08-27 20:57:54.750871	\N	\N
1119	106	151	CONFIRMED	\N	Enrolled for Testing & Quality Assurance	2025-07-17 09:00:00	2025-08-27 20:57:54.750871	\N	\N
1120	99	151	WAITLISTED	\N	Enrolled for Testing & Quality Assurance	2025-07-24 09:00:00	2025-08-27 20:57:54.750872	\N	\N
1121	100	151	WAITLISTED	\N	Enrolled for Testing & Quality Assurance	2025-07-17 09:00:00	2025-08-27 20:57:54.750872	\N	\N
1122	102	151	CONFIRMED	\N	Enrolled for Testing & Quality Assurance	2025-07-19 09:00:00	2025-08-27 20:57:54.750873	\N	\N
1123	98	151	WAITLISTED	\N	Enrolled for Testing & Quality Assurance	2025-07-26 09:00:00	2025-08-27 20:57:54.750873	\N	\N
1124	105	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-23 09:00:00	2025-08-27 20:57:54.750873	\N	\N
1125	106	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-27 09:00:00	2025-08-27 20:57:54.750874	\N	\N
1126	101	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-28 09:00:00	2025-08-27 20:57:54.750874	\N	\N
1127	98	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-27 09:00:00	2025-08-27 20:57:54.750875	\N	\N
1128	97	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-19 09:00:00	2025-08-27 20:57:54.750875	\N	\N
1129	100	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-18 09:00:00	2025-08-27 20:57:54.750876	\N	\N
1130	102	152	WAITLISTED	\N	Enrolled for Performance Optimization	2025-07-19 09:00:00	2025-08-27 20:57:54.750876	\N	\N
1131	99	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-24 09:00:00	2025-08-27 20:57:54.750876	\N	\N
1132	104	152	CONFIRMED	\N	Enrolled for Performance Optimization	2025-07-26 09:00:00	2025-08-27 20:57:54.750877	\N	\N
1133	98	153	WAITLISTED	\N	Enrolled for Security Audit & Fixes	2025-08-02 09:00:00	2025-08-27 20:57:54.750877	\N	\N
1134	103	153	CONFIRMED	\N	Enrolled for Security Audit & Fixes	2025-07-31 09:00:00	2025-08-27 20:57:54.750878	\N	\N
1135	102	153	CONFIRMED	\N	Enrolled for Security Audit & Fixes	2025-07-27 09:00:00	2025-08-27 20:57:54.750878	\N	\N
1136	97	153	CONFIRMED	\N	Enrolled for Security Audit & Fixes	2025-07-29 09:00:00	2025-08-27 20:57:54.750879	\N	\N
1137	100	153	CONFIRMED	\N	Enrolled for Security Audit & Fixes	2025-07-27 09:00:00	2025-08-27 20:57:54.750879	\N	\N
1138	101	153	CONFIRMED	\N	Enrolled for Security Audit & Fixes	2025-07-29 09:00:00	2025-08-27 20:57:54.750879	\N	\N
1139	99	153	WAITLISTED	\N	Enrolled for Security Audit & Fixes	2025-08-02 09:00:00	2025-08-27 20:57:54.75088	\N	\N
1140	98	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-07-27 09:00:00	2025-08-27 20:57:54.75088	\N	\N
1141	100	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-08-01 09:00:00	2025-08-27 20:57:54.750881	\N	\N
1142	101	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-08-01 09:00:00	2025-08-27 20:57:54.750881	\N	\N
1143	97	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-07-30 09:00:00	2025-08-27 20:57:54.750882	\N	\N
1144	99	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-08-04 09:00:00	2025-08-27 20:57:54.750882	\N	\N
1145	106	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-07-26 09:00:00	2025-08-27 20:57:54.750882	\N	\N
1146	104	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-08-01 09:00:00	2025-08-27 20:57:54.750883	\N	\N
1147	105	154	CONFIRMED	\N	Enrolled for User Acceptance Testing	2025-07-29 09:00:00	2025-08-27 20:57:54.750883	\N	\N
1148	104	155	CONFIRMED	\N	Enrolled for Production Deployment	2025-08-08 09:00:00	2025-08-27 20:57:54.750884	\N	\N
1149	102	155	WAITLISTED	\N	Enrolled for Production Deployment	2025-08-08 09:00:00	2025-08-27 20:57:54.750884	\N	\N
1150	99	155	CONFIRMED	\N	Enrolled for Production Deployment	2025-08-04 09:00:00	2025-08-27 20:57:54.750885	\N	\N
1151	103	155	WAITLISTED	\N	Enrolled for Production Deployment	2025-08-01 09:00:00	2025-08-27 20:57:54.750885	\N	\N
1152	98	155	CONFIRMED	\N	Enrolled for Production Deployment	2025-08-12 09:00:00	2025-08-27 20:57:54.750885	\N	\N
1153	100	155	CONFIRMED	\N	Enrolled for Production Deployment	2025-08-06 09:00:00	2025-08-27 20:57:54.750886	\N	\N
1154	106	155	CONFIRMED	\N	Enrolled for Production Deployment	2025-08-02 09:00:00	2025-08-27 20:57:54.750886	\N	\N
1155	101	155	CONFIRMED	\N	Enrolled for Production Deployment	2025-08-12 09:00:00	2025-08-27 20:57:54.750887	\N	\N
1156	101	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-03 09:00:00	2025-08-27 20:57:54.750887	\N	\N
1157	104	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-08 09:00:00	2025-08-27 20:57:54.750888	\N	\N
1158	100	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-11 09:00:00	2025-08-27 20:57:54.750888	\N	\N
1159	99	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-08 09:00:00	2025-08-27 20:57:54.750888	\N	\N
1160	106	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-06 09:00:00	2025-08-27 20:57:54.750889	\N	\N
1161	102	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-01 09:00:00	2025-08-27 20:57:54.750889	\N	\N
1162	98	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-12 09:00:00	2025-08-27 20:57:54.75089	\N	\N
1163	103	156	CONFIRMED	\N	Enrolled for Documentation & Handover	2025-08-03 09:00:00	2025-08-27 20:57:54.75089	\N	\N
1164	106	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-09 09:00:00	2025-08-27 20:57:54.750891	\N	\N
1165	101	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-07 09:00:00	2025-08-27 20:57:54.750891	\N	\N
1166	105	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-09 09:00:00	2025-08-27 20:57:54.750891	\N	\N
1167	97	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-16 09:00:00	2025-08-27 20:57:54.750892	\N	\N
1168	99	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-13 09:00:00	2025-08-27 20:57:54.750892	\N	\N
1169	100	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-08 09:00:00	2025-08-27 20:57:54.750893	\N	\N
1170	102	157	WAITLISTED	\N	Enrolled for Client Presentation & Demo	2025-08-14 09:00:00	2025-08-27 20:57:54.750893	\N	\N
1171	103	157	CONFIRMED	\N	Enrolled for Client Presentation & Demo	2025-08-06 09:00:00	2025-08-27 20:57:54.750894	\N	\N
1172	104	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-12 09:00:00	2025-08-27 20:57:54.750894	\N	\N
1173	105	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-11 09:00:00	2025-08-27 20:57:54.750894	\N	\N
1174	99	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-12 09:00:00	2025-08-27 20:57:54.750895	\N	\N
1175	98	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-11 09:00:00	2025-08-27 20:57:54.750895	\N	\N
1176	102	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-18 09:00:00	2025-08-27 20:57:54.750896	\N	\N
1177	97	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-12 09:00:00	2025-08-27 20:57:54.750896	\N	\N
1178	106	158	WAITLISTED	\N	Enrolled for Project Retrospective	2025-08-10 09:00:00	2025-08-27 20:57:54.750897	\N	\N
1179	103	158	CONFIRMED	\N	Enrolled for Project Retrospective	2025-08-16 09:00:00	2025-08-27 20:57:54.750897	\N	\N
1180	106	159	CONFIRMED	\N	Enrolled for Portfolio Development	2025-08-06 09:00:00	2025-08-27 20:57:54.750898	\N	\N
1181	102	159	CONFIRMED	\N	Enrolled for Portfolio Development	2025-08-17 09:00:00	2025-08-27 20:57:54.750898	\N	\N
1182	105	159	CONFIRMED	\N	Enrolled for Portfolio Development	2025-08-12 09:00:00	2025-08-27 20:57:54.750898	\N	\N
1183	101	159	WAITLISTED	\N	Enrolled for Portfolio Development	2025-08-16 09:00:00	2025-08-27 20:57:54.750899	\N	\N
1184	99	159	CONFIRMED	\N	Enrolled for Portfolio Development	2025-08-07 09:00:00	2025-08-27 20:57:54.750899	\N	\N
1185	100	159	CONFIRMED	\N	Enrolled for Portfolio Development	2025-08-18 09:00:00	2025-08-27 20:57:54.7509	\N	\N
1186	97	159	WAITLISTED	\N	Enrolled for Portfolio Development	2025-08-18 09:00:00	2025-08-27 20:57:54.7509	\N	\N
1187	103	159	CONFIRMED	\N	Enrolled for Portfolio Development	2025-08-13 09:00:00	2025-08-27 20:57:54.7509	\N	\N
1188	98	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-12 09:00:00	2025-08-27 20:57:54.750901	\N	\N
1189	104	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-16 09:00:00	2025-08-27 20:57:54.750901	\N	\N
1190	101	160	WAITLISTED	\N	Enrolled for Industry Best Practices	2025-08-18 09:00:00	2025-08-27 20:57:54.750902	\N	\N
1191	103	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-16 09:00:00	2025-08-27 20:57:54.750902	\N	\N
1192	102	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-08 09:00:00	2025-08-27 20:57:54.750903	\N	\N
1193	100	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-13 09:00:00	2025-08-27 20:57:54.750903	\N	\N
1194	99	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-12 09:00:00	2025-08-27 20:57:54.750903	\N	\N
1195	106	160	CONFIRMED	\N	Enrolled for Industry Best Practices	2025-08-09 09:00:00	2025-08-27 20:57:54.750904	\N	\N
\.


--
-- Data for Name: feedback; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.feedback (id, user_id, session_id, rating, comment, is_anonymous, created_at, updated_at, instructor_rating, session_quality, would_recommend) FROM stdin;
89	109	171	4.5	Great session! Very informative.	f	2025-09-06 12:25:23.556088	2025-09-06 12:25:23.556094	\N	\N	\N
91	109	170	4	Automated test feedback submission - this is a test	f	2025-09-06 12:50:40.289353	2025-09-06 12:50:40.289356	\N	\N	\N
93	109	175	4.5	Testing HTTP 400 bug fix - this should work now!	f	2025-09-06 13:06:33.255891	2025-09-06 13:06:33.255894	\N	\N	\N
94	109	176	5	Test feedback from fix validation - final test	f	2025-09-06 13:08:44.954812	2025-09-06 13:08:44.954815	\N	\N	\N
95	109	181	5	HTTP 400 bug fix verification - SUCCESS!	f	2025-09-06 13:16:31.661651	2025-09-06 13:16:31.661653	\N	\N	\N
99	97	133	4	Az oktató egy fasz amúgy fasza volt	f	2025-09-06 13:37:53.265126	2025-09-06 13:37:53.265135	2	5	t
96	97	124	4	Kurva jo volt! köszi!	f	2025-09-06 13:28:31.79851	2025-09-06 13:42:56.619341	3	5	f
98	97	130	1	Egyest adok bár 5öst akartam.	f	2025-09-06 13:29:04.702731	2025-09-06 13:44:12.291968	5	5	f
88	97	117	4.5	Nagyon hasznos gyakorlat volt! A Web Development Fundamentals session remek volt.	f	2025-09-06 09:38:40.391298	2025-09-06 13:44:29.138611	5	5	t
97	97	129	2	Kapd be! ezt a szart ! még egyszer nem jövök!	f	2025-09-06 13:28:46.668434	2025-09-06 13:45:06.025943	5	5	t
92	97	120	1	szar tesztelése  	f	2025-09-06 12:55:21.954212	2025-09-06 13:45:20.376091	1	2	f
100	97	136	2	Ezzel a tanárhoz biztos hogy nem! majd jövőre!	f	2025-09-06 13:46:04.825397	2025-09-06 13:46:04.825406	1	5	f
101	97	138	5		f	2025-09-06 13:46:13.538556	2025-09-06 13:46:13.538565	5	5	t
102	97	140	3		f	2025-09-06 13:46:29.757577	2025-09-06 13:46:29.757589	4	2	t
103	97	141	2		f	2025-09-06 13:49:57.527566	2025-09-06 13:49:57.527574	2	2	f
104	97	146	5	Fasza volt	f	2025-09-06 13:50:08.100025	2025-09-06 13:50:08.100034	5	5	t
105	97	149	5	ez már zsir volt	f	2025-09-06 13:50:17.803512	2025-09-06 13:50:17.803522	5	5	t
106	97	150	3	nehéz anyag de az oktató sokat segített	f	2025-09-06 13:50:53.95433	2025-09-06 13:50:53.954339	4	2	t
107	97	151	5	5/5 excellent	f	2025-09-06 13:51:07.907361	2025-09-06 13:51:07.907368	5	5	t
108	97	153	3		f	2025-09-06 13:51:20.67133	2025-09-06 13:51:20.671342	2	3	f
109	97	157	5		f	2025-09-06 13:51:24.538175	2025-09-06 13:51:24.538187	5	5	t
110	97	158	5		f	2025-09-06 13:51:27.757108	2025-09-06 13:51:27.757116	5	5	t
111	97	219	4		f	2025-09-07 09:15:10.717502	2025-09-07 09:15:10.71751	5	1	f
112	97	222	5		f	2025-09-10 18:11:54.470588	2025-09-10 18:11:54.470594	1	1	f
\.


--
-- Data for Name: group_users; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.group_users (group_id, user_id) FROM stdin;
26	98
26	100
26	105
24	104
24	106
24	97
24	101
23	102
23	98
23	99
22	105
22	100
22	103
25	104
25	106
25	99
25	102
22	97
27	97
\.


--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.groups (id, name, description, semester_id, created_at, updated_at) FROM stdin;
22	Frontend Specialists	React.js, Vue.js, Modern CSS, UX/UI Design	15	2025-08-27 20:57:54.718049	2025-08-27 20:57:54.71805
23	Backend Engineers	Node.js, Python Django/Flask, Database Design	15	2025-08-27 20:57:54.718051	2025-08-27 20:57:54.718052
24	Full-Stack Developers	End-to-end web application development	15	2025-08-27 20:57:54.718052	2025-08-27 20:57:54.718053
25	Mobile App Project Team	React Native e-commerce app development	16	2025-08-27 20:57:54.718053	2025-08-27 20:57:54.718053
26	DevOps Infrastructure Team	CI/CD pipelines, AWS deployment, monitoring	16	2025-08-27 20:57:54.718054	2025-08-27 20:57:54.718054
27	Septermber Games	szeptemberi teszt játékok	17	2025-08-31 14:25:33.623942	2025-08-31 14:25:33.623956
28	Web Development Fundamentals	Introduction to web development	20	2025-09-06 10:15:38.237919	2025-09-06 10:15:38.237923
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.notifications (id, user_id, title, message, type, is_read, related_session_id, related_booking_id, created_at, read_at) FROM stdin;
\.


--
-- Data for Name: project_enrollments; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_enrollments (id, project_id, user_id, enrolled_at, status, progress_status, completion_percentage, instructor_approved, final_grade, completed_at) FROM stdin;
2	1	114	2025-09-08 18:58:43.315809	active	planning	0	f	\N	\N
4	1	97	2025-09-08 21:11:26.871334	active	planning	0	f	\N	\N
5	2	97	2025-09-08 21:11:31.360934	active	planning	0	f	\N	\N
1	1	113	2025-09-08 18:27:08.463295	withdrawn	planning	0	f	\N	\N
6	1	109	2025-09-09 17:32:52.696373	withdrawn	planning	0	f	\N	\N
7	2	109	2025-09-09 17:33:49.191658	active	planning	0	f	\N	\N
8	2	114	2025-09-09 17:33:53.815615	active	planning	0	f	\N	\N
3	2	113	2025-09-08 20:27:34.906442	withdrawn	planning	0	f	\N	\N
\.


--
-- Data for Name: project_milestone_progress; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_milestone_progress (id, enrollment_id, milestone_id, status, submitted_at, instructor_feedback, instructor_approved_at, sessions_completed, created_at, updated_at) FROM stdin;
1	1	1	pending	\N	\N	\N	0	2025-09-08 18:27:08.63118	2025-09-08 18:27:08.631186
2	1	2	pending	\N	\N	\N	0	2025-09-08 18:27:08.631187	2025-09-08 18:27:08.631188
3	1	3	pending	\N	\N	\N	0	2025-09-08 18:27:08.631189	2025-09-08 18:27:08.631189
4	1	4	pending	\N	\N	\N	0	2025-09-08 18:27:08.63119	2025-09-08 18:27:08.63119
5	2	1	pending	\N	\N	\N	0	2025-09-08 18:58:43.325959	2025-09-08 18:58:43.325968
6	2	2	pending	\N	\N	\N	0	2025-09-08 18:58:43.325969	2025-09-08 18:58:43.32597
7	2	3	pending	\N	\N	\N	0	2025-09-08 18:58:43.325971	2025-09-08 18:58:43.325971
8	2	4	pending	\N	\N	\N	0	2025-09-08 18:58:43.325972	2025-09-08 18:58:43.325972
9	3	5	pending	\N	\N	\N	0	2025-09-08 20:27:34.915649	2025-09-08 20:27:34.915654
10	3	6	pending	\N	\N	\N	0	2025-09-08 20:27:34.915655	2025-09-08 20:27:34.915656
11	3	7	pending	\N	\N	\N	0	2025-09-08 20:27:34.915657	2025-09-08 20:27:34.915657
12	3	8	pending	\N	\N	\N	0	2025-09-08 20:27:34.915658	2025-09-08 20:27:34.915658
13	4	1	pending	\N	\N	\N	0	2025-09-08 21:11:26.8937	2025-09-08 21:11:26.893704
14	4	2	pending	\N	\N	\N	0	2025-09-08 21:11:26.893706	2025-09-08 21:11:26.893706
15	4	3	pending	\N	\N	\N	0	2025-09-08 21:11:26.893707	2025-09-08 21:11:26.893707
16	4	4	pending	\N	\N	\N	0	2025-09-08 21:11:26.893708	2025-09-08 21:11:26.893708
17	5	5	pending	\N	\N	\N	0	2025-09-08 21:11:31.364596	2025-09-08 21:11:31.364599
18	5	6	pending	\N	\N	\N	0	2025-09-08 21:11:31.3646	2025-09-08 21:11:31.364601
19	5	7	pending	\N	\N	\N	0	2025-09-08 21:11:31.364602	2025-09-08 21:11:31.364602
20	5	8	pending	\N	\N	\N	0	2025-09-08 21:11:31.364603	2025-09-08 21:11:31.364603
21	6	1	pending	\N	\N	\N	0	2025-09-09 17:32:52.715332	2025-09-09 17:32:52.715337
22	6	2	pending	\N	\N	\N	0	2025-09-09 17:32:52.715339	2025-09-09 17:32:52.71534
23	6	3	pending	\N	\N	\N	0	2025-09-09 17:32:52.71534	2025-09-09 17:32:52.715341
24	6	4	pending	\N	\N	\N	0	2025-09-09 17:32:52.715342	2025-09-09 17:32:52.715342
25	7	5	pending	\N	\N	\N	0	2025-09-09 17:33:49.205785	2025-09-09 17:33:49.20579
26	7	6	pending	\N	\N	\N	0	2025-09-09 17:33:49.205791	2025-09-09 17:33:49.205791
27	7	7	pending	\N	\N	\N	0	2025-09-09 17:33:49.205792	2025-09-09 17:33:49.205793
28	7	8	pending	\N	\N	\N	0	2025-09-09 17:33:49.205793	2025-09-09 17:33:49.205794
29	8	5	pending	\N	\N	\N	0	2025-09-09 17:33:53.822531	2025-09-09 17:33:53.82254
30	8	6	pending	\N	\N	\N	0	2025-09-09 17:33:53.822542	2025-09-09 17:33:53.822544
31	8	7	pending	\N	\N	\N	0	2025-09-09 17:33:53.822546	2025-09-09 17:33:53.822547
32	8	8	pending	\N	\N	\N	0	2025-09-09 17:33:53.822549	2025-09-09 17:33:53.82255
\.


--
-- Data for Name: project_milestones; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_milestones (id, project_id, title, description, order_index, required_sessions, xp_reward, deadline, is_required, created_at) FROM stdin;
1	1	Adatforrás elemzés és tervezés	Elemezd a rendelkezésre álló adatokat és tervezd meg a dashboard struktúráját	1	2	50	2025-10-15	t	2025-09-08 18:22:02.787645
2	1	Backend API fejlesztés	Készíts RESTful API-t az adatok kezelésére Python és FastAPI használatával	2	3	75	2025-11-01	t	2025-09-08 18:22:02.787653
3	1	Frontend dashboard implementáció	Fejleszd ki a React alapú dashboard interfészt interaktív chartokkal	3	3	75	2025-11-20	t	2025-09-08 18:22:02.787654
4	1	Testelés és optimalizáció	Végezz teljesítmény teszteket és optimalizáld a rendszert	4	2	50	2025-12-10	t	2025-09-08 18:22:02.787655
5	2	App design és UX tervezés	Tervezd meg az alkalmazás felhasználói interfészét és user experience-ét	1	2	60	2025-10-20	t	2025-09-08 18:22:02.793192
6	2	Backend szolgáltatások	Készíts backend API-t user management és data tracking funkciókkal	2	4	80	2025-11-10	t	2025-09-08 18:22:02.793196
7	2	Mobile app fejlesztés	Implementáld a React Native alkalmazást core funkciókkal	3	4	80	2025-11-30	t	2025-09-08 18:22:02.793197
8	2	Tesztelés és publikálás	Végezz tesztelést és készítsd elő az alkalmazást publikálásra	4	2	60	2025-12-15	t	2025-09-08 18:22:02.793197
\.


--
-- Data for Name: project_sessions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.project_sessions (id, project_id, session_id, milestone_id, is_required, created_at) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.projects (id, title, description, semester_id, instructor_id, max_participants, required_sessions, xp_reward, deadline, status, created_at, updated_at) FROM stdin;
1	Football Analytics Dashboard	Hozz létre egy komplex elemzési dashboard-ot a football statisztikákhoz. A projekt során Python, React és adatvizualizációs könyvtárakat fogsz használni.	17	111	8	10	300	2025-12-15	active	2025-09-08 18:22:02.762412	2025-09-08 18:22:02.762419
2	Mobile Fitness Tracker App	Fejlessz egy cross-platform mobil alkalmazást fitness tracking funkciókkal. React Native és Node.js technológiákat fogsz használni.	17	111	6	12	350	2025-12-20	active	2025-09-08 18:22:02.769771	2025-09-08 18:22:02.769775
\.


--
-- Data for Name: quiz_answer_options; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_answer_options (id, question_id, option_text, is_correct, order_index) FROM stdin;
69	22	Engagement rate	t	0
70	22	Number of followers	f	1
71	22	Number of posts	f	2
72	22	Number of comments	f	3
73	23	True	t	0
74	23	False	f	1
75	24	content	t	0
76	24	Content	t	1
77	24	CONTENT	t	2
78	25	Target audience identification	t	0
79	25	Budget planning	f	1
80	25	Creating creatives	f	2
81	25	Media selection	f	3
82	26	True	t	0
83	26	False	f	1
84	27	Fixed costs do not change with production volume	t	0
85	27	Fixed costs are always higher	f	1
86	27	Variable costs are constant	f	2
87	27	There is no difference between them	f	3
88	28	True	t	0
89	28	False	f	1
90	29	ROI	t	0
91	29	profitability	t	1
92	29	profit	t	2
93	30	Where revenue equals costs	t	0
94	30	The point of maximum profit	f	1
95	30	The minimum margin	f	2
96	30	The highest selling price	f	3
97	31	Python	t	0
98	31	HTML	f	1
99	31	CSS	f	2
100	31	SQL	f	3
101	32	True	t	0
102	32	False	f	1
103	33	MySQL	t	0
104	33	PostgreSQL	t	1
105	33	Oracle	t	2
106	33	SQL Server	t	3
107	34	Scalability and flexibility	t	0
108	34	Always cheaper	f	1
109	34	No internet connection needed	f	2
110	34	Complete data security guaranteed	f	3
111	35	It occurs with oxygen utilization	t	0
112	35	Short, intense workload	f	1
113	35	Only through anaerobic pathways	f	2
114	35	Can only be done by running	f	3
115	36	True	t	0
116	36	False	f	1
117	37	60	t	0
118	37	sixty	t	1
119	37	60%	t	2
120	38	133-152 beats/min (70-80% max HR)	t	0
121	38	95-114 beats/min (50-60% max HR)	f	1
122	38	171-190 beats/min (90-100% max HR)	f	2
123	38	60-80 beats/min (resting)	f	3
124	39	Carbohydrates	t	0
125	39	Protein	f	1
126	39	Fat	f	2
127	39	Vitamins	f	3
128	40	True	t	0
129	40	False	f	1
130	41	1.2-2.0	t	0
131	41	1,2-2,0	t	1
132	41	1.6	t	2
133	42	Vitamin C	t	0
134	42	Vitamin D	f	1
135	42	Vitamin B12	f	2
136	42	Vitamin E	f	3
\.


--
-- Data for Name: quiz_attempts; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_attempts (id, user_id, quiz_id, started_at, completed_at, time_spent_minutes, score, total_questions, correct_answers, xp_awarded, passed) FROM stdin;
24	97	6	2025-09-10 18:12:33.037612+02	\N	\N	\N	5	0	0	f
25	97	6	2025-09-10 18:12:33.066019+02	2025-09-10 18:13:17.508844+02	44	0	5	0	0	f
27	97	7	2025-09-10 18:38:04.166124+02	\N	\N	\N	4	0	0	f
26	97	7	2025-09-10 18:38:04.154184+02	2025-09-10 18:49:21.511351+02	677	66.66666666666666	4	2	0	f
28	97	8	2025-09-10 18:52:28.438999+02	2025-09-10 18:55:49.690369+02	201	50	4	1	0	f
29	97	9	2025-09-10 19:07:32.905607+02	2025-09-10 19:07:44.724756+02	12	50	4	2	0	f
30	97	10	2025-09-10 19:19:10.058314+02	2025-09-10 19:19:20.434085+02	10	25	4	1	0	f
\.


--
-- Data for Name: quiz_questions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_questions (id, quiz_id, question_text, question_type, points, order_index, explanation, created_at) FROM stdin;
22	6	What is the most important KPI for social media campaigns?	MULTIPLE_CHOICE	1	0	The engagement rate is the most accurate metric for measuring social media success.	2025-09-10 16:40:01.842743+02
23	6	SEO stands for Search Engine Optimization.	TRUE_FALSE	1	1	SEO indeed stands for Search Engine Optimization, which means optimizing content for search engines.	2025-09-10 16:40:01.842743+02
24	6	_____ marketing aims to create valuable content for the target audience.	FILL_IN_BLANK	1	2	Content marketing is all about creating valuable content for your audience.	2025-09-10 16:40:01.842743+02
25	6	What is the first step in planning a successful marketing campaign?	MULTIPLE_CHOICE	1	3	Without precise target audience identification, you cannot plan an effective campaign.	2025-09-10 16:40:01.842743+02
26	6	Email marketing remains a relevant marketing channel in 2024.	TRUE_FALSE	1	4	Email marketing continues to be one of the highest ROI marketing channels.	2025-09-10 16:40:01.842743+02
27	7	What is the difference between fixed and variable costs?	MULTIPLE_CHOICE	1	0	Fixed costs are independent of production volume (e.g. rent), variable costs are proportional to it.	2025-09-10 16:40:01.842743+02
28	7	Inflation means a decrease in the value of money.	TRUE_FALSE	1	1	During inflation, prices rise, so the purchasing power of money decreases.	2025-09-10 16:40:01.842743+02
29	7	We measure a company's profitability based on the _____ indicator.	FILL_IN_BLANK	1	2	ROI (Return on Investment) shows the return on investment.	2025-09-10 16:40:01.842743+02
30	7	What is the break-even point?	MULTIPLE_CHOICE	1	3	Break-even point is the production/sales level where there is neither profit nor loss.	2025-09-10 16:40:01.842743+02
31	8	Which programming language is object-oriented?	MULTIPLE_CHOICE	1	0	Python is a multi-paradigm language that supports object-oriented programming.	2025-09-10 16:40:01.842743+02
32	8	HTTPS is the encrypted version of the HTTP protocol.	TRUE_FALSE	1	1	HTTPS is HTTP enhanced with SSL/TLS encryption.	2025-09-10 16:40:01.842743+02
33	8	_____ is a relational database management system.	FILL_IN_BLANK	1	2	There are several RDBMS systems like MySQL, PostgreSQL, Oracle, SQL Server.	2025-09-10 16:40:01.842743+02
34	8	What is the main advantage of cloud computing services?	MULTIPLE_CHOICE	1	3	Cloud services are popular mainly for flexible resource management.	2025-09-10 16:40:01.842743+02
35	9	What is the main characteristic of aerobic exercise?	MULTIPLE_CHOICE	1	0	During aerobic exercise, sufficient oxygen is available for energy production.	2025-09-10 16:40:01.842743+02
36	9	Lactate accumulation causes muscle fatigue.	TRUE_FALSE	1	1	Lactate (lactic acid) accumulation in muscles causes fatigue and burning sensation.	2025-09-10 16:40:01.842743+02
37	9	The human body has approximately _____% water content.	FILL_IN_BLANK	1	2	The human body consists of approximately 60% water, which is important to replenish during sports.	2025-09-10 16:40:01.842743+02
38	9	What is the ideal heart rate during exercise for a 30-year-old athlete?	MULTIPLE_CHOICE	1	3	For a 30-year-old, max HR ~190, ideal for training is 70-80% (133-152 beats/min).	2025-09-10 16:40:01.842743+02
39	10	Which macronutrient is the main energy source for athletes?	MULTIPLE_CHOICE	1	0	Carbohydrates provide the fastest available energy during exercise.	2025-09-10 16:40:01.842743+02
40	10	It is recommended to consume protein within 30 minutes after exercise for muscle growth.	TRUE_FALSE	1	1	The 30-minute 'anabolic window' after exercise is optimal for muscle building.	2025-09-10 16:40:01.842743+02
41	10	Athletes should consume _____ g/kg of protein daily.	FILL_IN_BLANK	1	2	Athletes should consume 1.2-2.0 g/kg protein daily based on their body weight.	2025-09-10 16:40:01.842743+02
42	10	Which vitamin helps iron absorption?	MULTIPLE_CHOICE	1	3	Vitamin C significantly improves iron absorption in the body.	2025-09-10 16:40:01.842743+02
\.


--
-- Data for Name: quiz_user_answers; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quiz_user_answers (id, attempt_id, question_id, selected_option_id, answer_text, is_correct, answered_at) FROM stdin;
72	26	28	88	\N	t	2025-09-10 18:49:21.498945+02
73	26	29	\N	ROI	t	2025-09-10 18:49:21.498945+02
74	26	30	94	\N	f	2025-09-10 18:49:21.498945+02
75	28	31	97	\N	t	2025-09-10 18:55:49.663387+02
76	28	32	102	\N	f	2025-09-10 18:55:49.663387+02
77	29	35	112	\N	f	2025-09-10 19:07:44.69997+02
78	29	36	115	\N	t	2025-09-10 19:07:44.69997+02
79	29	37	\N	60%	t	2025-09-10 19:07:44.69997+02
80	29	38	122	\N	f	2025-09-10 19:07:44.69997+02
81	30	39	125	\N	f	2025-09-10 19:19:20.425199+02
82	30	40	129	\N	f	2025-09-10 19:19:20.425199+02
83	30	41	\N	1,2-2,0	t	2025-09-10 19:19:20.425199+02
84	30	42	134	\N	f	2025-09-10 19:19:20.425199+02
\.


--
-- Data for Name: quizzes; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.quizzes (id, title, description, category, difficulty, time_limit_minutes, xp_reward, passing_score, is_active, created_at, updated_at) FROM stdin;
6	Digital Marketing Fundamentals	Test your knowledge in digital marketing!	MARKETING	MEDIUM	12	75	70	t	2025-09-10 16:40:01.842743+02	\N
7	Business Economics	Test of fundamental economic concepts and principles.	ECONOMICS	MEDIUM	15	80	75	t	2025-09-10 16:40:01.842743+02	\N
8	Computer Science Fundamentals	Basics of computer science and programming.	INFORMATICS	EASY	10	60	70	t	2025-09-10 16:40:01.842743+02	\N
9	Sports Physiology Basics	Physiological background of exercise and sports.	SPORTS_PHYSIOLOGY	MEDIUM	12	85	75	t	2025-09-10 16:40:01.842743+02	\N
10	Sports Nutrition	Nutritional knowledge for athletes.	NUTRITION	MEDIUM	10	70	70	t	2025-09-10 16:40:01.842743+02	\N
\.


--
-- Data for Name: semesters; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.semesters (id, code, name, start_date, end_date, is_active, created_at, updated_at) FROM stdin;
15	2025-SPRING	Spring 2025 Development Bootcamp	2025-03-01	2025-06-30	f	2025-08-27 20:57:54.218501	2025-08-27 21:09:15.140919
17	2025/2-4415	Early September Test	2025-09-01	2025-09-06	t	2025-08-31 09:30:34.555197	2025-08-31 09:30:34.555205
16	2025-SUMMER	Summer 2025 Internship Program	2025-07-01	2025-08-30	f	2025-08-27 20:57:54.218508	2025-08-31 09:31:35.134355
18	FALL2025	Fall 2025	2025-08-01	2025-12-31	t	2025-08-31 14:42:32.973613	2025-08-31 14:42:32.973619
19	TEST2025	Test Semester 2025	2025-09-15	2025-12-15	t	2025-09-02 13:41:30.960894	2025-09-02 13:41:30.960897
20	2025_FALL	Fall 2025	2025-07-08	2025-10-06	t	2025-09-06 10:15:23.987297	2025-09-06 10:15:23.987299
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.sessions (id, title, description, date_start, date_end, mode, capacity, location, meeting_link, semester_id, group_id, instructor_id, created_at, updated_at, sport_type, level, instructor_name) FROM stdin;
128	Database Design & PostgreSQL	Week 7 - 3 hour intensive session	2025-04-18 09:00:00	2025-04-18 12:00:00	HYBRID	13	DevStudio Academy, Conference Room A	\N	15	23	94	2025-08-27 20:57:54.73063	2025-08-27 20:57:54.73063	General	All Levels	\N
129	Authentication & JWT Security	Week 7 - 2 hour intensive session	2025-04-14 09:00:00	2025-04-14 11:00:00	HYBRID	15	\N	\N	15	23	94	2025-08-27 20:57:54.730631	2025-08-27 20:57:54.730631	General	All Levels	\N
131	Python Django Framework	Week 9 - 3 hour intensive session	2025-05-02 09:00:00	2025-05-02 12:00:00	OFFLINE	15	\N	\N	15	23	94	2025-08-27 20:57:54.730632	2025-08-27 20:57:54.730632	General	All Levels	\N
132	GraphQL vs REST APIs	Week 9 - 2 hour intensive session	2025-04-28 09:00:00	2025-04-28 11:00:00	HYBRID	14	\N	\N	15	23	94	2025-08-27 20:57:54.730633	2025-08-27 20:57:54.730633	General	All Levels	\N
133	Microservices Architecture	Week 10 - 3 hour intensive session	2025-05-07 14:00:00	2025-05-07 17:00:00	OFFLINE	12	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-1940	15	\N	95	2025-08-27 20:57:54.730633	2025-08-27 20:57:54.730634	General	All Levels	\N
134	Docker Containerization	Week 10 - 2 hour intensive session	2025-05-09 09:00:00	2025-05-09 11:00:00	OFFLINE	12	\N	https://meet.devstudio.com/session-9738	15	\N	95	2025-08-27 20:57:54.730634	2025-08-27 20:57:54.730634	General	All Levels	\N
135	AWS Cloud Deployment	Week 11 - 3 hour intensive session	2025-05-12 09:00:00	2025-05-12 12:00:00	ONLINE	15	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-1021	15	\N	95	2025-08-27 20:57:54.730635	2025-08-27 20:57:54.730635	General	All Levels	\N
136	Project Planning & Architecture	Week 12 - 3 hour intensive session	2025-05-21 14:00:00	2025-05-21 17:00:00	ONLINE	13	\N	\N	15	24	93	2025-08-27 20:57:54.730635	2025-08-27 20:57:54.730636	General	All Levels	\N
137	Agile Development Workshop	Week 12 - 3 hour intensive session	2025-05-23 09:00:00	2025-05-23 12:00:00	ONLINE	15	\N	https://meet.devstudio.com/session-2046	15	24	93	2025-08-27 20:57:54.730636	2025-08-27 20:57:54.730636	General	All Levels	\N
138	Code Review & Quality Assurance	Week 13 - 3 hour intensive session	2025-05-26 09:00:00	2025-05-26 12:00:00	OFFLINE	13	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-3046	15	24	93	2025-08-27 20:57:54.730637	2025-08-27 20:57:54.730637	General	All Levels	\N
139	Unit Testing Best Practices	Week 13 - 2 hour intensive session	2025-05-28 14:00:00	2025-05-28 16:00:00	HYBRID	14	DevStudio Academy, Conference Room A	\N	15	24	93	2025-08-27 20:57:54.730638	2025-08-27 20:57:54.730638	General	All Levels	\N
140	Final Project Presentations	Week 14 - 3 hour intensive session	2025-06-06 09:00:00	2025-06-06 12:00:00	ONLINE	15	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-9720	15	24	93	2025-08-27 20:57:54.730638	2025-08-27 20:57:54.730639	General	All Levels	\N
141	Career Development Workshop	Week 14 - 3 hour intensive session	2025-06-02 09:00:00	2025-06-02 12:00:00	OFFLINE	15	\N	https://meet.devstudio.com/session-5417	15	24	93	2025-08-27 20:57:54.730639	2025-08-27 20:57:54.730639	General	All Levels	\N
142	Industry Networking Event	Week 14 - 2 hour intensive session	2025-06-04 14:00:00	2025-06-04 16:00:00	OFFLINE	15	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-6623	15	24	93	2025-08-27 20:57:54.73064	2025-08-27 20:57:54.73064	General	All Levels	\N
143	Real Client Project Briefing	Internship Week 1 - Real project work (4h)	2025-07-02 09:00:00	2025-07-02 13:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-2732	16	\N	93	2025-08-27 20:57:54.737639	2025-08-27 20:57:54.73764	General	All Levels	\N
144	Technical Requirements Analysis	Internship Week 1 - Real project work (3h)	2025-07-04 09:00:00	2025-07-04 12:00:00	HYBRID	11	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-1961	16	\N	94	2025-08-27 20:57:54.737641	2025-08-27 20:57:54.737641	General	All Levels	\N
145	System Architecture Design	Internship Week 2 - Real project work (4h)	2025-07-09 09:00:00	2025-07-09 13:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-9550	16	26	95	2025-08-27 20:57:54.737641	2025-08-27 20:57:54.737642	General	All Levels	\N
146	Database Schema Planning	Internship Week 2 - Real project work (3h)	2025-07-11 09:00:00	2025-07-11 12:00:00	HYBRID	10	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-4331	16	\N	94	2025-08-27 20:57:54.737642	2025-08-27 20:57:54.737642	General	All Levels	\N
147	Frontend Prototype Development	Internship Week 3 - Real project work (4h)	2025-07-16 09:00:00	2025-07-16 13:00:00	HYBRID	10	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-4879	16	\N	93	2025-08-27 20:57:54.737643	2025-08-27 20:57:54.737643	General	All Levels	\N
148	Backend API Implementation	Internship Week 3 - Real project work (4h)	2025-07-18 09:00:00	2025-07-18 13:00:00	HYBRID	11	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-9795	16	\N	94	2025-08-27 20:57:54.737644	2025-08-27 20:57:54.737644	General	All Levels	\N
149	Mobile App Development Sprint	Internship Week 4 - Real project work (4h)	2025-07-23 09:00:00	2025-07-23 13:00:00	HYBRID	12	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-8685	16	25	96	2025-08-27 20:57:54.737644	2025-08-27 20:57:54.737645	General	All Levels	\N
150	DevOps Pipeline Setup	Internship Week 4 - Real project work (3h)	2025-07-25 09:00:00	2025-07-25 12:00:00	HYBRID	11	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-9925	16	26	95	2025-08-27 20:57:54.737645	2025-08-27 20:57:54.737645	General	All Levels	\N
119	JavaScript ES6+ Essentials	Week 2 - 3 hour intensive session	2025-03-14 09:00:00	2025-03-14 12:00:00	OFFLINE	13	DevStudio Academy, Conference Room A	\N	15	22	93	2025-08-27 20:57:54.730623	2025-08-27 20:57:54.730623	Programming	Beginner	Dr. Johnson
117	Web Development Fundamentals	Week 1 - 3 hour intensive session	2025-09-03 04:45:00	2025-09-04 04:50:00	ONLINE	2	DevStudio Academy, Conference Room A	\N	15	24	93	2025-08-27 20:57:54.730619	2025-09-03 04:39:52.430473	General	All Levels	\N
118	HTML5 & CSS3 Modern Techniques	Week 1 - 2 hour intensive session	2025-03-05 14:00:00	2025-03-05 16:00:00	ONLINE	13	DevStudio Academy, Conference Room A	\N	15	22	93	2025-08-27 20:57:54.730622	2025-08-27 20:57:54.730623	Programming	Intermediate	Dr. Johnson
121	React.js Component Architecture	Week 3 - 3 hour intensive session	2025-03-19 14:00:00	2025-03-19 17:00:00	OFFLINE	14	DevStudio Academy, Conference Room A	\N	15	22	93	2025-08-27 20:57:54.730625	2025-08-27 20:57:54.730625	Programming	Intermediate	Dr. Johnson
130	RESTful API Best Practices	Week 8 - 3 hour intensive session	2025-09-23 12:00:00	2025-09-23 15:00:00	OFFLINE	3	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-6332	15	23	94	2025-08-27 20:57:54.730631	2025-09-06 19:09:55.509376	General	All Levels	\N
120	Git Version Control Workflow	Week 2 - 2 hour intensive session	2025-09-10 17:56:35.583515	2025-09-10 19:56:35.583515	HYBRID	15	\N	\N	15	\N	95	2025-08-27 20:57:54.730624	2025-09-09 17:56:35.585205	General	All Levels	\N
122	State Management with Redux	Week 3 - 2 hour intensive session	2025-09-13 17:56:35.583515	2025-09-13 19:56:35.583515	OFFLINE	12	\N	https://meet.devstudio.com/session-8026	15	22	93	2025-08-27 20:57:54.730625	2025-09-09 17:56:35.58521	General	All Levels	\N
123	Vue.js Alternative Framework	Week 4 - 3 hour intensive session	2025-09-16 17:56:35.583515	2025-09-16 19:56:35.583515	OFFLINE	14	DevStudio Academy, Conference Room A	\N	15	22	93	2025-08-27 20:57:54.730626	2025-09-09 17:56:35.585211	General	All Levels	\N
124	Responsive Design & Bootstrap	Week 4 - 2 hour intensive session	2025-09-19 17:56:35.583515	2025-09-19 19:56:35.583515	HYBRID	13	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-7716	15	22	93	2025-08-27 20:57:54.730627	2025-09-09 17:56:35.585211	General	All Levels	\N
151	Testing & Quality Assurance	Internship Week 5 - Real project work (4h)	2025-07-30 09:00:00	2025-07-30 13:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-9134	16	\N	93	2025-08-27 20:57:54.737646	2025-08-27 20:57:54.737646	General	All Levels	\N
152	Performance Optimization	Internship Week 5 - Real project work (3h)	2025-08-01 09:00:00	2025-08-01 12:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-5590	16	\N	94	2025-08-27 20:57:54.737647	2025-08-27 20:57:54.737647	General	All Levels	\N
153	Security Audit & Fixes	Internship Week 6 - Real project work (4h)	2025-08-06 09:00:00	2025-08-06 13:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-4140	16	\N	94	2025-08-27 20:57:54.737647	2025-08-27 20:57:54.737648	General	All Levels	\N
154	User Acceptance Testing	Internship Week 6 - Real project work (3h)	2025-08-08 09:00:00	2025-08-08 12:00:00	HYBRID	10	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-3393	16	\N	93	2025-08-27 20:57:54.737648	2025-08-27 20:57:54.737648	General	All Levels	\N
155	Production Deployment	Internship Week 7 - Real project work (4h)	2025-08-13 09:00:00	2025-08-13 13:00:00	HYBRID	10	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-4519	16	26	95	2025-08-27 20:57:54.737649	2025-08-27 20:57:54.737649	General	All Levels	\N
156	Documentation & Handover	Internship Week 7 - Real project work (4h)	2025-08-15 09:00:00	2025-08-15 13:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-4767	16	\N	93	2025-08-27 20:57:54.73765	2025-08-27 20:57:54.73765	General	All Levels	\N
157	Client Presentation & Demo	Internship Week 8 - Real project work (4h)	2025-08-20 09:00:00	2025-08-20 13:00:00	HYBRID	8	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-3377	16	\N	93	2025-08-27 20:57:54.73765	2025-08-27 20:57:54.737651	General	All Levels	\N
158	Project Retrospective	Internship Week 8 - Real project work (3h)	2025-08-22 09:00:00	2025-08-22 12:00:00	HYBRID	10	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-3288	16	\N	93	2025-08-27 20:57:54.737651	2025-08-27 20:57:54.737651	General	All Levels	\N
159	Portfolio Development	Internship Week 8 - Real project work (4h)	2025-08-20 09:00:00	2025-08-20 13:00:00	HYBRID	10	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-4239	16	\N	93	2025-08-27 20:57:54.737652	2025-08-27 20:57:54.737652	General	All Levels	\N
160	Industry Best Practices	Internship Week 8 - Real project work (3h)	2025-08-22 09:00:00	2025-08-22 12:00:00	HYBRID	9	DevStudio Academy, Project Lab	https://meet.devstudio.com/internship-6724	16	\N	93	2025-08-27 20:57:54.737652	2025-08-27 20:57:54.737653	General	All Levels	\N
162	Test Session - 24h deadline	\N	2025-09-01 10:00:00	2025-09-01 11:00:00	ONLINE	10	\N	\N	18	\N	\N	2025-08-31 15:03:14.367767	2025-08-31 15:03:14.367772	General	All Levels	\N
163	Test Session - 48h safe	\N	2025-09-03 14:00:00	2025-09-03 15:00:00	ONLINE	10	\N	\N	18	\N	\N	2025-08-31 15:04:07.857164	2025-08-31 15:04:07.857166	General	All Levels	\N
164	Test Past Session	\N	2025-08-30 10:00:00	2025-08-30 11:00:00	ONLINE	10	\N	\N	18	\N	\N	2025-08-31 15:13:58.408999	2025-08-31 15:13:58.409003	General	All Levels	\N
169	Advanced Football Training	Tactical drills, match preparation, and advanced techniques for experienced players	2025-09-10 14:15:00	2025-09-11 14:20:00	HYBRID	1	online		18	\N	\N	2025-09-02 17:46:10.47302	2025-09-03 04:28:08.539374	Football	Advanced	Coach Martinez
168	Test Session Creation Fix	Testing the frontend fix	2025-09-03 14:00:00	2025-09-03 15:00:00	ONLINE	10	\N	\N	18	\N	\N	2025-09-02 13:32:17.072063	2025-09-02 13:32:17.072067	General	All Levels	\N
161	szerdai hahota	elmegyünk nevetni szerdán közösen 	2025-09-03 11:20:00	2025-09-03 11:21:00	ONLINE	1		http://localhost:3000/admin	17	\N	93	2025-08-31 09:38:47.333476	2025-09-03 11:16:38.78925	General	All Levels	\N
175	Vue.js Testing - HTTP 400 Fix Session	Session for testing HTTP 400 feedback bug fix	2025-09-04 15:00:00	2025-09-04 17:00:00	OFFLINE	15	Test Room HTTP400	\N	15	\N	109	2025-09-06 13:05:38.844893	2025-09-06 13:05:38.844897	General	All Levels	\N
176	API Test Session - Final Test	Session for API testing	2025-09-05 10:00:00	2025-09-05 12:00:00	OFFLINE	10	API Test Room	\N	15	\N	109	2025-09-06 13:08:44.929921	2025-09-06 13:08:44.929923	General	All Levels	\N
181	Final HTTP 400 Fix Verification	\N	2025-09-05 13:16:19.024871	2025-09-05 14:16:19.024878	OFFLINE	10	\N	\N	15	\N	109	2025-09-06 13:16:19.025743	2025-09-06 13:16:19.025745	General	All Levels	\N
183	Test Booking Session	Testing if booking works after fix	2025-09-07 10:00:00	2025-09-07 11:00:00	OFFLINE	10	Test Room	\N	19	22	93	2025-09-06 13:57:00.104881	2025-09-06 13:57:00.104883	General	All Levels	\N
184	Test Booking Session 2	Testing booking more than 24h ahead	2025-09-08 10:00:00	2025-09-08 11:00:00	OFFLINE	10	Test Room 2	\N	19	22	93	2025-09-06 13:57:18.520653	2025-09-06 13:57:18.520655	General	All Levels	\N
170	JavaScript Basics - COMPLETED	Introduction to JavaScript programming	2025-09-03 10:15:38.24148	2025-09-03 12:15:38.241488	OFFLINE	20	Room A101	\N	20	28	111	2025-09-06 10:15:38.250247	2025-09-06 10:15:38.250251	Programming	Beginner	Dr. Johnson
171	CSS Advanced Techniques	Advanced CSS styling techniques	2025-08-30 10:15:38.241491	2025-08-30 12:15:38.241492	OFFLINE	20	Room A102	\N	20	28	111	2025-09-06 10:15:38.250252	2025-09-06 10:15:38.250252	Programming	Intermediate	Dr. Johnson
172	React Fundamentals	Introduction to React.js	2025-09-08 10:15:38.241494	2025-09-08 12:15:38.241494	OFFLINE	20	Room A103	\N	20	28	111	2025-09-06 10:15:38.250253	2025-09-06 10:15:38.250253	Programming	Intermediate	Dr. Johnson
126	Node.js Server Development	Week 6 - 3 hour intensive session	2025-04-07 09:00:00	2025-04-07 12:00:00	OFFLINE	13	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-6382	15	23	94	2025-08-27 20:57:54.730628	2025-08-27 20:57:54.730629	Programming	Advanced	Dr. Johnson
173	Node.js Backend Development	Building APIs with Node.js	2025-09-11 10:15:38.241496	2025-09-11 12:15:38.241497	OFFLINE	20	Room A104	\N	20	28	111	2025-09-06 10:15:38.250254	2025-09-06 10:15:38.250254	Programming	Advanced	Dr. Johnson
219	🚀 ACTIVE Check-in Test Session	This session is currently active - you can check in now!	2025-09-06 20:55:46	2025-09-06 21:55:46	OFFLINE	20	Test Lab A	\N	19	\N	111	2025-09-06 21:26:58.291877	\N	programming	intermediate	\N
220	📅 Future Booking Test	This session starts in 2 hours - book it now	2025-09-06 23:25:46	2025-09-07 00:25:46	OFFLINE	15	Test Lab B	\N	19	\N	111	2025-09-06 21:26:58.291877	\N	football	beginner	\N
221	⏰ Past Session - Attendance Pending	This session ended 1 hour ago - attendance is pending	2025-09-06 19:25:46	2025-09-06 20:25:46	OFFLINE	10	Test Lab C	\N	19	\N	111	2025-09-06 21:26:58.291877	\N	basketball	advanced	\N
222	🔥 LIVE SESSION - Check-in Test	This session is currently ACTIVE! Test your check-in functionality now!	2025-09-06 21:04:38.724434	2025-09-06 22:04:38.724434	OFFLINE	25	Live Test Arena	\N	19	\N	111	2025-09-06 23:04:42.143614	\N	basketball	intermediate	\N
226	LIVE - Football Training Session	Live session for testing check-in functionality	2025-09-07 08:42:31.091764	2025-09-07 09:42:31.091764	OFFLINE	20	Main Field	\N	18	22	2	2025-09-07 08:57:31.094157	2025-09-07 08:57:31.094161	General	All Levels	\N
223	Live Football Training Session	Current live training session for testing live check-in functionality	2025-09-07 07:00:00	2025-09-07 08:00:00	OFFLINE	20	Main Football Field	\N	17	\N	\N	2025-09-07 07:20:30.793028	2025-09-07 07:44:50.603518	Football	Intermediate	Coach Martinez
227	Test Future Session	A test session for booking functionality	2025-10-09 17:56:01.819784	2025-10-09 19:56:01.819784	OFFLINE	10	Test Room	\N	20	\N	111	2025-09-09 17:56:01.821303	2025-09-09 17:56:01.821307	General	All Levels	\N
125	Frontend Testing (Jest, Cypress)	Week 5 - 3 hour intensive session	2025-09-22 17:56:35.583515	2025-09-22 19:56:35.583515	HYBRID	13	DevStudio Academy, Conference Room A	https://meet.devstudio.com/session-2381	15	22	93	2025-08-27 20:57:54.730628	2025-09-09 17:56:35.585212	General	All Levels	\N
127	Express.js API Design	Week 6 - 2 hour intensive session	2025-09-25 17:56:35.583515	2025-09-25 19:56:35.583515	HYBRID	13	\N	\N	15	23	94	2025-08-27 20:57:54.730629	2025-09-09 17:56:35.585212	General	All Levels	\N
\.


--
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.user_achievements (id, user_id, badge_type, title, description, icon, earned_at, semester_count) FROM stdin;
1	97	returning_student	🔄 Returning Student	Participated in 5 semesters!	🔄	2025-09-07 09:14:16.055509	5
2	97	veteran_student	🏅 Veteran Student	A seasoned learner with 5 semesters!	🏅	2025-09-07 09:14:16.058877	5
3	97	master_student	👑 Master Student	A true master with 5 semesters!	👑	2025-09-07 09:14:16.060487	5
4	97	feedback_champion	💬 Feedback Champion	Provided 17 valuable feedbacks!	💬	2025-09-07 09:14:16.062069	\N
5	113	returning_student	🔄 Returning Student	Participated in 2 semesters!	🔄	2025-09-09 17:57:14.10886	2
\.


--
-- Data for Name: user_stats; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.user_stats (id, user_id, semesters_participated, first_semester_date, current_streak, total_bookings, total_attended, total_cancelled, attendance_rate, feedback_given, average_rating_given, punctuality_score, total_xp, level, created_at, updated_at) FROM stdin;
3	111	0	\N	0	0	0	0	0	0	0	0	0	1	2025-09-08 22:41:40.511142	2025-09-08 22:46:23.131138
2	113	2	2025-07-08 00:00:00	0	2	0	0	0	0	0	0	1000	1	2025-09-07 09:45:22.270296	2025-09-09 17:57:52.036845
1	97	5	2025-03-01 00:00:00	0	51	33	9	64.70588235294117	19	3.6052631578947367	0	4625	4	2025-09-07 09:14:15.830676	2025-09-10 19:38:30.516318
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: lovas.zoltan
--

COPY public.users (id, name, email, password_hash, role, is_active, created_at, updated_at, created_by) FROM stdin;
2	System Administrator	admin@company.com	$2b$12$TfOwfOEl5IEJv0By4lbOB.VmfdyjI9XjSAaGuU9E/n8athwFiUB9m	ADMIN	t	2025-08-26 18:54:09.561392	2025-08-26 18:54:09.561396	\N
107	System Administrator	admin@yourcompany.com	$2b$12$.qpVXJ41V32u6uzI.EEA0O.tVfGLv8Z9RPNsVx4p7Xl3LUiDc81cC	ADMIN	t	2025-09-02 04:38:19.611325	2025-09-02 04:43:11.328618	\N
105	Lucas Mueller	lucas.mueller@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	f	2025-08-27 20:57:54.716209	2025-09-02 08:36:39.518463	\N
104	Priya Sharma	priya.sharma@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	f	2025-08-27 20:57:54.716208	2025-09-02 08:36:42.499298	\N
102	Sofia Andersson	sofia.andersson@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	f	2025-08-27 20:57:54.716206	2025-09-02 08:36:50.216455	\N
109	Alex Smith	alex@example.com	$2b$12$0nD1uXGVBoi71y1.QLGEZ.F98mqLmoA8o/KC6S5Yk089DL1zsixVa	STUDENT	t	2025-09-06 10:14:31.368941	2025-09-06 10:14:31.368946	\N
110	Maria Garcia	maria@example.com	$2b$12$5X.dOXLT4GOcZVj6UiLUTuAwuoNzauNxHCmqgKacu8PK1qmeU/mxW	STUDENT	t	2025-09-06 10:14:31.368947	2025-09-06 10:14:31.368948	\N
97	Alex Johnson	alex.johnson@student.devstudio.com	$2b$12$QHL1B160z1WP8ZAdDHRnkel2GovUscrMUAHKDelf5Xbxv/vgFjTPy	STUDENT	t	2025-08-27 20:57:54.716198	2025-09-02 13:19:06.29243	\N
113	Emma Newcomer	emma.newcomer@student.devstudio.com	$2b$12$UHrr9cb.xj2Xs390.oAgKuplvgJqZUFsNgTqI3aExahYdKFKEdRgy	STUDENT	t	2025-09-07 09:45:07.102756	2025-09-07 09:45:07.102761	\N
114	Test Student	test.student@devstudio.com	$2b$12$nOPrqNyg1e0hTxFZBk580eGcpwhPZnwRVZJSpmZ8MajAn3WbBGgdS	STUDENT	t	2025-09-08 18:54:48.424962	2025-09-08 18:54:48.424971	\N
111	Dr. Johnson	instructor@example.com	$2b$12$MDNM1YQV9EaxnEQZiFzD8etB1/3CevywukAZ.YzA25bT2ijWtoPlO	INSTRUCTOR	t	2025-09-06 10:14:31.368948	2025-09-08 22:41:08.670842	\N
106	Zoe Williams	zoe.williams@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	t	2025-08-27 20:57:54.716209	2025-09-09 17:59:43.001867	\N
103	Ryan O'Connor	ryan.oconnor@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	t	2025-08-27 20:57:54.716207	2025-09-09 18:06:50.932938	\N
93	Sarah Chen	sarah.chen@devstudio.com	$2b$12$qmihYa8aHtmyrD4d1u3iWe4gzEbVS5u2z/nABbcILvce7HhtTUHG6	INSTRUCTOR	t	2025-08-27 20:57:54.480188	2025-08-27 20:57:54.480192	\N
94	Marcus Rodriguez	marcus.rodriguez@devstudio.com	$2b$12$qmihYa8aHtmyrD4d1u3iWe4gzEbVS5u2z/nABbcILvce7HhtTUHG6	INSTRUCTOR	t	2025-08-27 20:57:54.480193	2025-08-27 20:57:54.480193	\N
95	Dr. Elena Kowalski	elena.kowalski@devstudio.com	$2b$12$qmihYa8aHtmyrD4d1u3iWe4gzEbVS5u2z/nABbcILvce7HhtTUHG6	INSTRUCTOR	t	2025-08-27 20:57:54.480194	2025-08-27 20:57:54.480194	\N
96	James Thompson	james.thompson@devstudio.com	$2b$12$qmihYa8aHtmyrD4d1u3iWe4gzEbVS5u2z/nABbcILvce7HhtTUHG6	INSTRUCTOR	t	2025-08-27 20:57:54.480195	2025-08-27 20:57:54.480195	\N
98	Maria Garcia	maria.garcia@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	t	2025-08-27 20:57:54.716203	2025-08-27 20:57:54.716204	\N
99	David Kim	david.kim@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	t	2025-08-27 20:57:54.716204	2025-08-27 20:57:54.716204	\N
100	Emma Wilson	emma.wilson@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	t	2025-08-27 20:57:54.716205	2025-08-27 20:57:54.716205	\N
101	Michael Brown	michael.brown@student.devstudio.com	$2b$12$196FLroKT3qLBAyqcVTFxerGwS0iYJ1S.fpwf6CeEyRyh61q83E9e	STUDENT	t	2025-08-27 20:57:54.716206	2025-08-27 20:57:54.716206	\N
\.


--
-- Name: attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.attendance_id_seq', 1074, true);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.bookings_id_seq', 1294, true);


--
-- Name: feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.feedback_id_seq', 112, true);


--
-- Name: groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.groups_id_seq', 28, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: project_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_enrollments_id_seq', 8, true);


--
-- Name: project_milestone_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_milestone_progress_id_seq', 32, true);


--
-- Name: project_milestones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_milestones_id_seq', 8, true);


--
-- Name: project_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.project_sessions_id_seq', 1, false);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.projects_id_seq', 2, true);


--
-- Name: quiz_answer_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_answer_options_id_seq', 136, true);


--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_attempts_id_seq', 30, true);


--
-- Name: quiz_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_questions_id_seq', 42, true);


--
-- Name: quiz_user_answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quiz_user_answers_id_seq', 84, true);


--
-- Name: quizzes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.quizzes_id_seq', 10, true);


--
-- Name: semesters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.semesters_id_seq', 20, true);


--
-- Name: sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.sessions_id_seq', 227, true);


--
-- Name: user_achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.user_achievements_id_seq', 5, true);


--
-- Name: user_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.user_stats_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lovas.zoltan
--

SELECT pg_catalog.setval('public.users_id_seq', 114, true);


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
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


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
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: lovas.zoltan
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (id);


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
-- Name: ix_notifications_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);


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
-- Name: ix_project_sessions_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_project_sessions_id ON public.project_sessions USING btree (id);


--
-- Name: ix_projects_id; Type: INDEX; Schema: public; Owner: lovas.zoltan
--

CREATE INDEX ix_projects_id ON public.projects USING btree (id);


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

\unrestrict cCEhO5k1xLEP19eFcN2kUdztN30q8RKsowl0h7cgFR9cPI9XIeXEz0bFBF22zHw

