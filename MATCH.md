# Design match (84 items)

How closely each model's front render matches its design, from `pipeline_models/<code>/meta.json`.

- **in-game**: compared at 1/4 of the design resolution, about the size the item is drawn on screen in game.
- **exact**: compared per pixel at full design resolution. It saturates near 0.9: a 1-pixel blur of the design itself scores only 0.68 against the original.

| | in-game | exact |
|---|---|---|
| median | 0.987 | 0.903 |
| min | 0.958 | 0.807 |
| items >= 0.99 | 26 | 0 |
| items >= 0.98 | 63 | 0 |
| items >= 0.97 | 78 | 0 |

| Item | Faces | In-game | Exact | Silhouette | Stopped by |
|---|---|---|---|---|---|
| B09_1 Bone longbow | 2399 | 0.958 | 0.844 | 0.000 | plateau |
| B03_6 Necrotic skull censer | 2400 | 0.961 | 0.853 | 0.000 | budget |
| B08_3 Solar scale platebody | 2399 | 0.963 | 0.808 | 0.000 | plateau |
| B08_6 Verdant crystal body | 2399 | 0.965 | 0.807 | 0.000 | budget |
| B12_2 Seraph longsword | 2399 | 0.969 | 0.869 | 0.000 | budget |
| B11_6 Necrotic soulstaff | 2400 | 0.970 | 0.892 | 0.000 | no error left to fix |
| B09_3 Dragonspine bow | 2400 | 0.972 | 0.838 | 0.000 | budget |
| B08_1 Seraph feather mantle | 2400 | 0.974 | 0.864 | 0.000 | budget |
| B03_1 Necrotic battleaxe | 2400 | 0.975 | 0.868 | 0.000 | plateau |
| B09_2 Shadowvine bow | 2316 | 0.975 | 0.902 | 0.000 | no error left to fix |
| B03_2 Necrotic spear | 2400 | 0.976 | 0.853 | 0.000 | no error left to fix |
| B12_4 Crimson rapier | 2400 | 0.977 | 0.917 | 0.000 | plateau |
| B07_4 Nightstalker ranger tunic | 2400 | 0.977 | 0.956 | 0.000 | target |
| B04_5 Ribcage platebody | 2399 | 0.977 | 0.858 | 0.000 | budget |
| B05_6 Paladin greaves | 2400 | 0.977 | 0.907 | 0.000 | budget |
| B03_3 Necrotic flail | 2399 | 0.978 | 0.901 | 0.000 | budget |
| B11_5 Solar sceptre | 2400 | 0.978 | 0.890 | 0.000 | no error left to fix |
| B02_3 Crimson crystal scimitar | 2400 | 0.979 | 0.925 | 0.000 | plateau |
| B09_5 Seraph crossbow | 2400 | 0.979 | 0.854 | 0.000 | budget |
| B02_4 Sapphire pickaxe | 2399 | 0.979 | 0.932 | 0.000 | budget |
| B09_6 Runic crossbow | 2400 | 0.980 | 0.887 | 0.000 | budget |
| B01_5 Silver filigree platebody | 2399 | 0.980 | 0.827 | 0.000 | budget |
| B03_5 Necrotic crossbow | 2399 | 0.981 | 0.864 | 0.000 | budget |
| B12_3 Bloodfang cleaver | 2399 | 0.981 | 0.937 | 0.000 | budget |
| B14_1 Dragonfire shield | 2400 | 0.982 | 0.901 | 0.000 | budget |
| B05_1 Crimson knight helm | 2399 | 0.982 | 0.947 | 0.000 | plateau |
| B10_5 Runeweaver robe top | 2399 | 0.983 | 0.880 | 0.000 | budget |
| B06_5 Magma mace | 2400 | 0.983 | 0.936 | 0.000 | plateau |
| B13_1 Amulet of the sun | 2399 | 0.983 | 0.889 | 0.000 | budget |
| B10_6 Runeweaver robe skirt | 2399 | 0.983 | 0.895 | 0.000 | budget |
| B07_6 Valkyrie platebody | 2399 | 0.983 | 0.875 | 0.000 | budget |
| B14_2 Glacial crystal shield | 2400 | 0.984 | 0.879 | 0.000 | budget |
| B09_4 Crystal-root bow | 2399 | 0.984 | 0.885 | 0.000 | plateau |
| B12_1 Abyssal tidewhip | 2399 | 0.984 | 0.852 | 0.000 | budget |
| B13_3 Sapphire amulet | 2399 | 0.985 | 0.851 | 0.000 | budget |
| B03_4 Necrotic twin mauls | 2400 | 0.985 | 0.879 | 0.000 | budget |
| B08_4 Solar scale platelegs | 2400 | 0.986 | 0.862 | 0.000 | budget |
| B04_4 Horned bone helm | 2399 | 0.986 | 0.870 | 0.000 | budget |
| B08_5 Verdant crystal helm | 2399 | 0.986 | 0.848 | 0.000 | budget |
| B14_6 Crimson spiked roundshield | 2400 | 0.987 | 0.914 | 0.000 | budget |
| B14_3 Solar heater shield | 2400 | 0.987 | 0.874 | 0.000 | budget |
| B06_1 Magma helm | 2399 | 0.987 | 0.937 | 0.000 | budget |
| B07_1 Woodland ranger tunic | 2399 | 0.987 | 0.929 | 0.000 | budget |
| B04_6 Bone bracers | 2399 | 0.988 | 0.882 | 0.000 | budget |
| B10_3 Astral robe bottom | 2400 | 0.988 | 0.926 | 0.000 | budget |
| B07_5 Valkyrie winged helm | 2399 | 0.988 | 0.900 | 0.000 | plateau |
| B12_5 Gilded fang | 2400 | 0.988 | 0.918 | 0.000 | plateau |
| B01_1 Copper scale platebody | 2399 | 0.989 | 0.875 | 0.000 | budget |
| B05_4 Paladin full helm | 2399 | 0.989 | 0.895 | 0.000 | budget |
| B08_2 Solar helm | 2400 | 0.989 | 0.862 | 0.000 | budget |
| B05_5 Paladin platebody | 2400 | 0.989 | 0.901 | 0.000 | budget |
| B11_4 Stormcaller staff | 2399 | 0.989 | 0.916 | 0.000 | plateau |
| B02_2 Crimson dragonscale body | 2399 | 0.989 | 0.895 | 0.000 | budget |
| B05_3 Crimson knight tassets | 2400 | 0.989 | 0.922 | 0.000 | budget |
| B01_4 Shadowsteel platebody | 2399 | 0.990 | 0.966 | 0.000 | target |
| B04_2 Reaver platelegs | 2399 | 0.990 | 0.928 | 0.000 | budget |
| B07_3 Emberhide ranger tunic | 2400 | 0.990 | 0.954 | 0.000 | budget |
| B13_4 Verdant shard amulet | 2399 | 0.990 | 0.932 | 0.000 | budget |
| B13_6 Magma cape | 2400 | 0.990 | 0.905 | 0.000 | budget |
| B11_1 Voidwoven hood | 2399 | 0.990 | 0.954 | 0.000 | target |
| B11_3 Voidwoven robe skirt | 2399 | 0.991 | 0.951 | 0.000 | budget |
| B07_2 Tidewalker ranger tunic | 2399 | 0.991 | 0.950 | 0.000 | plateau |
| B13_2 Crimson cord necklace | 2399 | 0.991 | 0.959 | 0.000 | plateau |
| B02_1 Royal sapphire platebody | 2399 | 0.991 | 0.913 | 0.000 | budget |
| B04_1 Reaver platebody | 2399 | 0.991 | 0.923 | 0.000 | budget |
| B01_6 Jade crystal platebody | 2400 | 0.992 | 0.922 | 0.000 | budget |
| B10_1 Astral wizard hat | 2400 | 0.993 | 0.928 | 0.000 | plateau |
| B01_3 Steel platebody | 2399 | 0.993 | 0.909 | 0.000 | budget |
| B04_3 Reaver warboots | 2400 | 0.993 | 0.928 | 0.000 | plateau |
| B14_4 Jade thorn shield | 2400 | 0.993 | 0.917 | 0.000 | budget |
| B10_2 Astral robe top | 2399 | 0.993 | 0.927 | 0.000 | budget |
| B10_4 Runeweaver hood | 2399 | 0.993 | 0.946 | 0.000 | budget |
| B11_2 Voidwoven robe top | 2399 | 0.993 | 0.954 | 0.000 | budget |
| B12_6 Goblin knotclub | 2399 | 0.994 | 0.958 | 0.000 | budget |
| B06_6 Magma kiteshield | 2400 | 0.994 | 0.955 | 0.000 | target |
| B13_5 Obsidian cape | 2400 | 0.994 | 0.936 | 0.000 | budget |
| B01_2 Iron platebody | 2399 | 0.994 | 0.927 | 0.000 | budget |
| B06_3 Magma gauntlets | 2400 | 0.995 | 0.954 | 0.000 | target |
| B05_2 Crimson chain hauberk | 2399 | 0.995 | 0.887 | 0.000 | budget |
| B02_6 Magma hatchet | 2400 | 0.995 | 0.893 | 0.000 | budget |
| B06_2 Magma platebody | 2400 | 0.996 | 0.925 | 0.000 | budget |
| B02_5 Magma pickaxe | 2399 | 0.996 | 0.927 | 0.000 | budget |
| B14_5 Sapphire dragon kiteshield | 2399 | 0.997 | 0.886 | 0.000 | budget |
| B06_4 Magma dagger | 2324 | 0.997 | 0.952 | 0.000 | target |
