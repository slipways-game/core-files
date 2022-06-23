name = "Campaign Mission - Rips"
contents = [
    "../shared/rips-shared.py",
    "babyrips.py",
    "babyrips.xls"
]
starting_conditions = [
    "StandardMapgen(BabyRipsMapgenSettings())",
    "BabyRipsMissionMapgen()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring()",
    "BabyRipsMainMission()",
    "BabyRipsStory()",
]
