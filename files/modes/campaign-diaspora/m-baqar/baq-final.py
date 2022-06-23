#########################################################
# Main mission class

class BaqarMainMission(OneRaceMainMission):
    def __init__(self):
        OneRaceMainMission.__init__(self, "baqar", [
            BMMFinishWall(), BMMSecurePlanets()
        ])

    def scoring_rules(self):
        return [
            ScoringCampaignTasks([0, 1, 2, 3, 4, 4]),
            ScoringSecurePlanets([2, 4, 6, 8, 10]),
            ScoringWallPercentage([40, 55, 70, 85, 100])
        ]

    def conditions(self): return [
        (WinMissionOnTime, "BaqarMainMission()", 28),
        ManageGrowth,
        EatSignalsOnDiscovery,
        SealTime,
        WallContainment,
        BuildOnlyInside,
        RehostPylonsOnColonization,
        BMDebugging,
    ]

    def do_additional_setup(self):
        game.Stock.Receive(Resource.Cash, 20) # starting bonus
        game.Camera.ZoomTo(16) # zoom out to maximum scale
    
    def things_to_explain(self):
        return [
            ("custom", "special.spacetime_seal"),
            ("custom", "mission.baqar.leave_nobody_behind"),
            ("structure", "battery"),
            ("structure", "powered_pylon"),
        ]
    
    def borrowed_techs(self):
        return {
            "silthid": ["mass_lensing", "extreme_mini", "bioextraction"],
            "dendr": ["xenofoods", "enlightenment", "genesis_cells"],
            "aphorian": ["wave_augmentation", "brain_machine_interface", "hyperdense_arch"],
            "vattori": ["orbital_labs", "quantum_computing", "skill_download"],
        }

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

##########################################################
# Mapgen

class BaqarMissionMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        pass

class BaqarMissionMapgenSettings:
    def create_zones(self):
        settings = MapgenDefaults().create_zones()
        settings["link_values"] = [lv * 1.1 for lv in settings["link_values"]]
        return settings

class NebulaColors(GlobalCondition):
    def activate(self):
        game.CustomData.Set("nebula_colors", Vector2(0.9, 0.08))
        game.CustomData.Set("nebula_brightness", f(0.16))

##########################################################
# Mission goals and scoring

class BMMFinishWall:
    def check_completion(self):
        return game.CustomData.Has("contained")
    def description(self): return LS("mission.baqar.goal.finish_wall")

class BMMSecurePlanets:
    def __init__(self):
        self._required = constants.Int("baq.required_planets")        
    def state(self): return (self.count_planets(), self._required)
    def check_completion(self): return self.state()[0] >= self._required
    def short(self): return "%d/%d:lv2:" % self.state()
    def description(self): return LS("mission.baqar.goal.secure_planets", None, self._required)
    @staticmethod
    def count_planets():
        return sum(1 for p in game.Nodes.PlanetsWithLevelOrHigher(2))

class BMMPowerPylons:
    def __init__(self):
        self._required = constants.Int("baq.required_pylon_power")
    def requires(self): return (0,)
    def state(self): return (self.pylon_percentage(), self._required)
    def check_completion(self): return self.state()[0] >= self._required
    def short(self): return "%d/%d%%" % self.state()
    def description(self): return LS("mission.baqar.goal.power_pylons", None, self._required)
    @staticmethod
    def pylon_percentage():
        powered, total = 0, 0
        for p in game.Nodes.WithType("structure.powered_pylon"):
            total += 1
            if p.Level >= 1: powered += 1
        if total == 0: return 0
        return int(round(powered * 100 / total))

class ScoringSecurePlanets(ScoringFiveRanks):
    def __init__(self, increments):
        base = constants.Int("baq.required_planets")
        self._limits = [0] + [base + i for i in increments]
    def tags(self): return ["mission"]
    def id(self): return "scoring.baqar.secure_planets"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return BMMSecurePlanets.count_planets()
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":planet:"
    def number_text(self, number, rank): return "%d:planet:" % number   

