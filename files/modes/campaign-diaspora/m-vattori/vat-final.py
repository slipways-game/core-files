#########################################################
# Main mission class

class VattoriMainMission(OneRaceMainMission):
    def __init__(self):
        OneRaceMainMission.__init__(self, "vattori", [VMMEnoughVessels(), VMMSuccessfulInRift()])

    def scoring_rules(self):
        return [
            ScoringCampaignTasks([0,1,2,3,4,4]),
            ScoringRiftPlanets([1,2,3,4,6]),
            ScoringVessels([1,2,4,6,8])
        ]

    def conditions(self): return [
        (WinMissionOnTime, "VattoriMainMission()", 28),
        (KeepTrackOfPlanets,),
        (ForbidCrossingEdges,),
        (ShifterCrossingRules,),
        (RestrictStructures,)
    ]

    def do_additional_setup(self):
        game.Stock.Receive(Resource.Cash, 20) # starting bonus
    
    def things_to_explain(self):
        return [
            ("custom", "special.inside_the_rifts"),
            ("structure", "phase_shifter"),
            ("project", "mind_extractor")
        ]
    
    def borrowed_techs(self):
        return {
            "baqar": ["mineral_seeding", "mass_reactors", "gravitic_tugs"],
            "dendr": ["disease_eradication", "weather_control", "biome_reconstruction"],
            "silthid": ["flexible_fabrication", "extreme_mini", "bioextraction"],
            "aphorian": ["geoharvesting", "economic_zones", "hyperdense_arch"],
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
# Mission goals and scoring

class VMMEnoughVessels:
    def __init__(self):
        self._required = constants.Int("vat.required_vessels")
    def description(self): return LS("mission.vattori.goal.enough_vessels", None, self._required)
    def check_completion(self): return self.state()[0] >= self._required
    def state(self): return (game.Nodes.TotalProduction(Resource.All["A"]), self._required)
    def short(self): return "%d/%d:A:" % self.state()

class VMMSuccessfulInRift:
    def __init__(self):
        self._required = constants.Int("vat.required_planets")        
    def requires(self): return (0,)
    def state(self): return (self.count_planets(), self._required)
    def check_completion(self): return self.state()[0] >= self._required
    def short(self): return "%d/%d:planet:" % self.state()
    def description(self): return LS("mission.vattori.goal.planets_in_rift", None, self._required)
    @staticmethod
    def count_planets():
        return sum(1 for p in game.Nodes.PlanetsWithLevelOrHigher(2) if regions.PresentFor(p))

class ScoringRiftPlanets(ScoringFiveRanks):
    def __init__(self, increments):
        base = constants.Int("vat.required_planets")
        self._limits = [0] + [base + i for i in increments]
    def tags(self): return ["mission"]
    def id(self): return "scoring.vattori.planets_in_rift"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return VMMSuccessfulInRift.count_planets()
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":lv2:"
    def number_text(self, number, rank): return "%d:lv2:" % number   

class ScoringVessels(ScoringFiveRanks):
    def __init__(self, increments):
        base = constants.Int("vat.required_vessels")
        self._limits = [0] + [base + i for i in increments]
    def tags(self): return ["mission"]
    def id(self): return "scoring.vattori.vessels"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return game.Nodes.TotalProduction(Resource.All["A"])
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":A:"
    def number_text(self, number, rank): return "%d:A:" % number   

#########################################################
# Music

class VattoriMusic(MusicProgression):
    def __init__(self):
        self._required = float(constants.Int("vat.required_vessels"))

    def _check_for_transition(self, prev):
        vessels = game.Nodes.TotalProduction(Resource.All["A"])
        prop = vessels / self._required
        lv = 0
        if prop > 0.0: lv += 1
        if prop >= 0.5: lv += 1
        if prop >= 1.0: lv += 1
        if prev < lv: return lv

###############################################################
# Mapgen

class VattoriMissionMapgen(GlobalCondition):
    """Makes sure that the rip manager is present and that the effects of the rip on the map are felt."""
    def activate(self):
        self.react_to(Trigger.GameWorldSetup, self.on_world_setup, 100)
        self.react_to(Trigger.MapGenerated, self.on_map_generated)

    def on_world_setup(self, data):
        if "regions" in globals():
            self._regions = regions
        else:
            rng = game.RNG("regions")
            self._regions = self.generate_regions(rng)

    def on_map_generated(self, data):
        nudge_signals_in_or_out(1.2, 0.24)
        add_more_stuff_inside_rifts()

    MAX_OFFSET = 0.25
    def generate_regions(self, rng):
        rotation = Randomness.Float(rng, 0.0, math.pi * 2)
        offset = Randomness.PointInsideUnitCircle(rng) * f(self.MAX_OFFSET)
        return world.Add(TextureBasedRegions({
            "texture_path": "Campaign/Vattori/Tex_VattoriMission_Regions",
            "render_material_path": "Campaign/Vattori/Mat_VattoriMission_Regions",
            "scale": 0.35,
            "threshold": 0.3,
            "rotation": rotation,
            "offset": offset,
            "zero_radius": -10,
            "base_radius": 12,
            "one_radius": 880
        }))

    def debug_commands(self, position):
        def regenerate():
            old = find("TextureBasedRegions")
            if old: old.Discard()
            rng = game.RNG("%f,%f" % (position.x, position.y))
            self.generate_regions(rng)
        def value_at_point():
            log(self._regions.ValueAt(position))
        return [
            {"text": "regions: regenerate", "action": regenerate},
            {"text": "regions: value at this point", "action": value_at_point}
        ]

def nudge_signals_in_or_out(feeler_distance, step):
    # set up parameters
    feeler_distance = f(feeler_distance)
    feelers = [rotate_vector(Vector2.right * feeler_distance, a) for a in range(0, 360, 45)]
    nudge_size = f(step)
    # actual nudging
    deleted_things = []
    for t in game.Map.Signals:
        retries = 10            
        while retries > 0:
            pos = t.Position
            middle = regions.PresentAt(pos)
            nudge_dir = Vector2.zero
            needs_nudge = False
            for fl in feelers:
                if regions.PresentAt(pos + fl) != middle:
                    nudge_dir -= fl
                    needs_nudge = True
            if needs_nudge:
                if nudge_dir == Vector2.zero:
                    # no consensus on direction, give up
                    retries = 0
                    break
                retries -= 1
                t.Position += nudge_dir.normalized * nudge_size
            else:
                break
        if retries == 0:
            # retries exhausted, delete
            deleted_things.append(t)        
    for d in deleted_things:
        game.Map.RemoveSignal(d)

RIFT_PLANET_TYPES = [
    "earthlike", "ocean", "arctic", "swamp", "jungle", "arid",
    "factory", "mining", "remnant", "factory", "mining", "ice", "barren"
]
RIFT_PLANET_TYPES = ["planet." + t for t in RIFT_PLANET_TYPES]
def add_more_stuff_inside_rifts():
    rng = game.RNG("more_in_rifts")
    for t in game.Map.Signals:
        inside = regions.PresentAt(t.Position)
        if not inside: continue
        replace = False
        if t.Contents == "structure.forebear_station":
            replace = True
        elif not t.Contents.startswith("planet."):
            replace = Randomness.WithProbability(rng, 0.15)
        elif t.Contents[7:] not in RIFT_PLANET_TYPES:
            replace = True
        if replace:
            nearby_planet_kinds = set(s.Contents for s in game.Map.SignalsWithin(t.Position, 9.0) if s.Contents.startswith("planet."))
            remaining_kinds = [k for k in RIFT_PLANET_TYPES if not k in nearby_planet_kinds]
            if len(remaining_kinds) == 0:
                remaining_kinds = RIFT_PLANET_TYPES
            new_type = Randomness.Pick(rng, remaining_kinds)
            t.Contents = new_type
            if t.Size == PotentialSize.Small:
                t.Size = PotentialSize.Medium

###############################################################
# Building restrictions

GRACE_REGION = 0.005

class ForbidCrossingEdges(GlobalCondition):
    def global_connection_validation(self, pc):
        if pc.EndNode:
            start_in = regions.PresentFor(pc.StartNode)
            end_in = regions.PresentFor(pc.EndNode)
            if start_in != end_in:
                is_shifter = pc.StartNode.NodeType == "structure.phase_shifter" or pc.EndNode.NodeType == "structure.phase_shifter"
                if not is_shifter:
                    return Permission.No(LS("connection.problem.cannot_cross_edge"))
        has_ins, has_outs = is_connection_in_out(pc)
        if has_ins and has_outs:
            return Permission.No(LS("connection.problem.cannot_cross_edge"))    
        return Permission.Yes()

class ShifterCrossingRules(GlobalCondition):
    def global_connection_validation(self, pc):
        shifter = None
        if pc.StartNode.NodeType == "structure.phase_shifter": shifter = pc.StartNode
        if pc.EndNode and pc.EndNode.NodeType == "structure.phase_shifter": shifter = pc.EndNode
        if shifter is None:
            return Permission.Yes()
        if conditions.GetOrCreate("RiftBouncing()").IsActive:
            return Permission.Yes()        
        if len(shifter.Connections) != 1:
            return Permission.Yes()
        prev_c = shifter.Connections[0]
        old_has_ins, old_has_outs = is_connection_in_out(prev_c)
        new_has_ins, new_has_outs = is_connection_in_out(pc)
        if (old_has_ins and new_has_ins) or (old_has_outs and new_has_outs) or (not new_has_ins and not new_has_outs):
            return Permission.No(LS("connection.problem.both_same_side"))
        return Permission.Yes()

def is_connection_in_out(pc):
    if isinstance(pc, PlannedConnection):
        a, b = pc.StartPoint, pc.EndPoint
    else:
        a, b = pc.From.Position, pc.To.Position     
    length = (b - a).magnitude
    step = ((b - a) / length) * f(0.1)
    step_count = int(math.floor(length / 0.1))
    pos = a
    has_ins, has_outs = False, False
    for i in range(step_count):
        value = regions.ValueAt(pos)
        if value <= -GRACE_REGION: 
            has_outs = True
        elif value >= GRACE_REGION: 
            has_ins = True
        if has_ins and has_outs:
            return has_ins, has_outs
        pos += step
    return has_ins, has_outs

class RestrictStructures(GlobalCondition):
    FORBIDDEN_STRUCTURES = ["habitat", "food_processor"]

    def global_structure_placement_rules(self, kind):
        return [ScriptedPlacement(self)]

    def is_permitted(self, pos, ps):
        value = regions.ValueAt(pos)        
        if value >= 0.0 and ps.Kind.ID in self.FORBIDDEN_STRUCTURES:
            return Permission.No(LS("structure.placement.not_inside_rift"))
        if value >= -5 * GRACE_REGION and value <= 5 * GRACE_REGION and ps.Kind.ID != "phase_shifter":
            return Permission.No(LS("structure.placement.not_on_rift_edge"))
        return Permission.Yes()

###############################################################
# Inside the destroyed regions

class KeepTrackOfPlanets(GlobalCondition):
    def activate(self):
        game.Qualities.EstablishGlobally(QualityAlteredPlanet)

class QualityAlteredPlanet:
    INDUSTRY_INDEX = None

    def name(self): return LS("quality.altered_planet")
    def desc(self): return LS("quality.altered_planet.desc")
    def sentiment(self): return QualitySentiment.Neutral
    def hidden(self, node): return True

    def applies(self, node):
        return isinstance(node, Planet) and regions.PresentFor(node)

    def effects(self, node):
        # remove P/B colonization options
        yield ColonizationOptions.RemoveMatching(self.industry_prohibited)
        # replace some industries with others
        yield ColonizationOptions.ReplaceMatching(self.industry_replacement)
        # add new A-based options
        for ik in self.added_options_for(node.Kind):
            yield ColonizationOptions.Add(ik.ID)
        # allow connections to mind extractors
        yield ConnectivityRule.Calling(self.connectivity)

    def added_options_for(self, planet_kind):
        if not QualityAlteredPlanet.INDUSTRY_INDEX:
            index = {}
            for ik in IndustryKind.AllList:
                if not ik.ID.startswith("a_"): continue
                kind_id = ik.ID.split("_")[1]
                index[kind_id] = index.get(kind_id, []) + [ik]
            QualityAlteredPlanet.INDUSTRY_INDEX = index
        return QualityAlteredPlanet.INDUSTRY_INDEX.get(planet_kind.ID, [])
    
    def industry_prohibited(self, industry_kind):
        resources = "PBF"
        for n in industry_kind.BaseLevel.BaseNeeds:
            if n.Resource.ID in resources:
                return True
        for p in industry_kind.BaseLevel.BaseProducts:
            if p.ID in resources:
                return True        
        return False

    REPLACED_INDUSTRIES = {"arid_solar": "mod_arid_solar"}
    def industry_replacement(self, industry_kind):
        new_id = self.REPLACED_INDUSTRIES.get(industry_kind.ID, None)
        if new_id:
            return IndustryKind.All[new_id]

    def connectivity(self, node, other):
        # allow mind extractor connections before colonization
        if other is not None and (other.NodeType == "structure.mind_extractor" or other.NodeType == "check"):
            return NodeConnectivity.Accepts()
        return None # otherwise default

class QualityBiphasicPlants:
    INDUSTRY_INDEX = {}
    def name(self): return LS("tech.biphasic_plants")
    def desc(self): return LS("quality.biphasic_plants.desc")
    def sentiment(self): return QualitySentiment.Positive
    def hidden(self, node): return True

    def applies(self, node):
        return isinstance(node, Planet) and regions.PresentFor(node)

    def effects(self, node):
        # add the food options, if any
        for ik in self.added_options_for(node.Kind):
            yield ColonizationOptions.Add(ik.ID)

    def added_options_for(self, planet_kind):
        if not self.INDUSTRY_INDEX:
            index = {}
            for ik in IndustryKind.AllList:
                if not ik.ID.startswith("bf_"): continue
                kind_id = ik.ID.split("_")[1]
                index[kind_id] = index.get(kind_id, []) + [ik]
            self.INDUSTRY_INDEX = index
        return self.INDUSTRY_INDEX.get(planet_kind.ID, [])

################################################
# Extractors and shifters

def shifter_upgrade(node, industry, level):
    if level == 1 and not node.HasAnyProject:
        return Permission.NoWithNoReason()
    if level == 2 and node.HasUnmetNeeds:
        return Permission.No(LS("warning.needs_unfulfilled", None, ":P:"))
    return Permission.Yes()

def shifter_placement():
    return [ScriptedPlacement(EdgeOfRegionOnly(rotate=True))]

def shifter_cost(kind):
    cash = constants.Int("shifter.cost.$")
    return CompoundCost.Parse("%d$,2S,1mo" % cash)

def shifter_connectivity(node, other):
    if other is not None and other.NodeType == "structure.phase_shifter":
        if not conditions.GetOrCreate("RiftBouncing()").IsActive:
            return NodeConnectivity.Rejects(LS("connection.problem.two_shifters"))
    if node.Connections.Count >= 2:
        return NodeConnectivity.Rejects(LS("structure.relay.too_many_connections"))
    return NodeConnectivity.Accepts()

class MindExtractorProject:
    def available(self, node):
        # override the default completely
        return node.NodeType == "structure.phase_shifter"

class MindExtractorQuality:
    def name(self): return LS("project.mind_extractor")
    def desc(self): return LS("project.mind_extractor.desc")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node): 
        return None

