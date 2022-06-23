#########################################################
# Main mission class

class DarkMainMission(MainMission):
    REQ_LABS = {"forgiving": 3, "reasonable": 4, "challenging": 4, "tough": 4}
    REQ_SCIENCE = {"forgiving": 15, "reasonable": 20, "challenging": 24, "tough": 24}
    TWEAK_SCIENCE = {"forgiving": 0.6, "reasonable": 0.83, "challenging": 1, "tough": 1}
    TWEAK_BEST_LAB = {"forgiving": -2, "reasonable": -1, "challenging": 0, "tough": 0}

    def __init__(self):
        req_labs = self.REQ_LABS[game.GameConfig.Difficulty.ID]
        req_science = self.REQ_SCIENCE[game.GameConfig.Difficulty.ID]
        MainMission.__init__(self, "dark", [DMMActivateLabs(req_labs, 8), DMMTotalScience(req_science)])

    @staticmethod
    def get():
        return game.Conditions.Get("DarkMainMission()").PythonObject

    def scenario_id(self): return "m-dark"
    def scoring_rules(self): 
        diff = game.GameConfig.Difficulty.ID
        s_tweak, b_tweak = self.TWEAK_SCIENCE[diff], self.TWEAK_BEST_LAB[diff]
        science_thresholds = [int(round(t * s_tweak)) for t in [0, 12, 24, 30, 35, 40]]
        best_thresholds = [max(0, t + b_tweak) for t in [0, 3, 5, 7, 9, 11]]
        return [
            ScoringDarkScience(science_thresholds),
            ScoringDarkBestLab(best_thresholds),
        ]
    def conditions(self): return [
        (PointAnomaliesOut,),
        (DarkProgression,),
        (DarkStory,),
        (WinMissionOnTime, "DarkMainMission()", 27),
    ]

    def do_additional_setup(self):
        game.Camera.ZoomTo(16) # zoom out to maximum scale

    def perks_available(self):
        return ["luxury", "well_prepared", "geology", "explorers", "social_capital", "nutrition", "experimental_tech", "efficient", "researchers", "careful_observation"]

    def things_to_explain(self):
        return [
            ("cond", "InterferenceRule()"),
            ("action", "setup_sensor"),
            ("cond", "NoLabsRule()"),
            ("structure", "anomaly_lab")
        ]
    
    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

class DMMActivateLabs:
    def __init__(self, count, out_of):
        self._required = count
        self._out_of = out_of
    def active_labs(self):
        return game.CustomData.GetOr("labs_active", 0)
    def state(self): 
        return self.active_labs()
    def short(self):
        return "%d/%d" % (self.state(), self._required)
    def check_completion(self):
        return self.active_labs() >= self._required
    def description(self): return LS("mission.dark.goal.activate", None, self._required, self._out_of)

