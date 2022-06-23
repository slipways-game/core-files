name = "Campaign Mission - Izzium Mining"
contents = [
    "refine.py",
    "refine.xls"
]
starting_conditions = [
    "StandardMapgen()",
    "RefineMapgen()",
    "RefinePlanetComposition()",
    "StandardConditions('no_time_limit', 'no_slipspace_overload')",
    "CampaignScoring()",
    "RefineMainMission()",
#    "RefineStory()",
#    "RefineMusic()"
]
