#########################################################
# Main mission structure

class HoleMainMission(MainMission):
    def __init__(self):
        MainMission.__init__(self, "hole", [HMMContainTheHole()])

    @staticmethod
    def get():
        return game.Conditions.Get("HoleMainMission()").PythonObject

    def scenario_id(self): return "m-hole"
    def scoring_rules(self):
        return [
            ScoringSupportedPylons(),
            ScoringCampaignTime(self, [1000, 24, 23, 22, 21, 20])
        ]
    def conditions(self): return [
        (ManageGrowth,),
        (HoleMusic,),
        (CheckContainment,),
        (EatSignalsOnDiscovery,),
        (RehostPylonsOnColonization,),
        (WinMissionOnTime, "HoleMainMission()", 25),
    ]

    def things_to_explain(self):
        return [
            ("custom", "mission.hole.loss_rule"), 
            ("structure", "pylon")
        ]
    def perks_available(self):
        return ["luxury", "novelty_traders", "miners", "prospectors", "social_capital", "nutrition", "space_architects", "efficient", "careful_observation", "curiosity"]
    
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

class HMMContainTheHole:
    def check_completion(self):
        return game.CustomData.Has("contained")
    def description(self): return LS("mission.hole.stage.contain")

class CheckContainment(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.StructureBuilt, self.when_structure_built)

    def when_structure_built(self, data):
        if data["node"].NodeType == "structure.rift_wall":
            self.perform_check(wall_ends(data["node"])[0])

    def perform_check(self, start_pylon):
        # already known?
        if game.CustomData.Has("contained"): return
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
        # check if the hole is contained within
        # we just have to check if the center is inside - due to other rules (walls cannot cross the hole)
        # this guarantees the entire hole is inside
        points = [v.Position for v in visited_in_order]
        points.append(points[0]) # close loop
        poly = CollidingPolygon(points)
        if poly.ContainsPoint(self.hole().Position):
            self.store_win()

    def hole(self):
        return game.Nodes.FirstWithType("special.hole")

    def store_win(self):
        ConsUpdateNodeData().add(game, "contained", game.Time.NormalizedTurn).issue()
        
#########################################################
# Story, music and info

class HoleMusic(MusicProgression):
    PROGRESS_THRESHOLD = 4
    def _check_for_transition(self, prev):
        wall_count = sum(1 for w in game.Nodes.WithType("structure.rift_wall"))
        mission_complete = HoleMainMission.get().finished_on() is not None
        lv = 0
        if wall_count >= 1: lv += 1
        if wall_count >= 6: lv += 1
        if mission_complete: lv += 1
        if prev < lv: return lv

#########################################################
# Scoring

class ScoringSupportedPylons(ScoringFiveRanks):
    def id(self): return "scoring.hole.supported_pylons"

    def base_number(self):
        pylons = list(game.Nodes.WithType("structure.pylon"))
        endgame_rules = game.CustomData.GetOr("contained", False)
        if endgame_rules:
            # only count the biggest ring of pylons, all the rest are irrelevant
            remaining = list(pylons)
            rings = []
            while len(remaining) > 0:
                reachable = pylon_find_reachable(remaining[0])
                for rp in reachable:
                    remaining.remove(rp)
                rings.append(reachable)
            # pick the biggest ring
            biggest_ring = max(rings, key=len)
            pylons = biggest_ring
        # now, calculate the percentage
        supported_pylon_count = sum(1 for p in pylons if self.pylon_supported(p))
        pylon_count = len(pylons)
        if pylon_count == 0: return 0
        return round(supported_pylon_count * 100.0 / pylon_count)
    
    @staticmethod
    def pylon_supported(pylon):
        host = pylon.CustomData.GetOr("host", None)
        return host and host.Level >= 2

    def rank_limits(self): return [0, 45, 55, 65, 75, 85]
    def rank_text(self, number): return "%d%%" % number
    def number_text(self, number, rank): return "%d%%" % number if number > 0 else "-"
    def tags(self): return ["mission"]