class DMMTotalScience:
    def __init__(self, requirement):
        self._required = requirement
    def total_science(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return game.Stock.Income(Resource.Science)
    def state(self): 
        return self.total_science()
    def short(self):
        return "%d/%d:S:" % (self.state(), self._required)
    def check_completion(self):
        return self.total_science() >= self._required
    def description(self): return LS("mission.dark.goal.science", None, self._required)

#########################################################
# Progression

class DarkSetup(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_setup)

    def on_setup(self, data):
        # add cash
        default_cash = constants.Int("starting.cash")
        bonus = math.floor(default_cash * 0.25)
        game.Stock.Receive(Resource.Cash, bonus)

class DarkProgression(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.NodeUpgraded, self.when_upgraded)
    
    def when_upgraded(self, data):
        node = data["node"]
        if node.NodeType != "structure.anomaly_lab": return
        if data["level"] != 1: return
        self.lab_activated()
    
    def lab_activated(self):
        now_active = game.CustomData.GetOr("labs_active", 0) + 1
        # advance music
        music.TransitionToLevel(now_active)
        # do the story bit
        pass
        # store info
        ConsUpdateNodeData().inc(game, "labs_active").issue()

#########################################################
# Scoring

class ScoringDarkBestLab(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.dark.best_lab"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        outputs = [anomaly_science_output(l) for l in game.Nodes.WithType("structure.anomaly_lab")]
        return max(outputs) if len(outputs) > 0 else 0
    def rank_limits(self): return self._limits
    def post_rank_text(self): return ":S:"
    def number_text(self, number, rank): return "%d:S:" % number

class ScoringDarkScience(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.dark.total_science"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return game.Stock.Income(Resource.Science)
    def rank_limits(self): return self._limits
    def post_rank_text(self): return ":S:"
    def number_text(self, number, rank): return "%d:S:" % number

#########################################################
# Mapgen

class DarkMapConfig(MapgenDefaults):
    def create_zones(self):
        point_counts = [22, 60, 70, 90, 103, 81, 73, 56, 34] # total signal counts in each zone
        planet_counts = [15, 30, 40, 60, 60, 55, 52, 38, 22] # total planet counts in each zone
        link_values_per_planet = [6.6, 6.3, 5.2, 4.7, 4.4, 3.45, 2.55, 1.7, 0.66] # target average planet link value in each zone
        return {
            "zones": Zones.circle(Vector2.zero, 3.1, 24, point_counts),
            "centers": [Vector2.zero],
            "planet_counts": planet_counts,
            "link_values": link_values_per_planet
        }

class DarkMapgen(GlobalCondition):
    DISTANCE_SETUPS = [[5,0,7,2,6,1,4,3]]
    ANGLE_SETUP = [-0.07, 0.28, 0.57, 0.75, 0.93, 1.25, 1.55, 1.75]
    DISTANCES = {
        "forgiving": (6.25, 8.25),
        "reasonable": (6.75, 9),
        "challenging": (7.25, 9.5),
        "tough": (7.5, 9.75),
        "tough+": (7.75, 10),
        "sandbox": (9, 12)
    }

    def activate(self):
        self._rng = Randomness.SeededRNG(game.GameSeed, "dark_mapgen")
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        generation = data["generation"]
        generation.Refinement("after_node_types", 800, self.refinement_sprinkle_anomalies())
        generation.Refinement("after_planet_types", 900, self.reject_if_starting_position_bad())

    def generate_anomaly_positions(self):
        d_setup = Randomness.Pick(self._rng, self.DISTANCE_SETUPS)
        a_setup = self.ANGLE_SETUP
        distance_low, distance_high = self.DISTANCES[game.GameConfig.Difficulty.ID]
        root_angle = Randomness.Float(self._rng, 0, math.pi * 2)
        for i in range(8):
            angle = root_angle + math.pi * a_setup[i]
            distance = lerp(distance_low, distance_high, d_setup[i] / 7.0)
            yield Vector2(math.cos(angle) * distance, math.sin(angle) * distance)

    def refinement_sprinkle_anomalies(self):
        def refine(gen, signals, zones):
            for attempt in range(30):
                positions = list(self.generate_anomaly_positions())
                victims = []
                for p in positions:
                    candidates = []
                    for max_distance in range(1, 4):
                        candidates = [s for s in gen.SignalsNear(p, max_distance) if s.Contents == "nothing" or s.Contents == "structure.asteroid"]
                        if len(candidates) > 0:
                            break
                    if len(candidates) == 0: break
                    victim = Randomness.Pick(self._rng, candidates)
                    victims.append(victim)
                if len(victims) == 8 or attempt == 29:
                    for victim in victims:
                        victim.Contents = "structure.anomaly_lab"
                        victim.Size = PotentialSize.Big
                    break
        return refine

    def reject_if_starting_position_bad(self):
        bad_planets = ["planet.ice", "planet.barren", "planet.lava"]
        def refine(gen, signals, zones):
            visible = gen.SignalsNear(Vector2.zero, 2.13)
            good_planets = sum(1 for p in visible if p.Contents.startswith("planet.") and p.Contents not in bad_planets)
            log("Good planets: %d" % good_planets)
            if good_planets < 6:
                gen.RejectThisMap()
        return refine

#########################################################
# View

class PointAnomaliesOut(GlobalCondition):
    def activate(self):
        self._markers = {}
        self._create_markers()
        self.react_to(Trigger.BeforeSignalRevealed, self.before_revealed)

    def _create_markers(self):
        signals = [a for a in game.Map.Signals if a.Contents == "structure.anomaly_lab"]
        signals += [p.Signal for p in every(Potential) if p.Signal.Contents == "structure.anomaly_lab"]
        for s in signals:
            self._markers[s] = world.Add(AreaMarker(s.Position, 1, "quest_target_area"))

    def before_revealed(self, data):
        signal = data["signal"]
        if signal in self._markers:
            self._markers[signal].Discard()

#########################################################
# Sensors

class SetupSensorRules:
    COSTS_PER_TYPE = {
        "earthlike": 2,
        "ocean": 2,
        "swamp": 2,
        "jungle": 2,
        "arctic": 2,
        "arid": 7,
        "primordial": 7,
        "mining": 7,
        "factory": 7,
        "remnant": 7,
        "barren": 12,
        "ice": 12,
        "lava": 12
    }

    def is_uncolonized_planet(self, node):
        return node.NodeType.StartsWith("planet.") and node.Level < 0       

    def defer_costs(self): return True
    def repeatable(self): return False

    def cost(self, node):
        kind = node.Kind.ID
        return CompoundCost.Parse("%d$, 1mo" % self.COSTS_PER_TYPE[kind])

    def applies(self, node):
        if node.Connections.Count > 0: return False
        return self.is_uncolonized_planet(node) and node.Kind.ID in self.COSTS_PER_TYPE

    def execute_with_context(self, node, context):
        command = context["command"]
        world.Add(SensorModalOp(command, node, 60, 4.5))
        return {}

    def revert(self, data): pass # delegated to the ModalOp

SetupSensor = SetupSensorRules()

def hide_level_icon(node):
    return None

def sensor_chrome(node):
    direction = node.CustomData.GetOr("direction", 0)
    return [{
        "type": NodeChrome.DirectionDisc,
        "direction": direction,
        "width": 100,
        "swing": 0.1
    }]

#############################################################
# Anomaly structures

def anomaly_wants(need, offered_resource):
    # no filling stuff that's already met
    if need.IsMet: return False
    # is this a defined need?
    if need.AskingFor is not None:
        return need.AskingFor == offered_resource
    # we don't want anything we don't have already
    received = [n.MetWith for n in need.Consumer.Needs if n.IsMet]
    if offered_resource in received:
        return False
    # we accept anything researchable
    return offered_resource.ID in "OLBTW"

def anomaly_want_normal(need, offered_resource):
    # disable conflation for robots here
    if offered_resource.ID == "B" and need.AskingFor is not None and need.AskingFor.ID == "P":
        return False

def anomaly_unknown_need(node):
    header = LS("structure.anomaly.tooltip_need_header", "Any researchable resource")
    desc = LS("structure.anomaly.tooltip_need", "Deliver a new researchable resource that isn't already supplied")
    return InfoBlock(header, desc)

def anomaly_info_on_upgrades(node):
    if node.Level < 1: return None # default handling below level 1
    # get data
    resources_supplied = sum(1 for n in node.Needs if n.IsMet and n.AskingFor is None)
    maxed_out = resources_supplied >= len(AnomalyResearch.PROGRESSION) - 1
    if not maxed_out:
        next_step = AnomalyResearch.PROGRESSION[resources_supplied + 1] - AnomalyResearch.PROGRESSION[resources_supplied]
    # header
    header = LS("structure.lab.upgrade_header", "Possible upgrades")
    # what's possible/impossible?
    info = []
    if not maxed_out:
        info.append(LS("structure.anomaly.send_another", "Send another researchable resource (:O:/:L:/:W:/:T:/:B:) to increase science output by [[delta:{1}S]].", next_step))
    else:
        info.append(LS("structure.anomaly.maxed_out", "All researchable resources delivered."))
    info.append(LS("structure.lab.could_use_researchers", "Send more :P: for [[delta:+1S]] each."))
    return InfoBlock(header, info)

def anomaly_upgrade(node, industry, level):
    if not node.Receives(Resource.People):
        return Permission.No(LS("structure.anomaly.needs_researchers", "Send researchers (:P:) to activate this structure."))
    return Permission.Yes()

def anomaly_science_output(node):
    return ResourceFlow.TotalFlowAtNode(Resource.Science, node)

class AnomalyResearch:
    PROGRESSION = [1, 2, 3, 5, 7, 10]
    def name(self): return LS("quality.anomaly_research", "Anomaly Research")
    def desc(self): 
        return LS("quality.anomaly_research.desc",
            "Research effectiveness increases with the number of different resources supplied.")
    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): 
        people_need = node.Need(Resource.People)
        if not people_need: return None
        people_supplied = people_need.ImportCount
        if people_supplied == 0: return None
        researchers_bonus = max(0, people_supplied - 1)
        resources_supplied = sum(1 for n in node.Needs if n.IsMet and n.AskingFor is None)
        resources_supplied = min(resources_supplied, len(self.PROGRESSION) - 1)
        research = self.PROGRESSION[resources_supplied]
        research += researchers_bonus
        return [
            ChangeProducts.Add(research, Resource.Science, "anomaly_research"),
            ChangeProducts.ReduceProduction(1, Resource.Science, None, True) # hidden tweak to make the amount displayed correct
        ]

class AnomalyNeeds:
    MAXIMUM = 5
    def name(self): return LS("", "")
    def desc(self): return LS("", "")
    def hidden(self, node): return True
    def sentiment(self): return QualitySentiment.Neutral
    def effects(self, node):
        resources_supplied = sum(1 for n in node.Needs if n.IsMet and n.AskingFor is None)
        needs_required = min(self.MAXIMUM, resources_supplied + 1)
        return [
            ChangeNeeds.AddUnknowns(needs_required)
        ]

###################################################################
# Explanations

class ExplanationRule(GlobalCondition):
    def __init__(self, string, *args):
        self._string, self._args = string, args
    def info(self):
        ci = CondInfo()
        ci.FullDescription = LS(self._string, None, *self._args)
        return ci

class InterferenceRule(ExplanationRule):
    def __init__(self):
        ExplanationRule.__init__(self, "mission.dark.interference_rule")

class NoLabsRule(ExplanationRule):
    def __init__(self):
        ExplanationRule.__init__(self, "mission.dark.no_labs_rule")

###################################################################
# Fluff

class DarkStory(StoryBits):
    def __init__(self):
        StoryBits.__init__(self, [
            LabDiscoveredPopup(),
            LabProgressPopup(1, "text_recovered", "text_1", "look_elsewhere"),
            LabProgressPopup(2, "more_text_recovered", "text_3", "text_4"),
            LabProgressPopup(3, "more_text_recovered", "text_5"),
            LabProgressPopup(4, "more_text_recovered", "text_6"),
            LabProgressPopup(5, "more_text_recovered", "text_7"),
        ])

class LabDiscoveredPopup(PopupTutorial):
    def __init__(self):
        PopupTutorial.__init__(self)
    def condition(self):
        return any(game.Nodes.WithType("structure.anomaly_lab"))
    def steps(self):
        return [StoryBit("mission.dark.initial_discovery", ["vattori", "dendr", "baqar", "silthid", "aphorian"])]

class LabProgressPopup(PopupTutorial):
    THRESHOLD = 4
    def __init__(self, labs, *text):
        self._labs = labs
        self._text = text
        PopupTutorial.__init__(self, args=[labs] + list(text))
    def condition(self):
        labs_over_threshold = sum(1 for n in game.Nodes.WithType("structure.anomaly_lab") if anomaly_science_output(n) >= self.THRESHOLD)
        return labs_over_threshold >= self._labs
    def steps(self):
        return [LabFragments(self._text)]

class LabFragments(TutorialStep):
    def __init__(self, text):
        TutorialStep.__init__(self)
        self._text = text
    def id(self): return "fragments"
    def manual_advance(self): return True
    def ls_text(self):
        texts = [L("mission.dark.%s" % text_id) for text_id in self._text]
        return "\n".join(texts)
    def character(self):
        member = Randomness.Pick(list(game.Council.Members))
        return member.Race.ID

######################################################################
# Sector type stuff

class DarkSectorType(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_conditions)

    def setup_conditions(self, data):
        game.Conditions.Activate(PointAnomaliesOut)

