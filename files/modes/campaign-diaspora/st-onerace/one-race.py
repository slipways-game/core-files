#########################################################
# Main mission class

class OneRaceSectorType(GlobalCondition):
    def borrowed_techs(self):
        return {
            "baqar": ["geothermals", "mass_reactors", "gravitic_tugs"],
            "silthid": ["mass_lensing", "extreme_mini", ("nanofabrication", "flexible_fabrication")],
            "aphorian": ["brain_machine_interface", ("geoharvesting", "economic_zones"), "hyperdrive"],
            "vattori": ["orbital_labs", "quantum_computing", "matter_transposition"],
            "dendr": ["culture_hubs", "xenofoods", ("enlightenment", "genesis_cells")]
        }

    def select_screen(self):
        return {
            "races_to_pick": 1,
            "perks_per_race": 100,
            "block_width": 600,
            "forward_button_text": LS("menus.continue")
        }

    def menu_flow_setup(self): return True

    def altered_menu_flow(self):
        return ("modes/campaign-diaspora/st-onerace/st-onerace", "OneRaceSTMenuFlow()")

    def potential_techs(self):        
        patterns = {r.ID: "all" for r in Race.AllPlayable}
        return {"pattern_for_race": patterns}

    def perks_available(self):
        perks = []
        for r in Race.AllPlayable:
            perks += (p.ID for p in r.Perks)
        return perks


class OneRaceSTMenuFlow:
    def pages(self):
        return [
            PagePickPotentialTechs('012344'),
            PagePickPotentialPerks(2),
            PageSelectRacesAndPerks(),
            PageBorrowTechs(2),
            PageUnlockPotentialTechs(),
            PageTechsForceUnlock('slipstream_relay'),
            PageStartScenario()
        ]
