###############################################
# Base class for the final five race missions

class OneRaceMainMission(MainMission):
    def __init__(self, race_id, goals):
        MainMission.__init__(self, race_id, goals)
        self._race_id = race_id

    @classmethod
    def get(cls):
        return game.Conditions.Get(cls.__name__ + "()").PythonObject

    def scenario_id(self): return "m-%s" % self._race_id
    def scenario_group(self): return "g-onerace"

    def select_screen(self):
        return {
            "races_to_pick": 1,
            "perks_to_pick": 2,
            "perks_per_race": 2,
            "preselect_races": [self._race_id],
            "lock_races": True,
            "block_width": 600,
            "forward_button_text": LS("menus.continue")
        }

    def potential_techs(self):        
        patterns = {r.ID: "all" for r in Race.AllPlayable}
        return {"pattern_for_race": patterns}

    def perks_available(self):
        perks = []
        for r in Race.AllPlayable:
            perks += (p.ID for p in r.Perks)
        return perks

###############################################
# Different logic for quests

class OneRaceQuestHooks:
    def generate_quest_offers(self, rng_seed):
        # generate the quests
        quests = []
        rng = game.RNG("quest_offers", rng_seed)
        for m in empire.Council.Members:
            for qk in QuestKind.AllForRace(m.Race):
                quest_id = qk.ID
                if game.CustomData.Has("quest_started_%s" % quest_id):
                    continue # quest already used
                offer = QuestOffer(m.Race.ID, qk.ID, rng)
                if not offer.valid:
                    #raise Exception("Quest offers for one race missions always have to be valid.")
                    pass
                else:
                    quests.append(offer)
        return quests

    def quest_started(self, quest):
        updates = ConsUpdateNodeData()
        updates.add(game, "quest_started_%s" % quest.quest_id(), True)
        updates.issue()

    def should_offer_quests(self):
        for m in empire.Council.Members:
            if m.SatisfactionLevel >= 4: return False
        return True


###############################################################
# Adding rips

class OneRaceRipsMapgen(GlobalCondition):
    def __init__(self, count, how_far):
        self._count = count
        self._how_far = how_far

    """Makes sure that the rip manager is present and that the effects of the rip on the map are felt."""
    def activate(self):
        self.react_to(Trigger.GameWorldSetup, self.create_rip_model)
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def create_rip_model(self, data):
        RipManager.CreateIfNeeded(world)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # add rips during mapgen
        count = self._count
        map_generation.Refinement("after_planet_types", 1000, refinement_place_rips(count, 1, 3.6, settings = {
            "min_distance": self._how_far, "max_distance": 24
        }))
        map_generation.Refinement("after_planet_types", 1010, refinement_instantiate_rips)
        # rip effects from shared code
        map_generation.Refinement("after_planet_types", 1050, refinement_add_rip_effects(rip_refinement_settings()))

def rip_refinement_settings():
    return {
        "apply_quirk": None   # no rip-based quirk in this scenario
    }

def generate_rips(rip_manager):
    generate_rips_from_stored_points(rip_manager) # use the functionality from shared
