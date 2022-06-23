name = "Campaign Mission - Izzium Threat"
contents = [
    "izzium.py",
    "izzium.xls"
]
starting_conditions = [
    "StandardMapgen()",
    "IzziumMapgen()",
    "IzziumSetup()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring()",
    "IzziumMainMission()",
    "IzziumStory()",
    "IzziumMusic()"
]
