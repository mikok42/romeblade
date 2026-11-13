"""Map RTW EDU type names to Native M&B troop stand-ins by role keywords."""
from __future__ import print_function

# Player side (team 0) uses Swadian stand-ins; enemy (team 1) Vaegir.
ROLE_TROOPS = {
    "player": {
        "infantry": "trp_swadian_infantry",
        "missile": "trp_swadian_crossbowman",
        "cavalry": "trp_swadian_man_at_arms",
    },
    "enemy": {
        "infantry": "trp_vaegir_infantry",
        "missile": "trp_vaegir_archer",
        "cavalry": "trp_vaegir_horseman",
    },
}

MISSILE_KEYS = (
    "archer",
    "crossbow",
    "slinger",
    "javelin",
    "peltast",
    "hurler",
    "skirmish",
)
CAVALRY_KEYS = (
    "cavalry",
    "horse",
    "equite",
    "cataphract",
    "camel",
    "chariot",
    "general",
    "bodyguard",
)


def role_for_edu(edu_name):
    n = edu_name.lower()
    if any(k in n for k in CAVALRY_KEYS):
        return "cavalry"
    if any(k in n for k in MISSILE_KEYS):
        return "missile"
    return "infantry"


def role_counts(fingerprint):
    """Collapse EDU fingerprint into infantry/missile/cavalry headcounts."""
    out = {"infantry": 0, "missile": 0, "cavalry": 0}
    for edu, n in fingerprint.items():
        out[role_for_edu(edu)] += int(n)
    return out


def troop_plan(fingerprint, side):
    """side: 'player' or 'enemy' -> list of (troop_id_str, count) with count>0."""
    roles = role_counts(fingerprint)
    table = ROLE_TROOPS[side]
    plan = []
    for role, troop in table.items():
        c = roles.get(role, 0)
        if c > 0:
            plan.append((troop, c))
    if not plan:
        plan.append((table["infantry"], 1))
    return plan
