--
-- PostgreSQL database dump
--

\restrict 57YmORFZgsvJljbBaXCWewkAF7zeDejJwVOn19DqmoOG6fymDynYRcy63xjIUSz

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
-- Data for Name: semesters; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.semesters VALUES (15, 'TOURN-20260123-001', '🇧🇷 BR - "Neymar''s Five " - RIO', '2026-01-23', '2026-01-23', 'INSTRUCTOR_ASSIGNED', 'IN_PROGRESS', true, 50, '2026-01-22 20:15:19.682911', '2026-01-22 20:19:52.096039', 3, 'LFA_FOOTBALL_PLAYER', 'AMATEUR', NULL, NULL, 4, 4, NULL, NULL, NULL, 3, NULL, 'INDIVIDUAL', false, true, '2026-01-22 19:19:52.094594', 'OPEN_ASSIGNMENT', 20, 'custom', '{"version": "1.0.0", "description": "Custom reward policy", "policy_name": "custom", "placement_rewards": {"1ST": {"xp": 5000, "credits": 10000}, "2ND": {"xp": 3000, "credits": 5000}, "3RD": {"xp": 2000, "credits": 2500}, "PARTICIPANT": {"xp": 500, "credits": 150}}}');
INSERT INTO public.semesters VALUES (10, 'TOURN-20260122-001', '🇦🇹 AT - "Nike Winter Cup ''26" - VIE', '2026-01-22', '2026-01-22', 'INSTRUCTOR_ASSIGNED', 'REWARDS_DISTRIBUTED', true, 350, '2026-01-21 10:17:06.745971', '2026-01-21 19:11:06.666648', 3, 'LFA_FOOTBALL_PLAYER', 'AMATEUR', NULL, NULL, 2, 2, NULL, NULL, NULL, 1, NULL, 'INDIVIDUAL', false, true, '2026-01-21 09:37:14.767878', 'OPEN_ASSIGNMENT', 12, 'default', '{"version": "1.0.0", "description": "Standard reward policy for all tournament types and specializations", "policy_name": "default", "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"], "placement_rewards": {"1ST": {"xp": 500, "credits": 100}, "2ND": {"xp": 300, "credits": 50}, "3RD": {"xp": 200, "credits": 25}, "PARTICIPANT": {"xp": 50, "credits": 0}}, "participation_rewards": {"session_attendance": {"xp": 10, "credits": 0}}, "applies_to_all_tournament_types": true}');
INSERT INTO public.semesters VALUES (12, 'TOURN-20260122-002', '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO', '2026-01-22', '2026-01-22', 'INSTRUCTOR_ASSIGNED', 'REWARDS_DISTRIBUTED', true, 100, '2026-01-21 20:28:22.5418', '2026-01-21 22:51:09.762471', 3, 'LFA_FOOTBALL_PLAYER', 'AMATEUR', NULL, NULL, 5, 4, NULL, NULL, NULL, 3, NULL, 'INDIVIDUAL', false, true, '2026-01-21 21:35:47.280782', 'OPEN_ASSIGNMENT', 10, 'custom', '{"version": "1.0.0", "description": "Custom reward policy", "policy_name": "custom", "placement_rewards": {"1ST": {"xp": 1500, "credits": 1000}, "2ND": {"xp": 700, "credits": 500}, "3RD": {"xp": 275, "credits": 250}, "PARTICIPANT": {"xp": 100, "credits": 50}}}');


