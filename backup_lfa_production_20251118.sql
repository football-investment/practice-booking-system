--
-- PostgreSQL database dump
--

\restrict yYDqNttrOHNhjprrbpkJxtJVMrh0wIhnz3EZR2OIa1b66pgGvaNJH1Wezo8U7hE

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: achievements; Type: TABLE; Schema: public; Owner: lfa_user
--

CREATE TABLE public.achievements (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    category character varying(50) NOT NULL,
    requirement_type character varying(50) NOT NULL,
    requirement_value integer NOT NULL,
    xp_reward integer DEFAULT 0,
    credits_reward integer DEFAULT 0,
    icon character varying(100),
    rarity character varying(20) DEFAULT 'common'::character varying,
    is_hidden boolean DEFAULT false,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.achievements OWNER TO lfa_user;

--
-- Name: achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: lfa_user
--

CREATE SEQUENCE public.achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.achievements_id_seq OWNER TO lfa_user;

--
-- Name: achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lfa_user
--

ALTER SEQUENCE public.achievements_id_seq OWNED BY public.achievements.id;


--
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: lfa_user
--

CREATE TABLE public.user_achievements (
    id integer NOT NULL,
    user_id integer NOT NULL,
    achievement_id integer NOT NULL,
    earned_at timestamp with time zone DEFAULT now(),
    current_progress integer DEFAULT 0,
    is_completed boolean DEFAULT false
);


ALTER TABLE public.user_achievements OWNER TO lfa_user;

--
-- Name: user_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: lfa_user
--

CREATE SEQUENCE public.user_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_achievements_id_seq OWNER TO lfa_user;

--
-- Name: user_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lfa_user
--

ALTER SEQUENCE public.user_achievements_id_seq OWNED BY public.user_achievements.id;


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: lfa_user
--

CREATE TABLE public.user_sessions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    session_token character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp without time zone NOT NULL,
    is_active boolean,
    ip_address character varying(45),
    user_agent text
);


ALTER TABLE public.user_sessions OWNER TO lfa_user;

--
-- Name: user_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: lfa_user
--

CREATE SEQUENCE public.user_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_sessions_id_seq OWNER TO lfa_user;

--
-- Name: user_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lfa_user
--

ALTER SEQUENCE public.user_sessions_id_seq OWNED BY public.user_sessions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: lfa_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(100) NOT NULL,
    display_name character varying(100),
    bio text,
    profile_picture character varying(255),
    favorite_position character varying(50),
    is_active boolean DEFAULT true,
    user_type character varying(20) DEFAULT 'user'::character varying,
    is_premium boolean DEFAULT false,
    level integer DEFAULT 1,
    xp integer DEFAULT 0,
    credits integer DEFAULT 5,
    games_played integer DEFAULT 0,
    games_won integer DEFAULT 0,
    friend_count integer DEFAULT 0,
    achievement_points integer DEFAULT 0,
    average_performance real DEFAULT 0.0,
    last_activity timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    premium_expires_at timestamp without time zone,
    games_lost integer DEFAULT 0,
    total_playtime_minutes integer DEFAULT 0,
    best_scores jsonb DEFAULT '{}'::jsonb,
    skill_ratings jsonb DEFAULT '{}'::jsonb,
    skills jsonb DEFAULT '{}'::jsonb,
    challenge_wins integer DEFAULT 0,
    challenge_losses integer DEFAULT 0,
    tournament_wins integer DEFAULT 0,
    notification_preferences jsonb DEFAULT '{}'::jsonb,
    privacy_settings jsonb DEFAULT '{}'::jsonb,
    login_count integer DEFAULT 0,
    last_purchase_date timestamp without time zone,
    total_credits_purchased integer DEFAULT 0,
    transaction_history jsonb DEFAULT '[]'::jsonb,
    language character varying(10) DEFAULT 'en'::character varying,
    timezone character varying(50) DEFAULT 'UTC'::character varying,
    last_login timestamp without time zone,
    total_score double precision DEFAULT 0.0
);


