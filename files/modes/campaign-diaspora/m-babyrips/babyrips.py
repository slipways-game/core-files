#########################################################
# Main mission structure

class BabyRipsMainMission(MainMission):
    def __init__(self):
        MainMission.__init__(self, "babyrips", [RMMResearchRips(self.required_data())])

    @staticmethod
    def get():
        return game.Conditions.Get("BabyRipsMainMission()").PythonObject

    def scenario_id(self): return "m-babyrips"
    def scoring_rules(self):
        diff = difficulty_ordinal()
        diff = clamp(0, 3, diff)
        base_data = [-100, 5, 7, 9, 11, 13]
        base_years = [100, 20, 17, 14, 12, 10]
        data_thresholds = [t + diff for t in base_data]
        year_limits = [t - diff for t in base_years]
        return [
            ScoringGatheringData(data_thresholds),
            ScoringTimeliness(year_limits)
        ]

    def conditions(self): return [
        (WinMissionOnTime, "BabyRipsMainMission()", 25),
        (BabyRipsMusic, self.required_data()),
        (GatheredDataWatcher,),
        (DataCounter, self.required_data()),
    ]

    def things_to_explain(self):
        return [("custom", "mission.rip.rift.explanation"), ("structure", "rift_outpost")]
    def perks_available(self):
        return ["novelty_traders", "luxury", "geology", "explorers", "prosperity", "nutrition", "experimental_tech", "efficient", "careful_observation", "researchers"]
    
    def do_additional_setup(self):
        pass

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

    def required_data(self):
        targets = [60, 70, 85, 100]
        diff = difficulty_ordinal()
        diff = clamp(0, 3, diff)
        return targets[diff]

class RMMResearchRips:
    def __init__(self, required):
        self._required = required
    def check_completion(self):
        if game.GameContext != GameContext.PlayingScenario: return False
        return self.collected() >= self._required
    def state(self):
        return (self.collected(),)
    def collected(self): return game.Stock.Reserve(Resource.All["Data"])
    def description(self): return LS("mission.brip.stage.research_rips", None, self._required)
    def short(self): return "%d/%d:Data:" % (self.collected(), self._required)

#########################################################
# Story, music and info

class BabyRipsMusic(MusicProgression):
    def __init__(self, data_required):
        self._required = data_required
        self._half = int(self._required / 2)

    def _check_for_transition(self, prev):
        active_outposts = sum(1 for o in game.Nodes.WithType("structure.rift_outpost") if o.Level >= 1)
        total_produced = game.Stock.Reserve(Resource.All["Data"])
        lv = 0
        if active_outposts >= 1: lv += 1
        if active_outposts >= 3: lv += 1
        if total_produced >= self._required: lv += 1
        if prev < lv: return lv

class DataCounter(GlobalCondition):
    def __init__(self, required):
        self._required = required
        self._prev_state = None

    def activate(self):
        self.react_to(Trigger.ActionTaken, self._refresh)
        self.react_to(Trigger.ActionReverted, self._refresh)
        self._refresh()
    
    def state(self):
        production = game.Nodes.TotalProduction(Resource.All["Data"])
        total = game.Stock.Reserve(Resource.All["Data"])
        return (production, total)

    def info(self):
        production, total = self.state()
        if production == 0: return None
        info = CondInfo()
        info.Icon = "icon_data"
        info.ShortText = "+%d:Data:" % production
        info.MediumText = LS("cond.data_collection.header", None, production)
        time_info = ""
        if total < self._required and production > 0:
            missing = self._required - total
            time_to_goal = math.ceil(missing / float(production))
            time_info = "\n" + styled(L("cond.data_collection.info", None, time_to_goal), "TooltipLight")
        info.Tooltip = "[s:TooltipHeader]%s[/s]%s" % (info.MediumText, time_info)
        info.Priority = 50
        return info

    def _refresh(self, data = None):
        state = self.state()
        if state != self._prev_state:
            self._prev_state = state
            self.signal_change()

class BabyRipsStory(StoryBits):
    def __init__(self):
        StoryBits.__init__(self, [
            BabyRipsStoryPopup(1, 1, "dendr", "vattori", "silthid"),
            BabyRipsStoryPopup(2, 2, "silthid", "aphorian", "vattori"),
            BabyRipsStoryPopup(3, 3, "baqar", "silthid", "aphorian"),
            BabyRipsStoryPopup(4, 4, "vattori", "dendr", "silthid"),
        ])

class BabyRipsStoryPopup(PopupTutorial):
    def __init__(self, threshold, text_index, *characters):
        self._threshold, self._text_index, self._characters = threshold, text_index, characters
        PopupTutorial.__init__(self, args=[threshold, text_index] + list(characters))
    def condition(self):
        working_outposts = sum(1 for n in game.Nodes.WithType("structure.rift_outpost") if n.Level >= 1)
        return working_outposts >= self._threshold
    def steps(self):
        return [
            StoryBit("mission.babyrips.tidbit.%d" % self._text_index, self._characters)
        ]

#########################################################
# Scoring

class ScoringTimeliness(ScoringFiveRanks):
    THRESHOLD = 5
    def __init__(self, limits):
        self._limits = limits

    def tags(self): return ["mission"]
    def id(self): return "scoring.babyrips.readiness"
    def desc_args(self): return (self.THRESHOLD,)
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return None
        return game.CustomData.GetOr("readiness_year", None)
    def rank_op(self): return "<="
    def rank_limits(self): return self._limits
    def rank_text(self, number): return str(game.Time.NormalizedTurnToYear(number))
    def number_text(self, number, rank): return str(game.Time.NormalizedTurnToYear(number)) if number is not None else "-"

