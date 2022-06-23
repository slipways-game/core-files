name = "Core"
contents = [
    "game.xls",    
    "game_rules.py",
    "core/utilities.py",
    "core/generation.py",
    "core/events.py",
    "core/resources.py",
    "core/consequences.py",
    "core/actions.py",
    "core/qualities.py",
    "core/structures.py",
    "core/conditions.py",
    "core/projects.py",
    "core/stations.py",
    "core/music.py",
    "core/scoring.py",
    "core/hubs.py",
    "core/races.py",
    "core/quests.py",
    "core/perks.py",
    "core/science.py",
    "core/mutators.py",
    "menus/pages.py",
    "core/seeds.py",
    "core/quirks.py",
    "core/storage.py",
    "modes/tutorial/tutorials.py",
    "core/achievements.py",
    "core/gamelog.py",

    "difficulty-forgiving.xls" / difficulty("forgiving"),
    "difficulty-challenging.xls" / difficulty("challenging"),
    "difficulty-tough.xls" / difficulty("tough"),
    "difficulty-sandbox.xls" / difficulty("sandbox"),
]
starting_conditions = [
    "MetaProgression()"
]