class EdgeOfRegionOnly:
    def __init__(self, rotate=True):
        self._feelers = [rotate_vector(Vector2.right, a) for a in range(0, 360, 15)]
        self._rot_feelers = [(a*0.5, rotate_vector(Vector2.right, a*0.5)) for a in range(0, 360, 15)]
        self._rotate = rotate

    def adjust_position(self, pos, ps):        
        pos_val = regions.ValueAt(pos)
        snaps = []
        for fdir in self._feelers:
            dist = f(0.5)
            ppos, ppos_val = pos, pos_val
            for _ in range(3):
                npos = ppos + fdir * dist
                npos_val = regions.ValueAt(npos)
                if ppos_val - npos_val < 0.0001: break                
                lerpf = ppos_val / (ppos_val - npos_val)
                lerpf = f(clamp(-1.0, 1.0, lerpf))
                ppos = lerp(ppos, npos, lerpf)
                ppos_val = regions.ValueAt(ppos)
                dist = f(dist * 0.5)
            if ppos_val > -GRACE_REGION and ppos_val < GRACE_REGION:
                snaps.append(ppos)
        if len(snaps) == 0: return pos
        actual_pos = min(snaps, key=lambda s: (s - pos).sqrMagnitude + regions.ValueAt(s) * 5)
        return actual_pos

    def rotation_at(self, pos, ps):
        if not self._rotate: return 0
        pos_val = regions.ValueAt(pos)
        if pos_val <= -GRACE_REGION or pos_val > GRACE_REGION: return 90
        dist = f(0.66)
        best_angle, best_diff = 90, 1.0
        for angle, fdir in self._rot_feelers:
            delta = fdir * dist
            apos, bpos = pos + delta, pos - delta
            aval, bval = regions.ValueAt(apos), regions.ValueAt(bpos)
            diff = abs(aval - bval)
            if diff < best_diff:
                best_angle, best_diff = angle, diff
        return best_angle + 90

    def is_permitted(self, pos, ps):
        region_value = regions.ValueAt(pos)
        if region_value <= -GRACE_REGION or region_value >= GRACE_REGION:
            return Permission.No(LS("structure.placement.edge_of_rift"))
        return Permission.Yes()