class ScoringWallPercentage(ScoringFiveRanks):
    def __init__(self, thresholds):
        self._limits = [0] + [i for i in thresholds]
    def tags(self): return ["mission"]
    def id(self): return "scoring.baqar.wall_percentage"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        strong, total = 0, 0
        for w in game.Nodes.WithType("structure.rift_wall"):
            if w.CustomData.GetOr("strengthened", False): strong += 1
            total += 1
        percentage = (strong * 100.0 / total) if total > 0 else 0.0
        percentage = int(round(percentage))
        return percentage
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return "%"
    def number_text(self, number, rank): return "%d%%" % number

###############################################################
# Music

class BaqarMusic(MusicProgression):        
    def _check_for_transition(self, prev):
        batteries = game.Nodes.WithType("structure.battery").Count
        walls = game.Nodes.WithType("structure.rift_wall").Count
        lv = 0
        if batteries > 0: lv += 1
        if walls >= 4: lv += 1
        if game.CustomData.Has("contained"): lv = 3
        if prev < lv: return lv

##############################################################
# Pylons

def pylon_model(): return "BigPylon"

def pylon_available(kind):
    # don't allow building more pylons once the hole is contained
    return not game.CustomData.GetOr("contained", False)

def pylon_desc_data(kind):
    return [BUILD_WALL_BONUS, STRENGTHEN_WALL_BONUS]

def pylon_placement():
    max_pylon_distance = constants.Float("pylon.max_distance_from_host")
    return [
        PlaceNear(node_can_host_pylon, max_pylon_distance, LS("structure.pylon.needs_host_planet"), "VPlaceNear", optional = True), 
        PlaceShowRays(pylon_placement_rays)
    ]

def pylon_placement_rays(pos, planned_pylon):
    return possible_pylon_connections(pos)

def pylon_fog_radius(node):
    return constants.Float("pylon.distance_limit")

def pylon_chrome(node):
    host = node.CustomData.GetOr("host", None)
    if host:
        return [{
            "type": NodeChrome.InfluenceLines,
            "influences": [NodeInfluence(node, host, InfluenceType.PotentialInput, InfluenceSentiment.Neutral)]
        }]
    else:
        return []    

def pylon_peers(node):
    return node.CustomData.GetOr("peers", [])
def pylon_walls(node):
    return node.CustomData.GetOr("walls", [])
def pylon_peers_with_walls(node):
    peers = []
    for w in pylon_walls(node):
        for p in wall_ends(w):
            if p != node: peers.append(p)
    return peers
def pylon_peers_without_walls(node):
    peers = set(pylon_peers(node))
    peers.difference_update(pylon_peers_with_walls(node))
    return list(peers)

def pylon_find_reachable(node):
    """Finds all the pylons reachable from this one. Includes the starting pylon."""
    ring = set()
    queue = [node]
    while len(queue) > 0:
        pylon = queue.pop()
        if pylon in ring: continue
        ring.add(pylon)
        peers = pylon_peers(pylon)
        queue += (p for p in peers if not p in ring)
    return ring

def pylon_info_on_upgrades(node):
    return None

def wall_ends(wall):
    return wall.CustomData.Get("ends")

def wall_end_positions(wall):
    ends = wall.CustomData.Get("ends")
    return (ends[0].Position, ends[1].Position)

def pylon_placed(pylon):
    # host
    host = pylon_find_host(pylon.Position)
    if host:
        establish_pylon_host_relation(pylon, host)
    # targets
    target_pylons = possible_pylon_connections(pylon.Position, pylon)
    for other in target_pylons:
        connect = ConsUpdateNodeData()
        connect.append_to_list(pylon, "peers", other)
        connect.append_to_list(other, "peers", pylon)
        connect.issue()
        build_wall = ConsBuildWall(pylon, other)
        commands.IssueScriptedConsequence(build_wall)

def pylon_upgraded(pylon):
    if pylon.Level == 1:
        walls = pylon_walls(pylon)
        update = ConsUpdateNodeData(trigger_changes=True)
        for w in walls:
            if not w.CustomData.GetOr("strenghtened", False):
                update.add(w, "strengthened", True)
                ConsBumpSeal(w, STRENGTHEN_WALL_BONUS).issue()
        update.issue()

def pylon_affects(pylon):
    affected = [other for other in game.Nodes.WithType("structure.powered_pylon") if other != pylon]
    return affected

def obstructs_pylon_connections(o, segment):
    if isinstance(o, INode):
        if o.NodeType == "wormhole": return False
        if o.NodeType.startswith("planet."):
            # reduce obstruction radius for planets
            distance = segment.DistanceTo(o.Position)
            if distance > 0.6: return False
    return True

