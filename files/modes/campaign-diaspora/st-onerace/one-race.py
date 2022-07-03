#########################################################
# Main mission class

class OneRaceSectorType(GlobalCondition):
    def borrowed_techs(self):
        borrowed = {}
        used = []
        rng = game.RNG("borrowed")
        races = Randomness.Shuffle(rng, Race.AllPlayable)
        for race in races:
            added = self.generate_borrowed_techs(race, used)
            borrowed[race.ID] = [tk.ID for tk in added]
            used += added
        return borrowed

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

    def generate_borrowed_techs(self, race, used):
        patterns = ["012", "023", "024", "123", "124", "134", "234"]
        rng = game.RNG("borrowed", race.ID)
        pattern = Randomness.Pick(rng, patterns)
        tp = TechParameters()
        tp.Race = race
        race_techs = list(game.Technology.Randomization.RandomTechs(tp, pattern, used, rng))
        return race_techs

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