--
-- Data for Name: semester_enrollments; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.semester_enrollments VALUES (9, 4, 10, 22, 'APPROVED', '2026-01-21 09:35:17.291097+01', '2026-01-21 09:35:17.291082+01', 4, NULL, NULL, true, NULL, NULL, true, '2026-01-21 09:35:17.291092+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-21 10:35:17.296837+01', '2026-01-21 10:35:17.296841+01');
INSERT INTO public.semester_enrollments VALUES (10, 5, 10, 23, 'APPROVED', '2026-01-21 09:35:37.650809+01', '2026-01-21 09:35:37.650794+01', 5, NULL, NULL, true, NULL, NULL, true, '2026-01-21 09:35:37.650804+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 10:35:37.653971+01', '2026-01-21 10:35:37.653974+01');
INSERT INTO public.semester_enrollments VALUES (11, 6, 10, 24, 'APPROVED', '2026-01-21 09:36:00.185574+01', '2026-01-21 09:36:00.185564+01', 6, NULL, NULL, true, NULL, NULL, true, '2026-01-21 09:36:00.185571+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 10:36:00.187176+01', '2026-01-21 10:36:00.187178+01');
INSERT INTO public.semester_enrollments VALUES (12, 7, 10, 25, 'APPROVED', '2026-01-21 09:36:19.893586+01', '2026-01-21 09:36:19.89357+01', 7, NULL, NULL, true, NULL, NULL, true, '2026-01-21 09:36:19.893581+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 10:36:19.897001+01', '2026-01-21 10:36:19.897004+01');
INSERT INTO public.semester_enrollments VALUES (13, 4, 12, 22, 'APPROVED', '2026-01-21 20:10:23.050484+01', '2026-01-21 20:10:23.050475+01', 4, NULL, NULL, true, NULL, NULL, true, '2026-01-21 20:10:23.050481+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-21 21:10:23.057422+01', '2026-01-21 21:10:23.057426+01');
INSERT INTO public.semester_enrollments VALUES (14, 5, 12, 23, 'APPROVED', '2026-01-21 20:11:09.328478+01', '2026-01-21 20:11:09.328463+01', 5, NULL, NULL, true, NULL, NULL, true, '2026-01-21 20:11:09.328472+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 21:11:09.330925+01', '2026-01-21 21:11:09.330929+01');
INSERT INTO public.semester_enrollments VALUES (15, 6, 12, 24, 'APPROVED', '2026-01-21 20:14:35.974455+01', '2026-01-21 20:14:35.974441+01', 6, NULL, NULL, true, NULL, NULL, true, '2026-01-21 20:14:35.97445+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 21:14:35.982329+01', '2026-01-21 21:14:35.982332+01');
INSERT INTO public.semester_enrollments VALUES (16, 7, 12, 25, 'APPROVED', '2026-01-21 20:15:10.483095+01', '2026-01-21 20:15:10.483081+01', 7, NULL, NULL, true, NULL, NULL, true, '2026-01-21 20:15:10.48309+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 21:15:10.485558+01', '2026-01-21 21:15:10.485561+01');
INSERT INTO public.semester_enrollments VALUES (17, 13, 12, 31, 'APPROVED', '2026-01-21 21:28:17.201185+01', '2026-01-21 21:28:17.201169+01', 13, NULL, NULL, true, NULL, NULL, true, '2026-01-21 21:28:17.201181+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-21 22:28:17.204869+01', '2026-01-21 22:28:17.204874+01');
INSERT INTO public.semester_enrollments VALUES (18, 14, 12, 32, 'APPROVED', '2026-01-21 21:28:48.552131+01', '2026-01-21 21:28:48.552115+01', 14, NULL, NULL, true, NULL, NULL, true, '2026-01-21 21:28:48.552126+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-21 22:28:48.554709+01', '2026-01-21 22:28:48.554713+01');
INSERT INTO public.semester_enrollments VALUES (19, 15, 12, 33, 'APPROVED', '2026-01-21 21:29:22.320111+01', '2026-01-21 21:29:22.320092+01', 15, NULL, NULL, true, NULL, NULL, true, '2026-01-21 21:29:22.320106+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-21 22:29:22.323386+01', '2026-01-21 22:29:22.323389+01');
INSERT INTO public.semester_enrollments VALUES (20, 16, 12, 34, 'APPROVED', '2026-01-21 21:29:53.686761+01', '2026-01-21 21:29:53.686748+01', 16, NULL, NULL, true, NULL, NULL, true, '2026-01-21 21:29:53.686756+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-21 22:29:53.68904+01', '2026-01-21 22:29:53.689043+01');
INSERT INTO public.semester_enrollments VALUES (37, 4, 15, 22, 'APPROVED', '2026-01-22 19:16:41.82843+01', '2026-01-22 19:16:41.828417+01', 4, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:16:41.828427+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-22 20:16:41.834201+01', '2026-01-22 20:16:41.834206+01');
INSERT INTO public.semester_enrollments VALUES (38, 5, 15, 23, 'APPROVED', '2026-01-22 19:17:02.024861+01', '2026-01-22 19:17:02.024846+01', 5, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:17:02.024856+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-22 20:17:02.028778+01', '2026-01-22 20:17:02.028782+01');
INSERT INTO public.semester_enrollments VALUES (39, 6, 15, 24, 'APPROVED', '2026-01-22 19:17:30.158425+01', '2026-01-22 19:17:30.15841+01', 6, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:17:30.15842+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-22 20:17:30.16329+01', '2026-01-22 20:17:30.163292+01');
INSERT INTO public.semester_enrollments VALUES (40, 7, 15, 25, 'APPROVED', '2026-01-22 19:17:54.189384+01', '2026-01-22 19:17:54.18937+01', 7, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:17:54.189379+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-22 20:17:54.193067+01', '2026-01-22 20:17:54.19307+01');
INSERT INTO public.semester_enrollments VALUES (41, 13, 15, 31, 'APPROVED', '2026-01-22 19:18:18.821005+01', '2026-01-22 19:18:18.820994+01', 13, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:18:18.821001+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-22 20:18:18.824822+01', '2026-01-22 20:18:18.824825+01');
INSERT INTO public.semester_enrollments VALUES (42, 14, 15, 32, 'APPROVED', '2026-01-22 19:18:36.188055+01', '2026-01-22 19:18:36.18804+01', 14, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:18:36.188049+01', NULL, 'YOUTH', false, NULL, NULL, '2026-01-22 20:18:36.191802+01', '2026-01-22 20:18:36.191806+01');
INSERT INTO public.semester_enrollments VALUES (43, 15, 15, 33, 'APPROVED', '2026-01-22 19:18:58.552269+01', '2026-01-22 19:18:58.552262+01', 15, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:18:58.552266+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-22 20:18:58.55432+01', '2026-01-22 20:18:58.554322+01');
INSERT INTO public.semester_enrollments VALUES (44, 16, 15, 34, 'APPROVED', '2026-01-22 19:19:23.753435+01', '2026-01-22 19:19:23.753425+01', 16, NULL, NULL, true, NULL, NULL, true, '2026-01-22 19:19:23.753432+01', NULL, 'AMATEUR', false, NULL, NULL, '2026-01-22 20:19:23.756329+01', '2026-01-22 20:19:23.756331+01');


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.sessions VALUES (1, '🇦🇹 AT - "Nike Winter Cup ''26" - VIE - Round 1 - Match 1', 'League match 1 of 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 4, 'TBD', NULL, 'General', 'All Levels', NULL, 10, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round 1', '{"recorded_at": "2026-01-21T16:47:00.466822", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 2, "score": null, "notes": null}, {"user_id": 5, "rank": 3, "score": null, "notes": null}, {"user_id": 6, "rank": 1, "score": null, "notes": null}, {"user_id": 7, "rank": 4, "score": null, "notes": null}]}', true, 'League', 1, 1, '2026-01-21 10:37:14.772449', '2026-01-21 17:47:00.471288', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (2, '🇦🇹 AT - "Nike Winter Cup ''26" - VIE - Round 1 - Match 2', 'League match 2 of 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 4, 'TBD', NULL, 'General', 'All Levels', NULL, 10, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round 1', '{"recorded_at": "2026-01-21T16:48:51.104828", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 1, "score": null, "notes": null}, {"user_id": 6, "rank": 2, "score": null, "notes": null}, {"user_id": 7, "rank": 3, "score": null, "notes": null}, {"user_id": 5, "rank": 4, "score": null, "notes": null}]}', true, 'League', 1, 2, '2026-01-21 10:37:14.772459', '2026-01-21 17:48:51.106167', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (56, '🇧🇷 BR - "Neymar''s Five " - RIO - Group A - Round 1', 'Group A ranking round (4 players)', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 1', NULL, true, 'Group Stage', 1, 1, '2026-01-22 20:19:51.987793', '2026-01-22 20:19:51.987797', 'GROUP_ISOLATED', 'A', 4, 'group_membership', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"group": "A", "group_size": 4, "expected_participants": 4}', '{4,6,13,15}');
INSERT INTO public.sessions VALUES (57, '🇧🇷 BR - "Neymar''s Five " - RIO - Group A - Round 2', 'Group A ranking round (4 players)', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 2', NULL, true, 'Group Stage', 2, 2, '2026-01-22 20:19:52.007115', '2026-01-22 20:19:52.007116', 'GROUP_ISOLATED', 'A', 4, 'group_membership', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"group": "A", "group_size": 4, "expected_participants": 4}', '{4,6,13,15}');
INSERT INTO public.sessions VALUES (58, '🇧🇷 BR - "Neymar''s Five " - RIO - Group A - Round 3', 'Group A ranking round (4 players)', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 3', NULL, true, 'Group Stage', 3, 3, '2026-01-22 20:19:52.018898', '2026-01-22 20:19:52.0189', 'GROUP_ISOLATED', 'A', 4, 'group_membership', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"group": "A", "group_size": 4, "expected_participants": 4}', '{4,6,13,15}');
INSERT INTO public.sessions VALUES (59, '🇧🇷 BR - "Neymar''s Five " - RIO - Group B - Round 1', 'Group B ranking round (4 players)', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 1', NULL, true, 'Group Stage', 1, 4, '2026-01-22 20:19:52.02956', '2026-01-22 20:19:52.029562', 'GROUP_ISOLATED', 'B', 4, 'group_membership', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"group": "B", "group_size": 4, "expected_participants": 4}', '{5,7,14,16}');
INSERT INTO public.sessions VALUES (60, '🇧🇷 BR - "Neymar''s Five " - RIO - Group B - Round 2', 'Group B ranking round (4 players)', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 2', NULL, true, 'Group Stage', 2, 5, '2026-01-22 20:19:52.039119', '2026-01-22 20:19:52.039121', 'GROUP_ISOLATED', 'B', 4, 'group_membership', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"group": "B", "group_size": 4, "expected_participants": 4}', '{5,7,14,16}');
INSERT INTO public.sessions VALUES (61, '🇧🇷 BR - "Neymar''s Five " - RIO - Group B - Round 3', 'Group B ranking round (4 players)', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 3', NULL, true, 'Group Stage', 3, 6, '2026-01-22 20:19:52.049841', '2026-01-22 20:19:52.049843', 'GROUP_ISOLATED', 'B', 4, 'group_membership', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"group": "B", "group_size": 4, "expected_participants": 4}', '{5,7,14,16}');
INSERT INTO public.sessions VALUES (62, '🇧🇷 BR - "Neymar''s Five " - RIO - Round of 4 - Match 1', 'Knockout stage match - top 4 qualifiers', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round of 4', NULL, true, 'Knockout Stage', 1, 1, '2026-01-22 20:19:52.059765', '2026-01-22 20:19:52.059766', 'QUALIFIED_ONLY', NULL, 4, 'top_group_qualifiers', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"round_name": "Round of 4", "qualified_count": 4, "expected_participants": 4}', NULL);
INSERT INTO public.sessions VALUES (63, '🇧🇷 BR - "Neymar''s Five " - RIO - Round of 4 - Match 2', 'Knockout stage match - top 4 qualifiers', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round of 4', NULL, true, 'Knockout Stage', 1, 2, '2026-01-22 20:19:52.070048', '2026-01-22 20:19:52.070049', 'QUALIFIED_ONLY', NULL, 4, 'top_group_qualifiers', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"round_name": "Round of 4", "qualified_count": 4, "expected_participants": 4}', NULL);
INSERT INTO public.sessions VALUES (64, '🇧🇷 BR - "Neymar''s Five " - RIO - Round of 2 - Match 1', 'Knockout stage match - top 4 qualifiers', '2026-01-23 00:00:00', '2026-01-23 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 15, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round of 2', NULL, true, 'Knockout Stage', 2, 1, '2026-01-22 20:19:52.082418', '2026-01-22 20:19:52.082421', 'QUALIFIED_ONLY', NULL, 2, 'top_group_qualifiers', NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"round_name": "Round of 2", "qualified_count": 4, "expected_participants": 2}', NULL);
INSERT INTO public.sessions VALUES (23, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group A - Round 1 - Match 1', 'Group stage match 1', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 1', '{"recorded_at": "2026-01-21T21:36:58.396598", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 13, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 2, "score": null, "notes": null}, {"user_id": 16, "rank": 3, "score": null, "notes": null}, {"user_id": 14, "rank": 4, "score": null, "notes": null}, {"user_id": 6, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 15, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 1, 1, '2026-01-21 22:35:47.122844', '2026-01-21 22:36:58.39718', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (3, '🇦🇹 AT - "Nike Winter Cup ''26" - VIE - Round 2 - Match 1', 'League match 3 of 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 4, 'TBD', NULL, 'General', 'All Levels', NULL, 10, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round 2', '{"recorded_at": "2026-01-21T16:49:36.980693", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 4, "score": null, "notes": null}, {"user_id": 5, "rank": 3, "score": null, "notes": null}, {"user_id": 6, "rank": 2, "score": null, "notes": null}, {"user_id": 7, "rank": 1, "score": null, "notes": null}]}', true, 'League', 2, 1, '2026-01-21 10:37:14.772463', '2026-01-21 17:49:36.981247', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (4, '🇦🇹 AT - "Nike Winter Cup ''26" - VIE - Round 2 - Match 2', 'League match 4 of 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 4, 'TBD', NULL, 'General', 'All Levels', NULL, 10, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round 2', '{"recorded_at": "2026-01-21T16:50:18.604671", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 3, "score": null, "notes": null}, {"user_id": 7, "rank": 4, "score": null, "notes": null}, {"user_id": 6, "rank": 2, "score": null, "notes": null}]}', true, 'League', 2, 2, '2026-01-21 10:37:14.772466', '2026-01-21 17:50:18.60506', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (5, '🇦🇹 AT - "Nike Winter Cup ''26" - VIE - Round 3 - Match 1', 'League match 5 of 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 4, 'TBD', NULL, 'General', 'All Levels', NULL, 10, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round 3', '{"recorded_at": "2026-01-21T16:50:47.489047", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 2, "score": null, "notes": null}, {"user_id": 6, "rank": 3, "score": null, "notes": null}, {"user_id": 7, "rank": 4, "score": null, "notes": null}]}', true, 'League', 3, 1, '2026-01-21 10:37:14.772469', '2026-01-21 17:50:47.489451', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (6, '🇦🇹 AT - "Nike Winter Cup ''26" - VIE - Round 3 - Match 2', 'League match 6 of 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 4, 'TBD', NULL, 'General', 'All Levels', NULL, 10, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round 3', '{"recorded_at": "2026-01-21T16:51:16.799551", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 2, "score": null, "notes": null}, {"user_id": 6, "rank": 3, "score": null, "notes": null}, {"user_id": 7, "rank": 4, "score": null, "notes": null}]}', true, 'League', 3, 2, '2026-01-21 10:37:14.772472', '2026-01-21 17:51:16.800005', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (24, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group A - Round 1 - Match 2', 'Group stage match 2', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 1', '{"recorded_at": "2026-01-21T21:37:51.667122", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 16, "rank": 1, "score": null, "notes": null}, {"user_id": 6, "rank": 2, "score": null, "notes": null}, {"user_id": 14, "rank": 3, "score": null, "notes": null}, {"user_id": 13, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 5, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 1, 2, '2026-01-21 22:35:47.141745', '2026-01-21 22:37:51.667363', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (25, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group A - Round 2 - Match 1', 'Group stage match 3', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 2', '{"recorded_at": "2026-01-21T21:38:51.247394", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 5, "rank": 1, "score": null, "notes": null}, {"user_id": 13, "rank": 2, "score": null, "notes": null}, {"user_id": 15, "rank": 3, "score": null, "notes": null}, {"user_id": 16, "rank": 4, "score": null, "notes": null}, {"user_id": 14, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 6, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 2, 3, '2026-01-21 22:35:47.150074', '2026-01-21 22:38:51.247622', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (26, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group A - Round 2 - Match 2', 'Group stage match 4', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 2', '{"recorded_at": "2026-01-21T21:39:36.485314", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 16, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 2, "score": null, "notes": null}, {"user_id": 13, "rank": 3, "score": null, "notes": null}, {"user_id": 14, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 5, "score": null, "notes": null}, {"user_id": 6, "rank": 6, "score": null, "notes": null}, {"user_id": 7, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 2, 4, '2026-01-21 22:35:47.159373', '2026-01-21 22:39:36.485747', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (27, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group A - Round 3 - Match 1', 'Group stage match 5', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 3', '{"recorded_at": "2026-01-21T21:40:16.468926", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 16, "rank": 1, "score": null, "notes": null}, {"user_id": 13, "rank": 2, "score": null, "notes": null}, {"user_id": 5, "rank": 3, "score": null, "notes": null}, {"user_id": 6, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 5, "score": null, "notes": null}, {"user_id": 14, "rank": 6, "score": null, "notes": null}, {"user_id": 4, "rank": 7, "score": null, "notes": null}, {"user_id": 7, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 3, 5, '2026-01-21 22:35:47.167706', '2026-01-21 22:40:16.469175', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (28, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group A - Round 3 - Match 2', 'Group stage match 6', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group A - Round 3', '{"recorded_at": "2026-01-21T21:41:04.591763", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 2, "score": null, "notes": null}, {"user_id": 13, "rank": 3, "score": null, "notes": null}, {"user_id": 14, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 6, "score": null, "notes": null}, {"user_id": 16, "rank": 5, "score": null, "notes": null}, {"user_id": 6, "rank": 8, "score": null, "notes": null}, {"user_id": 7, "rank": 7, "score": null, "notes": null}]}', true, 'Group Stage', 3, 6, '2026-01-21 22:35:47.178313', '2026-01-21 22:41:04.592096', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (32, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group B - Round 2 - Match 2', 'Group stage match 10', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 2', '{"recorded_at": "2026-01-21T21:46:36.848502", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 13, "rank": 1, "score": null, "notes": null}, {"user_id": 5, "rank": 2, "score": null, "notes": null}, {"user_id": 14, "rank": 3, "score": null, "notes": null}, {"user_id": 15, "rank": 4, "score": null, "notes": null}, {"user_id": 16, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 6, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 2, 10, '2026-01-21 22:35:47.21657', '2026-01-21 22:46:36.848871', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (35, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Round of 4 - Match 1', 'Knockout stage match', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round of 4', '{"recorded_at": "2026-01-21T21:49:03.730165", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 5, "rank": 1, "score": null, "notes": null}, {"user_id": 13, "rank": 2, "score": null, "notes": null}, {"user_id": 14, "rank": 3, "score": null, "notes": null}, {"user_id": 16, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 6, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Knockout Stage', 1, 1, '2026-01-21 22:35:47.248878', '2026-01-21 22:49:03.730507', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (29, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group B - Round 1 - Match 1', 'Group stage match 7', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 1', '{"recorded_at": "2026-01-21T21:41:48.970639", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 5, "rank": 1, "score": null, "notes": null}, {"user_id": 15, "rank": 2, "score": null, "notes": null}, {"user_id": 13, "rank": 3, "score": null, "notes": null}, {"user_id": 14, "rank": 4, "score": null, "notes": null}, {"user_id": 16, "rank": 5, "score": null, "notes": null}, {"user_id": 4, "rank": 6, "score": null, "notes": null}, {"user_id": 6, "rank": 7, "score": null, "notes": null}, {"user_id": 7, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 1, 7, '2026-01-21 22:35:47.186811', '2026-01-21 22:41:48.970863', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (30, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group B - Round 1 - Match 2', 'Group stage match 8', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 1', '{"recorded_at": "2026-01-21T21:45:03.997360", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 4, "rank": 1, "score": null, "notes": null}, {"user_id": 13, "rank": 2, "score": null, "notes": null}, {"user_id": 14, "rank": 3, "score": null, "notes": null}, {"user_id": 16, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 6, "rank": 8, "score": null, "notes": null}, {"user_id": 5, "rank": 7, "score": null, "notes": null}]}', true, 'Group Stage', 1, 8, '2026-01-21 22:35:47.197385', '2026-01-21 22:45:04.001165', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (31, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group B - Round 2 - Match 1', 'Group stage match 9', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 2', '{"recorded_at": "2026-01-21T21:45:53.216254", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 5, "rank": 1, "score": null, "notes": null}, {"user_id": 13, "rank": 2, "score": null, "notes": null}, {"user_id": 16, "rank": 3, "score": null, "notes": null}, {"user_id": 15, "rank": 4, "score": null, "notes": null}, {"user_id": 14, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 4, "rank": 7, "score": null, "notes": null}, {"user_id": 6, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 2, 9, '2026-01-21 22:35:47.205956', '2026-01-21 22:45:53.216648', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (33, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group B - Round 3 - Match 1', 'Group stage match 11', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 3', '{"recorded_at": "2026-01-21T21:47:21.018887", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 15, "rank": 1, "score": null, "notes": null}, {"user_id": 6, "rank": 2, "score": null, "notes": null}, {"user_id": 13, "rank": 3, "score": null, "notes": null}, {"user_id": 14, "rank": 4, "score": null, "notes": null}, {"user_id": 16, "rank": 6, "score": null, "notes": null}, {"user_id": 7, "rank": 5, "score": null, "notes": null}, {"user_id": 5, "rank": 8, "score": null, "notes": null}, {"user_id": 4, "rank": 7, "score": null, "notes": null}]}', true, 'Group Stage', 3, 11, '2026-01-21 22:35:47.227707', '2026-01-21 22:47:21.019277', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (34, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Group B - Round 3 - Match 2', 'Group stage match 12', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Group B - Round 3', '{"recorded_at": "2026-01-21T21:48:17.831143", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 13, "rank": 1, "score": null, "notes": null}, {"user_id": 15, "rank": 2, "score": null, "notes": null}, {"user_id": 5, "rank": 3, "score": null, "notes": null}, {"user_id": 16, "rank": 4, "score": null, "notes": null}, {"user_id": 14, "rank": 5, "score": null, "notes": null}, {"user_id": 7, "rank": 6, "score": null, "notes": null}, {"user_id": 6, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Group Stage', 3, 12, '2026-01-21 22:35:47.238249', '2026-01-21 22:48:17.831384', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (36, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Round of 4 - Match 2', 'Knockout stage match', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round of 4', '{"recorded_at": "2026-01-21T21:49:49.109133", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 15, "rank": 1, "score": null, "notes": null}, {"user_id": 13, "rank": 2, "score": null, "notes": null}, {"user_id": 5, "rank": 3, "score": null, "notes": null}, {"user_id": 6, "rank": 4, "score": null, "notes": null}, {"user_id": 16, "rank": 5, "score": null, "notes": null}, {"user_id": 14, "rank": 6, "score": null, "notes": null}, {"user_id": 7, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Knockout Stage', 1, 2, '2026-01-21 22:35:47.260247', '2026-01-21 22:49:49.109555', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);
INSERT INTO public.sessions VALUES (37, '🇧🇷 BR - " F1rst Gānball Games™️ Cup" - RIO - Round of 2 - Match 1', 'Knockout stage match', '2026-01-22 00:00:00', '2026-01-22 00:00:00', 'on_site', 8, 'TBD', NULL, 'General', 'All Levels', NULL, 12, NULL, 3, NULL, false, NULL, NULL, 'scheduled', false, 50, 1, true, 'Round of 2', '{"recorded_at": "2026-01-21T21:50:27.967358", "recorded_by": 3, "recorded_by_name": "Grand Master", "match_notes": null, "results": [{"user_id": 5, "rank": 1, "score": null, "notes": null}, {"user_id": 14, "rank": 2, "score": null, "notes": null}, {"user_id": 6, "rank": 3, "score": null, "notes": null}, {"user_id": 16, "rank": 4, "score": null, "notes": null}, {"user_id": 15, "rank": 5, "score": null, "notes": null}, {"user_id": 13, "rank": 6, "score": null, "notes": null}, {"user_id": 7, "rank": 7, "score": null, "notes": null}, {"user_id": 4, "rank": 8, "score": null, "notes": null}]}', true, 'Knockout Stage', 2, 1, '2026-01-21 22:35:47.270426', '2026-01-21 22:50:27.9677', NULL, NULL, NULL, NULL, NULL, 'INDIVIDUAL_RANKING', 'PLACEMENT', '{"ranking_criteria": "final_placement"}', NULL);


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.bookings VALUES (1, 4, 1, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 9);
INSERT INTO public.bookings VALUES (2, 4, 2, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 9);
INSERT INTO public.bookings VALUES (3, 4, 3, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 9);
INSERT INTO public.bookings VALUES (4, 4, 4, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 9);
INSERT INTO public.bookings VALUES (5, 4, 5, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 9);
INSERT INTO public.bookings VALUES (6, 4, 6, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 9);
INSERT INTO public.bookings VALUES (7, 5, 1, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 10);
INSERT INTO public.bookings VALUES (8, 5, 2, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 10);
INSERT INTO public.bookings VALUES (9, 5, 3, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 10);
INSERT INTO public.bookings VALUES (10, 5, 4, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 10);
INSERT INTO public.bookings VALUES (11, 5, 5, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 10);
INSERT INTO public.bookings VALUES (12, 5, 6, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 10);
INSERT INTO public.bookings VALUES (13, 6, 1, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 11);
INSERT INTO public.bookings VALUES (14, 6, 2, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 11);
INSERT INTO public.bookings VALUES (15, 6, 3, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 11);
INSERT INTO public.bookings VALUES (16, 6, 4, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 11);
INSERT INTO public.bookings VALUES (17, 6, 5, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 11);
INSERT INTO public.bookings VALUES (18, 6, 6, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 11);
INSERT INTO public.bookings VALUES (19, 7, 1, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 12);
INSERT INTO public.bookings VALUES (20, 7, 2, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 12);
INSERT INTO public.bookings VALUES (21, 7, 3, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 12);
INSERT INTO public.bookings VALUES (22, 7, 4, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 12);
INSERT INTO public.bookings VALUES (23, 7, 5, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 12);
INSERT INTO public.bookings VALUES (24, 7, 6, 'CONFIRMED', NULL, NULL, '2026-01-21 10:45:38.71306', NULL, NULL, NULL, 12);
INSERT INTO public.bookings VALUES (25, 4, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.124901', '2026-01-21 22:35:47.126101', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (26, 5, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.129717', '2026-01-21 22:35:47.130093', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (27, 6, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.13461', '2026-01-21 22:35:47.134901', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (28, 7, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.13588', '2026-01-21 22:35:47.136123', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (29, 13, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.13713', '2026-01-21 22:35:47.137383', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (30, 14, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.138317', '2026-01-21 22:35:47.138525', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (31, 15, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.139446', '2026-01-21 22:35:47.139649', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (32, 16, 23, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.140495', '2026-01-21 22:35:47.140696', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (33, 4, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.142952', '2026-01-21 22:35:47.143157', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (34, 5, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.143609', '2026-01-21 22:35:47.14386', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (35, 6, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.144753', '2026-01-21 22:35:47.144984', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (36, 7, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.145742', '2026-01-21 22:35:47.145945', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (37, 13, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.146617', '2026-01-21 22:35:47.146804', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (38, 14, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.147389', '2026-01-21 22:35:47.147572', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (39, 15, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.148259', '2026-01-21 22:35:47.148441', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (40, 16, 24, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.149032', '2026-01-21 22:35:47.149211', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (41, 4, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.150896', '2026-01-21 22:35:47.151025', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (42, 5, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.151305', '2026-01-21 22:35:47.151487', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (43, 6, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.15206', '2026-01-21 22:35:47.152398', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (44, 7, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.153219', '2026-01-21 22:35:47.153555', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (45, 13, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.154365', '2026-01-21 22:35:47.1547', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (46, 14, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.155487', '2026-01-21 22:35:47.155816', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (47, 15, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.156589', '2026-01-21 22:35:47.156924', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (48, 16, 25, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.157733', '2026-01-21 22:35:47.158066', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (49, 4, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.160551', '2026-01-21 22:35:47.160708', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (50, 5, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.161066', '2026-01-21 22:35:47.161272', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (51, 6, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.161949', '2026-01-21 22:35:47.162148', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (52, 7, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.162987', '2026-01-21 22:35:47.163185', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (53, 13, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.163829', '2026-01-21 22:35:47.164029', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (54, 14, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.164725', '2026-01-21 22:35:47.16492', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (55, 15, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.165593', '2026-01-21 22:35:47.165793', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (56, 16, 26, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.166501', '2026-01-21 22:35:47.166709', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (57, 4, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.168839', '2026-01-21 22:35:47.169078', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (58, 5, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.169508', '2026-01-21 22:35:47.169836', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (59, 6, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.170677', '2026-01-21 22:35:47.171002', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (60, 7, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.171871', '2026-01-21 22:35:47.172208', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (61, 13, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.173375', '2026-01-21 22:35:47.173706', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (62, 14, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.174658', '2026-01-21 22:35:47.174986', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (63, 15, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.175928', '2026-01-21 22:35:47.176259', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (64, 16, 27, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.177081', '2026-01-21 22:35:47.177281', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (65, 4, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.179665', '2026-01-21 22:35:47.179847', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (66, 5, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.180238', '2026-01-21 22:35:47.180455', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (67, 6, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.181137', '2026-01-21 22:35:47.181343', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (68, 7, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.182048', '2026-01-21 22:35:47.182245', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (69, 13, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.182897', '2026-01-21 22:35:47.183092', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (70, 14, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.183746', '2026-01-21 22:35:47.183941', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (71, 15, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.184639', '2026-01-21 22:35:47.184833', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (72, 16, 28, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.185539', '2026-01-21 22:35:47.185755', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (73, 4, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.187739', '2026-01-21 22:35:47.187976', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (74, 5, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.188561', '2026-01-21 22:35:47.188889', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (75, 6, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.190021', '2026-01-21 22:35:47.19035', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (76, 7, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.19128', '2026-01-21 22:35:47.191605', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (77, 13, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.192565', '2026-01-21 22:35:47.192897', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (78, 14, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.193832', '2026-01-21 22:35:47.194093', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (79, 15, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.194962', '2026-01-21 22:35:47.19519', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (80, 16, 29, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.196026', '2026-01-21 22:35:47.196247', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (81, 4, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.198243', '2026-01-21 22:35:47.198394', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (82, 5, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.198732', '2026-01-21 22:35:47.198949', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (83, 6, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.199617', '2026-01-21 22:35:47.199832', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (84, 7, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.200497', '2026-01-21 22:35:47.200712', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (85, 13, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.201373', '2026-01-21 22:35:47.20159', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (86, 14, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.202325', '2026-01-21 22:35:47.202539', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (87, 15, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.203206', '2026-01-21 22:35:47.203419', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (88, 16, 30, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.204422', '2026-01-21 22:35:47.204634', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (89, 4, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.206996', '2026-01-21 22:35:47.207147', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (90, 5, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.207555', '2026-01-21 22:35:47.207769', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (91, 6, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.208611', '2026-01-21 22:35:47.208828', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (92, 7, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.209719', '2026-01-21 22:35:47.209937', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (93, 13, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.210759', '2026-01-21 22:35:47.211044', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (94, 14, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.21201', '2026-01-21 22:35:47.212262', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (95, 15, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.213071', '2026-01-21 22:35:47.213305', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (96, 16, 31, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.215124', '2026-01-21 22:35:47.215378', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (97, 4, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.217432', '2026-01-21 22:35:47.217611', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (98, 5, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.217945', '2026-01-21 22:35:47.218196', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (99, 6, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.21892', '2026-01-21 22:35:47.219186', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (100, 7, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.220493', '2026-01-21 22:35:47.220826', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (101, 13, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.22198', '2026-01-21 22:35:47.222309', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (102, 14, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.223451', '2026-01-21 22:35:47.223777', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (103, 15, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.224666', '2026-01-21 22:35:47.224999', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (104, 16, 32, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.226041', '2026-01-21 22:35:47.22637', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (105, 4, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.229539', '2026-01-21 22:35:47.22975', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (106, 5, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.230177', '2026-01-21 22:35:47.230441', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (107, 6, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.231202', '2026-01-21 22:35:47.231451', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (108, 7, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.232101', '2026-01-21 22:35:47.232349', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (109, 13, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.232992', '2026-01-21 22:35:47.233235', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (110, 14, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.233919', '2026-01-21 22:35:47.234163', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (111, 15, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.234812', '2026-01-21 22:35:47.235104', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (112, 16, 33, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.23682', '2026-01-21 22:35:47.23706', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (113, 4, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.23934', '2026-01-21 22:35:47.239567', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (114, 5, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.240246', '2026-01-21 22:35:47.240497', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (115, 6, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.241404', '2026-01-21 22:35:47.241647', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (116, 7, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.242533', '2026-01-21 22:35:47.242818', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (117, 13, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.243685', '2026-01-21 22:35:47.244039', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (118, 14, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.245053', '2026-01-21 22:35:47.245345', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (119, 15, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.246124', '2026-01-21 22:35:47.246379', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (120, 16, 34, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.247223', '2026-01-21 22:35:47.247514', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (121, 4, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.249938', '2026-01-21 22:35:47.250139', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (122, 5, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.250582', '2026-01-21 22:35:47.250904', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (123, 6, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.251867', '2026-01-21 22:35:47.252198', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (124, 7, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.253166', '2026-01-21 22:35:47.253495', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (125, 13, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.254434', '2026-01-21 22:35:47.254768', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (126, 14, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.255855', '2026-01-21 22:35:47.256179', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (127, 15, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.257219', '2026-01-21 22:35:47.257545', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (128, 16, 35, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.258503', '2026-01-21 22:35:47.258828', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (129, 4, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.261294', '2026-01-21 22:35:47.261567', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (130, 5, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.262128', '2026-01-21 22:35:47.262468', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (131, 6, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.263407', '2026-01-21 22:35:47.263703', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (132, 7, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.264456', '2026-01-21 22:35:47.264746', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (133, 13, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.265484', '2026-01-21 22:35:47.265766', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (134, 14, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.266478', '2026-01-21 22:35:47.266763', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (135, 15, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.267668', '2026-01-21 22:35:47.267947', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (136, 16, 36, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.268827', '2026-01-21 22:35:47.269108', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (137, 4, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.271376', '2026-01-21 22:35:47.271608', NULL, NULL, 13);
INSERT INTO public.bookings VALUES (138, 5, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.272019', '2026-01-21 22:35:47.272356', NULL, NULL, 14);
INSERT INTO public.bookings VALUES (139, 6, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.273201', '2026-01-21 22:35:47.273532', NULL, NULL, 15);
INSERT INTO public.bookings VALUES (140, 7, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.274381', '2026-01-21 22:35:47.274706', NULL, NULL, 16);
INSERT INTO public.bookings VALUES (141, 13, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.275545', '2026-01-21 22:35:47.275871', NULL, NULL, 17);
INSERT INTO public.bookings VALUES (142, 14, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.27675', '2026-01-21 22:35:47.277078', NULL, NULL, 18);
INSERT INTO public.bookings VALUES (143, 15, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.278173', '2026-01-21 22:35:47.278572', NULL, NULL, 19);
INSERT INTO public.bookings VALUES (144, 16, 37, 'CONFIRMED', NULL, NULL, '2026-01-21 21:35:47.279574', '2026-01-21 22:35:47.279927', NULL, NULL, 20);
INSERT INTO public.bookings VALUES (289, 4, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:51.992046', '2026-01-22 20:19:51.992759', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (290, 5, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:51.994611', '2026-01-22 20:19:51.994902', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (291, 6, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:51.999651', '2026-01-22 20:19:51.999885', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (292, 7, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.001151', '2026-01-22 20:19:52.001375', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (293, 13, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.002231', '2026-01-22 20:19:52.002438', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (294, 14, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.003245', '2026-01-22 20:19:52.003447', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (295, 15, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.00426', '2026-01-22 20:19:52.004459', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (296, 16, 56, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.005591', '2026-01-22 20:19:52.005791', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (297, 4, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.008577', '2026-01-22 20:19:52.008849', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (298, 5, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.009355', '2026-01-22 20:19:52.009561', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (299, 6, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.010534', '2026-01-22 20:19:52.010738', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (300, 7, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.011742', '2026-01-22 20:19:52.012008', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (301, 13, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.013077', '2026-01-22 20:19:52.013404', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (302, 14, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.014413', '2026-01-22 20:19:52.014914', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (303, 15, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.015841', '2026-01-22 20:19:52.016306', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (304, 16, 57, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.017332', '2026-01-22 20:19:52.017638', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (305, 4, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.019998', '2026-01-22 20:19:52.020175', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (306, 5, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.020497', '2026-01-22 20:19:52.02073', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (307, 6, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.021425', '2026-01-22 20:19:52.021651', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (308, 7, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.022332', '2026-01-22 20:19:52.022557', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (309, 13, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.02326', '2026-01-22 20:19:52.023482', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (310, 14, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.024394', '2026-01-22 20:19:52.024914', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (311, 15, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.026097', '2026-01-22 20:19:52.026347', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (312, 16, 58, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.027395', '2026-01-22 20:19:52.027653', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (313, 4, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.031047', '2026-01-22 20:19:52.031323', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (314, 5, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.03181', '2026-01-22 20:19:52.032094', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (315, 6, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.032951', '2026-01-22 20:19:52.033256', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (316, 7, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.034017', '2026-01-22 20:19:52.03426', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (317, 13, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.034954', '2026-01-22 20:19:52.035184', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (318, 14, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.035838', '2026-01-22 20:19:52.03606', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (319, 15, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.03679', '2026-01-22 20:19:52.037054', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (320, 16, 59, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.037781', '2026-01-22 20:19:52.038018', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (321, 4, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.04031', '2026-01-22 20:19:52.040473', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (322, 5, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.040963', '2026-01-22 20:19:52.041187', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (323, 6, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.042234', '2026-01-22 20:19:52.042475', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (324, 7, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.043446', '2026-01-22 20:19:52.043669', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (325, 13, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.044638', '2026-01-22 20:19:52.044861', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (326, 14, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.045911', '2026-01-22 20:19:52.046233', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (327, 15, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.047283', '2026-01-22 20:19:52.04759', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (328, 16, 60, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.048388', '2026-01-22 20:19:52.048637', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (329, 4, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.050917', '2026-01-22 20:19:52.051084', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (330, 5, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.051409', '2026-01-22 20:19:52.051641', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (331, 6, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.052315', '2026-01-22 20:19:52.052542', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (332, 7, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.053201', '2026-01-22 20:19:52.053424', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (333, 13, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.054112', '2026-01-22 20:19:52.054329', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (334, 14, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.055014', '2026-01-22 20:19:52.055235', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (335, 15, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.056221', '2026-01-22 20:19:52.056623', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (336, 16, 61, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.057891', '2026-01-22 20:19:52.058313', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (337, 4, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.060999', '2026-01-22 20:19:52.061159', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (338, 5, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.061617', '2026-01-22 20:19:52.061837', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (339, 6, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.063102', '2026-01-22 20:19:52.063494', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (340, 7, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.064717', '2026-01-22 20:19:52.065016', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (341, 13, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.065766', '2026-01-22 20:19:52.065995', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (342, 14, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.066703', '2026-01-22 20:19:52.066936', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (343, 15, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.067658', '2026-01-22 20:19:52.067906', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (344, 16, 62, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.068624', '2026-01-22 20:19:52.068868', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (345, 4, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.070968', '2026-01-22 20:19:52.071134', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (346, 5, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.071583', '2026-01-22 20:19:52.07199', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (347, 6, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.073288', '2026-01-22 20:19:52.073691', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (348, 7, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.07495', '2026-01-22 20:19:52.075348', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (349, 13, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.076445', '2026-01-22 20:19:52.076693', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (350, 14, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.077704', '2026-01-22 20:19:52.077948', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (351, 15, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.078998', '2026-01-22 20:19:52.079412', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (352, 16, 63, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.080514', '2026-01-22 20:19:52.080831', NULL, NULL, 44);
INSERT INTO public.bookings VALUES (353, 4, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.083397', '2026-01-22 20:19:52.083586', NULL, NULL, 37);
INSERT INTO public.bookings VALUES (354, 5, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.083952', '2026-01-22 20:19:52.084207', NULL, NULL, 38);
INSERT INTO public.bookings VALUES (355, 6, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.084929', '2026-01-22 20:19:52.085185', NULL, NULL, 39);
INSERT INTO public.bookings VALUES (356, 7, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.085917', '2026-01-22 20:19:52.086168', NULL, NULL, 40);
INSERT INTO public.bookings VALUES (357, 13, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.089183', '2026-01-22 20:19:52.089431', NULL, NULL, 41);
INSERT INTO public.bookings VALUES (358, 14, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.090493', '2026-01-22 20:19:52.09074', NULL, NULL, 42);
INSERT INTO public.bookings VALUES (359, 15, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.091973', '2026-01-22 20:19:52.092286', NULL, NULL, 43);
INSERT INTO public.bookings VALUES (360, 16, 64, 'CONFIRMED', NULL, NULL, '2026-01-22 19:19:52.093337', '2026-01-22 20:19:52.093582', NULL, NULL, 44);


--
-- Data for Name: attendance; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.attendance VALUES (5, 4, 1, 1, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:36:34.336544', '2026-01-21 17:36:34.33655');
INSERT INTO public.attendance VALUES (6, 5, 1, 7, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:36:35.949591', '2026-01-21 17:36:35.949597');
INSERT INTO public.attendance VALUES (7, 6, 1, 13, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:36:37.122899', '2026-01-21 17:36:37.122904');
INSERT INTO public.attendance VALUES (8, 7, 1, 19, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:36:38.955183', '2026-01-21 17:36:38.955187');
INSERT INTO public.attendance VALUES (9, 4, 2, 2, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:48:32.948411', '2026-01-21 17:48:32.948417');
INSERT INTO public.attendance VALUES (10, 5, 2, 8, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:48:34.188938', '2026-01-21 17:48:34.188944');
INSERT INTO public.attendance VALUES (11, 6, 2, 14, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:48:35.246874', '2026-01-21 17:48:35.246877');
INSERT INTO public.attendance VALUES (12, 7, 2, 20, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:48:36.410413', '2026-01-21 17:48:36.410418');
INSERT INTO public.attendance VALUES (13, 4, 3, 3, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:12.806739', '2026-01-21 17:49:12.806744');
INSERT INTO public.attendance VALUES (14, 5, 3, 9, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:13.97609', '2026-01-21 17:49:13.976094');
INSERT INTO public.attendance VALUES (15, 6, 3, 15, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:15.956927', '2026-01-21 17:49:15.95693');
INSERT INTO public.attendance VALUES (16, 7, 3, 21, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:20.684807', '2026-01-21 17:49:20.684812');
INSERT INTO public.attendance VALUES (17, 4, 4, 4, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:54.130226', '2026-01-21 17:49:54.13023');
INSERT INTO public.attendance VALUES (18, 5, 4, 10, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:55.316883', '2026-01-21 17:49:55.316888');
INSERT INTO public.attendance VALUES (19, 6, 4, 16, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:56.478572', '2026-01-21 17:49:56.478576');
INSERT INTO public.attendance VALUES (20, 7, 4, 22, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:49:57.549382', '2026-01-21 17:49:57.549387');
INSERT INTO public.attendance VALUES (21, 4, 5, 5, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:50:31.512446', '2026-01-21 17:50:31.512451');
INSERT INTO public.attendance VALUES (22, 5, 5, 11, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:50:32.696483', '2026-01-21 17:50:32.696488');
INSERT INTO public.attendance VALUES (23, 6, 5, 17, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:50:34.090734', '2026-01-21 17:50:34.090738');
INSERT INTO public.attendance VALUES (24, 7, 5, 23, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:50:35.201915', '2026-01-21 17:50:35.201921');
INSERT INTO public.attendance VALUES (25, 4, 6, 6, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:51:03.427352', '2026-01-21 17:51:03.427357');
INSERT INTO public.attendance VALUES (26, 5, 6, 12, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:51:04.429668', '2026-01-21 17:51:04.429671');
INSERT INTO public.attendance VALUES (27, 6, 6, 18, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:51:05.850794', '2026-01-21 17:51:05.850798');
INSERT INTO public.attendance VALUES (28, 7, 6, 24, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 17:51:06.358193', '2026-01-21 17:51:06.358197');
INSERT INTO public.attendance VALUES (29, 4, 23, 25, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.1296', '2026-01-21 22:36:07.32276');
INSERT INTO public.attendance VALUES (30, 5, 23, 26, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.134547', '2026-01-21 22:36:08.338875');
INSERT INTO public.attendance VALUES (31, 6, 23, 27, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.135837', '2026-01-21 22:36:09.325658');
INSERT INTO public.attendance VALUES (32, 7, 23, 28, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.137081', '2026-01-21 22:36:09.991268');
INSERT INTO public.attendance VALUES (33, 13, 23, 29, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.13828', '2026-01-21 22:36:11.222455');
INSERT INTO public.attendance VALUES (34, 14, 23, 30, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.139412', '2026-01-21 22:36:11.87555');
INSERT INTO public.attendance VALUES (35, 15, 23, 31, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.140461', '2026-01-21 22:36:13.13701');
INSERT INTO public.attendance VALUES (36, 16, 23, 32, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.141379', '2026-01-21 22:36:14.407741');
INSERT INTO public.attendance VALUES (37, 4, 24, 33, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.143559', '2026-01-21 22:37:06.186187');
INSERT INTO public.attendance VALUES (38, 5, 24, 34, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.144708', '2026-01-21 22:37:07.491941');
INSERT INTO public.attendance VALUES (39, 6, 24, 35, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.145705', '2026-01-21 22:37:08.634949');
INSERT INTO public.attendance VALUES (40, 7, 24, 36, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.146587', '2026-01-21 22:37:09.734365');
INSERT INTO public.attendance VALUES (41, 13, 24, 37, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.14736', '2026-01-21 22:37:10.787817');
INSERT INTO public.attendance VALUES (42, 14, 24, 38, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.14823', '2026-01-21 22:37:11.898313');
INSERT INTO public.attendance VALUES (43, 15, 24, 39, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.149003', '2026-01-21 22:37:12.903264');
INSERT INTO public.attendance VALUES (44, 16, 24, 40, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.149757', '2026-01-21 22:37:13.904702');
INSERT INTO public.attendance VALUES (45, 4, 25, 41, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.151275', '2026-01-21 22:38:09.020786');
INSERT INTO public.attendance VALUES (46, 5, 25, 42, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.152026', '2026-01-21 22:38:10.118016');
INSERT INTO public.attendance VALUES (47, 6, 25, 43, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.153165', '2026-01-21 22:38:11.052752');
INSERT INTO public.attendance VALUES (48, 7, 25, 44, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.154309', '2026-01-21 22:38:12.150921');
INSERT INTO public.attendance VALUES (49, 13, 25, 45, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.155433', '2026-01-21 22:38:13.268376');
INSERT INTO public.attendance VALUES (50, 14, 25, 46, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.156535', '2026-01-21 22:38:14.259703');
INSERT INTO public.attendance VALUES (51, 15, 25, 47, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.15768', '2026-01-21 22:38:15.26903');
INSERT INTO public.attendance VALUES (52, 16, 25, 48, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.158832', '2026-01-21 22:38:16.501638');
INSERT INTO public.attendance VALUES (53, 4, 26, 49, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.161029', '2026-01-21 22:38:55.458804');
INSERT INTO public.attendance VALUES (54, 5, 26, 50, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.161915', '2026-01-21 22:38:56.516574');
INSERT INTO public.attendance VALUES (55, 6, 26, 51, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.162951', '2026-01-21 22:38:57.656255');
INSERT INTO public.attendance VALUES (56, 7, 26, 52, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.163796', '2026-01-21 22:38:58.670707');
INSERT INTO public.attendance VALUES (57, 13, 26, 53, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.164693', '2026-01-21 22:38:59.623737');
INSERT INTO public.attendance VALUES (58, 14, 26, 54, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.165561', '2026-01-21 22:39:00.734934');
INSERT INTO public.attendance VALUES (59, 15, 26, 55, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.16647', '2026-01-21 22:39:01.637572');
INSERT INTO public.attendance VALUES (60, 16, 26, 56, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.167358', '2026-01-21 22:39:03.255203');
INSERT INTO public.attendance VALUES (61, 4, 27, 57, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.169454', '2026-01-21 22:39:40.932562');
INSERT INTO public.attendance VALUES (62, 5, 27, 58, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.170624', '2026-01-21 22:39:42.220898');
INSERT INTO public.attendance VALUES (63, 6, 27, 59, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.171817', '2026-01-21 22:39:43.468331');
INSERT INTO public.attendance VALUES (64, 7, 27, 60, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.173322', '2026-01-21 22:39:44.649035');
INSERT INTO public.attendance VALUES (65, 13, 27, 61, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.174604', '2026-01-21 22:39:45.58707');
INSERT INTO public.attendance VALUES (66, 14, 27, 62, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.175874', '2026-01-21 22:39:46.565446');
INSERT INTO public.attendance VALUES (67, 15, 27, 63, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.177049', '2026-01-21 22:39:47.625447');
INSERT INTO public.attendance VALUES (68, 16, 27, 64, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.177968', '2026-01-21 22:39:48.700685');
INSERT INTO public.attendance VALUES (69, 4, 28, 65, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.180201', '2026-01-21 22:40:25.723338');
INSERT INTO public.attendance VALUES (70, 5, 28, 66, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.181105', '2026-01-21 22:40:27.090384');
INSERT INTO public.attendance VALUES (71, 6, 28, 67, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.182016', '2026-01-21 22:40:28.470473');
INSERT INTO public.attendance VALUES (72, 7, 28, 68, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.182865', '2026-01-21 22:40:29.915147');
INSERT INTO public.attendance VALUES (73, 13, 28, 69, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.183714', '2026-01-21 22:40:30.977218');
INSERT INTO public.attendance VALUES (74, 14, 28, 70, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.184607', '2026-01-21 22:40:31.925348');
INSERT INTO public.attendance VALUES (75, 15, 28, 71, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.185503', '2026-01-21 22:40:32.942057');
INSERT INTO public.attendance VALUES (76, 16, 28, 72, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.186443', '2026-01-21 22:40:34.471632');
INSERT INTO public.attendance VALUES (77, 4, 29, 73, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.188506', '2026-01-21 22:41:09.800868');
INSERT INTO public.attendance VALUES (78, 5, 29, 74, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.189967', '2026-01-21 22:41:11.003692');
INSERT INTO public.attendance VALUES (79, 6, 29, 75, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.191227', '2026-01-21 22:41:12.220658');
INSERT INTO public.attendance VALUES (80, 7, 29, 76, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.192511', '2026-01-21 22:41:13.329354');
INSERT INTO public.attendance VALUES (81, 13, 29, 77, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.193785', '2026-01-21 22:41:14.436954');
INSERT INTO public.attendance VALUES (82, 14, 29, 78, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.19492', '2026-01-21 22:41:15.634716');
INSERT INTO public.attendance VALUES (83, 15, 29, 79, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.195987', '2026-01-21 22:41:16.867397');
INSERT INTO public.attendance VALUES (84, 16, 29, 80, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.197008', '2026-01-21 22:41:17.925175');
INSERT INTO public.attendance VALUES (85, 4, 30, 81, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.198694', '2026-01-21 22:44:26.803814');
INSERT INTO public.attendance VALUES (86, 5, 30, 82, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.199582', '2026-01-21 22:44:30.389834');
INSERT INTO public.attendance VALUES (87, 6, 30, 83, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.200462', '2026-01-21 22:44:31.518281');
INSERT INTO public.attendance VALUES (88, 7, 30, 84, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.201338', '2026-01-21 22:44:32.749704');
INSERT INTO public.attendance VALUES (89, 13, 30, 85, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.202291', '2026-01-21 22:44:34.368742');
INSERT INTO public.attendance VALUES (90, 14, 30, 86, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.203171', '2026-01-21 22:44:35.440281');
INSERT INTO public.attendance VALUES (91, 15, 30, 87, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.204387', '2026-01-21 22:44:36.555962');
INSERT INTO public.attendance VALUES (92, 16, 30, 88, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.205608', '2026-01-21 22:44:37.776791');
INSERT INTO public.attendance VALUES (93, 4, 31, 89, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.20752', '2026-01-21 22:45:15.827295');
INSERT INTO public.attendance VALUES (95, 6, 31, 91, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.209682', '2026-01-21 22:45:19.030456');
INSERT INTO public.attendance VALUES (96, 7, 31, 92, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.210704', '2026-01-21 22:45:20.132071');
INSERT INTO public.attendance VALUES (97, 13, 31, 93, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.211962', '2026-01-21 22:45:21.2794');
INSERT INTO public.attendance VALUES (94, 5, 31, 90, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.208575', '2026-01-21 22:45:17.254718');
INSERT INTO public.attendance VALUES (98, 14, 31, 94, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.213033', '2026-01-21 22:45:22.307262');
INSERT INTO public.attendance VALUES (99, 15, 31, 95, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.215083', '2026-01-21 22:45:23.496792');
INSERT INTO public.attendance VALUES (100, 16, 31, 96, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.216094', '2026-01-21 22:45:24.498588');
INSERT INTO public.attendance VALUES (101, 4, 32, 97, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.217904', '2026-01-21 22:46:01.990252');
INSERT INTO public.attendance VALUES (102, 5, 32, 98, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.21888', '2026-01-21 22:46:03.424451');
INSERT INTO public.attendance VALUES (103, 6, 32, 99, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.220439', '2026-01-21 22:46:04.37715');
INSERT INTO public.attendance VALUES (104, 7, 32, 100, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.221927', '2026-01-21 22:46:05.412904');
INSERT INTO public.attendance VALUES (105, 13, 32, 101, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.223397', '2026-01-21 22:46:06.595322');
INSERT INTO public.attendance VALUES (106, 14, 32, 102, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.224612', '2026-01-21 22:46:07.644071');
INSERT INTO public.attendance VALUES (107, 15, 32, 103, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.225988', '2026-01-21 22:46:08.635795');
INSERT INTO public.attendance VALUES (108, 16, 32, 104, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.227275', '2026-01-21 22:46:09.775468');
INSERT INTO public.attendance VALUES (109, 4, 33, 105, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.230125', '2026-01-21 22:46:40.28673');
INSERT INTO public.attendance VALUES (110, 5, 33, 106, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.231159', '2026-01-21 22:46:41.69507');
INSERT INTO public.attendance VALUES (111, 6, 33, 107, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.232062', '2026-01-21 22:46:42.194724');
INSERT INTO public.attendance VALUES (112, 7, 33, 108, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.232953', '2026-01-21 22:46:42.698422');
INSERT INTO public.attendance VALUES (113, 13, 33, 109, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.23388', '2026-01-21 22:46:44.164855');
INSERT INTO public.attendance VALUES (114, 14, 33, 110, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.234774', '2026-01-21 22:46:45.845753');
INSERT INTO public.attendance VALUES (115, 15, 33, 111, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.23678', '2026-01-21 22:46:47.12005');
INSERT INTO public.attendance VALUES (116, 16, 33, 112, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.237819', '2026-01-21 22:46:48.284062');
INSERT INTO public.attendance VALUES (117, 4, 34, 113, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.240192', '2026-01-21 22:47:34.643956');
INSERT INTO public.attendance VALUES (118, 5, 34, 114, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.241365', '2026-01-21 22:47:37.778257');
INSERT INTO public.attendance VALUES (119, 6, 34, 115, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.242494', '2026-01-21 22:47:39.058885');
INSERT INTO public.attendance VALUES (120, 7, 34, 116, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.243618', '2026-01-21 22:47:40.159708');
INSERT INTO public.attendance VALUES (121, 13, 34, 117, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.244989', '2026-01-21 22:47:43.76172');
INSERT INTO public.attendance VALUES (122, 14, 34, 118, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.246079', '2026-01-21 22:47:45.678816');
INSERT INTO public.attendance VALUES (123, 15, 34, 119, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.247176', '2026-01-21 22:47:46.849539');
INSERT INTO public.attendance VALUES (124, 16, 34, 120, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.248369', '2026-01-21 22:47:48.082129');
INSERT INTO public.attendance VALUES (125, 4, 35, 121, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.250535', '2026-01-21 22:48:24.827176');
INSERT INTO public.attendance VALUES (126, 5, 35, 122, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.251814', '2026-01-21 22:48:25.994426');
INSERT INTO public.attendance VALUES (127, 6, 35, 123, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.253113', '2026-01-21 22:48:27.150311');
INSERT INTO public.attendance VALUES (128, 7, 35, 124, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.254383', '2026-01-21 22:48:28.395234');
INSERT INTO public.attendance VALUES (129, 13, 35, 125, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.255802', '2026-01-21 22:48:29.511616');
INSERT INTO public.attendance VALUES (130, 14, 35, 126, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.257166', '2026-01-21 22:48:30.819687');
INSERT INTO public.attendance VALUES (131, 15, 35, 127, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.25845', '2026-01-21 22:48:32.05557');
INSERT INTO public.attendance VALUES (132, 16, 35, 128, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.259753', '2026-01-21 22:48:33.280545');
INSERT INTO public.attendance VALUES (133, 4, 36, 129, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.262061', '2026-01-21 22:49:11.136014');
INSERT INTO public.attendance VALUES (134, 5, 36, 130, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.263354', '2026-01-21 22:49:12.909496');
INSERT INTO public.attendance VALUES (135, 6, 36, 131, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.264407', '2026-01-21 22:49:14.140902');
INSERT INTO public.attendance VALUES (136, 7, 36, 132, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.265438', '2026-01-21 22:49:15.444392');
INSERT INTO public.attendance VALUES (137, 13, 36, 133, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.266431', '2026-01-21 22:49:16.628227');
INSERT INTO public.attendance VALUES (138, 14, 36, 134, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.267622', '2026-01-21 22:49:17.704966');
INSERT INTO public.attendance VALUES (139, 15, 36, 135, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.268781', '2026-01-21 22:49:18.864102');
INSERT INTO public.attendance VALUES (140, 16, 36, 136, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.269935', '2026-01-21 22:49:20.043365');
INSERT INTO public.attendance VALUES (141, 4, 37, 137, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.271964', '2026-01-21 22:49:55.862183');
INSERT INTO public.attendance VALUES (142, 5, 37, 138, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.273148', '2026-01-21 22:49:57.097729');
INSERT INTO public.attendance VALUES (143, 6, 37, 139, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.274327', '2026-01-21 22:49:58.204534');
INSERT INTO public.attendance VALUES (144, 7, 37, 140, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.275492', '2026-01-21 22:49:59.446614');
INSERT INTO public.attendance VALUES (145, 13, 37, 141, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.276695', '2026-01-21 22:50:00.582765');
INSERT INTO public.attendance VALUES (146, 14, 37, 142, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.278092', '2026-01-21 22:50:01.731872');
INSERT INTO public.attendance VALUES (147, 15, 37, 143, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.279512', '2026-01-21 22:50:03.030767');
INSERT INTO public.attendance VALUES (148, 16, 37, 144, 'present', NULL, NULL, NULL, 3, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-21 21:35:47.280709', '2026-01-21 22:50:04.24828');
INSERT INTO public.attendance VALUES (293, 4, 56, 289, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:51.994527', '2026-01-22 20:19:51.997152');
INSERT INTO public.attendance VALUES (294, 5, 56, 290, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:51.999597', '2026-01-22 20:19:52.000375');
INSERT INTO public.attendance VALUES (295, 6, 56, 291, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.001106', '2026-01-22 20:19:52.001787');
INSERT INTO public.attendance VALUES (296, 7, 56, 292, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.002194', '2026-01-22 20:19:52.002818');
INSERT INTO public.attendance VALUES (297, 13, 56, 293, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.003211', '2026-01-22 20:19:52.00384');
INSERT INTO public.attendance VALUES (298, 14, 56, 294, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.004226', '2026-01-22 20:19:52.004886');
INSERT INTO public.attendance VALUES (299, 15, 56, 295, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.005558', '2026-01-22 20:19:52.00621');
INSERT INTO public.attendance VALUES (300, 16, 56, 296, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.00671', '2026-01-22 20:19:52.008049');
INSERT INTO public.attendance VALUES (301, 4, 57, 297, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.009319', '2026-01-22 20:19:52.009987');
INSERT INTO public.attendance VALUES (302, 5, 57, 298, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.010498', '2026-01-22 20:19:52.011174');
INSERT INTO public.attendance VALUES (303, 6, 57, 299, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.011707', '2026-01-22 20:19:52.01256');
INSERT INTO public.attendance VALUES (304, 7, 57, 300, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.013011', '2026-01-22 20:19:52.013758');
INSERT INTO public.attendance VALUES (305, 13, 57, 301, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.014319', '2026-01-22 20:19:52.015339');
INSERT INTO public.attendance VALUES (306, 14, 57, 302, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.015771', '2026-01-22 20:19:52.016796');
INSERT INTO public.attendance VALUES (307, 15, 57, 303, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.017246', '2026-01-22 20:19:52.018026');
INSERT INTO public.attendance VALUES (308, 16, 57, 304, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.018415', '2026-01-22 20:19:52.019632');
INSERT INTO public.attendance VALUES (309, 4, 58, 305, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.020458', '2026-01-22 20:19:52.021047');
INSERT INTO public.attendance VALUES (310, 5, 58, 306, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.021385', '2026-01-22 20:19:52.021955');
INSERT INTO public.attendance VALUES (311, 6, 58, 307, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.022294', '2026-01-22 20:19:52.022857');
INSERT INTO public.attendance VALUES (312, 7, 58, 308, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.023223', '2026-01-22 20:19:52.023768');
INSERT INTO public.attendance VALUES (313, 13, 58, 309, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.02431', '2026-01-22 20:19:52.025526');
INSERT INTO public.attendance VALUES (314, 14, 58, 310, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.026053', '2026-01-22 20:19:52.026818');
INSERT INTO public.attendance VALUES (315, 15, 58, 311, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.027349', '2026-01-22 20:19:52.028259');
INSERT INTO public.attendance VALUES (316, 16, 58, 312, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.028809', '2026-01-22 20:19:52.030534');
INSERT INTO public.attendance VALUES (317, 4, 59, 313, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.03176', '2026-01-22 20:19:52.032503');
INSERT INTO public.attendance VALUES (318, 5, 59, 314, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.032901', '2026-01-22 20:19:52.033611');
INSERT INTO public.attendance VALUES (319, 6, 59, 315, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.033974', '2026-01-22 20:19:52.03458');
INSERT INTO public.attendance VALUES (320, 7, 59, 316, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.034915', '2026-01-22 20:19:52.035481');
INSERT INTO public.attendance VALUES (321, 13, 59, 317, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.035801', '2026-01-22 20:19:52.036353');
INSERT INTO public.attendance VALUES (322, 14, 59, 318, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.036741', '2026-01-22 20:19:52.037379');
INSERT INTO public.attendance VALUES (323, 15, 59, 319, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.037739', '2026-01-22 20:19:52.038328');
INSERT INTO public.attendance VALUES (324, 16, 59, 320, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.038675', '2026-01-22 20:19:52.03978');
INSERT INTO public.attendance VALUES (325, 4, 60, 321, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.040926', '2026-01-22 20:19:52.041643');
INSERT INTO public.attendance VALUES (326, 5, 60, 322, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.042197', '2026-01-22 20:19:52.042911');
INSERT INTO public.attendance VALUES (327, 6, 60, 323, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.043408', '2026-01-22 20:19:52.044107');
INSERT INTO public.attendance VALUES (328, 7, 60, 324, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.044601', '2026-01-22 20:19:52.045282');
INSERT INTO public.attendance VALUES (329, 13, 60, 325, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.045858', '2026-01-22 20:19:52.046743');
INSERT INTO public.attendance VALUES (330, 14, 60, 326, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.047216', '2026-01-22 20:19:52.047954');
INSERT INTO public.attendance VALUES (331, 15, 60, 327, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.04834', '2026-01-22 20:19:52.04897');
INSERT INTO public.attendance VALUES (332, 16, 60, 328, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.04936', '2026-01-22 20:19:52.050546');
INSERT INTO public.attendance VALUES (333, 4, 61, 329, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.05137', '2026-01-22 20:19:52.051937');
INSERT INTO public.attendance VALUES (334, 5, 61, 330, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.052277', '2026-01-22 20:19:52.052838');
INSERT INTO public.attendance VALUES (335, 6, 61, 331, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.053164', '2026-01-22 20:19:52.053729');
INSERT INTO public.attendance VALUES (336, 7, 61, 332, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.054076', '2026-01-22 20:19:52.054628');
INSERT INTO public.attendance VALUES (337, 13, 61, 333, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.054979', '2026-01-22 20:19:52.055533');
INSERT INTO public.attendance VALUES (338, 14, 61, 334, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.056154', '2026-01-22 20:19:52.057196');
INSERT INTO public.attendance VALUES (339, 15, 61, 335, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.057827', '2026-01-22 20:19:52.058848');
INSERT INTO public.attendance VALUES (340, 16, 61, 336, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.059371', '2026-01-22 20:19:52.060473');
INSERT INTO public.attendance VALUES (341, 4, 62, 337, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.061581', '2026-01-22 20:19:52.062276');
INSERT INTO public.attendance VALUES (342, 5, 62, 338, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.062961', '2026-01-22 20:19:52.064146');
INSERT INTO public.attendance VALUES (343, 6, 62, 339, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.06465', '2026-01-22 20:19:52.065371');
INSERT INTO public.attendance VALUES (344, 7, 62, 340, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.065725', '2026-01-22 20:19:52.066316');
INSERT INTO public.attendance VALUES (345, 13, 62, 341, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.066663', '2026-01-22 20:19:52.067261');
INSERT INTO public.attendance VALUES (346, 14, 62, 342, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.067617', '2026-01-22 20:19:52.068229');
INSERT INTO public.attendance VALUES (347, 15, 62, 343, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.068584', '2026-01-22 20:19:52.069196');
INSERT INTO public.attendance VALUES (348, 16, 62, 344, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.069546', '2026-01-22 20:19:52.070603');
INSERT INTO public.attendance VALUES (349, 4, 63, 345, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.071517', '2026-01-22 20:19:52.07255');
INSERT INTO public.attendance VALUES (350, 5, 63, 346, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.073222', '2026-01-22 20:19:52.074255');
INSERT INTO public.attendance VALUES (351, 6, 63, 347, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.074886', '2026-01-22 20:19:52.075824');
INSERT INTO public.attendance VALUES (352, 7, 63, 348, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.076405', '2026-01-22 20:19:52.077134');
INSERT INTO public.attendance VALUES (353, 13, 63, 349, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.077663', '2026-01-22 20:19:52.078422');
INSERT INTO public.attendance VALUES (354, 14, 63, 350, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.078947', '2026-01-22 20:19:52.079966');
INSERT INTO public.attendance VALUES (355, 15, 63, 351, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.080453', '2026-01-22 20:19:52.081337');
INSERT INTO public.attendance VALUES (356, 16, 63, 352, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.081774', '2026-01-22 20:19:52.08302');
INSERT INTO public.attendance VALUES (357, 4, 64, 353, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.083911', '2026-01-22 20:19:52.084531');
INSERT INTO public.attendance VALUES (358, 5, 64, 354, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.084888', '2026-01-22 20:19:52.085525');
INSERT INTO public.attendance VALUES (359, 6, 64, 355, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.085876', '2026-01-22 20:19:52.086493');
INSERT INTO public.attendance VALUES (360, 7, 64, 356, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.089143', '2026-01-22 20:19:52.089904');
INSERT INTO public.attendance VALUES (361, 13, 64, 357, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.090453', '2026-01-22 20:19:52.091283');
INSERT INTO public.attendance VALUES (362, 14, 64, 358, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.091909', '2026-01-22 20:19:52.092767');
INSERT INTO public.attendance VALUES (363, 15, 64, 359, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.093297', '2026-01-22 20:19:52.09403');
INSERT INTO public.attendance VALUES (364, 16, 64, 360, 'absent', NULL, NULL, NULL, NULL, 'pending_confirmation', NULL, NULL, NULL, NULL, NULL, NULL, 0, '2026-01-22 19:19:52.094544', '2026-01-22 20:19:52.094976');


--
-- Data for Name: tournament_rankings; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.tournament_rankings VALUES (1, 10, 4, NULL, 'USER', 1, 14.00, NULL, NULL, NULL, '2026-01-21 17:51:16.796083+01');
INSERT INTO public.tournament_rankings VALUES (2, 10, 5, NULL, 'USER', 3, 7.00, NULL, NULL, NULL, '2026-01-21 17:51:16.796083+01');
INSERT INTO public.tournament_rankings VALUES (3, 10, 6, NULL, 'USER', 2, 11.00, NULL, NULL, NULL, '2026-01-21 17:51:16.796083+01');
INSERT INTO public.tournament_rankings VALUES (4, 10, 7, NULL, 'USER', 4, 4.00, NULL, NULL, NULL, '2026-01-21 17:51:16.796083+01');
INSERT INTO public.tournament_rankings VALUES (6, 12, 5, NULL, 'USER', 1, 26.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (5, 12, 13, NULL, 'USER', 2, 25.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (11, 12, 15, NULL, 'USER', 3, 11.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (7, 12, 16, NULL, 'USER', 4, 11.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (8, 12, 14, NULL, 'USER', 5, 6.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (12, 12, 4, NULL, 'USER', 6, 6.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (9, 12, 6, NULL, 'USER', 7, 5.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');
INSERT INTO public.tournament_rankings VALUES (10, 12, 7, NULL, 'USER', 8, 0.00, NULL, NULL, NULL, '2026-01-21 22:50:27.964515+01');


--
-- Name: attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attendance_id_seq', 364, true);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bookings_id_seq', 360, true);


--
-- Name: semester_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.semester_enrollments_id_seq', 44, true);


--
-- Name: semesters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.semesters_id_seq', 15, true);


--
-- Name: sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.sessions_id_seq', 64, true);


--
-- Name: tournament_rankings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournament_rankings_id_seq', 12, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 57YmORFZgsvJljbBaXCWewkAF7zeDejJwVOn19DqmoOG6fymDynYRcy63xjIUSz

