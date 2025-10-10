-- 📚 LFA Football Projects & Milestones
-- Realistic football-themed projects for testing

BEGIN;

-- Clean existing test projects
DELETE FROM project_milestone_progress WHERE milestone_id IN (
    SELECT id FROM project_milestones WHERE project_id IN (
        SELECT id FROM projects WHERE title LIKE '%Fiatal%' OR title LIKE '%Kapus%' OR title LIKE '%Taktikai%' OR title LIKE '%Barcelona%'
    )
);
DELETE FROM project_milestones WHERE project_id IN (
    SELECT id FROM projects WHERE title LIKE '%Fiatal%' OR title LIKE '%Kapus%' OR title LIKE '%Taktikai%' OR title LIKE '%Barcelona%'
);
DELETE FROM project_enrollments WHERE project_id IN (
    SELECT id FROM projects WHERE title LIKE '%Fiatal%' OR title LIKE '%Kapus%' OR title LIKE '%Taktikai%' OR title LIKE '%Barcelona%'
);
DELETE FROM projects WHERE title LIKE '%Fiatal%' OR title LIKE '%Kapus%' OR title LIKE '%Taktikai%' OR title LIKE '%Barcelona%';

-- 📚 1. FUTBALL PROJEKTEK LÉTREHOZÁSA
INSERT INTO projects (
    title, description, semester_id, instructor_id, max_participants, required_sessions, 
    xp_reward, deadline, status, difficulty, created_at, updated_at
) VALUES

-- Project 1: Barcelona Academy Training Program
(
    'Barcelona Academy - Fiatal Tehetségek Programja',
    'Átfogó fejlesztési program a Barcelona módszertan alapján. A projekt során elsajátítod a pozíciós játékot, a labdabirtoklás művészetét és a tiki-taka stílust. Guardiola személyes mentorálásával.',
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM users WHERE email = 'guardiola@lfa.test'),
    8,
    12,
    500,
    '2025-09-22',
    'ACTIVE',
    'ADVANCED',
    NOW(),
    NOW()
),

-- Project 2: Real Madrid Cantera Excellence
(
    'Real Madrid Cantera - Excelencia Program',
    'A Real Madrid hagyományos értékei alapján épülő fejlesztési program. Technikai készségek, taktikai tudás és mentális erősség fejlesztése. Ancelotti vezetésével a galácticos örökségét viszed tovább.',
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM users WHERE email = 'ancelotti@lfa.test'),
    10,
    10,
    450,
    '2025-09-22',
    'ACTIVE',
    'INTERMEDIATE',
    NOW(),
    NOW()
),

-- Project 3: Liverpool Mentality Monsters
(
    'Liverpool Academy - Mentality Monsters Training',
    'Klopp-féle intenzív fejlesztési program a "Mentality Monsters" filozófia alapján. Fizikai erőnlét, gégenpress taktika és csapatszellem fejlesztése. Heavy metal futball a gyakorlatban.',
    (SELECT id FROM semesters WHERE code = 'LIVE-TEST-2025'),
    (SELECT id FROM users WHERE email = 'klopp@lfa.test'),
    12,
    15,
    600,
    '2025-09-22',
    'ACTIVE',
    'ADVANCED',
    NOW(),
    NOW()
),

-- Cross-semester project for testing restrictions
(
    'Cross-Semester Speciális Program',
    'Speciális fejlesztési program különböző szemeszterek közötti interakciók tesztelésére. Ez a projekt NEM elérhető a LIVE-TEST-2025 szemeszterből.',
    (SELECT id FROM semesters WHERE code = 'CROSS-TEST-2025'),
    (SELECT id FROM users WHERE email = 'klopp@lfa.test'),
    5,
    8,
    300,
    '2025-08-31',
    'ACTIVE',
    'INTERMEDIATE',
    NOW(),
    NOW()
);

-- 🎯 2. MÉRFÖLDKÖVEK LÉTREHOZÁSA

-- Barcelona Academy Project Milestones
INSERT INTO project_milestones (
    project_id, title, description, order_index, required_sessions, xp_reward, 
    deadline, is_required, created_at
) VALUES

