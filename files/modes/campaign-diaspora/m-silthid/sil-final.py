#########################################################
# Main mission class

class SilthidMainMission(OneRaceMainMission):
    def __init__(self):
        OneRaceMainMission.__init__(self, "silthid", [SMMIgniteGate(), SMMSendEnoughPeople()])
        self._one_last = None

    def scoring_rules(self):
        return [
            ScoringCampaignTasks([0, 1, 2, 3, 4, 4]),
            ScoringPeopleSent([2, 4, 6, 8, 10]),
            ScoringGateActivation([100, 27, 26, 25, 24, 23]),
        ]

    def conditions(self): return [
        (WinMissionOnTime, "SilthidMainMission()", 28),
        (IzziumMarkers,),
        (TerminalRewards,),
        (GateIgnition,)
    ]

    def do_additional_setup(self):
        game.Stock.Receive(Resource.Cash, 20) # starting bonus
    
    def things_to_explain(self):
        morale_boost = MoraleBoost.TRADE_BONUS
        terminal_upkeep = constants.Int("sil.terminal.build_upkeep")
        terminal_cash = constants.Int("sil.terminal.bonus.$")
        terminal_science = constants.Int("sil.terminal.bonus.S")
        return [
            ("structure", "gate_focus"),
            ("custom", "special.building_terminals", terminal_cash, terminal_science, terminal_upkeep),
            ("custom", "special.izzium_planets"),
            ("custom", "special.completing_terminals"),
            ("custom", "special.delivering_people", morale_boost)
        ]
    
    def borrowed_techs(self):
        return {
            "baqar": ["geothermals", "asteroid_mining", "gravitic_tugs"],
            "dendr": ["asteroid_dwelling", "enlightenment", "empathic_links"],
            "aphorian": ["wave_augmentation", "geoharvesting", "hyperdrive"],
            "vattori": ["orbital_labs", "quantum_computing", "matter_transposition"],
        }

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

    def grant_time_extension(self):
        active = game.CustomData.GetOr("active_terminals", 0)
        terminals_with_situations = sum(1 for t in game.Nodes.WithType("structure.gate_terminal") if t.Situation and t.Situation.EventID == "event_complete_terminal_reversible")
        eligible = active < 5 and (terminals_with_situations + active >= 5)
        self._one_last = self._one_last or OneLastAction(["start_situation", "run_event"])
        return eligible and self._one_last.still_in_grace_period()

##########################################################
# Mission goals and scoring

class SMMIgniteGate:
    def check_completion(self):
        focus = game.Nodes.FirstWithType("structure.gate_focus")
        if focus is None: return False
        return focus.CustomData.GetOr("ignited", False)        
    def description(self): return LS("mission.silthid.goal.ignite_gate")

class SMMSendEnoughPeople:
    def __init__(self):
        self._required = constants.Int("sil.goal.required_people")
    def requires(self): return (0,)
    def check_completion(self):
        return total_people_sent() >= self._required
    def description(self): return LS("mission.silthid.goal.send_enough_people", None, self._required)
    def state(self): return (total_people_sent(), self._required)
    def short(self): return "%d/%d:P:" % self.state()

class ScoringPeopleSent(ScoringFiveRanks):
    def __init__(self, increments):
        base = constants.Int("sil.goal.required_people")
        self._limits = [0] + [base + i for i in increments]
    def tags(self): return ["mission"]
    def id(self): return "scoring.silthid.people_sent"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return total_people_sent()
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":P:"
    def number_text(self, number, rank): return "%d:P:" % number   

def total_people_sent():
    terms = game.Nodes.WithType("structure.gate_terminal")
    total = sum(t.CustomData.GetOr("connected_people", 0) for t in terms)
    return total

class ScoringGateActivation(ScoringFiveRanks):
    THRESHOLD = 5
    def __init__(self, limits):
        self._limits = limits

    def tags(self): return ["mission"]
    def id(self): return "scoring.silthid.gate_activation"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return None
        return game.CustomData.GetOr("ignition_year", None)
    def rank_op(self): return "<="
    def rank_limits(self): return self._limits
    def rank_text(self, number): return str(game.Time.NormalizedTurnToYear(number))
    def number_text(self, number, rank): return str(game.Time.NormalizedTurnToYear(number)) if number is not None else "-"

#########################################################
# Music

