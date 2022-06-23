name = "Campaign Mission - Bridge"
contents = [
    "bridge.py",
    "bridge.xls"
]
starting_conditions = [
    "StandardMapgen(BridgeMapSettings())",    
    "StandardConditions('no_time_limit', 'no_slipspace_overload')",
    "StandardScoring(exclude=['empire_size'])",
    "BridgeMainMission()",
]