-- Barcelona Project Milestones
(
    (SELECT id FROM projects WHERE title = 'Barcelona Academy - Fiatal Tehetségek Programja'),
    'Pozíciós Játék Alapjai',
    'A Barcelona-stílusú pozíciós játék elsajátítása. 4-3-3 formáció, labdabirtoklás és rövidpassz-játék alapjai.',
    1,
    3,
    50,
    '2025-09-21',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Barcelona Academy - Fiatal Tehetségek Programja'),
    'Tiki-Taka Mesterfokon',
    'Gyors labdacserék, mozgás labda nélkül és a térnyerés művészete. Guardiola személyes coaching-ja.',
    2,
    4,
    75,
    '2025-09-22',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Barcelona Academy - Fiatal Tehetségek Programja'),
    'Mérkőzés Alkalmazás',
    'A tanult elemek alkalmazása valós mérkőzés helyzetekben. 11 vs 11 taktikai szimuláció.',
    3,
    5,
    100,
    '2025-09-22',
    true,
    NOW()
),

-- Real Madrid Project Milestones
(
    (SELECT id FROM projects WHERE title = 'Real Madrid Cantera - Excelencia Program'),
    'Galácticos Mentalitás',
    'A Real Madrid történelmi nagyságának megértése és a bajnoki mentalitás kialakítása.',
    1,
    2,
    40,
    '2025-09-21',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Real Madrid Cantera - Excelencia Program'),
    'Technikai Excelencia',
    'Kiváló technikai készségek fejlesztése: labdavezetés, lövés, fejjáték. Ancelotti módszertana.',
    2,
    4,
    80,
    '2025-09-22',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Real Madrid Cantera - Excelencia Program'),
    'Champions League Szimuláció',
    'Nagy tétű mérkőzések szimulációja. Nyomás alatt játék és döntő pillanatok kezelése.',
    3,
    4,
    90,
    '2025-09-22',
    true,
    NOW()
),

-- Liverpool Project Milestones
(
    (SELECT id FROM projects WHERE title = 'Liverpool Academy - Mentality Monsters Training'),
    'Fizikai Kondíció Alapok',
    'Klopp-féle intenzív fizikai felkészítés. Állóképesség, gyorsaság és robbanékonyság fejlesztése.',
    1,
    4,
    60,
    '2025-09-21',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Liverpool Academy - Mentality Monsters Training'),
    'Gégenpress Taktika',
    'A Liverpool jellegzetes préselő játékstílusának elsajátítása. Intenzív labdaszerzés és gyors átmenet.',
    2,
    5,
    80,
    '2025-09-22',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Liverpool Academy - Mentality Monsters Training'),
    'You''ll Never Walk Alone',
    'Csapatszellem és mentális erősség fejlesztése. A Liverpool kultúra és értékek megértése.',
    3,
    3,
    70,
    '2025-09-22',
    true,
    NOW()
),
(
    (SELECT id FROM projects WHERE title = 'Liverpool Academy - Mentality Monsters Training'),
    'Anfield Atmosphere',
    'Nagy tömeg előtti játék és a támogatók erejének hasznosítása. Hazai pálya előny maximalizálása.',
    4,
    3,
    90,
    '2025-09-22',
    false,
    NOW()
);

COMMIT;

-- Verification query
SELECT 
    p.title as project_title,
    p.difficulty,
    p.max_participants,
    p.required_sessions,
    p.xp_reward,
    u.name as instructor_name,
    s.name as semester_name,
    COUNT(pm.id) as milestone_count
FROM projects p
LEFT JOIN users u ON p.instructor_id = u.id
LEFT JOIN semesters s ON p.semester_id = s.id
LEFT JOIN project_milestones pm ON p.id = pm.project_id
WHERE p.title LIKE '%Barcelona%' OR p.title LIKE '%Real Madrid%' OR p.title LIKE '%Liverpool%' OR p.title LIKE '%Cross-Semester%'
GROUP BY p.id, p.title, p.difficulty, p.max_participants, p.required_sessions, p.xp_reward, u.name, s.name
ORDER BY p.title;

-- 🎉 LFA Football Projects Created!
-- 📚 4 realistic football projects with detailed milestones
-- 🎯 Cross-semester restriction testing enabled
-- ⚽ Ready for enrollment testing!