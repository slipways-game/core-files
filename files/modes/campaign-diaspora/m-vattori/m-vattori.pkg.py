name = "Campaign Mission - Vattori Final"
contents = [
    "../shared/one-race-mission-ingame.py",
    "vat-final.py",
    "../st-onerace/one-race.xls",
    "vat-final.xls"
]
starting_conditions = [
    "StandardMapgen()",
    "VattoriMissionMapgen()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring('no_tasks')",
    "VattoriMainMission()",
    "VattoriMusic()"   
]
