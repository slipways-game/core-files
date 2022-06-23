name = "Campaign Mission - Hole"
contents = [
    "../shared/hole-shared.py",
    "hole.py",
    "hole.xls"
]
starting_conditions = [
    "StandardMapgen(HoleMapgenSettings())",
    "MapGenNoBadPlanets()",
    "HoleMapgen()",
    "HoleStartingResources()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring()",
    "HoleMainMission()",
]
