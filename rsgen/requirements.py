"""Equip requirements for the 84 redesigns (a proposal, OSRS conventions).

Levels follow each item's material/theme tier, the way OSRS gear is laddered:
armour needs Defence, melee weapons Attack (Strength for crushing two-handers),
bows/crossbows and ranger gear Ranged, robes and staves Magic, tools their
gathering skill too. Change a number here and rebuild: build.py writes it to
out/defs/requirements.json and the manifest.
"""

# OSRS skill ids (same order as the client's skill list)
SKILL_ID = {'attack': 0, 'defence': 1, 'strength': 2, 'hitpoints': 3, 'ranged': 4, 'prayer': 5, 'magic': 6,
            'woodcutting': 8, 'mining': 14}

REQUIREMENTS = {
    # B01-B02 platebodies: metal tiers
    'B01_1': {'defence': 1},                       # Copper scale platebody (bronze tier)
    'B01_2': {'defence': 1},                       # Iron platebody
    'B01_3': {'defence': 5},                       # Steel platebody
    'B01_4': {'defence': 30},                      # Shadowsteel platebody
    'B01_5': {'defence': 20},                      # Silver filigree platebody
    'B01_6': {'defence': 50},                      # Jade crystal platebody
    'B02_1': {'defence': 40},                      # Royal sapphire platebody
    'B02_2': {'ranged': 60, 'defence': 40},        # Crimson dragonscale body (d'hide-style)
    'B02_3': {'attack': 60},                       # Crimson crystal scimitar
    'B02_4': {'attack': 40, 'mining': 41},         # Sapphire pickaxe
    'B02_5': {'attack': 60, 'mining': 61},         # Magma pickaxe
    'B02_6': {'attack': 60, 'woodcutting': 61},    # Magma hatchet
    # B03 necrotic weapons
    'B03_1': {'attack': 70, 'strength': 70},       # Necrotic battleaxe
    'B03_2': {'attack': 70},                       # Necrotic spear
    'B03_3': {'attack': 70},                       # Necrotic flail
    'B03_4': {'strength': 75},                     # Necrotic twin mauls
    'B03_5': {'ranged': 70},                       # Necrotic crossbow
    'B03_6': {'magic': 70, 'prayer': 50},          # Necrotic skull censer
    # B04 reaver / bone set
    'B04_1': {'defence': 60},                      # Reaver platebody
    'B04_2': {'defence': 60},                      # Reaver platelegs
    'B04_3': {'defence': 60},                      # Reaver warboots
    'B04_4': {'defence': 45},                      # Horned bone helm
    'B04_5': {'defence': 45},                      # Ribcage platebody
    'B04_6': {'defence': 45},                      # Bone bracers
    # B05 crimson knight / paladin
    'B05_1': {'defence': 50},                      # Crimson knight helm
    'B05_2': {'defence': 50},                      # Crimson chain hauberk
    'B05_3': {'defence': 50},                      # Crimson knight tassets
    'B05_4': {'defence': 55, 'prayer': 40},        # Paladin full helm
    'B05_5': {'defence': 55, 'prayer': 40},        # Paladin platebody
    'B05_6': {'defence': 55, 'prayer': 40},        # Paladin greaves
    # B06 magma set
    'B06_1': {'defence': 65},                      # Magma helm
    'B06_2': {'defence': 65},                      # Magma platebody
    'B06_3': {'defence': 65},                      # Magma gauntlets
    'B06_4': {'attack': 65},                       # Magma dagger
    'B06_5': {'attack': 65},                       # Magma mace
    'B06_6': {'defence': 65},                      # Magma kiteshield
    # B07 ranger tunics + valkyrie
    'B07_1': {'ranged': 20, 'defence': 10},        # Woodland ranger tunic
    'B07_2': {'ranged': 40, 'defence': 20},        # Tidewalker ranger tunic
    'B07_3': {'ranged': 50, 'defence': 25},        # Emberhide ranger tunic
    'B07_4': {'ranged': 60, 'defence': 30},        # Nightstalker ranger tunic
    'B07_5': {'defence': 60},                      # Valkyrie winged helm
    'B07_6': {'defence': 60},                      # Valkyrie platebody
    # B08 seraph / solar / verdant
    'B08_1': {'prayer': 70, 'defence': 40},        # Seraph feather mantle
    'B08_2': {'defence': 70},                      # Solar helm
    'B08_3': {'defence': 70},                      # Solar scale platebody
    'B08_4': {'defence': 70},                      # Solar scale platelegs
    'B08_5': {'defence': 75},                      # Verdant crystal helm
    'B08_6': {'defence': 75},                      # Verdant crystal body
    # B09 bows and crossbows
    'B09_1': {'ranged': 45},                       # Bone longbow
    'B09_2': {'ranged': 60},                       # Shadowvine bow
    'B09_3': {'ranged': 75},                       # Dragonspine bow
    'B09_4': {'ranged': 70},                       # Crystal-root bow
    'B09_5': {'ranged': 80},                       # Seraph crossbow
    'B09_6': {'ranged': 61},                       # Runic crossbow (rune tier)
    # B10-B11 robes and staves
    'B10_1': {'magic': 40},                        # Astral wizard hat
    'B10_2': {'magic': 40},                        # Astral robe top
    'B10_3': {'magic': 40},                        # Astral robe bottom
    'B10_4': {'magic': 55},                        # Runeweaver hood
    'B10_5': {'magic': 55},                        # Runeweaver robe top
    'B10_6': {'magic': 55},                        # Runeweaver robe skirt
    'B11_1': {'magic': 70, 'defence': 30},         # Voidwoven hood
    'B11_2': {'magic': 70, 'defence': 30},         # Voidwoven robe top
    'B11_3': {'magic': 70, 'defence': 30},         # Voidwoven robe skirt
    'B11_4': {'magic': 65},                        # Stormcaller staff
    'B11_5': {'magic': 70},                        # Solar sceptre
    'B11_6': {'magic': 75},                        # Necrotic soulstaff
    # B12 melee weapons
    'B12_1': {'attack': 70},                       # Abyssal tidewhip
    'B12_2': {'attack': 80},                       # Seraph longsword
    'B12_3': {'attack': 70, 'strength': 70},       # Bloodfang cleaver
    'B12_4': {'attack': 60},                       # Crimson rapier
    'B12_5': {'attack': 50},                       # Gilded fang
    'B12_6': {'attack': 10},                       # Goblin knotclub
    # B13 neck and capes
    'B13_1': {'prayer': 45},                       # Amulet of the sun
    'B13_2': {},                                   # Crimson cord necklace
    'B13_3': {},                                   # Sapphire amulet
    'B13_4': {'magic': 40},                        # Verdant shard amulet
    'B13_5': {},                                   # Obsidian cape
    'B13_6': {'defence': 60},                      # Magma cape
    # B14 shields
    'B14_1': {'defence': 75},                      # Dragonfire shield
    'B14_2': {'defence': 70},                      # Glacial crystal shield
    'B14_3': {'defence': 70},                      # Solar heater shield
    'B14_4': {'defence': 50},                      # Jade thorn shield
    'B14_5': {'defence': 60},                      # Sapphire dragon kiteshield
    'B14_6': {'defence': 40},                      # Crimson spiked roundshield
}


def requirements(code):
    """[(skill name, skill id, level)] for an item, sorted by skill id."""
    return sorted(((s, SKILL_ID[s], lv) for s, lv in REQUIREMENTS[code].items()), key=lambda r: r[1])
