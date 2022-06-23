name = "Campaign Mission - Dark"
contents = [
    "dark.py",
    "dark.xls"
]
starting_conditions = [
    "StandardMapgen(DarkMapConfig())", 
    "DarkMapgen()",   
    "DarkSetup()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring()",
    "DarkMainMission()",
]
