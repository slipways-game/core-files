name = "Campaign Mission - Silthid Final"
contents = [
    "../shared/rips-shared.py",
    "../shared/one-race-mission-ingame.py",
    "sil-final.py",
    "../st-onerace/one-race.xls",
    "sil-final.xls"
]
starting_conditions = [
    "StandardMapgen(SilthidMapgenSettings())",
    "MapgenSilthidPlanetTypes()",
    "AddIzziumMapgen()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring('no_tasks')",
    "SilthidMainMission()",
    "SilthidMusic()"
]
