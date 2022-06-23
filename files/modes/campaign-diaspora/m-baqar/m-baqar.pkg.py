name = "Campaign Mission - Ba'qar Final"
contents = [
    "../shared/one-race-mission-ingame.py",
    "../shared/hole-shared.py",
    "baq-final.py",
    "../st-onerace/one-race.xls",
    "baq-final.xls",
]
starting_conditions = [
    "StandardMapgen(BaqarMissionMapgenSettings())",
    "BaqarMissionMapgen()",
    "HoleMapgen()",
    "ReplaceWormholeWithSeal()",
    "NebulaColors()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring('no_tasks')",
    "BaqarMainMission()",
    "BaqarMusic()"
]