def possible_pylon_connections(position, pylon_node = None):
    distance_limit = constants.Float("pylon.distance_limit")
    # check if we can support more walls
    free_slots = 2
    # look for possible walls
    others = game.Nodes.WithType("structure.powered_pylon")
    possible_connections = []
    for o in others:
        distance = (o.Position - position).magnitude
        if distance > distance_limit: continue # too far
        if len(pylon_peers(o)) >= 2: continue # nothing can connect to more than two others
        possible_connections.append(o)
    # pick which connections work
    possible_connections.sort(key=lambda p: (position - p.Position).sqrMagnitude)
    indirectly_connected = set()
    pylons_to_connect_to = []
    for other in possible_connections:
        if free_slots <= 0: break
        if other in indirectly_connected: continue
        # obstructed?
        segment = CollidingSegment(position, other.Position)
        obstructions = list(o for o in Obstruction.CheckForObstructionsNow(world, pylon_node, segment) if o.Owner != other)
        filtered_obstructions = [o for o in obstructions if obstructs_pylon_connections(o.Owner, segment)]
        if len(filtered_obstructions) > 0: continue
        # nope, everything works
        pylons_to_connect_to.append(other)
        indirectly_connected.add(other)
        indirectly_connected.update(pylon_peers(other))
        free_slots -= 1
    return pylons_to_connect_to

class ConsBuildWall:
    def __init__(self, node, other):
        self._a, self._b = node, other

    def apply(self):
        # structure build
        midpoint = (self._a.Position + self._b.Position) * f(0.5)
        self._wall = world.Add(Structure(midpoint, StructureKind.All["rift_wall"]))
        self._wall.CustomData.Set("ends", [self._a, self._b])
        strengthened = self._a.Level > 0 or self._b.Level > 0
        self._wall.CustomData.Set("strengthened", strengthened)
        self._wall.AddObstruction(LinearObstruction(self._a.Position - midpoint, self._b.Position - midpoint))
        self._wall.TriggerChange()
        # "own" the wall from the pylons
        update = ConsUpdateNodeData()
        update.append_to_list(self._a, "walls", self._wall)
        update.append_to_list(self._b, "walls", self._wall)
        update.issue()
        # fake the trigger so other things can normally react to wall builds
        game.Triggers.ActivateFromScript(Trigger.StructureBuilt, {
            "node": self._wall, "structures": List[INode]([self._wall]), "count": 1
        })
        # grant some time whenever a wall is constructed
        time_bonus = BUILD_WALL_BONUS
        if strengthened: time_bonus += STRENGTHEN_WALL_BONUS
        ConsBumpSeal(self._wall, time_bonus).issue()

    def revert(self):
        # destroy the wall
        self._wall.Discard()

def unpowered_pylons():
    return sum(1 for p in game.Nodes.WithType("structure.powered_pylon") if p.Level == 0)

class UnpoweredPylonPenalty:
    def name(self): return LS("quality.unpowered_pylon")
    def desc(self): return LS("quality.unpowered_pylon.desc")
    def effects(self, node):
        if node.Level == 1: return
        penalty = unpowered_pylons()
        return [ResourceFlow.Cash(-penalty, FlowCategory.StructureUpkeep)]

###################################################
# Pylon hosting

def node_can_host_pylon(node):
    if not node.NodeType.startswith("planet."): return False
    if node.Level < 0: return False
    return True

def pylon_find_host(pylon_pos):
    max_pylon_distance = constants.Float("pylon.max_distance_from_host")
    candidates = list(n for n in game.Nodes.Within(pylon_pos, max_pylon_distance) if node_can_host_pylon(n))
    if len(candidates) == 0:
        return None
    if len(candidates) > 1:
        candidates.sort(key=lambda n: (pylon_pos - n.Position).sqrMagnitude)
    return candidates[0]

def establish_pylon_host_relation(pylon, host):
    current_pylons = host.CustomData.GetOr("pylons", [])
    current_dependent = host.CustomData.GetOr("dependent_nodes", [])
    cons = ConsUpdateNodeData()
    cons.add(pylon, "host", host)
    cons.add(host, "pylons", current_pylons + [pylon])
    cons.add(host, "dependent_nodes", current_dependent + [pylon])
    cons.issue()

