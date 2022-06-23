name = "Campaign Mission - Aphorian Final"
contents = [
    "../shared/rips-shared.py",
    "../shared/one-race-mission-ingame.py",
    "aph-final.py",
    "../st-onerace/one-race.xls",
    "aph-final.xls"
]
starting_conditions = [
    "StandardMapgen()",
    "OneRaceRipsMapgen(36, 9)",
    "StandardConditions('no_time_limit')",
    "CampaignScoring('no_tasks')",
    "AphorianMainMission()",
    "AphorianMusic()"
]
