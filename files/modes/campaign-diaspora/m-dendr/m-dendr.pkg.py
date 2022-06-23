name = "Campaign Mission - Dendr Final"
contents = [
    "../shared/one-race-mission-ingame.py",
    "den-final.py",
    "../st-onerace/one-race.xls",
    "den-final.xls"
]
starting_conditions = [
    "StandardMapgen()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring('no_tasks')",
    "DendrMainMission()",
    "DendrMusic()"
]