class PylonUpkeep:
    UPKEEPS_BY_LEVEL = [10, 6, 3, 1, 0]
    def name(self): return LS("structure.pylon.upkeep")
    def desc(self): return LS("structure.pylon.upkeep.desc")
    def effects(self, node):
        if node.Level == 1: return
        host = node.CustomData.GetOr("host", None)
        host_level = host.Level if host else 0
        host_level = clamp(0, len(self.UPKEEPS_BY_LEVEL) - 1, host_level)
        upkeep = self.UPKEEPS_BY_LEVEL[host_level]  
        return [ResourceFlow.Cash(-upkeep, FlowCategory.StructureUpkeep)]

class RehostPylonsOnColonization(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.PlanetColonized, self.when_colonized)
    
    def when_colonized(self, data):
        planet = data["node"]
        max_pylon_distance = constants.Float("pylon.max_distance_from_host")
        pylons_nearby = [n for n in game.Nodes.Within(planet, max_pylon_distance) if n.NodeType == "structure.pylon"]
        ConsRefreshNode(*pylons_nearby).issue()
        for pylon in pylons_nearby:
            if pylon.CustomData.Has("host"): continue
            establish_pylon_host_relation(pylon, planet)
        ConsRefreshNode(*pylons_nearby).issue()

#####################################################
# Seal

def seal_fog_radius(seal): return constants.Distance("accessible_space.radius")

def seal_tooltip(me, original):
    active = me.CustomData.Get("active")
    if not active:
        return [original, LS("structure.seal.inactive_tooltip")]
    time_left = me.CustomData.Get("months_left")
    return [original, LS("structure.seal.time_left", None, time_left)]

def seal():
    try:
        return game.Nodes.FirstWithType("structure.spacetime_seal")
    except:
        return None

class ReplaceWormholeWithSeal(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapGenerated, self.on_map_generated)

    def on_map_generated(self, _):
        wormhole = game.Nodes.FirstWithType("wormhole")
        wormhole.Discard()
        seal = world.Add(Structure(wormhole.Position, StructureKind.All["spacetime_seal"]))
        seal.CustomData.Set("active", True)
        seal.CustomData.Set("batteries", 0)
        seal.CustomData.Set("months_left", constants.Int("seal.free_months"))
        seal.CustomData.Set("inactive_years", 0)

BUILD_WALL_BONUS = 6
STRENGTHEN_WALL_BONUS = 4
SHUNT_BONUS = 30
class SealTime(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.TimePassed, self.when_time_passes)
        self.react_to(Trigger.NewTurn, self.when_year_passes, 600)
    
    def when_time_passes(self, data):
        s = seal()
        months = data["months"]
        months_left = s.CustomData.Get("months_left")
        message_shown = months_left > 12 and (months_left - months) <= 12
        was_active = s.CustomData.Get("active")
        if was_active:
            seal_broken = months_left <= months
            update = ConsUpdateNodeData(trigger_changes=True)
            update.dec(s, "months_left", months)
            update.add(s, "active", not seal_broken)
            update.when_done_or_reverted(lambda: self.show_message_then_refresh(message_shown))
            if seal_broken:
                update.when_done_or_reverted(self.update_batteries)
            update.issue()

    def when_year_passes(self, data):
        s = seal()
        was_active = s.CustomData.Get("active")
        if not was_active:
            update = ConsUpdateNodeData(trigger_changes=True)
            update.inc(s, "inactive_years")
            update.issue()

    def update_batteries(self):
        for b in game.Nodes.WithType("structure.battery"):
            b.TriggerChange()

    def show_message_then_refresh(self, show_message):
        if show_message:
            self.post_message(self._msg_seal_breaking)
        self.signal_change()
    
    def _msg_seal_breaking(self):                
        seal = game.Nodes.FirstWithType("structure.spacetime_seal")
        msg = MessageContent()        
        # text
        msg.Important = True
        msg.ShortText = LS("structure.seal.msg_about_to_break")
        msg.Picture = "situation"
        # reactions
        def jump():
            game.Camera.JumpTo(seal)
            return MessageAction.Dismiss
        msg.WhenClicked = jump
        msg.WhenDismissed = lambda: MessageAction.Dismiss        
        msg.DiscardCondition = lambda: seal.CustomData.GetOr("months_left", 0) > 12
        return msg

    def info(self):
        s = seal()
        active = s.CustomData.Get("active")
        months_left = s.CustomData.Get("months_left")
        if not active: return None
        ci = CondInfo()
        ci.Important = True
        ci.Icon = "icon_seal_time"
        ci.Priority = 0
        short = "%dmo" % months_left
        if months_left <= 12:
            short = styled(short, "Bad")
        ci.ShortText = short
        ci.FullDescription = LS("structure.seal.time_left.long", None, months_left)
        tooltip_header = styled(LS("structure.spacetime_seal"), "TooltipHeader")
        ci.Tooltip = RichText.Paragraphs([tooltip_header, styled(ci.FullDescription, "TooltipLight")])
        return ci

