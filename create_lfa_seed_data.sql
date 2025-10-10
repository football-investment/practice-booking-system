-- 🏈 LFA Player Testing Environment - Seed Data
-- Created: 2025.09.20 for 2-day testing period
-- Password for all accounts: FootballMaster2025!

BEGIN;

-- 🧹 Clean existing test data
DELETE FROM project_milestone_progress WHERE enrollment_id IN (
    SELECT id FROM project_enrollments WHERE user_id IN (
        SELECT id FROM users WHERE email LIKE '%@lfa.test'
    )
);
DELETE FROM project_enrollments WHERE user_id IN (
    SELECT id FROM users WHERE email LIKE '%@lfa.test'
);
DELETE FROM attendance WHERE user_id IN (
    SELECT id FROM users WHERE email LIKE '%@lfa.test'
);
DELETE FROM bookings WHERE user_id IN (
    SELECT id FROM users WHERE email LIKE '%@lfa.test'
);
DELETE FROM users WHERE email LIKE '%@lfa.test';

-- Clean existing test content
DELETE FROM sessions WHERE title LIKE '%Taktikai%' OR title LIKE '%Labdabirtoklás%' OR title LIKE '%Kondicionálás%' OR title LIKE '%Mérkőzés%';
DELETE FROM projects WHERE title LIKE '%Fiatal%' OR title LIKE '%Kapus%' OR title LIKE '%Barcelona%' OR title LIKE '%Real Madrid%';
DELETE FROM project_milestones WHERE project_id IN (
    SELECT id FROM projects WHERE title LIKE '%Fiatal%' OR title LIKE '%Kapus%' OR title LIKE '%Barcelona%' OR title LIKE '%Real Madrid%'
);
DELETE FROM groups WHERE name LIKE '%Academy%' OR name LIKE '%Cantera%' OR name LIKE '%Development%';
DELETE FROM semesters WHERE code LIKE '%LIVE%' OR code LIKE '%DEMO%' OR code LIKE '%CROSS%';

-- 📅 1. SZEMESZTEREK LÉTREHOZÁSA
INSERT INTO semesters (code, name, start_date, end_date, is_active, created_at, updated_at) VALUES
('LIVE-TEST-2025', 'Éles Teszt Szemeszter 2025.09.20-22', '2025-09-20', '2025-09-22', true, NOW(), NOW()),
('DEMO-PAST-2025', 'Demo Múltbeli Szemeszter', '2025-07-01', '2025-07-31', false, NOW(), NOW()),
('DEMO-FUTURE-2026', 'Demo Jövőbeli Szemeszter', '2026-01-15', '2026-01-17', false, NOW(), NOW()),
('CROSS-TEST-2025', 'Cross-Semester Teszt', '2025-08-01', '2025-08-31', true, NOW(), NOW());

