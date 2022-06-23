#########################################################
# Main mission class

class AphorianMainMission(OneRaceMainMission):
    def __init__(self):
        required = constants.Int("aph.required_trade")
        self._required = required
        OneRaceMainMission.__init__(self, "aphorian", [AMMEnoughTrade(required)])

    def scoring_rules(self):
        trade_limits = [5, 10, 15, 20, 25]
        trade_limits = [0] + [self._required + l for l in trade_limits]
        return [
            ScoringCampaignTasks([0, 1, 2, 3, 4, 4]),
            ScoringFinalInstability([100, 80, 64, 48, 32, 16]),
            ScoringTrade(trade_limits)
        ]

    def conditions(self): return [
        (WinMissionOnTime, "AphorianMainMission()", 28),
        ConnectionStabilizing,
        SectorInstability,
        UnstableSlipwaysCount,
        TradeTracking,
    ]

    def do_additional_setup(self):
        pass
    
    def things_to_explain(self):
        return [
            ("cond", "SectorInstability()"),
            ("structure", "trap"),
            ("structure", "anchor"),
        ]
    
    def borrowed_techs(self):
        return {
            "baqar": ["mass_reactors", "gravitic_tugs", "void_synthesis"],
            "dendr": ["xenofoods", "weather_control", "genesis_cells"],
            "silthid": ["mass_lensing", "integrated_manufacturing", "extreme_mini"],
            "vattori": ["orbital_labs", "machine_sentience", "skill_download"],
        }

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

###############################################################
# Mission goals

class AMMEnoughTrade:
    def __init__(self, required):
        self._required = required
        self._tt = None

    def state(self):
        self._tt = self._tt or TradeTracking.get()
        total = self._tt.current_total() if self._tt else 0
        return total, self._required

    def description(self): return LS("mission.aphorian.goal.trade_routes", None, self._required)
    def short(self): return "%d/%d" % self.state()

    def check_completion(self):
        current, needed = self.state()
        return current >= needed


class TradeTracking(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.TradeRouteEstablished, self.new_route)
        self.react_to(Trigger.ActionReverted, self.recount)
        self.recount()

    @staticmethod
    def get(): 
        cond = conditions.Get("TradeTracking()")
        return cond.PythonObject if cond else None

    def current_total(self): return self._total

    def recount(self, data = None):
        self._total = sum(1 for tr in every(TradeRoute))
    
    def new_route(self, data = None):
        self._total += 1

###############################################################
# Music

class AphorianMusic(MusicProgression):
    def __init__(self):
        self._required = float(constants.Int("aph.required_trade"))
        self._tt = None
        
    def _check_for_transition(self, prev):
        self._tt = self._tt or TradeTracking.get()
        total = self._tt.current_total() if self._tt else 0
        prop = total / self._required        
        lv = 0
        if prop >= 0.25: lv += 1
        if prop >= 0.65: lv += 1
        if prop >= 1.0: lv += 1
        if prev < lv: return lv

###############################################################
# Scoring 