class SilthidMusic(MusicProgression):
    def _check_for_transition(self, prev):
        focus = game.Nodes.FirstWithType("structure.gate_focus")        
        ignited = focus and focus.CustomData.GetOr("ignited", False)
        active = game.CustomData.GetOr("active_terminals", 0)
        lv = 0
        if active >= 1: lv += 1
        if active >= 3: lv += 1
        if ignited: lv += 1
        if prev < lv: return lv

#########################################################
# Mapgen stuff

class SilthidMapgenSettings:
    def create_zones(self):
        # slightly denser outer zones to make working with the fargate easier
        settings = MapgenDefaults().create_zones()        
        for i in range(1, 4):
            settings["planet_counts"][i] = int(settings["planet_counts"][i] * 1.13)
            settings["link_values"][i] = settings["link_values"][i] * 1.1
        return settings

class MapgenSilthidPlanetTypes(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.factory", 8, 11, ["planet.barren", "planet.ice", "planet.lava", "planet.arid"]),
            ("planet.mining", 8, 11, ["planet.barren", "planet.ice", "planet.lava", "planet.arid"]),
        ])

#########################################################
# Izzium quirk

class AddIzziumMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # sprinkle the izzium planets
        izzium_prevalence = constants.Float("sil.izzium_planets")
        planet_types = ["planet.%s" % p for p in ["earthlike", "swamp", "arid", "arctic", "ocean", "jungle", "barren", "ice", "lava"]]
        sprinkler = refinement_sprinkle_quirk(QuirkIzziumPlanet.EXPR, planet_types, 
            zone_density = lambda index: izzium_prevalence * 0.5 if index == 0 else izzium_prevalence,
            maximize_distances = True)
        map_generation.Refinement("after_planet_types", 700, sprinkler)

class QuirkIzziumPlanet:
    EXPR = "QuirkIzziumPlanet()"

    def name(self): return LS("quirk.sil_izzium_planet")
    def desc(self): return LS("quirk.sil_izzium_planet.desc")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): return 10 if node.Level < 0 else 0
    def icon(self, node): return {"type": "neutral", "text": ":res_izz:"}
    def hidden(self, node): return True

    def uses_people(self, industry_kind):
        base_lv = industry_kind.BaseLevel
        if any(n.Resource == Resource.People for n in base_lv.BaseNeeds): return True
        if any(p == Resource.People for p in base_lv.BaseProducts): return True
        return False

    def effects(self, node):
        effects = [
            ColonizationOptions.RemoveMatching(self.uses_people),
            ColonizationOptions.Add("izzium_mining")
        ]
        return effects

class IzziumMarkers(GlobalCondition):
    def activate(self):
        self.recreate_markers()
        self.react_to(Trigger.AfterNodeDiscovered, self.node_discovered)

    def recreate_markers(self):
        self._markers = {}
        all_signals = [p.Signal for p in every(Potential)]
        all_signals += game.Map.Signals
        quirk_expr = QuirkIzziumPlanet.EXPR
        for s in all_signals:
            if s.Quirk == quirk_expr:
                self._markers[s] = world.Add(AreaMarker(s.Position, 0.65, "dashed_outline_no_fow"))

    def node_discovered(self, data):
        self.check_signal(data["signal"])

    def check_signal(self, sig):
        if sig in self._markers:
            commands.IssueScriptedConsequence(ConsDropMarker(self._markers, sig))

class ConsDropMarker:
    def __init__(self, dict, sig):
        self._dict = dict
        self._sig = sig
        self._marker = self._dict[self._sig]
    
    def apply(self):
        self._marker.Discard()
        del self._dict[self._sig]
    
    def revert(self):
        self._marker = world.Revive(self._marker)
        self._dict[self._sig] = self._marker

class SilStabilize:
    @staticmethod
    def execute(node):
        game.Qualities.Detach("QuirkIzziumPlanet()", node)
        return {"node": node}

    @staticmethod
    def revert(data):
        game.Qualities.Attach("QuirkIzziumPlanet()", data["node"])
    
    @staticmethod
    def applies(node):
        return any(q.ScriptExpression == "QuirkIzziumPlanet()" for q in node.GetQualities())

##########################################################
# Gate

GATE_PLANNED_RADIUS_INCREASE = 0.8

def focus_cost(kind):
    cost_text = "%d$, 4mo" % constants.Int("sil.fargate.cost")
    return CompoundCost.Parse(cost_text)

def focus_just_once(kind):
    return game.Nodes.FirstWithType("structure.gate_focus") is None

def focus_obstruction(model):
    planned = not isinstance(model, Structure)
    radius = constants.Float("sil.gate.radius")
    if planned:
        radius += GATE_PLANNED_RADIUS_INCREASE
    else:
        radius -= 0.2
    return CircularObstruction.Transient(radius, False, True)