-- 👥 2. FUTBALLISTA FELHASZNÁLÓK
INSERT INTO users (name, email, password_hash, role, is_active, created_at, updated_at) VALUES
-- 🎯 Players (LFA Test Players)
('Lionel Messi', 'messi@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'STUDENT', true, NOW(), NOW()),
('Cristiano Ronaldo', 'ronaldo@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'STUDENT', true, NOW(), NOW()),
('Neymar Jr.', 'neymar@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'STUDENT', true, NOW(), NOW()),
('Kylian Mbappé', 'mbappe@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'STUDENT', true, NOW(), NOW()),

-- 🏃‍♂️ Instructors (Coaches)
('Pep Guardiola', 'guardiola@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'INSTRUCTOR', true, NOW(), NOW()),
('Carlo Ancelotti', 'ancelotti@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'INSTRUCTOR', true, NOW(), NOW()),
('Jürgen Klopp', 'klopp@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'INSTRUCTOR', true, NOW(), NOW()),

-- 👑 Admins (Legends)
('Diego Maradona', 'maradona@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'ADMIN', true, NOW(), NOW()),
('Pelé', 'pele@lfa.test', '$2b$12$LmA0UW9eoM/IaijwTxB55.S5Gs8u44N4nKzRCqHDJtK.n/Fb8Bw7m', 'ADMIN', true, NOW(), NOW());

-- 🏟️ 3. CSOPORTOK (Football Teams)
INSERT INTO groups (name, semester_id, description, created_at, updated_at) VALUES
('FC Barcelona Academy', (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'), 'Barcelona ifjúsági akadémia', NOW(), NOW()),
('Real Madrid Cantera', (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'), 'Real Madrid utánpótlás', NOW(), NOW()),
('PSG Development', (SELECT id FROM semesters WHERE code = 'DEMO-PAST-2025'), 'PSG fejlesztési program', NOW(), NOW()),
('Manchester City Youth', (SELECT id FROM semesters WHERE code = 'DEMO-FUTURE-2026'), 'Man City ifjúsági csapat', NOW(), NOW()),
('Liverpool Academy', (SELECT id FROM semesters WHERE code = 'CROSS-TEST-2025'), 'Liverpool akadémia', NOW(), NOW());

-- ⚽ 4. FUTBALL SESSIONÖK (2025.09.20-22)
INSERT INTO sessions (
    title, description, date_start, date_end, capacity, mode, location, meeting_link,
    instructor_id, semester_id, group_id, sport_type, level, instructor_name,
    created_at, updated_at
) VALUES

-- 📅 Day 1 - 2025.09.20
(
    'Taktikai Alapok - 4-3-3 Formáció',
    'A modern futball alapformációjának elsajátítása Guardiola módszerével. Pozíciós játék, labdabirtoklás és nyomás után visszaszerzés.',
    '2025-09-20 09:00:00',
    '2025-09-20 10:30:00',
    25,
    'OFFLINE',
    'Puskás Aréna - Edzőpálya 1',
    NULL,
    (SELECT id FROM users WHERE email = 'guardiola@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'FC Barcelona Academy'),
    'Taktikai Edzés',
    'Haladó',
    'Pep Guardiola',
    NOW(),
    NOW()
),

(
    'Labdabirtoklás és Passzolás',
    'Technikai elemek fejlesztése Ancelotti-stílusú gyakorlatokkal. Rövid és hosszú passzok, első érintés, védelem alatti labdavezetés.',
    '2025-09-20 11:00:00',
    '2025-09-20 12:30:00',
    20,
    'OFFLINE',
    'Telki Edzőközpont - Műfüves pálya',
    NULL,
    (SELECT id FROM users WHERE email = 'ancelotti@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'Real Madrid Cantera'),
    'Technikai Edzés',
    'Középhaladó',
    'Carlo Ancelotti',
    NOW(),
    NOW()
),

(
    'Online Taktikai Elemzés',
    'Videós taktikai elemzés élő mérkőzésekből - interaktív online session. Real-time elemzés, játékos mozgások értékelése.',
    '2025-09-20 16:00:00',
    '2025-09-20 17:00:00',
    50,
    'ONLINE',
    NULL,
    'https://meet.lfa.test/tactical-analysis-sep20',
    (SELECT id FROM users WHERE email = 'guardiola@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'FC Barcelona Academy'),
    'Taktikai Elemzés',
    'Minden szint',
    'Pep Guardiola',
    NOW(),
    NOW()
),

-- 📅 Day 2 - 2025.09.21
(
    'Kondicionálás és Erőnlét',
    'Klopp-féle intenzív fizikai felkészítés és állóképesség fejlesztés. Intervall edzés, gyorsaság, robbanékonyság.',
    '2025-09-21 08:30:00',
    '2025-09-21 10:00:00',
    30,
    'OFFLINE',
    'NB1 Fitness Center - Erősítő terem',
    NULL,
    (SELECT id FROM users WHERE email = 'klopp@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'Real Madrid Cantera'),
    'Kondicionális Edzés',
    'Haladó',
    'Jürgen Klopp',
    NOW(),
    NOW()
),

(
    'Hybrid Taktikai Workshop',
    'Vegyes online-offline taktikai megbeszélés élő demonstrációval. Elméleti háttér és gyakorlati alkalmazás.',
    '2025-09-21 13:00:00',
    '2025-09-21 14:30:00',
    40,
    'HYBRID',
    'Magyar Labdarúgó Szövetség - Nagyterem',
    'https://meet.lfa.test/hybrid-workshop-sep21',
    (SELECT id FROM users WHERE email = 'guardiola@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'FC Barcelona Academy'),
    'Workshop',
    'Középhaladó',
    'Pep Guardiola',
    NOW(),
    NOW()
),

-- 📅 Day 3 - 2025.09.22 (Final day)
(
    'Mérkőzés Szimulációs Edzés',
    'Teljes mérkőzés szimulációs gyakorlat - záró edzés. 11 vs 11, taktikai variációk, játékhelyzetek elemzése.',
    '2025-09-22 09:00:00',
    '2025-09-22 11:00:00',
    22,
    'OFFLINE',
    'Bozsik Aréna - Főpálya',
    NULL,
    (SELECT id FROM users WHERE email = 'ancelotti@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'Real Madrid Cantera'),
    'Mérkőzés Szimuláció',
    'Profi',
    'Carlo Ancelotti',
    NOW(),
    NOW()
),

-- 🌐 CROSS-SEMESTER SESSION (Mbappé teszteléshez)
(
    'Cross-Semester Speciális Edzés',
    'Speciális edzés különböző szemeszterek közötti kapcsolatok tesztelésére. Csak Mbappé számára elérhető.',
    '2025-09-21 15:00:00',
    '2025-09-21 16:00:00',
    15,
    'OFFLINE',
    'Liverpool Training Ground',
    NULL,
    (SELECT id FROM users WHERE email = 'klopp@lfa.test'),
    (SELECT id FROM semesters WHERE code = 'CROSS-TEST-2025'),
    (SELECT id FROM groups WHERE name = 'Liverpool Academy'),
    'Speciális Edzés',
    'Teszt',
    'Jürgen Klopp',
    NOW(),
    NOW()
);

COMMIT;

-- 📊 Verify data
SELECT 
    '👥 Futballista felhasználók' as category,
    COUNT(*) as count
FROM users 
WHERE email LIKE '%@lfa.test'

UNION ALL

SELECT 
    '📅 Szemeszterek' as category,
    COUNT(*) as count
FROM semesters 
WHERE code LIKE '%TEST%' OR code LIKE '%DEMO%' OR code LIKE '%CROSS%'

UNION ALL

SELECT 
    '⚽ Football sessionök' as category,
    COUNT(*) as count
FROM sessions 
WHERE title LIKE '%Taktikai%' OR title LIKE '%Labdabirtoklás%' OR title LIKE '%Kondicionálás%' OR title LIKE '%Mérkőzés%' OR title LIKE '%Cross-Semester%'

UNION ALL

SELECT 
    '🏟️ Csoportok' as category,
    COUNT(*) as count
FROM groups 
WHERE name LIKE '%Academy%' OR name LIKE '%Cantera%' OR name LIKE '%Development%';

-- 🎉 Success message
-- 🎉 LFA Test Data Successfully Created!
-- 👥 9 futballista accounts ready
-- ⚽ 7 football sessions created  
-- 📅 4 test semesters configured
-- 🔑 Password for all accounts: FootballMaster2025!