"""
Football Skills Configuration
Unified skill structure for onboarding, skill progression engine, and dashboard
"""

from typing import Dict, List, TypedDict


class SkillDefinition(TypedDict):
    """Single skill definition"""
    key: str  # snake_case key for database
    name_en: str  # English display name
    name_hu: str  # Hungarian display name
    description_hu: str  # Hungarian description


class SkillCategory(TypedDict):
    """Skill category definition"""
    key: str
    name_en: str
    name_hu: str
    emoji: str
    skills: List[SkillDefinition]


# Complete skill structure
SKILL_CATEGORIES: List[SkillCategory] = [
    {
        "key": "outfield",
        "name_en": "Outfield",
        "name_hu": "Mezőnyjátékos technikai készségek",
        "emoji": "🟦",
        "skills": [
            {
                "key": "ball_control",
                "name_en": "Ball Control",
                "name_hu": "Labdakontroll",
                "description_hu": "A labda átvételének és kezelésének minősége különböző szituációkban."
            },
            {
                "key": "dribbling",
                "name_en": "Dribbling",
                "name_hu": "Cselezés",
                "description_hu": "Ellenféllel szembeni labdavezetési és irányváltási képesség."
            },
            {
                "key": "finishing",
                "name_en": "Finishing",
                "name_hu": "Befejezés",
                "description_hu": "Helyzetek gólra váltásának hatékonysága."
            },
            {
                "key": "shot_power",
                "name_en": "Shot Power",
                "name_hu": "Lövőerő",
                "description_hu": "A lövések ereje, különösen távolról vagy nagy intenzitású helyzetekben."
            },
            {
                "key": "long_shots",
                "name_en": "Long Shots",
                "name_hu": "Távoli lövések",
                "description_hu": "Pontosság és hatékonyság 16 méteren kívüli lövéseknél."
            },
            {
                "key": "volleys",
                "name_en": "Volleys",
                "name_hu": "Röplabdás lövések",
                "description_hu": "Levegőből, pattanás nélkül elvégzett lövések minősége."
            },
            {
                "key": "crossing",
                "name_en": "Crossing",
                "name_hu": "Beadások",
                "description_hu": "Oldalról érkező labdák pontossága és használhatósága."
            },
            {
                "key": "passing",
                "name_en": "Passing",
                "name_hu": "Passzok",
                "description_hu": "Rövid és középtávú passzok pontossága és időzítése."
            },
            {
                "key": "heading",
                "name_en": "Heading",
                "name_hu": "Fejelési pontosság",
                "description_hu": "Fejesek irányíthatósága támadásban és védekezésben."
            },
            {
                "key": "tackle",
                "name_en": "Tackle",
                "name_hu": "Szerelés állva",
                "description_hu": "Labdaszerzés álló helyzetben, szabályosan."
            },
            {
                "key": "marking",
                "name_en": "Marking",
                "name_hu": "Emberfogás",
                "description_hu": "Ellenfél követése, leválás megakadályozása."
            }
        ]
    },
    {
        "key": "set_pieces",
        "name_en": "Set Pieces",
        "name_hu": "Rögzített helyzetek",
        "emoji": "🟨",
        "skills": [
            {
                "key": "free_kicks",
                "name_en": "Free Kicks",
                "name_hu": "Szabadrúgások",
                "description_hu": "Közvetlen és közvetett szabadrúgások minősége."
            },
            {
                "key": "corners",
                "name_en": "Corners",
                "name_hu": "Szögletrúgások",
                "description_hu": "Szögletek pontossága és veszélyessége."
            },
            {
                "key": "penalties",
                "name_en": "Penalties",
                "name_hu": "Tizenegyesek",
                "description_hu": "Büntetők értékesítésének megbízhatósága."
            }
        ]
    },
    {
        "key": "mental",
        "name_en": "Mental",
        "name_hu": "Mentális és taktikai készségek",
        "emoji": "🟩",
        "skills": [
            {
                "key": "positioning_off",
                "name_en": "Positioning (Off)",
                "name_hu": "Helyezkedés támadásban",
                "description_hu": "Üres területek felismerése, jó pozíciók felvétele."
            },
            {
                "key": "positioning_def",
                "name_en": "Positioning (Def)",
                "name_hu": "Helyezkedés védekezésben",
                "description_hu": "Védekező pozíciók megtartása, zárások."
            },
            {
                "key": "vision",
                "name_en": "Vision",
                "name_hu": "Játéklátás",
                "description_hu": "Passzsávok, lehetőségek felismerése."
            },
            {
                "key": "aggression",
                "name_en": "Aggression",
                "name_hu": "Agresszivitás",
                "description_hu": "Párharcok intenzitása, harciasság."
            },
            {
                "key": "reactions",
                "name_en": "Reactions",
                "name_hu": "Reakcióidő",
                "description_hu": "Váratlan helyzetekre adott gyors válaszok."
            },
            {
                "key": "composure",
                "name_en": "Composure",
                "name_hu": "Hidegvér",
                "description_hu": "Nyomás alatti döntéshozatal minősége."
            },
            {
                "key": "consistency",
                "name_en": "Consistency",
                "name_hu": "Kiegyensúlyozottság",
                "description_hu": "Teljesítmény stabilitása mérkőzésről mérkőzésre."
            },
            {
                "key": "tactical_awareness",
                "name_en": "Tactical Awareness",
                "name_hu": "Taktikai tudatosság",
                "description_hu": "Csapatstruktúra és játékelvek megértése."
            }
        ]
    },
    {
        "key": "physical",
        "name_en": "Physical Fitness",
        "name_hu": "Fizikai képességek",
        "emoji": "🟥",
        "skills": [
            {
                "key": "acceleration",
                "name_en": "Acceleration",
                "name_hu": "Gyorsulás",
                "description_hu": "Első lépések robbanékonysága."
            },
            {
                "key": "sprint_speed",
                "name_en": "Sprint Speed",
                "name_hu": "Végsebesség",
                "description_hu": "Maximális futási sebesség."
            },
            {
                "key": "agility",
                "name_en": "Agility",
                "name_hu": "Agilitás",
                "description_hu": "Gyors irányváltás, testkontroll."
            },
            {
                "key": "jumping",
                "name_en": "Jumping",
                "name_hu": "Ugróképesség",
                "description_hu": "Fejpárbajokhoz és levegőben való játékhoz."
            },
            {
                "key": "strength",
                "name_en": "Strength",
                "name_hu": "Erő",
                "description_hu": "Test-test elleni párharcokban mutatott fizikai fölény."
            },
            {
                "key": "stamina",
                "name_en": "Stamina",
                "name_hu": "Állóképesség",
                "description_hu": "Terhelhetőség a mérkőzés teljes ideje alatt."
            },
            {
                "key": "balance",
                "name_en": "Balance",
                "name_hu": "Egyensúly",
                "description_hu": "Stabilitás mozgás és kontakt közben."
            }
        ]
    }
]


# Flat mapping for quick lookup: skill_key -> skill definition
ALL_SKILLS: Dict[str, SkillDefinition] = {}
for category in SKILL_CATEGORIES:
    for skill in category["skills"]:
        ALL_SKILLS[skill["key"]] = skill


# Default baseline for new skills (existing players migration)
DEFAULT_SKILL_BASELINE = 50.0


def get_all_skill_keys() -> List[str]:
    """Return list of all skill keys"""
    return list(ALL_SKILLS.keys())


def get_skill_display_name(skill_key: str, lang: str = "hu") -> str:
    """Get display name for a skill"""
    skill = ALL_SKILLS.get(skill_key)
    if not skill:
        return skill_key.replace("_", " ").title()
    return skill[f"name_{lang}"] if f"name_{lang}" in skill else skill["name_en"]


def get_skill_description(skill_key: str) -> str:
    """Get Hungarian description for a skill"""
    skill = ALL_SKILLS.get(skill_key)
    return skill.get("description_hu", "") if skill else ""


def get_category_by_key(category_key: str) -> SkillCategory | None:
    """Get category definition by key"""
    for category in SKILL_CATEGORIES:
        if category["key"] == category_key:
            return category
    return None
