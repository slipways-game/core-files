name = "Sector Type - Anomalies"
contents = [
    "../campaigns.py",
    "../../standard/mapgen.py",
    "dark.py",
    "dark.xls"
]
starting_conditions = [
    key("mapgen") / "StandardMapgen(DarkMapConfig())",
    "DarkMapgen()",   
    "DarkSetup()",
    "DarkSectorType()"
]
