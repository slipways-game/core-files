#########################################################
# Main mission class

class RefineMainMission(MainMission):
    LIMITS = {"forgiving": 75, "reasonable": 100, "challenging": 120, "tough": 140}
    SCORING_TWEAKS = {"forgiving": -3, "reasonable": -2, "challenging": -1, "tough": 0}
    def __init__(self):
        limit = self.LIMITS[game.GameConfig.Difficulty.ID]
        MainMission.__init__(self, "refine_izzium", [RMMRefineIzzium(limit), RMMInventIzzium()])

    @staticmethod
    def get():
        return game.Conditions.Get("RefineMainMission()").PythonObject

    def fake_advance(self):
        update = ConsUpdateNodeData()
        update.inc(game, "izzium_planets_colonized")
        update.when_done_or_reverted(lambda: self.signal_change())
        commands.IssueScriptedConsequence(update)

    def scenario_id(self): return "m-refine"
    def scoring_rules(self):
        tweak = self.SCORING_TWEAKS[game.GameConfig.Difficulty.ID]
        prod_thresholds = [0, 6, 10, 13, 17, 21]
        prod_thresholds = [max(0, t + tweak) for t in prod_thresholds]
        return [
            ScoringRefineProduction(prod_thresholds),
            ScoringCampaignTime(self, [100, 24, 23, 22, 20, 18])
        ]
    def conditions(self): return [
        (IzziumCounter,),
        (IzziumMusic,),
        (WinMissionOnTime, "RefineMainMission()", 25),
        (SlipspaceOverload,),
        (MineUpgradeBonus,)
    ]
    
    def forced_techs(self): return [
        ("baqar", "izzium_energy"),
        ("aphorian", "izzium_income"),
        ("vattori", "izzium_study"),
        ("silthid", "izzium_refinement"),
        ("dendr", "izzium_people")
    ]

    def perks_available(self):
        return ["well_prepared", "reciprocity", "miners", "prospectors", "prosperity", "nutrition", "efficient", "joint_factories", "scholars", "curiosity"]

    def things_to_explain(self):
        return [
            ("resource", "Izz"),
            ("cond", "MineUpgradeBonus()")
        ]
    
    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

class RMMRefineIzzium:
    def __init__(self, required_count):
        self._required = required_count
    def current(self):
        return self.state()[0]
    def state(self): 
        cond = game.Conditions.Get("IzziumCounter()")
        if cond is None: return (0, 0)
        cond = cond.PythonObject
        if cond is None: return (0, 0)
        state = (cond.current(), cond._production)
        return state
    def check_completion(self):
        return self.current() >= self._required
    def description(self): return LS("mission.ri.goal.refine", None, self._required)
    def short(self):
        current = self.current()
        return "%d/%d:Izz:" % (current, self._required)

class RMMInventIzzium:
    def check_completion(self):
        return any("izzium_" in t.Kind.ID for t in game.Technology.AllInvented)
    def description(self): return LS("mission.ri.goal.invent", None)

#########################################################
# Izzium quirk

class RefineMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # sprinkle the izzium planets
        planet_types = ["planet.%s" % p for p in ["earthlike", "swamp", "arid", "arctic", "ocean", "jungle", "barren", "ice", "lava"]]
        sprinkler = refinement_sprinkle_quirk(QuirkIzziumDeposits.EXPR, planet_types, 
            zone_density = lambda index: 0.13 if index == 0 else 0.2)
        map_generation.Refinement("after_planet_types", 700, sprinkler)

class RefinePlanetComposition(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.factory", 12, 10, ["planet.barren", "planet.ice", "planet.lava", "planet.remnant"]),
            ("planet.mining", 12, 10, ["planet.barren", "planet.ice", "planet.lava", "planet.remnant"])
        ])

class QuirkIzziumDeposits:
    EXPR = "QuirkIzziumDeposits()"

    def name(self): return LS("quirk.izzium_deposits", "Izzium Deposits")
    def desc(self): return LS("quirk.izzium_deposits.desc", "Izzium(:Izz:) can be mined on this planet.")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): return 10 if node.Level < 0 else 0
    def icon(self, node): return {"type": "positive", "text": ":res_izz:"}
    def hidden(self, node): return True

    def effects(self, node):
        effects = [ColonizationOptions.Add("izzium_mining")]
        if node.ActuallyProduces(Resource.All["Izz"]):
            effects.append(BlockFlows.OfCategory(FlowCategory.NoExport))
        return effects

class MineUpgradeBonus(GlobalCondition):
    BONUS = 10

    def activate(self):
        self.react_to(Trigger.NodeUpgraded, self.when_upgraded)

    def info(self):
        ci = CondInfo()
        ci.FullDescription = LS("cond.izzium_bonus.desc", None, self.BONUS)
        return ci
    
    def when_upgraded(self, data):
        planet = data["node"]
        if planet.IsProducerOf(Resource.All["Izz"]):
            ConsGrantResources(self.BONUS, Resource.Cash, planet).issue()