def focus_fow_points(ps):
    pts = [ps.Position]
    disp = Vector2.right * f(0.5)
    for a in range(0, 360, 45):
        pts += [ps.Position + rotate_vector(disp, a)]
    return pts

def focus_fog_reveal_radius(focus):
    return constants.Float("sil.gate.radius") + 5

GATE_EDIBLE_STRUCTURES = ["structure.asteroid", "structure.forebear_station"]
def focus_obstructed_by(planned, model):
    if isinstance(model, Node):
        if model.HasIndustry and model.Industry.Kind.ID != "station": return True
        if len(model.Connections) > 0: return True
        if model.NodeType.startswith("planet."): return False
        if model.NodeType == "structure.gate_terminal": return False
        if model.NodeType in GATE_EDIBLE_STRUCTURES: return False
    if isinstance(model, Potential):
        return False
    return True

def focus_tooltip(me, original):
    if me.CustomData.GetOr("ignited", False): return [Tooltip.HideThisTooltip]
    slot_count = constants.Int("sil.gate.slots")
    active = game.CustomData.GetOr("active_terminals", 0)
    return [original, LS("structure.gate_focus.tooltip", None, active, slot_count)]

def focus_placed(focus_node):
    # allow the player to rotate the structure
    build_cmd = None
    for cmd in reversed(commands.RecordedCommands):
        if cmd.CommandString and cmd.CommandString.startswith("build/gate_focus"):
            build_cmd = cmd
            break
    if not build_cmd:
        raise Exception("Wasn't able to find the build command.")
    world.Add(RotateStructureOp(build_cmd, focus_node, {
        "when_completed": lambda _: focus_finish_building(focus_node)
    }))

def focus_finish_building(focus_node):
    # destroy consumed objects
    eat_radius = constants.Float("sil.gate.radius") + GATE_PLANNED_RADIUS_INCREASE + 0.5
    eaten = list(game.Nodes.Within(focus_node.Position, eat_radius))
    eaten += list(game.Nodes.PotentialsWithin(focus_node.Position, eat_radius))
    for e in eaten:
        if e == focus_node: continue
        if isinstance(e, Structure) and e.NodeType == "structure.gate_terminal": continue
        commands.IssueScriptedConsequence(ConsBulldoze(focus_node, e))
    # set props
    radius = constants.Float("sil.gate.radius")
    slot_count = constants.Int("sil.gate.slots")
    rotation = focus_node.Rotation
    slot_offset = Vector2(radius + 0.01, 0)
    focus_node.CustomData.Set("finalized", True)
    for slot in range(slot_count):
        slot_angle = 90.0 + slot * 360.0 / slot_count + rotation
        slot_relative_pos = rotate_vector(slot_offset, slot_angle)
        focus_node.CustomData.Set("slot_pos_%d" % slot, focus_node.Position + slot_relative_pos)
        focus_node.CustomData.Set("slot_rotation_%d" % slot, slot_angle)
        focus_node.CustomData.Set("slot_terminal_%d" % slot, None)
    focus_node.TriggerChange()
    # placeholders
    commands.IssueScriptedConsequence(ConsAddTerminals(focus_node))
    # ping structure
    AnimationEvents.TriggerAnimation(focus_node, "Ping")

class ConsBulldoze:
    def __init__(self, gate, thing):
        self._gate = gate
        self._thing = thing

    def apply(self):
        if isinstance(self._thing, Potential):
            conditions.Get("IzziumMarkers()").PythonObject.check_signal(self._thing.Signal) # remove marker if necessary
            self._thing.Dissolve()
        else:
            AnimationEvents.TriggerAnimationWithData(self._thing, "ConsumedByRift", "rift", self._gate)
            self._thing.Discard()

    def revert(self):
        world.Revive(self._thing)

class ConsAddTerminals:
    def __init__(self, focus):
        self._focus = focus
        self._structures = []

    def apply(self):
        f = self._focus
        slot_count = constants.Int("sil.gate.slots")
        kind = StructureKind.All["gate_terminal"]
        for no in range(slot_count):
            pos = f.CustomData.Get("slot_pos_%d" % no)
            structure = world.Add(Structure(pos, kind))
            structure.Rotation = f.CustomData.Get("slot_rotation_%d" % no) + 180.0
            structure.AddElement(NumericProgress(TerminalProgressRules()))
            structure.CustomData.Set("slot_no", no)
            self._structures.append(structure)
            structure.TriggerChange()

    def revert(self):
        for s in self._structures:
            s.Discard()