#########################################################
# Battery

def battery_upgraded(battery):
    return
    if battery.Level == 1:
        ConsBumpSeal(battery, 16).issue()        

def battery_placed(battery):
    planet = game.Nodes.ClosestWith(battery.Position, 
        f(BATTERY_ORBIT + 0.3), 
        battery_host_condition())
    ConsBumpSeal(battery, SHUNT_BONUS).issue()
    update = ConsUpdateNodeData(trigger_changes=True)
    update.inc(seal(), "batteries")
    update.add(planet, "battery", battery)
    update.issue()

BATTERY_ORBIT = 1.35
def battery_placement():
    distance = constants.Distance("battery.max_distance")
    s = seal()
    node_cond = battery_host_condition()
    return [
        PlaceNear(lambda n: n == s, distance, LS("structure.battery.problem.near_seal"), "VPlaceNear"),
        PlaceNear(node_cond, f(BATTERY_ORBIT + 0.05), LS("structure.battery.problem.near_planet"), "VPlaceNear"),
        ScriptedPlacement(SnapToOrbit(BATTERY_ORBIT, node_cond))
    ]

def battery_obstructed_by(ps, node):
    viable = isinstance(node, Planet) and node.Level >= 2 and node.CustomData.GetOr("battery", None) is None
    return not viable

def battery_host_condition():
    magnitude = constants.Distance("battery.max_distance") + 0.5
    sqr_mag = magnitude * magnitude
    def cond(n):
        return isinstance(n, Planet) and n.Position.sqrMagnitude <= sqr_mag and n.Level >= 2 and n.CustomData.GetOr("battery", None) is None
    return cond

def battery_can_be_built(kind):
    return seal().CustomData.Get("active")

def battery_desc_data(kind): return [SHUNT_BONUS]

def battery_base_cost(kind):
    return battery_dynamic_cost(None)

def battery_dynamic_cost(ps):
    s = seal()
    existing_batteries = s.CustomData.Get("batteries") if s else 0
    base_cost = constants.FloatAt("battery.costs", existing_batteries, saturate=True)
    difficulty_multiplier = constants.Float("battery.costs.multiplier")
    mn, mx = constants.Distance("battery.min_distance"), constants.Distance("battery.max_distance")
    distance = (s.Position - ps.Position).magnitude if ps else 0
    distance_factor = inverse_lerp_clamped(mn, mx, distance)
    distance_multiplier = lerp(1.0, constants.Float("battery.cost_increase"), distance_factor)
    final_cost = int(round(base_cost * difficulty_multiplier * distance_multiplier))
    return CompoundCost.Parse("%d$, 1mo" % final_cost)

def battery_chrome(node):
    seal_active = seal().CustomData.Get("active")
    if seal_active:
        return [{
            "type": NodeChrome.InfluenceLines,
            "influences": [NodeInfluence(node, seal(), InfluenceType.PotentialOutput, InfluenceSentiment.Neutral)]
        }]
    else:
        return []

class ConsBumpSeal:
    def __init__(self, node, months):
        self._node = node
        self._months = months
        self._bumped = False

    def apply(self):
        s = seal()
        if not s.CustomData.Get("active"): return
        s.CustomData.Inc("months_left", self._months)
        if self._node is not None:
            HVPoppingInfo.Spawn(self._node).Show("+%d:time:" % self._months)
        s.TriggerChange()
        conditions.Get("SealTime()").PythonObject.signal_change()
        self._bumped = True

    def revert(self):
        if not self._bumped: return
        s = seal()
        s.CustomData.Dec("months_left", self._months)
        s.TriggerChange()
        conditions.Get("SealTime()").PythonObject.signal_change()

    def issue(self):
        commands.IssueScriptedConsequence(self)