#################################################################
# Tech stuff

class QualityBiphasicPlants:
    INDUSTRY_INDEX = {}
    def name(self): return LS("tech.biphasic_plants")
    def desc(self): return LS("quality.biphasic_plants.desc")
    def sentiment(self): return QualitySentiment.Positive
    def hidden(self, node): return True

    def applies(self, node):
        return isinstance(node, Planet) and regions.PresentFor(node)

    def effects(self, node):
        # add the food options, if any
        for ik in self.added_options_for(node.Kind):
            yield ColonizationOptions.Add(ik.ID)

    def added_options_for(self, planet_kind):
        if not self.INDUSTRY_INDEX:
            index = {}
            for ik in IndustryKind.AllList:
                if not ik.ID.startswith("bf_"): continue
                kind_id = ik.ID.split("_")[1]
                index[kind_id] = index.get(kind_id, []) + [ik]
            self.INDUSTRY_INDEX = index
        return self.INDUSTRY_INDEX.get(planet_kind.ID, [])

class RiftBouncing(GlobalCondition):
    """This is a marker condition whose presence is checked by shifter_connectivity. Doesn't do anything on its own."""
    def info(self):
        ci = CondInfo()
        ci.FullDescription = LS("cond.rift_bouncing.desc")
        return ci

class QualityExoticMatter:
    BONUS = 2
    def name(self): return LS("tech.exotic_matter")
    def desc(self): return LS("quality.exotic_matter.desc", None, self.BONUS)
    def sentiment(self): return QualitySentiment.Positive
    
    def applies(self, node):
        return True

    def effects(self, node):
        total = 0
        inside = regions.PresentFor(node)
        for n in node.ExportRoutes:
            crosses_edge = regions.PresentFor(n.Consumer) != inside
            if crosses_edge: total += self.BONUS
        if total > 0:
            return [ResourceFlow.Cash(total, FlowCategory.SpecialBonuses)]