##########################################################
# Building terminals

## Unfinished structure

def unfinished_node_tag(node, blocks):
    # hide until we start
    if node.Level == 0: return
    return blocks.DefaultText()

def unfinished_info_on_upgrades(node):
    if node.Level < 1:
        header = LS("structure.unfinished_terminal.waiting")
        text = LS("structure.unfinished_terminal.waiting.text")
    else:
        header = LS("structure.unfinished_terminal.in_progress")
        text = LS("structure.unfinished_terminal.in_progress.text")
    return InfoBlock(header, [text])

def unfinished_tooltip(node, original):
    progress = NumericProgress.For(node)
    progress_made = progress.CalculateYearlyProgress()
    if progress.IsCompleted: return [original]
    if progress_made == 0:
        return [original, LS("structure.unfinished_terminal.waiting.text")]
    else:
        return [original, LS("structure.unfinished_terminal.completion_in", None, progress.TicksToCompletion), LS("structure.unfinished_terminal.in_progress.text")]

class TerminalProgressRules:
    def loadable_expression(self): return "TerminalProgressRules()"
    def goal_number(self, node): 
        return constants.Int("sil.terminal.build_time")        
    def when_goal_complete(self, node, progress):        
        commands.IssueScriptedConsequence(ConsUpdateNodeData().add(node, "completed", True))
        commands.Issue(EnableSituation(world, node, "event_complete_terminal_reversible"))
    def show_if_not_started(self): return False

class TerminalProgressFlow:
    def name(self): return LS("quality.progress")
    def desc(self): return LS("quality.terminal_progress.desc")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        total = node.ImportCount
        if node.Level < 1: total = 0
        return [
            ResourceFlow.Flow(Resource.All["progress"], total, FlowCategory.Progress)
        ]

class TerminalBuildUpkeep:
    def name(self): return LS("quality.constructing_terminal")
    def desc(self): return LS("quality.constructing_terminal.desc", None, self.upkeep())
    def sentiment(self): return QualitySentiment.Positive

    def upkeep(self): return constants.Int("sil.terminal.build_upkeep")

    def effects(self, node):
        progress = NumericProgress.For(node)
        if progress is None or progress.IsCompleted: return
        if node.ImportCount == 0: return
        return [
            ResourceFlow.Cash(-self.upkeep(), FlowCategory.StructureUpkeep)
        ]

class TerminalRewards(GlobalCondition):
    """Gives a +$ +S immediate bonus for starting a new terminal."""
    def activate(self):
        self.react_to(Trigger.NodeUpgraded, self.node_upgraded)

    def node_upgraded(self, data):
        node = data["node"]
        if not node.HasIndustry: return
        if node.Industry.Kind.ID != "building_terminal": return
        if node.Level != 1: return
        self.grant_reward(node)
    
    def grant_reward(self, node):
        ConsGrantResources(constants.Int("sil.terminal.bonus.$"), Resource.Cash, node).issue()
        ConsGrantResources(constants.Int("sil.terminal.bonus.S"), Resource.Science, node).issue()


def event_complete_terminal_reversible(evt):
    evt.SetLocalizedTitle(LS("event.complete_terminal"))
    terminal_count = game.CustomData.GetOr("active_terminals", 0)
    chapter = "middle"
    if terminal_count == 0: chapter = "first"
    if terminal_count == 4: chapter = "last"
    bonus_effects = "" # " -> get(%d,$) -> get(%d,S)" % (constants.Int("sil.terminal.bonus.$"), constants.Int("sil.terminal.bonus.S"))
    evt.SetLocalizedText(LS("event.complete_terminal.%s" % chapter))
    evt.AddChoices(
        "Finish the process. -> complete_terminal" + bonus_effects
    )

class EffCompleteTerminal(ChoiceEffect):
    def consequence(self): return self
    
    def apply(self):
        node = self.node()
        # destroy useless connections
        for c in list(node.Connections):
            transports_ot = any(r.Resource.ID in "OT" for r in c.Routes)
            if transports_ot:
                commands.Issue(DestroyConnection(world, c))
        commands.Issue(ChangeNodeIndustry(world, node, IndustryKind.All["active_terminal"]))
        commands.IssueScriptedConsequence(ConsCompleteTerminalInPlace(node))
    
    def revert(self): pass