#########################################################
# Hole rules

class ManageGrowth(GlobalCondition):
    GROWTH_DIFFICULTY_MULTIPLIER = [0.86, 0.95, 1.0, 1.0]
    
    def __init__(self):
        self._protected_growth = constants.Float("hole.protected_growth")
        self._unprotected_growth = constants.Float("hole.unprotected_growth")
        self._growth_increase = constants.Float("hole.growth_increase_per_year")
        self._historical_influence = []

    def activate(self):
        self._hole = None
        self.react_to(Trigger.NewTurn, self.actually_grow, 700)
        self.react_to(Trigger.StructureBuilt, self.when_structure_built)
        # initial 'update' to get the projection right
        future_growth = self.calculate_growth(self.hole().Points, self.growth_speed())
        self.hole().ResizeTo(self.hole().Points, future_growth, False)

    def when_structure_built(self, data):
        if data["node"].NodeType == "structure.rift_wall":
            self.recalculate()

    def growth_speed(self):
        s = seal()
        seal_active = s.CustomData.Get("active")
        if seal_active: return -self._protected_growth
        years_inactive = s.CustomData.Get("inactive_years")
        growth = self._unprotected_growth
        growth += self._growth_increase * years_inactive
        return -growth

    def hole(self):
        if not self._hole:
            self._hole = game.Nodes.FirstWithType("special.hole")
        return self._hole

    def calculate_growth(self, original_points, how_much):
        how_much = f(how_much)
        retries = 50
        pos = self.hole().Position
        point_count = len(original_points)
        distances = [p.magnitude for p in original_points]
        min_distance = min(distances)
        max_distance = max(distances)
        mid_distance = (min_distance + max_distance) * 0.5
        spread = max_distance - mid_distance
        # prevent from collapsing to nothing, bugs
        slow_down = inverse_lerp_clamped(10.0, 20.0, mid_distance) * 0.99 + 0.01
        how_much = how_much * f(slow_down)
        history = self.hole().CustomData.GetOr("historical_wall_influence", None)
        history = list(history) if history else [1.0] * point_count # fresh copy
        while retries > 0:
            retries -= 1
            points = list(original_points)
            rng = Randomness.SeededRNG("hole_grow", game.Time.NormalizedTurn + retries * 100)
            noise_x = 0.0
            noise_xstep = 1.0 / (len(points) - 1)
            noise_y = Randomness.Float(rng, 0.0, 1.0)
            i = 0
            failed = False
            modulo = point_count - 1
            backtracks = 0
            while i < modulo:
                pt = points[i]
                growth_dir = pt.normalized
                distance_factor = clamp(0.2, 1.8, 1.0 + game.Noise.GetNoise(noise_x, noise_y) * 5.0)
                # take walls into account (and historical wall influence)
                wall_1 = min(history[i], self.wall_influence(pos + pt))
                history[i] = wall_1
                if wall_1 > 0.0:
                    distance_factor *= wall_1
                    angle = 0#Randomness.Float(rng, -3, 3)
                    growth_v = rotate_vector(growth_dir, angle) * f(distance_factor) * how_much
                    # smoothing out to prevent issues
                    balancing = 1.0 + (distances[i] - mid_distance) / spread * 0.32
                    growth_v *= f(balancing)
                    # check walls at the future point as well, take the max influence
                    wall_2 = self.wall_influence(pos + pt + growth_v)
                    if wall_2 < wall_1:
                        growth_v *= f(wall_2 / wall_1)
                        history[i] = wall_2
                    # finally done
                    new_pt = pt + growth_v
                else:
                    new_pt = pt
                # check correctness of angles (do not mess up the triangle fan)
                previous_pt = points[(i + modulo - 1) % modulo]
                next_pt = points[(i + 1) % modulo]
                previous_normal = Vector2(previous_pt.y, -previous_pt.x)
                next_normal = Vector2(next_pt.y, -next_pt.x)
                if Vector2.Dot(new_pt, previous_normal) < 0:
                    # we went behind the previous point in angle - not good, let's retry from the previous point
                    backtracks += 1
                    if backtracks > 100:
                        failed = True
                        break
                    # backtrack to previous point (if possible)
                    if i > 0:
                        points[i-1] = original_points[i-1]
                        if i-1 == 0:
                            points[len(points)-1] = original_points[len(original_points)-1]                    
                        i -= 1                    
                        noise_x -= noise_xstep
                    continue
                if Vector2.Dot(new_pt, next_normal) > 0:
                    # we went ahead of the next point in angle - let's retry this point until we get it right
                    continue
                # point ok, remember the change
                points[i] = new_pt
                if i == 0: 
                    points[-1] = new_pt
                i += 1
                noise_x += noise_xstep
            # done with the loop, did it complete?
            if not failed:
                history_update = ConsUpdateNodeData().add(self.hole(), "historical_wall_influence", history)
                history_update.issue()
                return points
        raise Exception("Unable to grow.")

    wall_checks = set()
    def wall_influence(self, point):
        wall_checks = self.wall_checks
        wall_checks.clear()
        dist_sq = 100
        for node in game.Nodes.Within(point, f(6)):
            if node.NodeType == "structure.rift_wall":
                n = node
                if not n in wall_checks:
                    wall_checks.add(n)
                    ends = wall_end_positions(n)
                    d = Intersecting.DistancePointToSegmentSquared(point, ends[0], ends[1])
                    if d < dist_sq:
                        dist_sq = d
            elif node.NodeType == "structure.powered_pylon":
                for n in pylon_walls(node):
                    if not n in wall_checks:
                        wall_checks.add(n)
                        ends = wall_end_positions(n)
                        d = Intersecting.DistancePointToSegmentSquared(point, ends[0], ends[1])
                        if d < dist_sq:
                            dist_sq = d
        if dist_sq <= 1: return 0.0
        if dist_sq >= 25: return 1.0
        return inverse_lerp_clamped(1, 5, math.sqrt(dist_sq))

    def recalculate(self):
        growth = self.calculate_growth(self.hole().Points, self.growth_speed())
        commands.IssueScriptedConsequence(ConsGrowHole(self.hole(), None, growth))
        
    def actually_grow(self, data):
        hole_pos = self.hole().Position
        grown_points = self.hole().ProjectedPoints
        future_growth = self.calculate_growth(grown_points, self.growth_speed())        
        commands.IssueScriptedConsequence(ConsGrowHole(self.hole(), grown_points, future_growth))
        commands.IssueScriptedConsequence(DestroyConsumedObjects(hole_pos + pt for pt in grown_points))

