name = "Campaign Mission - Forebear Computer"
contents = [
    "computer.py",
    "computer.xls"
]
starting_conditions = [
    "StandardMapgen()",
    "ComputerMapgen()",
    "ComputerResources()",
    "StandardConditions('no_time_limit')",
    "CampaignScoring()",
    "ComputerMainMission()",
    "ComputerStory()",
    "ComputerMusic()"
]