class ConsCompleteTerminalInPlace:
    def __init__(self, node):
        self._focus = game.Nodes.FirstWithType("structure.gate_focus")
        self._node = node
        self._slot_no = node.CustomData.Get("slot_no")

    def apply(self):
        node = self._node
        # increase counter
        game.CustomData.Inc("active_terminals")
        # set terminal reference
        self._focus.CustomData.Set("slot_terminal_%d" % self._slot_no, node)
        # trigger
        game.Triggers.ActivateFromScript(Trigger.Custom("TerminalLocked"), {
            "focus": self._focus, "term": self._node, "slot": self._slot_no 
        })
        # animate
        AnimationEvents.TriggerAnimation(node, "Ping")
        # refresh to update the morale quality
        self.refresh_connected()
        return [self._node]

    def revert(self):
        game.CustomData.Dec("active_terminals")
        self._focus.CustomData.Set("slot_terminal_%d" % self._slot_no, None)
        self.refresh_connected()
        return [self._node]

    def refresh_connected(self):
        nodes = set()
        for term in game.Nodes.WithType("structure.gate_terminal"):
            for r in game.Reachability.ReachableNodes(term):
                nodes.add(r)
        for n in nodes:
            n.RefreshState()

##########################################################
# Active terminals

def finished_tooltip(term, original):
    return [original, LS("structure.gate_terminal.connect_people")]

def finished_node_tag(node, blocks):
    return ""

def finished_chrome(term):
    people = term.CustomData.GetOr("connected_people", 0)
    return [{
        "type": NodeChrome.Text,
        "text": "%d:P:" % people,
        "bg_color": UIColors.ChromeStandardBG
    }]

def finished_before_trade(term):
    reachable = [r for r in game.Reachability.ReachableNodes(term) if r.ActuallyProduces(Resource.People)]
    total_people = 0
    for r in reachable:
        responsible_terminal = r.CustomData.GetOr("connected_terminal", None)
        if responsible_terminal is None and not commands.IsReverting:
            commands.IssueScriptedConsequence(ConsAssignToTerminal(r, term))
        elif responsible_terminal == term:
            total_people += r.AmountProduced(Resource.People)
    previous_value = term.CustomData.GetOr("connected_people", 0)
    if previous_value != total_people:
        ConsUpdateNodeData(trigger_changes = True).add(term, "connected_people", total_people).issue()

class ConsAssignToTerminal:
    def __init__(self, node, term):
        self._node = node
        self._term = term
        self._assigned = False

    def apply(self):
        if self._node.CustomData.GetOr("connected_terminal", None) is not None:
            return # somebody else already assigned to it
        self._node.CustomData.Set("connected_terminal", self._term)
        attach = ConsAttachQualityOnce(self._node, "morale_boosted", "MoraleBoost()")
        commands.IssueScriptedConsequence(attach)
        self._assigned = True
        return [self._term]

    def revert(self):
        if not self._assigned: return
        self._node.CustomData.Clear("connected_terminal")
        return [self._term]


class TerminalAcceptingPeople:
    def name(self): return LS("quality.accepting_people")
    def desc(self): return LS("quality.accepting_people.desc")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, term):
        people = term.CustomData.GetOr("connected_people", 0)
        return [LabelEffect.With("%d:P:" % people)]

class MoraleBoost:
    TRADE_BONUS = 30
    def name(self): return LS("quality.morale_boost")
    def desc(self): return LS("quality.morale_boost.desc", None, self.TRADE_BONUS)
    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node):
        return [
            PercentageBonus.TradeIncome(self.TRADE_BONUS)
        ]

##########################################################
# Ignition

class GateIgnition(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.Custom("TerminalLocked"), self.check_for_ignition)

    def check_for_ignition(self, data):
        focus = data["focus"]
        if focus.CustomData.GetOr("ignited", False): return
        slot_count = constants.Int("sil.gate.slots")
        for s in range(slot_count):
            slot_taken = focus.CustomData.GetOr("slot_terminal_%d" % s, None) is not None
            if not slot_taken: 
                return
        # all slots taken, let's go!
        self.ignite(focus)

    def ignite(self, focus):
        commands.IssueScriptedConsequence(ConsIgniteGate(focus))
        pass

class ConsIgniteGate:
    def __init__(self, focus):
        self._focus = focus

    def apply(self):
        self._focus.CustomData.Set("ignited", True)
        game.CustomData.Set("ignition_year", game.Time.NormalizedTurn)
        self._focus.TriggerChange()

    def revert(self):
        self._focus.CustomData.Set("ignited", False)
        game.CustomData.Clear("ignition_year")
        self._focus.TriggerChange()
