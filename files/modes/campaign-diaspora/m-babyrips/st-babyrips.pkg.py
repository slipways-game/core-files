name = "Sector type - Rips"
contents = [
    "../campaigns.py",
    "../shared/rips-shared.py",
    "babyrips.py",
    "babyrips.xls",
    "st-babyrips.xls"
]
starting_conditions = [
    key("mapgen") / "StandardMapgen(BabyRipsMapgenSettings())",
    "BabyRipsMissionMapgen()"
]