class BMDebugging(GlobalCondition):
    def debug_commands(self, position):
        yield {
            "text": "debug: wall influence here",
            "action": lambda: self.wall_at(position)
        }
    
    def wall_at(self, position):
        mg = conditions.Get("ManageGrowth()").PythonObject
        log("Wall influence at %s -> %f" % (position, mg.wall_influence(position)))

############################################################################
# Hole generation

class HoleMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)
        self.react_to(Trigger.MapGenerated, self.on_map_generated)
    def on_map_setup(self, data):
        gen = data["generation"]
        game.CustomData.Set("hole_position", Vector2.zero)
        hole_size = constants.Float("accessible_space.radius") * constants.Float("distance.scale")
        gen.Refinement("after_planet_types", 1000, refinement_generate_hole(Vector2(hole_size, hole_size), 1.25))
        gen.Refinement("after_planet_types", 1005, refine_remove_signals_in_hole(inverted = True))
    def on_map_generated(self, data):
        instantiate_hole()

def instantiate_hole():
    pos = game.CustomData.Get("hole_position")
    points = game.CustomData.Get("hole_points")
    game.CustomData.Clear("hole_points")
    game.CustomData.Clear("hole_position")
    world.Add(GrowingHole(pos, points, GrowingHole.HoleType.Inverted))

####################################################
# Containment