#########################################################
# Hole rules

class ManageGrowth(GlobalCondition):
    GROWTH_DIFFICULTY_MULTIPLIER = [0.86, 0.95, 1.0, 1.0]

    def __init__(self):
        self._base_growth = constants.Float("hole.starting_growth")
        self._growth_increment = constants.Float("hole.yearly_increment")

    def activate(self):
        self._hole = None
        self.react_to(Trigger.NewTurn, self.actually_grow)
        self.react_to(Trigger.StructureBuilt, self.when_structure_built)
        # initial 'update' to get the projection right
        future_growth = self.calculate_growth(self.hole().Points, self.growth_speed())
        self.hole().ResizeTo(self.hole().Points, future_growth, False)

    def when_structure_built(self, data):
        if data["node"].NodeType == "structure.rift_wall":
            self.recalculate()

    def growth_speed(self):
        calculated = self._base_growth + game.Time.NormalizedTurn * self._growth_increment
        diff = clamp(0, 3, difficulty_ordinal())
        modified = self.GROWTH_DIFFICULTY_MULTIPLIER[diff] * calculated
        return modified

    def hole(self):
        if not self._hole:
            self._hole = game.Nodes.FirstWithType("special.hole")
        return self._hole

    def calculate_growth(self, original_points, how_much):
        how_much = f(how_much)
        retries = 50
        pos = self.hole().Position
        while retries > 0:
            retries -= 1
            points = list(original_points)
            point_count = len(points)
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
                distance_factor = max(0.2, 1.0 + game.Noise.GetNoise(noise_x, noise_y) * 5.0)
                distance_factor *= self.wall_influence(pos + pt)
                angle = Randomness.Float(rng, -3, 3)
                growth = rotate_vector(growth_dir, angle) * f(distance_factor) * how_much
                new_pt = pt + growth
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
                return points
        raise Exception("Unable to grow.")

    def wall_influence(self, point):
        def distance_to_wall(w):
            ends = wall_end_positions(w)
            return Intersecting.DistancePointToSegmentSquared(point, ends[0], ends[1])
        closest_wall = game.Nodes.ClosestOfType(point, "structure.rift_wall", f(4.25), distance_to_wall)
        distance_to_wall = 2
        if closest_wall:
            ends = wall_end_positions(closest_wall)
            distance_to_wall = Intersecting.DistancePointToSegment(point, ends[0], ends[1])
        return inverse_lerp_clamped(0.35, 1.5, distance_to_wall)

    def recalculate(self):
        growth = self.calculate_growth(self.hole().Points, self.growth_speed())
        commands.IssueScriptedConsequence(ConsGrowHole(self.hole(), None, growth))
        
    def actually_grow(self, data):
        hole_pos = self.hole().Position
        grown_points = self.hole().ProjectedPoints
        future_growth = self.calculate_growth(grown_points, self.growth_speed())        
        commands.IssueScriptedConsequence(ConsGrowHole(self.hole(), grown_points, future_growth))
        commands.IssueScriptedConsequence(DestroyConsumedObjects(hole_pos + pt for pt in grown_points))

#########################################################
# Wall structures

def pylon_available(kind):
    # don't allow building more pylons once the hole is contained
    return not game.CustomData.GetOr("contained", False)

def pylon_placement():
    max_pylon_distance = constants.Float("pylon.max_distance_from_host")
    return [
        PlaceNear(node_can_host_pylon, max_pylon_distance, LS("structure.pylon.needs_host_planet"), "VPlaceNear", optional = True), 
        PlaceShowRays(pylon_placement_rays)
    ]

def pylon_obstructed_by(planned, model):
    if isinstance(model, INode) and node_can_host_pylon(model):
        distance = (planned.Position - model.Position).magnitude
        return distance < 0.6
    else:
        return True