ALTER TABLE public.users OWNER TO lfa_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: lfa_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO lfa_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: lfa_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: achievements id; Type: DEFAULT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.achievements ALTER COLUMN id SET DEFAULT nextval('public.achievements_id_seq'::regclass);


--
-- Name: user_achievements id; Type: DEFAULT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_achievements ALTER COLUMN id SET DEFAULT nextval('public.user_achievements_id_seq'::regclass);


--
-- Name: user_sessions id; Type: DEFAULT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_sessions ALTER COLUMN id SET DEFAULT nextval('public.user_sessions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: achievements; Type: TABLE DATA; Schema: public; Owner: lfa_user
--

COPY public.achievements (id, name, description, category, requirement_type, requirement_value, xp_reward, credits_reward, icon, rarity, is_hidden, is_active, created_at) FROM stdin;
1	First Steps	Complete your first challenge	progression	challenges_completed	1	25	5	\N	common	f	t	2025-08-24 19:12:50.905892+02
2	Rising Star	Reach level 5	progression	level_reached	5	100	25	\N	rare	f	t	2025-08-24 19:12:50.905892+02
3	Champion	Win 10 challenges in a row	competitive	win_streak	10	200	50	\N	epic	f	t	2025-08-24 19:12:50.905892+02
4	Social Butterfly	Add 5 friends	social	friends_count	5	50	10	\N	common	f	t	2025-08-24 19:12:50.905892+02
5	XP Master	Earn 1000 total XP	progression	total_xp	1000	150	30	\N	rare	f	t	2025-08-24 19:12:50.905892+02
\.


--
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: lfa_user
--

COPY public.user_achievements (id, user_id, achievement_id, earned_at, current_progress, is_completed) FROM stdin;
\.


--
-- Data for Name: user_sessions; Type: TABLE DATA; Schema: public; Owner: lfa_user
--

COPY public.user_sessions (id, user_id, session_token, created_at, expires_at, is_active, ip_address, user_agent) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: lfa_user
--

COPY public.users (id, username, email, hashed_password, full_name, display_name, bio, profile_picture, favorite_position, is_active, user_type, is_premium, level, xp, credits, games_played, games_won, friend_count, achievement_points, average_performance, last_activity, created_at, updated_at, premium_expires_at, games_lost, total_playtime_minutes, best_scores, skill_ratings, skills, challenge_wins, challenge_losses, tournament_wins, notification_preferences, privacy_settings, login_count, last_purchase_date, total_credits_purchased, transaction_history, language, timezone, last_login, total_score) FROM stdin;
1	fixtest003	fixtest003@test.com	$2b$12$XFEFGaWD7BN/O85ysdXahucP7/sQAWYrlHFAQ24JjcBsNk0VjUVx2	Fix Test User 3	\N	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	2025-08-24 13:10:27.940472+02	2025-08-24 13:10:27.940472+02	2025-08-24 13:10:27.940472+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	\N	0
2	verify_claude_001	verify001@test.com	$2b$12$AYPOkrZQlzRvbV/Inmu6Me7QHER9MHEUWrY/Y8EU/azsfWk0Zj2VK	Verify Claude User	\N	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	2025-08-24 13:12:57.742498+02	2025-08-24 13:12:57.742498+02	2025-08-24 13:12:57.742498+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	\N	0
3	schema_test_user_1756054140169185	schema_test_1756054140169195@testcom	test_hash_12345	Schema Test User	\N	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	\N	2025-08-24 16:49:00.170245+02	2025-08-24 18:49:00.1592+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	\N	0
4	final_test_user_direct	finaltest_direct@example.com	$2b$12$3tN4cisgu83CqMGrR0xFGOl1MJ1paW3PQuc85tX/bioRZmm2/0/sK	Final Test User Direct	\N	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	\N	2025-08-24 16:50:48.979824+02	2025-08-24 18:50:48.473119+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	\N	0
5	final_test_user_curl	finaltest_curl@example.com	$2b$12$WWmPQkG.mm.QNtanKG5LqewoSsXp76Ac1TxP0kYffETRjeSQ7V7y6	Final Test User Curl	\N	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	\N	2025-08-24 16:51:25.37089+02	2025-08-24 18:51:25.101877+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	\N	0
7	gamification_test_user	gamification@test.com	$2b$12$uVf3FEI1ceWXjmyVGD9YnuBPcbSugmgfQqySTZZ4QVuvp6JR6Xduq	Gamification Test User	Gamification Test User	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	2025-08-24 17:08:22.109525+02	2025-08-24 17:08:22.109519+02	2025-08-24 19:08:21.833885+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	2025-08-24 17:08:22.109523	0
8	gamification_test_user2	gamification2@test.com	$2b$12$7BJSFjnqKjP6QnZzFMZFF.8RInXo1jfb1uGigXMNyL8DSKOKBViK2	Gamification Test User 2	Gamification Test User 2	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	2025-08-24 17:09:15.152661+02	2025-08-24 17:09:15.152656+02	2025-08-24 19:09:14.900338+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	0	\N	0	[]	en	UTC	2025-08-24 17:09:15.15266	0
9	gamification_test_user3	gamification3@test.com	$2b$12$U0sYVYm5du6TFK13ucR43Oz/mRoRE2A3a0HYSD7QP7IcZtQ.29qJm	Gamification Test User 3	Gamification Test User 3	\N	\N	\N	t	user	f	6	1045	5	1	1	0	0	0	2025-08-24 17:09:38.341088+02	2025-08-24 17:09:38.341082+02	2025-08-24 19:09:38.063705+02	\N	0	0	{}	{}	{}	1	0	0	{}	{}	0	\N	0	[]	en	UTC	2025-08-24 17:09:38.341087	0
6	validation_test_user	validation@test.com	$2b$12$QFT/jUFCxLxMZ9dPHJr1NOIoHnThcMrInd5DM3GA//bXgX0/vMsmC	Validation Test User	Validation Test User	\N	\N	\N	t	user	f	1	0	5	0	0	0	0	0	2025-08-25 06:37:05.280462+02	2025-08-24 16:54:29.929578+02	2025-08-24 18:54:29.637387+02	\N	0	0	{}	{}	{}	0	0	0	{}	{}	1	\N	0	[]	en	UTC	2025-08-25 06:37:05.280483	0
\.


--
-- Name: achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lfa_user
--

SELECT pg_catalog.setval('public.achievements_id_seq', 5, true);


--
-- Name: user_achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lfa_user
--

SELECT pg_catalog.setval('public.user_achievements_id_seq', 1, false);


--
-- Name: user_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lfa_user
--

SELECT pg_catalog.setval('public.user_sessions_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: lfa_user
--

SELECT pg_catalog.setval('public.users_id_seq', 9, true);


--
-- Name: achievements achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.achievements
    ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);


--
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (id);


--
-- Name: user_achievements user_achievements_user_id_achievement_id_key; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_user_id_achievement_id_key UNIQUE (user_id, achievement_id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_user_sessions_id; Type: INDEX; Schema: public; Owner: lfa_user
--

CREATE INDEX ix_user_sessions_id ON public.user_sessions USING btree (id);


--
-- Name: ix_user_sessions_session_token; Type: INDEX; Schema: public; Owner: lfa_user
--

CREATE UNIQUE INDEX ix_user_sessions_session_token ON public.user_sessions USING btree (session_token);


--
-- Name: user_achievements user_achievements_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_achievement_id_fkey FOREIGN KEY (achievement_id) REFERENCES public.achievements(id) ON DELETE CASCADE;


--
-- Name: user_achievements user_achievements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: lfa_user
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: lovas.zoltan
--

GRANT ALL ON SCHEMA public TO lfa_user;


--
-- PostgreSQL database dump complete
--

\unrestrict yYDqNttrOHNhjprrbpkJxtJVMrh0wIhnz3EZR2OIa1b66pgGvaNJH1Wezo8U7hE

