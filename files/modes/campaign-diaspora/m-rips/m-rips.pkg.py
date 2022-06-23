name = "Campaign Mission - Rips"
contents = [
    "../shared/rips-shared.py",
    "rips.py",
    "rips.xls"
]
starting_conditions = [
    "StandardMapgen(RipsMapgenSettings())",
    "MoreForgeworldsMapgen()",
    "RipsMissionMapgen()",
    "OutpostsMapgen()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring()",
    "RipsMainMission()",
    "RipsMusic()"
]
