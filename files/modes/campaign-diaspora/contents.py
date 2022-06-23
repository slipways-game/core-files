##############################################################
# Mutators for every mission

def scenario_computer():
    return {
        "label": LS("mission.forebear_computer"),
        "description": LS("mission.forebear_computer.short"),
        "packages": ["modes/campaign-diaspora/m-computer/m-computer"]
    }

def scenario_izzium():
    return {
        "label": LS("mission.izzium_danger"),
        "description": LS("mission.izzium_danger.short"),
        "packages": ["modes/campaign-diaspora/m-izzium/m-izzium"]
    }

def scenario_refine():
    return {
        "label": LS("mission.refine_izzium"),
        "description": LS("mission.refine_izzium.short"),
        "packages": ["modes/campaign-diaspora/m-refine/m-refine"]
    }

def scenario_dark():
    return {
        "label": LS("mission.dark"),
        "description": LS("mission.dark.short"),
        "packages": ["modes/campaign-diaspora/m-dark/m-dark"]
    }

def scenario_rips():
    return {
        "label": LS("mission.rips"),
        "description": LS("mission.rips.short"),
        "packages": ["modes/campaign-diaspora/m-rips/m-rips"]
    }

def scenario_babyrips():
    return {
        "label": LS("mission.babyrips"),
        "description": LS("mission.babyrips.short"),
        "packages": ["modes/campaign-diaspora/m-babyrips/m-babyrips"]
    }

def scenario_hole():
    return {
        "label": LS("mission.hole"),
        "description": LS("mission.hole.short"),
        "packages": ["modes/campaign-diaspora/m-hole/m-hole"]
    }

def scenario_five():
    return {
        "label": LS("mission.five"),
        "description": LS("mission.five.short"),
        "packages": ["modes/campaign-diaspora/m-five/m-five"]
    }

def scenario_missing():
    return {
        "label": LS("mission.missing"),
        "description": LS("mission.missing.desc"),
        "packages": [],
        "missing": True
    }

def act3_intro():
    return {
        "label": None,
        "description": LS("mission.act3_intro.desc")
    }

def scenario_race(race_id):
    def data_fn():
        return {
            "label": LS("mission.%s" % race_id),
            "description": LS("mission.%s.short" % race_id),
            "packages": ["modes/campaign-diaspora/m-%s/m-%s" % (race_id, race_id)]
        }
    return data_fn

##############################################################
# Actual mission list

class CampaignContents:
    CAMPAIGN_ID = "campaign-a"    
    SCENARIO_BASE_PACKAGE = "modes/campaign-diaspora/campaign-scenario-base"
    SCENARIOS = {
        "m-refine": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-refine/m-refine', 'RefineMainMission()')",
            "main_mutator": scenario_refine,
            "position": (-0.65, -0.5)
        },
        "m-izzium": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-izzium/m-izzium', 'IzziumMainMission()')",
            "main_mutator": scenario_izzium,
            "position": (-0.55, -0.2), "requires": ["m-refine"]
        },
        "m-computer": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-computer/m-computer', 'ComputerMainMission()')",
            "main_mutator": scenario_computer,
            "position": (-0.32, -0.36), "requires": ["m-izzium"]
        },
        "m-dark": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-dark/m-dark', 'DarkMainMission()')",
            "main_mutator": scenario_dark,
            "position": (-0.77, 0.12), "requires": ["m-izzium"]
        },
        
        "m-babyrips": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-babyrips/m-babyrips', 'BabyRipsMainMission()')",
            "main_mutator": scenario_babyrips,
            "position": (-0.15, -0.65), "requires": ["m-computer"]
        },
        "m-rips": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-rips/m-rips', 'RipsMainMission()')",
            "main_mutator": scenario_rips,
            "position": (0.08, -0.58), "requires": ["m-babyrips"]
        },
        "m-hole": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-hole/m-hole', 'HoleMainMission()')",
            "main_mutator": scenario_hole,
            "position": (0.12, -0.32), "requires": ["m-rips"]
        },
        "m-five": {
            "menu_flow": "StdMissionMenuFlow('modes/campaign-diaspora/m-five/m-five', 'FiveMainMission()')",
            "main_mutator": scenario_five,
            "position": (0.4, -0.42), "requires": ["m-rips"]
        },

        "m-act-3": {
            "info_node": act3_intro,
            "position": (0.6, -0.2), "requires": ["m-five", "m-hole"]
        },
        "m-aphorian": {
            "menu_flow": "OneRaceMissionMenuFlow('modes/campaign-diaspora/m-aphorian/m-aphorian', 'AphorianMainMission()')",
            "main_mutator": scenario_race("aphorian"),
            "position": (0.48, -0.67),
            "requires": ["m-five", "m-hole"], "connects_to": ["m-act-3"]
        },
        "m-silthid": {
            "menu_flow": "OneRaceMissionMenuFlow('modes/campaign-diaspora/m-silthid/m-silthid', 'SilthidMainMission()')",
            "main_mutator": scenario_race("silthid"),
            "position": (0.65, 0.18),
            "requires": ["m-five", "m-hole"], "connects_to": ["m-act-3"]
        },        
        "m-baqar": {
            "menu_flow": "OneRaceMissionMenuFlow('modes/campaign-diaspora/m-baqar/m-baqar', 'BaqarMainMission()')",
            "main_mutator": scenario_race("baqar"),
            "position": (0.36, -0.05),
            "requires": ["m-five", "m-hole"], "connects_to": ["m-act-3"]
        },
        "m-dendr": {
            "menu_flow": "OneRaceMissionMenuFlow('modes/campaign-diaspora/m-dendr/m-dendr', 'DendrMainMission()')",
            "main_mutator": scenario_race("dendr"),
            "position": (0.93, 0.0),
            "requires": ["m-five", "m-hole"], "connects_to": ["m-act-3"]
        },
        "m-vattori": {
            "menu_flow": "OneRaceMissionMenuFlow('modes/campaign-diaspora/m-vattori/m-vattori', 'VattoriMainMission()')",
            "main_mutator": scenario_race("vattori"),
            "position": (0.75, -0.45),
            "requires": ["m-five", "m-hole"], "connects_to": ["m-act-3"]
        },
    }
