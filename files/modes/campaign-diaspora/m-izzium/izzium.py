#########################################################
# Main mission class

class IzziumMainMission(MainMission):
    REQS = {"forgiving": 9, "reasonable": 11, "challenging": 11, "tough": 11}
    TWEAKS = {"forgiving": -2, "reasonable": 0, "challenging": 0, "tough": 0}

    def __init__(self):
        req = self.REQS[game.GameConfig.Difficulty.ID]
        MainMission.__init__(self, "izzium_danger", [IMMColonizeIzziumPlanets(req)])

    @staticmethod
    def get():
        return game.Conditions.Get("IzziumMainMission()").PythonObject

    def activate(self):
        self.react_to(Trigger.PlanetColonized, self.when_planet_colonized)
        MainMission.activate(self)

    def when_planet_colonized(self, data):
        node = data["node"]
        if node.CustomData.GetOr("izzium", False):
            commands.IssueScriptedConsequence(ConsGrantResources(QuirkUnstableIzzium.COLONIZE_BONUS, Resource.Science, node))
            update = ConsUpdateNodeData()
            update.inc(game, "izzium_planets_colonized")
            update.when_done_or_reverted(lambda: self.signal_change())
            commands.IssueScriptedConsequence(update)

    def fake_advance(self):
        update = ConsUpdateNodeData()
        update.inc(game, "izzium_planets_colonized")
        update.when_done_or_reverted(lambda: self.signal_change())
        commands.IssueScriptedConsequence(update)

    def scenario_id(self): return "m-izzium"
    def scoring_rules(self):
        tweak = self.TWEAKS[game.GameConfig.Difficulty.ID]
        izzium_reqs = [0, 9, 11, 13, 15, 17]
        izzium_reqs = [max(0, r + tweak) for r in izzium_reqs]
        return [
            ScoringIzziumPlanets(izzium_reqs),
            ScoringCampaignTime(self, [100, 24, 22, 20, 18, 16])
        ]

    def conditions(self): return [
        (WinMissionOnTime, "IzziumMainMission()", 25)
    ]

    def perks_available(self):
        return ["novelty_traders", "reciprocity", "miners", "explorers", "social_capital", "growth", "experimental_tech", "joint_factories", "researchers", "curiosity"]

    def things_to_explain(self):
        return [("quality", "QuirkUnstableIzzium()"), ("structure", "stabilizer")]
    
    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("mission.id.failed"),
                "shown_elements": ["undo"]
            }

class IMMColonizeIzziumPlanets:
    def __init__(self, required_count):
        self._required = required_count
    def check_completion(self):
        return game.CustomData.GetOr("izzium_planets_colonized", 0) >= self._required
    def description(self): return LS("mission.id.stage.colonize_planets", None, self._required)
    def short(self):
        current = game.CustomData.GetOr("izzium_planets_colonized", 0)
        return "%d/%d" % (current, self._required)

#########################################################
# Map generation

class IzziumMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)
        # hotfix hack - include ScienceBonus even if it wasn't part of the save
        st_cond = game.Conditions.Get("SectorTypeIzziumScienceBonus()")
        mode = game.GameConfig.GameMode
        if mode != "campaign" and st_cond is None:
            game.Conditions.Activate("SectorTypeIzziumScienceBonus()")

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # sprinkle the izzium planets
        planet_types = ["planet.%s" % p for p in ["remnant", "mining", "earthlike", "swamp", "arid", "arctic", "ocean", "jungle"]]
        sprinkler = refinement_sprinkle_quirk(QuirkUnstableIzzium.EXPR, planet_types, 
            zone_density = lambda index: 0.16 if index == 0 else 0.27,
            maximize_distances = True)
        map_generation.Refinement("after_planet_types", 600, sprinkler)

class IzziumSetup(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_setup)

    def on_setup(self, data):
        # add cash
        default_cash = constants.Int("starting.cash")
        bonus = math.floor(default_cash * 0.25)
        game.Stock.Receive(Resource.Cash, bonus)

#########################################################
# Scoring