def pylon_connectivity(node, other):
    return NodeConnectivity.Rejects(LS("structure.pylon.no_slipways"))

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
    host = node.CustomData.GetOr("host", None)
    header = LS("structure.pylon.current_upkeep.header")
    info = []
    if not host:
        upkeep = -PylonUpkeep.UPKEEPS_BY_LEVEL[0]
        penalty = -UnsupportedPylonPenalty.penalty_for(node)
        info.append(LS("structure.pylon.please_support", None, upkeep + penalty))
    else:
        upkeep = -PylonUpkeep.UPKEEPS_BY_LEVEL[clamp(0, 4, host.Level)]
        info.append(LS("structure.pylon.supported_by", None, host.Name, upkeep))
        if host.Level < 4:
            improved_upkeep = -PylonUpkeep.UPKEEPS_BY_LEVEL[host.Level + 1]
            info.append(LS("structure.pylon.upkeep_upgrade", None, host.Level + 1, improved_upkeep))
    return InfoBlock(header, info)

def wall_ends(wall):
    return wall.CustomData.Get("ends")

def wall_end_positions(wall):
    ends = wall.CustomData.Get("ends")
    return (ends[0].Position, ends[1].Position)

def pylon_placed(pylon):
    # remember the host <-> pylon relationship
    host = pylon_find_host(pylon.Position)
    if host:
        establish_pylon_host_relation(pylon, host)
    # add rift walls
    establish_pylon_connections(pylon)

def pylon_affects(pylon):
    affected = [other for other in game.Nodes.WithType("structure.pylon") if other != pylon and other.CustomData.GetOr("host", None) is None]
    return affected

def establish_pylon_host_relation(pylon, host):
    current_pylons = host.CustomData.GetOr("pylons", [])
    current_dependent = host.CustomData.GetOr("dependent_nodes", [])
    cons = ConsUpdateNodeData()
    cons.add(pylon, "host", host)
    cons.add(host, "pylons", current_pylons + [pylon])
    cons.add(host, "dependent_nodes", current_dependent + [pylon])
    cons.issue()

def establish_pylon_connections(node):
    target_pylons = possible_pylon_connections(node.Position, node)
    for other in target_pylons:
        commands.IssueScriptedConsequence(BuildWall(node, other))

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
    others = game.Nodes.WithType("structure.pylon")
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

class BuildWall:
    def __init__(self, node, other):
        self._a, self._b = node, other

    def apply(self):
        # pylon data update
        self._a.CustomData.Set("peers", pylon_peers(self._a) + [self._b])
        self._b.CustomData.Set("peers", pylon_peers(self._b) + [self._a])
        # structure build
        midpoint = (self._a.Position + self._b.Position) * f(0.5)
        self._wall = world.Add(Structure(midpoint, StructureKind.All["rift_wall"]))
        self._wall.CustomData.Set("ends", [self._a, self._b])
        self._wall.AddObstruction(LinearObstruction(self._a.Position - midpoint, self._b.Position - midpoint))
        self._wall.TriggerChange()
        # fake the trigger so other things can normally react to wall builds
        game.Triggers.ActivateFromScript(Trigger.StructureBuilt, {
            "node": self._wall, "structures": List[INode]([self._wall]), "count": 1
        })

    def revert(self):
        # destroy the wall
        self._wall.Discard()
        # revert the peer update
        a_peers, b_peers = pylon_peers(self._a), pylon_peers(self._b)
        a_peers.remove(self._b)
        b_peers.remove(self._a)
        self._a.CustomData.Set("peers", a_peers)
        self._b.CustomData.Set("peers", b_peers)

def unhosted_pylon_count():
    return sum(1 for p in game.Nodes.WithType("structure.pylon") if p.CustomData.GetOr("host", None) is None)