class ScoringGatheringData(ScoringFiveRanks):
    def __init__(self, thresholds):
        self._thresholds = thresholds

    def tags(self): return ["mission"]
    def id(self): return "scoring.babyrips.gathering_data"
    def rank_limits(self): return self._thresholds
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return sum(n.CustomData.GetOr("data_flow", 0) for n in game.Nodes.WithType("structure.rift_outpost"))
    def number_text(self, number, rank):
        return "%s:Data:" % number

class GatheredDataWatcher(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ActionTaken, self.after_action)

    def after_action(self, data):
        if game.CustomData.Has("readiness_year"): return
        collection = sum(n.CustomData.GetOr("data_flow", 0) for n in game.Nodes.WithType("structure.rift_outpost"))
        if collection >= ScoringTimeliness.THRESHOLD:
            ConsUpdateNodeData().add(game, "readiness_year", game.Time.NormalizedTurn).issue()

#########################################################
# Generating rips

class BabyRipsMissionMapgen(GlobalCondition):
    """Makes sure that the rip manager is present and that the effects of the rip on the map are felt."""
    def activate(self):
        self.react_to(Trigger.GameWorldSetup, self.create_rip_model)
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def create_rip_model(self, data):
        RipManager.CreateIfNeeded(world)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # add rips during mapgen
        diff = difficulty_ordinal()
        count = [45, 52, 60, 60][diff]
        closest_rips = [(4.25,5), (4.25,5), (3.5, 4.25, 5), (3.5, 4.25, 5)][diff]
        map_generation.Refinement("after_planet_types", 1000, refinement_place_rips(count, 1, 3.6, closest_rips))
        map_generation.Refinement("after_planet_types", 1010, refinement_instantiate_rips)
        # rip effects from shared code
        map_generation.Refinement("after_planet_types", 1050, refinement_add_rip_effects(rip_refinement_settings()))

def rip_refinement_settings():
    return {
        "apply_quirk": None   # no rip-based quirk in this scenario
    }

def generate_rips(rip_manager):
    generate_rips_from_stored_points(rip_manager) # use the functionality from shared

class BabyRipsMapgenSettings:
    def create_zones(self):
        # increase link values slightly since the rips hinder the player a lot
        settings = MapgenDefaults().create_zones()
        settings["link_values"] = [lv * 1.1 for lv in settings["link_values"]]
        return settings

#########################################################
# Rift outposts

### Placing them in the first place

def rifto_placement():
    return [ScriptedPlacement(RipEdgePlacementRules), ScriptedPlacement(OneRiftOutpostPerRip)]

class OneRiftOutpostPerRip:
    @staticmethod
    def adjust_position(pos, ps): return pos

    @staticmethod
    def is_permitted(pos, ps):
        rip = rips.ClosestRip(pos)
        if rip:
            rip_name = rip.Name
            taken = any(n.CustomData.GetOr("rip", None) == rip_name for n in game.Nodes.WithType("structure.rift_outpost"))
            if taken:
                return Permission.No(LS("structure.rift_outpost.only_one_per"))
        return Permission.Yes()

def rifto_placed(node):
    rip = rips.ClosestRip(node.Position)
    if not rip:
        raise Exception("Couldn't find a rip for the rift outpost.")
    node.CustomData.Set("rip", rip.Name)

def rifto_obstructed_by(planned, model):
    return not rips.IsRip(model)

### Operation

RIFTO_THRESHOLD = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55]
def rifto_production(science_received):
    for i in range(len(RIFTO_THRESHOLD)):
        if RIFTO_THRESHOLD[i] > science_received:
            return i
    return 10

def rifto_upgrade(node, industry, level):
    if level > 2: return Permission.NoWithNoReason()
    perm = Permission.Yes()
    # are our needs met?
    if node.HasUnmetNeeds:
        perm = perm.Disallow(LS("structure.rift_outpost.unmanned"))
    # are we getting science?
    reachable = game.Reachability.ReachableNodes(node)
    connected_science = sum(n.AmountProduced(Resource.Science) for n in reachable)
    if connected_science == 0:
        perm = perm.Disallow(LS("structure.rift_outpost.no_science"))
    elif connected_science < RIFTO_THRESHOLD[-1] and level > 1:
        prod = rifto_production(connected_science)
        lacking = RIFTO_THRESHOLD[prod] - connected_science
        perm = perm.Disallow(LS("structure.rift_outpost.science_for_increase", None, lacking, RIFTO_THRESHOLD[prod]))
    # done checks
    return perm

def rifto_node_tag(node, blocks):
    if node.Level < 1: return blocks.DefaultText()
    production = node.CustomData.GetOr("data_flow", 0)
    if production == 0: return blocks.DefaultText()
    text = blocks.NeedsText() + blocks.Arrow() + blocks.CountedResource(production, Resource.All["Data"])
    return text

class RiftOutpostProducts:
    """A quality defining how much data flows from the outpost."""
    def hidden(self, node): return True
    def effects(self, node):
        if node.Level < 1: 
            node.CustomData.Set("data_flow", 0)
            return
        reachable = game.Reachability.ReachableNodes(node)
        connected_science = sum(n.AmountProduced(Resource.Science) for n in reachable)
        production = rifto_production(connected_science)
        node.CustomData.Set("data_flow", production)
        if production > 1:
            return [
                # minus one because one Data unit is built into the industry
                ChangeProducts.Add(production - 1, Resource.All["Data"])                
            ]

class RiftOutpostFlow:
    def name(self): return LS("quality.rift_outpost_flow")
    def desc(self): return LS("quality.rift_outpost_flow.desc")
    def effects(self, node):
        data_flow = node.AmountAvailable(Resource.All["Data"])
        if data_flow != 0: return [ResourceFlow.Flow(Resource.All["Data"], data_flow, FlowCategory.Other)]
        return []