class WallContainment(GlobalCondition):
    def activate(self):
        self._poly = None
        self.recreate_polygon()
        self.react_to(Trigger.StructureBuilt, self.when_structure_built)
        self.react_to(Trigger.AfterNodeDiscovered, self.when_node_discovered)

    def when_structure_built(self, data):
        node = data["node"]
        if node.NodeType == "structure.rift_wall":
            self.perform_check(wall_ends(node)[0])

    def when_node_discovered(self, data):
        if not self._poly: return
        n = data["node"]
        if not n.NodeType.startswith("planet."): return
        n.CustomData.Set("inside", self._poly.ContainsPoint(n.Position))

    def wall_exists(self):
        return self._poly is not None

    def is_inside_wall(self, pt):
        if not self._poly: return False
        return self._poly.ContainsPoint(pt)

    def perform_check(self, start_pylon):
        # already done?
        if game.CustomData.Has("contained"): return
        poly = self.find_loop_polygon(start_pylon)
        if poly:
            commands.IssueScriptedConsequence(ConsEstablishPoly(self, poly))
            
    def recreate_polygon(self):
        if not game.CustomData.Has("contained"): return
        pylons = game.Nodes.WithType("structure.powered_pylon")
        for p in pylons:
            poly = self.find_loop_polygon(p)
            if poly: break
        self._poly = poly


    def find_loop_polygon(self, start_pylon):
        # see if the walls connected to this pylon form a closed loop
        visited_in_order = []
        visited = set()
        coming_from = None
        node = start_pylon
        while not node in visited:
            visited.add(node)
            visited_in_order.append(node)
            peers = pylon_peers(node)
            if len(peers) <= 1:
                # all nodes need two peers in a closed loop
                return
            if peers[0] != coming_from:
                coming_from, node = node, peers[0]
            else:
                coming_from, node = node, peers[1]
        # ok, we have a loop!
        points = [v.Position for v in visited_in_order]
        points.append(points[0]) # close loop
        poly = CollidingPolygon(points)
        return poly

class ConsEstablishPoly:
    def __init__(self, containment, poly):
        self._containment = containment
        self._poly = poly

    def apply(self):
        self._containment._poly = self._poly
        update = ConsUpdateNodeData().add(game, "contained", game.Time.NormalizedTurn)
        self.assign_planet_information(update)
        update.issue()
        self.lose_game_if_anything_outside()

    def revert(self):
        self._containment._poly = None
    
    def assign_planet_information(self, update):
        for p in every(Planet):
            inside = self._poly.ContainsPoint(p.Position)
            update.add(p, "inside", inside)

    def lose_game_if_anything_outside(self):
        excluded_types = set(["structure.powered_pylon", "structure.spacetime_seal", "structure.rift_wall", "wormhole", "special.hole", "special.hole_stretch"])
        def node_checked(node):
            if node.NodeType in excluded_types: return False
            return node.HasIndustry and not node.Industry.Kind.IsHidden            
        for n in every(Node):
            if not node_checked(n): continue
            if not self._poly.ContainsPoint(n.Position):
                commands.IssueScriptedConsequence(LoseForStuffOutside(n))
                return

class BuildOnlyInside(GlobalCondition):
    def __init__(self):
        self._containment = None

    def activate(self):
        game.Qualities.EstablishGlobally(QPreventOutsideActions)

    def global_structure_placement_rules(self, kind):
        return [ScriptedPlacement(self)]

    def is_permitted(self, pos, ps):
        self._containment = self._containment or conditions.Get("WallContainment()").PythonObject
        wall_problem = self._containment.wall_exists() and not self._containment.is_inside_wall(pos) 
        if wall_problem:
            return Permission.No(LS("structure.problem.outside_wall"))
        return Permission.Yes()

class QPreventOutsideActions:
    def __init__(self):
        self._containment = None
    
    def hidden(self, node): return True
    def applies(self, node): return True
    def effects(self, node):
        return [ActionPermission.Calling(self.action_only_inside)]

    def action_only_inside(self, action):
        self._containment = self._containment or conditions.Get("WallContainment()").PythonObject
        node = action.Target
        wall_problem = self._containment.wall_exists() and not self._containment.is_inside_wall(node.Position)
        if wall_problem:
            return Permission.No(LS("action.problem.outside_wall"))
        return Permission.Yes()

class LoseForStuffOutside:
    def __init__(self, what):
        self._what = what

    def apply(self):
        empire.WinningLosing.EndScenario({
            "outcome": "loss", "defeat": True,
            "defeat_icon": "icon_mission_failed",
            "heading": LS("menus.game_end.mission_failed.header"),
            "comment": LS("mission.baqar.goal.contained"),
            "shown_elements": ["undo"],
            "focus_on": self._what
        })

    def revert(self):
        pass