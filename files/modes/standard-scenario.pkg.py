name = "Standard Mode Scenario"
contents = [
    "standard/mapgen.py",
    "standard/setup.py",
    "standard/storage.py",
    "tutorial/tutorials.py",
    "tutorial/ingame-tutorials.py"
]
starting_conditions = [
    key("mapgen") / "StandardMapgen()",
    "StandardPlanetQuirks()",
    "StandardConditions()",
    "StandardQuests()",
    "SixTechLevels()",
    "StandardScoring()",
    "QuirkScoringSetup()",
    "StandardStats()",
    "StandardStorage()",
    "IngamePopupTutorials()",
    "QuestBasedMusic(2)"
]