#########################################################
# Izzium production counter

class IzziumCounter(GlobalCondition):
    def activate(self):
        self.data.count = self.data.get_or('count', 0)
        self.react_to(Trigger.NewTurn, self._count_up)
        self.react_to(Trigger.ActionTaken, self._refresh)
        self.react_to(Trigger.ActionReverted, self._refresh)
        self._refresh()
    
    def current(self):
        return self.data.count

    def info(self):
        info = CondInfo()
        info.Icon = "icon_izzium"
        info.ShortText = "%d:Izz:" % self._production
        info.MediumText = LS("cond.izzium_production.header", "Izzium production: {1}:Izz:/y", self._production)
        info.Tooltip = "[s:TooltipHeader]%s[/s]" % (info.MediumText)
        info.Priority = 50
        return info

    def _refresh(self, data = None):
        self._production = game.Nodes.TotalProduction(Resource.All["Izz"])
        self.signal_change()

    def _count_up(self, data):       
        ConsUpdateNodeData().inc(self.host(), "count", self._production).issue()

########################################################
# Music

class IzziumMusic(MusicProgression):
    def _check_for_transition(self, previous_lv):
        count = game.Conditions.Get("IzziumCounter()").CustomData.GetOr("count", 0)
        if count >= 100: return 2
        if count >= 50: return 1
        return None

    def mission_based_music_transition(self, goal_index, goal):
        if RefineMainMission.get().finished(): return 3
        return music.Level

#########################################################
# Izzium delivery

def izzium_routes(product, consumer, path):
    existing_needs = [n for n in consumer.Needs if (n.AskingFor is not None and n.AskingFor.ID == "Izz")]
    if len(existing_needs) > 0:
        return [PossibleRoute.ForNeed(product, existing_needs[0], path)]
    # check for things that enable sending izzium
    works = False
    izzium_study = game.Technology.IsInvented("izzium_study")
    izzium_income = game.Technology.IsInvented("izzium_income")
    if izzium_study and consumer.ActuallyProduces(Resource.People):
        works = True
    if izzium_income and consumer.NodeType.startswith("planet."):
        works = True
    if works:
        return [PossibleRoute.InducingNeed(product, consumer, path)]
    return []

#########################################################
# Izzium technologies

class IzziumStudy:
    def __init__(self, bonus):
        self._bonus = bonus

    def name(self): return LS("quality.izzium_study", "Izzium Study")
    def desc(self): return LS("quality.izzium_study.desc", "Delivering :Izz: to a :P:-producing planet makes an additional [[delta:+{1}S]] there.", self._bonus)
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.Receives(Resource.All["Izz"]) and node.ActuallyProduces(Resource.People)

    def effects(self, node):
        return [ChangeProducts.Add(2, Resource.Science, "izzium_study")]

class IzziumIncome:
    def __init__(self, bonus):
        self._bonus = bonus

    def name(self): return LS("quality.izzium_income", "Short-Range Teleports")
    def desc(self): return LS("quality.izzium_income.desc", "Delivering :Izz: to a planet increases its trade income by *{1}%*.", self._bonus)
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.Receives(Resource.All["Izz"])

    def effects(self, node):
        return [PercentageBonus.TradeIncome(self._bonus)]

class IzziumRefinement:
    RESOURCES = ["B", "W", "P"]
    def name(self): return LS("quality.izzium_refinement", "Izzium Refinement")
    def desc(self): return LS("quality.izzium_refinement.desc", "Once their basic needs are met, izzium-producing planets make one extra unit of :Izz: for each additional :B: or :W: they receive.")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.ActuallyProduces(Resource.All["Izz"])

    def effect_size(self, node):
        if node.HasUnmetNeeds: return 0
        total = -2
        for n in node.Needs:
            if n.MetWith and n.MetWith.ID in self.RESOURCES:
                total += n.ImportCount
        return total

    def effects(self, node):
        count = self.effect_size(node)
        if count > 0:
            return [ChangeProducts.Add(count, Resource.All["Izz"], "izzium_refinement")]

class IzziumCracking:
    def name(self): return LS("quality.izzium_energy", "Subatomic Cracking")
    def desc(self): return LS("quality.izzium_energy.desc", "Izzium-producing planets make one unit of :E: for every two units of :Izz: they produce.")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.ActuallyProduces(Resource.All["Izz"])

    def effect_size(self, node):
        produced = sum(1 for p in node.Products if p.Resource.ID == "Izz" and p.IsReal)
        return math.floor(produced / 2)

    def effects(self, node):
        count = self.effect_size(node)
        if count > 0:
            return [ChangeProducts.Add(count, Resource.All["E"], "izzium_cracking")]

#########################################################
# Scoring

class ScoringRefineProduction(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.refine.output"
    def base_number(self):
        return game.Nodes.TotalProduction(Resource.All["Izz"])
    def rank_limits(self): return self._limits
    def post_rank_text(self): return ":Izz:"
    def number_text(self, number, rank): return "%d:Izz:" % number
    def tags(self): return ["mission"]