class ScoringIzziumPlanets(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "mission.id.scoring.izzium_planets"
    def base_number(self):
        return sum(1 for p in every(Planet) if p.Level >= 1 and p.CustomData.Has("izzium"))
    def rank_limits(self): return self._limits
    def post_rank_text(self): return ":planet:"
    def number_text(self, number, rank): return "%d:planet:" % number
    def tags(self): return ["mission"]

##########################################################
# Planet quirk

class QuirkUnstableIzzium:
    """The quirk that institutes new rules on izzium-infested planets."""
    EXPR = "QuirkUnstableIzzium()"
    COLONIZE_BONUS = 3

    def name(self): return LS("quirk.unstable_izzium")
    def desc(self): return LS("quirk.unstable_izzium.desc", None, self.COLONIZE_BONUS)
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): return 10
    def icon(self, node): return {"type": "negative", "text": ":res_izz:"}
    def hidden(self, node): return True

    def effects(self, node):
        return [
            ActionPermission.Calling(self.uninhabitable),
            ConnectivityRule.Calling(self.connectivity)
        ]

    def uninhabitable(self, node_action):
        if node_action.IsColonization:
            return Permission.No(LS("quirk.unstable_izzium.no_permission"))
        return Permission.Yes()
    
    def connectivity(self, node, other):
        if other is not None and (other.NodeType == "structure.stabilizer" or other.NodeType == "check"):
            return NodeConnectivity.Accepts()
        return NodeConnectivity.Rejects(LS("quirk.unstable_izzium.needs_stabilization"))        

class SectorTypeIzziumScienceBonus(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.PlanetColonized, self.when_planet_colonized)        

    def when_planet_colonized(self, data):
        node = data["node"]
        if node.CustomData.GetOr("izzium", False):
            commands.IssueScriptedConsequence(ConsGrantResources(QuirkUnstableIzzium.COLONIZE_BONUS, Resource.Science, node))

##########################################################
# Story and music

class IzziumMusic(MusicProgression):
    THRESHOLDS = [4, 7]
    def _check_for_transition(self, prev):
        if prev >= len(self.THRESHOLDS): return None
        colonized = game.CustomData.GetOr("izzium_planets_colonized", 0)
        return prev + 1 if colonized >= self.THRESHOLDS[prev] else None

    def mission_based_music_transition(self, goal_index, goal):
        return 3

class IzziumStory(StoryBits):
    def __init__(self):
        StoryBits.__init__(self, [
            IzziumStoryPopup(1, 1, "silthid"),
            IzziumStoryPopup(4, 2, "vattori"),
            IzziumStoryPopup(7, 3, "baqar"),
            IzziumStoryPopup(10, 4, "dendr")
        ])

class IzziumStoryPopup(PopupTutorial):
    def __init__(self, threshold, text_index, *characters):
        self._threshold, self._text_index, self._characters = threshold, text_index, characters
        PopupTutorial.__init__(self, args=[threshold, text_index] + list(characters))
    def condition(self):
        colonized = game.CustomData.GetOr("izzium_planets_colonized", 0)
        return colonized >= self._threshold
    def steps(self):
        return [
            StoryBit("mission.id.tidbit.%d" % self._text_index, self._characters)
        ]

##########################################################
# Stabilizer structure

def stabilizer_check_for_planets(stabilizer):
    # has to be active first
    if stabilizer.Level < 1: return
    reachable = game.Reachability.ReachableNodes(stabilizer)
    for r in reachable:
        if stabilizer_affects(r):
            stabilizer_fix_planet(r)            

def stabilizer_wants(need, offered_resource):
    if need.IsMet: return False # one copy please
    return None # otherwise defer to normal logic

def stabilizer_affects(node):
    return any(q for q in node.GetQualities() if q.ScriptExpression == QuirkUnstableIzzium.EXPR)

def stabilizer_fix_planet(node):
    commands.Issue(RemoveQuality(world, node, QuirkUnstableIzzium.EXPR))
    ConsUpdateNodeData().add(node, "izzium", True).issue()