class PylonUpkeep:
    UPKEEPS_BY_LEVEL = [10, 6, 3, 1, 0]
    def name(self): return LS("structure.pylon.upkeep")
    def desc(self): return LS("structure.pylon.upkeep.desc")
    def effects(self, node):
        host = node.CustomData.GetOr("host", None)
        host_level = host.Level if host else 0
        host_level = clamp(0, len(self.UPKEEPS_BY_LEVEL) - 1, host_level)
        upkeep = self.UPKEEPS_BY_LEVEL[host_level]  
        return [ResourceFlow.Cash(-upkeep, FlowCategory.StructureUpkeep)]

class UnsupportedPylonPenalty:
    UPKEEP_PER_UNSUPPORTED = [4, 4, 3, 2]
    def name(self): return LS("quality.unsupported_pylon_upkeep")
    def desc(self): return LS("quality.unsupported_pylon_upkeep.desc", None, -self.penalty_per_pylon())
    @staticmethod
    def penalty_per_pylon():
        diff = clamp(0, 3, difficulty_ordinal())
        return UnsupportedPylonPenalty.UPKEEP_PER_UNSUPPORTED[diff]
    @staticmethod
    def penalty_for(node):
        penalty = (unhosted_pylon_count() - 1) * UnsupportedPylonPenalty.penalty_per_pylon()
        return penalty
    def effects(self, node):
        host = node.CustomData.GetOr("host", None)
        if host is not None: return
        penalty = self.penalty_for(node)
        return [ResourceFlow.Cash(-penalty, FlowCategory.StructureUpkeep)]

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

#########################################################
# Map generation

class HoleStartingResources(GlobalCondition):
    CASH = 0
    SCIENCE = 0

    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.grant_resources)

    def grant_resources(self, _):
        game.Stock.Receive(Resource.Cash, self.CASH)
        game.Stock.Receive(Resource.Science, self.SCIENCE)

class HoleMapgenSettings:
    def create_zones(self):
        distance_scale = constants.Float("distance.scale")
        # determine the position for the hole
        hole_dimensions = Vector2(constants.Float("hole.width"), constants.Float("hole.height"))        
        rng = game.RNG("mapgen")
        angle = Randomness.Float(rng, 0, math.pi * 2)
        hole_dir = Vector2(math.cos(angle), math.sin(angle))
        hole_pos = hole_dir * constants.Float("hole.distance_from_start")
        hole_pos = Vector2.Scale(hole_pos, hole_dimensions)
        game.CustomData.Set("hole_position", hole_pos)
        # create zones that are bigger and a bit better than default
        settings = MapgenDefaults().create_zones()
        hole_width = min([hole_dimensions.x, hole_dimensions.y]) / distance_scale
        point_counts = [0, 65, 100, 100, 83, 81, 73, 56] # total signal counts in each zone
        planet_counts = [48, 72, 66, 50, 55, 52, 38]
        zones = Zones.circle(hole_pos, hole_width, 24 + hole_width, point_counts)
        zones = zones[1:] # remove the inner circle
        settings["zones"] = zones
        settings["planet_counts"] = planet_counts
        settings["link_values"] = [lv * 1.25 for lv in settings["link_values"]]
        return settings

class HoleMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)
        self.react_to(Trigger.MapGenerated, self.on_map_generated)
    def on_map_setup(self, data):
        gen = data["generation"]
        dimensions = Vector2(constants.Float("hole.width"), constants.Float("hole.height"))
        gen.Refinement("after_planet_types", 1000, refinement_generate_hole(dimensions, 1.0))
        gen.Refinement("after_planet_types", 1005, refine_remove_signals_in_hole(inverted = False))
    def on_map_generated(self, data):
        instantiate_hole()

def instantiate_hole():
    pos = game.CustomData.Get("hole_position")
    points = game.CustomData.Get("hole_points")
    game.CustomData.Clear("hole_points")
    game.CustomData.Clear("hole_position")
    world.Add(GrowingHole(pos, points))
