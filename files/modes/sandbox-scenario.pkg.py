name = "Sandbox Mode Scenario"
contents = [
    "standard/mapgen.py",
    "standard/setup.py",
    "sandbox/tech.py",
    "sandbox/setup.py",
    "tutorial/tutorials.py",
    "tutorial/ingame-tutorials.py"
]
mutators = [
    "mut_increased_tech_costs([180, 170, 160, 160, 170, 180])",
    "mut_quest_difficulty(3, 40)"
]
starting_conditions = [
    "StandardMapgen()",
    "StandardPlanetQuirks()",
    "SandboxResources()",
    "SandboxConditions()",
    "SandboxStats()",
    "SandboxQuests()",
    "SandboxTechLevels()",
    "SizeBasedMusic(4)",
    "IngamePopupTutorials()"
]