class QualityExoticStudy:
    BONUS = 1
    def name(self): return LS("tech.exotic_matter")
    def desc(self): return LS("quality.exotic_study.desc", None, self.BONUS)
    def sentiment(self): return QualitySentiment.Positive
    
    def applies(self, node):
        return node.NodeType.startswith("structure.") and node.NodeType.endswith("lab")

    def effects(self, node):
        total = 0
        inside = regions.PresentFor(node)
        for n in node.ImportRoutes:
            crosses_edge = regions.PresentFor(n.Producer) != inside
            if crosses_edge: total += self.BONUS
        if total > 0:
            return [ChangeProducts.Add(total, Resource.Science, "exotic_study")]

################################################################
# Special overrides for stuff with rifts/vessels

def lab_industry_rifts(node):
    inside = regions.PresentFor(node)
    return IndustryKind.All["rift_lab"] if inside else IndustryKind.All["lab"]

original_lab_count_researchers = lab_count_researchers
def lab_count_researchers(node):
    if node.Industry.Kind.ID != "rift_lab":
        return original_lab_count_researchers(node)
    return node.Need(Resource.All["A"]).ImportCount


class OrbitalLabsProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.IsProducerOf(Resource.People) or node.IsProducerOf(Resource.All["A"])

    def requirements_fulfilled(self, node):
        if not node.HasAvailable(Resource.People) and not node.HasAvailable(Resource.All["A"]):
            return Permission.No(LS("project.no_idle_people"))
    
class OrbitalLabsQuality:
    def name(self): return LS("project.orbital_labs", "Orbital labs")
    def desc(self): return LS("project.orbital_labs.desc", None, self.bonus())

    def bonus(self):
        return constants.Int("orbital_lab.bonus", 1)
    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): 
        bonus_science = self.bonus()
        resource = Resource.People
        if node.IsProducerOf(Resource.All["A"]):
            resource = Resource.All["A"]
        return [
            ChangeProducts.ReduceProduction(1, resource),
            ChangeProducts.Add(bonus_science, Resource.Science, "orbital_labs")
        ]