class ScoringFinalInstability(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.aphorian.instability"
    def base_number(self):
        return game.CustomData.GetOr("instability", 0)
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return "%"
    def rank_op(self): return "<="
    def number_text(self, number, rank): return "%d%%" % number

class ScoringTrade(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.aphorian.trade"
    def base_number(self):
        return TradeTracking.get().current_total()
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1    
    def number_text(self, number, rank): return str(number)

###############################################################
# Spacetime traps

TRAP_ORBIT = 0.8
TRAP_SHAPE_STEPS = 10
SLIPWAY_CONNECTIONS = set(["connection.slipway", "connection.everted"])

def trap_placement():
    return [
        PlaceNear(trap_node_eligible, f(TRAP_ORBIT + 0.05), LS("structure.trap.place_in_orbit"), "VPlaceNear"),
        ScriptedPlacement(SnapToOrbit(TRAP_ORBIT, trap_node_eligible))
    ]

def trap_view_model(): return "Trap"

def trap_node_eligible(node):
    return node.NodeType.startswith("planet.") and node.Level >= 0 and not node.CustomData.Has("has_trap")

def trap_obstructed_by(planned, model):
    return not isinstance(model, Node) or not trap_node_eligible(model)

def trap_placed(node):
    conn_stab = game.Conditions.Get("ConnectionStabilizing()").PythonObject
    planet = game.Nodes.ClosestWith(node.Position, f(TRAP_ORBIT + 0.2), trap_node_eligible)
    # add quality
    commands.Issue(AttachQuality(world, planet, "SpacetimeDumping()"))
    # set custom data and trigger stability check
    update = ConsUpdateNodeData()
    update.add(planet, "has_trap", True)
    update.add(node, "host", planet)
    update.add(node, "obstructs_hyperlanes", True)
    update.when_done(lambda: conn_stab.check_node(planet))
    update.issue()

def trap_connectivity(node, other):
    return NodeConnectivity.Ignores() # no connections to traps

def trap_obstruction(model):
    kind = model.Kind    
    points = list(trap_generate_raw_points(kind))
    points = list(trap_smooth_points(points))
    return TransientPolygonObstruction(points, True)

def trap_generate_raw_points(kind):
    structure_id = kind.ID
    distance = constants.Float("aph.%s.distance" % structure_id)
    full_angle = constants.Float("aph.%s.angle" % structure_id)
    angle_min, angle_max = -full_angle * 0.5, full_angle * 0.5
    steps = TRAP_SHAPE_STEPS
    near, far = TRAP_ORBIT, TRAP_ORBIT + distance
    center = Vector2(-near, 0)
    near_v, far_v = Vector2(near, 0), Vector2(far, 0)
    for n in range(steps + 1):
        a = lerp(angle_min, angle_max, float(n) / steps)
        yield center + rotate_vector(near_v, a)
    start = center + rotate_vector(near_v, angle_max)
    end = center + rotate_vector(far_v, angle_max)
    for n in range(1, steps):
        yield lerp(start, end, f(float(n) / steps))
    for n in range(steps + 1):
        a = lerp(angle_max, angle_min, float(n) / steps)
        yield center + rotate_vector(far_v, a)
    start = center + rotate_vector(far_v, angle_min)
    end = center + rotate_vector(near_v, angle_min)
    for n in range(1, steps):
        yield lerp(start, end, f(float(n) / steps))

def trap_smooth_points(pts):
    max_smooth = 0.2
    centroid = Vector2.zero
    for p in pts:
        centroid += p
    centroid /= f(len(pts))
    half_steps = int(TRAP_SHAPE_STEPS / 2)
    steps = TRAP_SHAPE_STEPS
    for idx, pt in enumerate(pts):
        idx = idx % steps
        smooth_str = 1.0 - (idx / float(half_steps))
        smooth_str = abs(smooth_str)
        smooth_str = math.pow(smooth_str, 2)
        if idx == steps * 2 or idx == steps  * 3:
            smooth_str += 0.8
        pt = lerp(pt, centroid, f(smooth_str * max_smooth))
        yield pt

class SpacetimeDumping:
    PENALTY = 1
    def name(self): return LS("quality.spacetime_dumping")
    def desc(self): return LS("quality.spacetime_dumping.desc", None, self.PENALTY)
    def sentiment(self): return QualitySentiment.Negative

    def effects(self, node):
        if not node.ActuallyProduces(Resource.People): return
        return [ResourceFlow.Happiness(-self.PENALTY, FlowCategory.HappinessProblems, self.name())]

############################################
# Anchor

ANCHOR_SHAPE_STEPS = 64

def anchor_obstruction(model):
    kind = model.Kind
    points = list(anchor_generate_points(kind))
    return TransientPolygonObstruction(points, True)

def anchor_generate_points(kind):
    structure_id = kind.ID
    distance = constants.Float("aph.%s.distance" % structure_id)
    steps = ANCHOR_SHAPE_STEPS
    a_step = 360.0 / steps
    center = Vector2.zero
    vec = Vector2(distance, f(0.0))
    for n in range(steps + 1):
        yield center + rotate_vector(vec, a_step * n)

def anchor_desc_data(kind):
    return [constants.Int("aph.anchor.bonus")]

def anchor_cost(structure_kind):
    cost = structure_kind.BaseCost
    anchors = len(game.Nodes.WithType("structure.anchor")) if hasattr(game, "Nodes") else 0 
    increase = constants.Int("aph.anchor.cost_increase") * anchors
    cost = cost.Add(Resource.Cash, increase)
    return cost

def anchor_placed(anchor):
    anchor.CustomData.Set("obstructs_hyperlanes", True)

############################################
# Instability

class ConnectionStabilizing(GlobalCondition):
    STABLE_OFFSET = 6
    UNSTABLE_OFFSET = 10

    def activate(self):
        self.react_to(Trigger.ConnectionBuilt, self.when_connection_built)

    def when_connection_built(self, data):
        self.check_connection(data["connection"])
    
    def check_node(self, node):
        for conn in node.Connections:
            self.check_connection(conn)

    def check_connection(self, conn):
        if not conn.Kind.TypedID in SLIPWAY_CONNECTIONS: return
        expected = any(e.CustomData.Has("has_trap") for e in (conn.From, conn.To))
        cached = conn.CustomData.GetOr("stabilized", None)
        if expected != cached:
            update = ConsUpdateNodeData()
            update.add(conn, "stabilized", expected)
            update.add(conn, "material_offset", self.STABLE_OFFSET if expected else self.UNSTABLE_OFFSET)
            update.when_done(lambda: conn.TriggerChange())
            update.issue()

class SectorInstability(GlobalCondition):
    def __init__(self):
        self._base_allowed = constants.Int("aph.allowed_slipways")
        self._anchor_bonus = constants.Int("aph.anchor.bonus")
        self._burden = 0
    
    def activate(self):
        self.recalculate_burden()
        self.react_to(Trigger.NewTurn, self.when_next_year_arrives)
        self.react_to(Trigger.WorldStateChanged, self.recalculate_burden)
    
    def recalculate_burden(self, data = None):
        if game.GameContext != GameContext.PlayingScenario: return
        total_unstable = self.calculate_unstable_slipways()
        allowed = self.calculate_allowed()
        self._unstable = total_unstable
        self._allowed = allowed
        self._burden = max(0, total_unstable - allowed)
        self.signal_change()

    def when_next_year_arrives(self, data):
        burden = self._burden
        update = ConsUpdateNodeData()
        update.add(game, "instability", lambda x: clamp(0, 100, (x or 0) + burden))
        update.when_done(self.check_for_loss)
        update.issue()

    def calculate_unstable_slipways(self): return sum(1 for s in every(Slipway) if not s.CustomData.GetOr("stabilized", False))
    def instability(self): return game.CustomData.GetOr("instability", 0) 
    def burden(self): return self._burden
    def unstable_vs_allowed(self): return (self._unstable, self._allowed)
    def calculate_allowed(self): 
        allowed = self._base_allowed
        if game.GameContext == GameContext.PlayingScenario:
            allowed += len(game.Nodes.WithType("structure.anchor")) * self._anchor_bonus
        return allowed
    
    def check_for_loss(self):
        if self.instability() >= 100:
            empire.WinningLosing.EndScenario({
                "outcome": "loss", "defeat": True,
                "defeat_icon": "icon_mission_failed",
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("mission.aphorian.game_end.spacetime_breakdown"),
                "shown_elements": ["undo"]
            })
        self.signal_change()

    def info(self):
        instability, burden, slipways = self.instability(), self.burden(), self.calculate_unstable_slipways()
        allowed = self.calculate_allowed()
        if -burden > instability:
            burden = -instability
        burden_text = ("+%d%%" if burden >= 0 else "%d%%") % burden
        burden_text = styled(burden_text, "SecondaryNumber")
        ci = CondInfo()
        ci.Important = True
        ci.Icon = "icon_sector_instability"
        short_text = "%d%%%s" % (instability, burden_text)
        if instability + 3 * burden >= 100:
            short_text = styled(short_text, "Bad")
        ci.ShortText = short_text
        # explanatory text
        intro_txt = L("cond.instability.intro")
        losing_txt = L("cond.instability.loss_condition", None, 100)
        if burden > 0:
            current_txt = L("cond.instability.current", None, instability, burden, slipways)
        else:
            current_txt = L("cond.instability.current.no_growth", None, instability, burden, allowed)
        explanation_txt = L("cond.instability.explanation", None, allowed)
        ci.FullDescription = RichText.Paragraphs([intro_txt, explanation_txt, losing_txt])
        tt_paragraphs = [explanation_txt, losing_txt, current_txt]
        tt_paragraphs = [styled(txt, "TooltipLight") for txt in tt_paragraphs]
        tt_paragraphs = [styled(L("cond.instability"), "TooltipHeader")] + tt_paragraphs
        ci.Tooltip = [RichText.Paragraphs(tt_paragraphs)]
        return ci

class UnstableSlipwaysCount(GlobalCondition):   
    def activate(self):
        self.react_to(Trigger.WorldStateChanged, lambda _: self.signal_change(), 900)
    
    def info(self):        
        ci = CondInfo()
        ci.Icon = "icon_unstable_slipways"
        unstable, allowed = conditions.Get("SectorInstability()").PythonObject.unstable_vs_allowed()
        short_text = "%d/%d" % (unstable, allowed)
        ci.ShortText = short_text        
        desc = L("cond.unstable_slipways.desc", None, unstable, allowed)
        if unstable > allowed:
            desc += " <nobr>" + L("cond.unstable_slipways.over", None, unstable - allowed) + "</nobr>"
        desc = Localization.MakeSentence(desc)
        ci.FullDescription = desc
        header = styled(LS("cond.unstable_slipways", None, unstable, allowed), "TooltipHeader")
        ci.Tooltip = RichText.Paragraphs([header, styled(ci.FullDescription, "TooltipLight")])
        return ci
