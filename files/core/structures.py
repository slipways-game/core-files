# Defines most of the rules used by the core structures in the game (those accessible in standard using tech or otherwise).
# Campaign-specific structures live in the mission files in "modes/campaign-diaspora/".

##############################################
# General

def hosts_probes(node):
    return node.Level >= 0

def reveals_fog(node):
    return node.Level >= 0

def fog_radius_minimal(node):
    return Planet.ObstructionRadius * 1.5

def fog_radius_planet(node):
    return FogOfWar.GetDefaultRange(world)

def ignores_all_connections(node, other):
    return NodeConnectivity.Ignores()

def needs_reject_duplicates(need, resource):
    """When used as the 'want_normal' rule, causes the structure to only accept one copy of needs. Useful for structures that get activated and can't really be upgraded."""
    if need.IsMet: return False
    return None # defer to default logic

##############################################
# Asteroids

def asteroid_tooltip(me, original):
    if me.Level == -1:
        bonus = constants.Int("asteroid.bonus")
        return [
            original, 
            LS("structure.asteroid.tooltip", "Can be exploited for wealth.\nYields [[delta:+{1}$]] for each nearby colonized planet.", bonus).ToString()
        ]
    return [original]

def asteroid_connectivity(node, other):
    for u in unlocks.LocalUnlocks("structure.asteroid", "industry"):
        # if we have anything we're just "not colonized"
        return NodeConnectivity.Rejects(LS("node.not_colonized", "not colonized"), 0)
    return NodeConnectivity.Ignores()

##############################################
# Laboratory

LAB_DISCOVERY_THRESHOLD = 4

def lab_affects(node):
    """Any change to a lab may change other labs (due to the dynamic upkeep)."""
    return list(nodes_of_type("structure.lab"))

def lab_industry(node):
    return IndustryKind.All["lab"]

def lab_wants(need, offered_resource):
    """Laboratories accept any of ore, tech, organics, bots to replace their special need."""
    locked, offered = need.MetWith, offered_resource
    if locked is not None:
        return offered == locked
    else:
        return offered.ID in "OLTBW"

def lab_want_normal(need, offered_resource):
    # disable conflation for robots here until study subject is set
    subject = lab_study_subject(need.Consumer)
    if subject is not None and subject.ID != "B": return
    if offered_resource.ID == "B" and need.AskingFor is not None and need.AskingFor.ID == "P":
        return False

def lab_accepts_special(node, resource):
    return False

def lab_count_researchers(node):
    needs = list(node.Needs)
    people = node.Need(Resource.People).ImportCount
    # 1 x each additional P
    researchers = people
    # special case for conflated B 'researchers'
    for n in range(2, len(needs)):
        asking = needs[n].AskingFor
        if asking == Resource.All["B"] or asking == Resource.People:
            researchers += needs[n].ImportCount
    return researchers

def lab_upgrade(lab, industry, lv):
    p = Permission.Yes()
    if lab_study_subject(lab) is None:
        p = p.Disallow(LS("structure.lab.no_study_subject"))
    if lab_count_researchers(lab) == 0:
        p = p.Disallow(LS("structure.lab.no_researchers"))
    if p.Allowed and lab.HasUnmetNeeds:
        p = Permission.NoWithNoReason() # fallback
    return p

def lab_output(node):
    return sum(1 for p in node.Products if p.Resource == Resource.Science)

def lab_study_subject(node):
    unknown_needs = [n for n in node.Needs if n.AskingFor is None]
    return unknown_needs[0].MetWith if len(unknown_needs) > 0 else None

def lab_older_labs(node):
    return [lab for lab in every(Structure) 
        if lab.NodeType == "structure.lab" 
        and lab.EstablishedOn < node.EstablishedOn]

def lab_info_unknown_need(node):
    header = LS("structure.lab.tooltip_study_subject", "Study subject")
    text = LS("structure.lab.tooltip_deliver", "Deliver :O:/:L:/:T:/:B:/:W: to start research.")
    return InfoBlock(header, text)

def lab_info_on_upgrades(node):
    if node.Level < 1: return None # default handling below level 1
    # get data
    subject_resource = lab_study_subject(node)    
    # header
    header = LS("structure.lab.upgrade_header", "Possible upgrades")
    # what's possible/impossible?
    info = []
    info.append(LS("structure.lab.could_use_resource", "Send more :{1}: for [[delta:+2S]] each.", subject_resource))
    info.append(LS("structure.lab.could_use_researchers", "Send more :P: for [[delta:+1S]] each."))
    return InfoBlock(header, info)

class LabDiminishingReturns:
    def name(self): return LS("quality.diminishing_returns", "Diminishing returns")
    def desc(self): return LS("quality.diminishing_returns.desc", "For each lab already researching the same resource, laboratory output is lowered by 2:S:.")
    def sentiment(self): return QualitySentiment.Negative    
    def visibility(self, node): return 5 if self.penalty(node) > 0 else 0
    def icon(self, node): return {"text": ":S:", "type": "negative", "sub_icon": "mod_negdown"}
    
    def penalty(self, node):
        my_subject = lab_study_subject(node)   
        if my_subject is None: return 0
        other_labs = [lab for lab in lab_older_labs(node)
            if lab_study_subject(lab) == my_subject
            and lab != node]
        penalty = len(other_labs) * 2
        if penalty > 0:
            game.CustomData.Set("diminishing_returns_seen", True)
        return penalty

    def effects(self, node):
        penalty = self.penalty(node)
        if penalty > 0:
            return [ChangeProducts.ReduceProduction(penalty, Resource.Science)]
        else:
            return []

class LabUpkeep:
    BASE, INCREASE = 5, 2

    def name(self): return LS("quality.lab_upkeep", "Laboratory upkeep")
    def desc(self): return LS("quality.lab_upkeep.desc",
        "Lab upkeep costs {1}:$:, plus {2}:$: for every other lab you have.", LabUpkeep.BASE, LabUpkeep.INCREASE)

    def effects(self, node):
        lab_count = len([s for s in every(Structure) if s.NodeType == "structure.lab"])
        total = LabUpkeep.BASE + LabUpkeep.INCREASE * (lab_count - 1)
        # local bonus
        local_modifier = 1.0 + PercentageBonus.GetBonus(node, "structure.upkeep")
        total = round(local_modifier * total)
        # global bonus
        modified = constants.Int("industry.lab.upkeep.$", total)
        if modified != 0:
            return [ResourceFlow.Cash(-modified, FlowCategory.StructureUpkeep)]

class LabResearch:
    def name(self): return LS("", "")
    def sentiment(self): return QualitySentiment.Positive
    
    def hidden(self, node): return True

    def effects(self, node):
        if node.Level < 1: return []
        needs = list(node.Needs)
        unknown_needs = [n for n in needs if n.AskingFor is None]
        # 1 x researchers beyond the first
        researchers = lab_count_researchers(node)
        people_bonus = max(0, researchers - 1)
        # 2 x each additional studied resource
        study_need = unknown_needs[0] if len(unknown_needs) > 0 else None
        study_count = study_need.ImportCount if study_need else 0
        study_bonus = 2 * max(0, study_count - 1)        
        # add production
        return [ChangeProducts.Add(people_bonus + study_bonus, Resource.Science, "research")]

##############################################
# Food processor

def food_proc_upgrade(node, industry, lv):
    if not node.Needs[0].IsMet:
        return Permission.No(LS("structure.food_proc.cant_upgrade", "Deliver :L: or :W: to start producing food."))
    return Permission.Yes()

def food_proc_wants(need, offered_resource):
    locked, offered = need.MetWith, offered_resource
    if locked is not None:
        return offered == locked
    else:
        return offered.ID in "LW"

def food_proc_unknown_need(node):
    header = LS("structure.food_proc.tooltip_need_header", "Substrate")
    desc = LS("structure.food_proc.tooltip_need", "Deliver :L:/:W: to start production.")
    return InfoBlock(header, desc)

def food_proc_info_on_upgrades(node):
    if node.Level < 1: return None # default handling below level 1
    unsupplied = [need for need in node.Needs if need.AskingFor and need.AskingFor.ID in "LW" and not need.IsMet]
    if len(unsupplied) > 0:
        unsupplied = unsupplied[0]
        header = LS("structure.lab.upgrade_header")
        info = [LS("structure.food_proc.other_resource", None, unsupplied.AskingFor.ID)]
        return InfoBlock(header, info)
    else:
        return None

class FoodProcQuality:
    def name(self): return LS("", "")
    def sentiment(self): return QualitySentiment.Neutral
    def hidden(self, node): return True

    def effects(self, node):
        effects = []
        if len(node.Needs) < 1: return
        # generating the "other" need
        if node.Needs[0].IsMet:
            first_resource = node.Needs[0].MetWith.ID
            added = "W" if first_resource == "L" else "L"
            effects += [ChangeNeeds.AddOne(Resource.All[added])]
        # generating output
        output = 0
        if any(need.AskingFor and need.AskingFor.ID in "LW" and need.IsMet for need in node.Needs): output += 1
        if output > 0:
            effects.append(ChangeProducts.Add(output, Resource.All["F"], "food_proc"))
        return effects

##############################################
# Relays

def infra_channel(): return 1

RELAY_PENALTY_PER_PAIR = 12
def connection_cost_relay_penalty(node, planned_connection, base_cost):
    # only one side applies the penalty
    if node != planned_connection.StartNode: return base_cost
    # is the other side a relay as well?
    other = planned_connection.EndNode
    if not other or not other.RelaysConnections: return base_cost
    # ok, we're connecting relays - check if we can use the simple rule, or we need the expensive one
    # because something 'cutsRelayTrees'
    if cuts_relay_trees(node): return base_cost # all paths on 'our side' will be cut, because they all feature 'node'
    if cuts_relay_trees(other): return base_cost # all paths on 'their side' will be cut, because they all feature 'other'
    our_side_cuts = set(n for n in game.Reachability.ReachableNodes(node) if cuts_relay_trees(n))
    their_side_cuts = set(n for n in game.Reachability.ReachableNodes(other) if cuts_relay_trees(n))
    expensive_rule_needed = len(our_side_cuts) + len(their_side_cuts) > 0
    if expensive_rule_needed:
        # the expensive rule removes things that are cut by cutting nodes
        our_side_paths = (p for n, p in game.Reachability.ReachableNodesWithPaths(node) if n.RelaysConnections)
        our_side_size = sum(1 for p in our_side_paths if path_does_not_feature_nodes(node, p, our_side_cuts)) + 1
        their_side_paths = (p for n, p in game.Reachability.ReachableNodesWithPaths(other) if n.RelaysConnections)
        their_side_size = sum(1 for p in their_side_paths if path_does_not_feature_nodes(other, p, their_side_cuts)) + 1
    else:
        # the cheap rule just looks at reachable counts, since that's enough
        our_side_size = sum(1 for n in game.Reachability.ReachableNodes(node) if n.RelaysConnections) + 1 # +1 for ourselves
        their_side_size = sum(1 for n in game.Reachability.ReachableNodes(other) if n.RelaysConnections) + 1
    penalty_base = our_side_size * their_side_size
    # do we already see each other? (loop)
    if other in game.Reachability.ReachableNodes(node): penalty_base = min(1, penalty_base)
    # apply the penalty
    penalty = penalty_base * RELAY_PENALTY_PER_PAIR
    return base_cost.Add(Resource.Cash, penalty)

def path_does_not_feature_nodes(start_node, connection_path, disallowed_nodes):
    node = start_node
    if node in disallowed_nodes: return False
    for conn in connection_path:
        node = conn.OtherEnd(node)
        if node in disallowed_nodes: return False
    return True

def cuts_relay_trees(node):
    rule = node.Industry and node.Industry.Kind.Rules.cutsRelayTrees
    return rule and rule(node)    

def relay_effective_radius(node):
    if node.CustomData.Has("lensified"):
        return f(0.5)
    return None

##############################################
# Trade hubs

class TradeHubNeeds:
    def name(self): return LocalizedString.Empty
    def desc(self): return LocalizedString.Empty
    def hidden(self, node): return True

    def effects(self, node):
        met_needs = sum(1 for n in node.Needs if n.IsMet)
        to_add = clamp(0, 4, met_needs - 2)
        yield ChangeNeeds.AddUnknowns(to_add)

class TradeHubHappiness:
    def name(self): return LocalizedString.Empty
    def desc(self): return LocalizedString.Empty
    def hidden(self, node): return True

    def effects(self, node):
        met_needs = sum(1 for n in node.Needs if n.IsMet)
        bonus = (met_needs >= 5) + (met_needs >= 7) * 2
        if bonus > 0:
            yield ChangeProducts.Add(bonus, Resource.Happiness)

def trade_hub_description(node):
    return LS("structure.trade_hub.desc", None, 1, 2, 4)

def trade_hub_price(node):
    return f(1.0) if node.Level > 0 else f(0.0)
    
def trade_hub_upgrade(node, industry, level):
    met_needs = sum(1 for n in node.Needs if n.IsMet)
    if met_needs >= 3:
        return Permission.Yes()
    else:
        return Permission.No(LS("structure.trade_hub.needs_three"))

def trade_hub_unknown_need(node):
    header = LS("structure.trade_hub.tooltip_need_header", "Any resource")
    desc = LS("structure.trade_hub.tooltip_need", "Deliver anything not already traded here")
    return InfoBlock(header, desc)

def trade_hub_wants(need, offered_resource):
    """Trade hubs want their resources to all be different."""
    # no filling stuff that's already met
    if need.IsMet: return False    
    # only the first unfilled need may be filled
    unmet_needs = [n for n in need.Consumer.Needs if not n.IsMet]
    if need != unmet_needs[0]: return False
    # only some resources accepted (can't trade people ;)
    offered = offered_resource.ID
    if not offered in "OLTBGFW": return False
    # can't accept same thing twice
    hub = need.Consumer
    met_needs = [n for n in hub.Needs if n.IsMet]
    used_resources = [n.MetWith.ID for n in met_needs]
    return offered not in used_resources

##############################################
# Ascension gate happiness

class AscensionGateHappiness(AnonymousHiddenQuality):
    def effects(self, node):
        people = node.AmountReceived(Resource.People)
        bonus_happiness = clamp(0, 2, people - 1) + max(0, people - 3) * 2
        if bonus_happiness:
            return [ChangeProducts.Add(bonus_happiness, Resource.Happiness)]

##############################################
# Void synthesizer

def voidsynth_upgrade(node, industry, lv):
    return Permission.Yes()

def voidsynth_info_on_upgrades(node):
    return None

def voidsynth_unknown_product(node):
    header = LS("structure.void_synth.tooltip_product_header", "Output")
    desc = LS("structure.void_synth.tooltip_product", "Can produce :L:/:O:/:T:/:F:/:W: once connected\nto a planet with an unmet need")
    return InfoBlock(header, desc)

def voidsynth_tweak_route(route):
    # only supply unmet needs
    if route.need.IsMet: return None
    # ... and only for directly connected planets
    if len(route.path) > 1: return None
    # ... and only one route per planet
    already_delivering_something = any(er.Consumer == route.consumer for er in route.Producer.ExportRoutes)
    if already_delivering_something: return None
    # okay, that checks out
    return route

def voidsynth_after_trade(me):
    # do we have an unallocated product available?
    if len(me.Products) == 0 or me.Products[len(me.Products)-1].Resource.ID != "?": 
        return
    # what are we directly connected to?
    others = set((c, c.OtherEnd(me)) for c in me.Connections)
    for connection, other in others:
        # already servicing this node?
        if any(er.Consumer == other for er in me.ExportRoutes):
            continue
        # try to provide for the first unmet need at the other end
        # we also require it to be one of L, O, T, F, W
        unmet_needs = [n for n in other.Needs if not n.IsMet and n.AskingFor is not None and n.AskingFor.ID in "LOTFW"]
        if len(unmet_needs) == 0:
            continue
        # OK, this is it - let's turn our last output into this thing
        # the built-in VoidsynthOutputCount quality will then make another unknown output if that's possible
        unmet_resource = unmet_needs[0].AskingFor
        quality = "DetermineUnknownOutput('%s')" % unmet_resource.ID
        qualities.AttachForTheLifetimeOf(quality, me, connection)
        return

class VoidsynthOutputCount(AnonymousHiddenQuality):
    def effects(self, node):
        needed = node.ExportCount + 1
        added = min(needed, 3) - 1 # max. 3 outputs, -1 because one is present from the start
        return [ChangeProducts.AddUnknown(added)]

##############################################
# Teleporter

def teleporter_force_pairing():
    unpaired = [s for s in game.Nodes.WithType("structure.teleporter") if s.CustomData.Get("paired") is None]
    if len(unpaired) == 1:
        # second in a pair - only allow placing where it can pair
        complaint = LS("structure.teleporter.too_far", "too far away")
        return [PlaceNear(lambda n: n == unpaired[0], constants.Distance("teleporter.range"), complaint, "VPlaceNear")]
    else:
        # first in a pair can be placed anywhere
        return [PlaceAnywhere()]

def teleporter_cost(structure_kind):
    cost = structure_kind.BaseCost
    unpaired_exists = any(s.CustomData.Get("paired") is None for s in game.Nodes.WithType("structure.teleporter"))
    if unpaired_exists:
        return CompoundCost(ResourceCost.Cash(0))
    else:
        return cost

def teleporter_when_placed(me):
    # try to find another unpaired teleporter
    potential_pairs = [s for s in every(Structure) if
        s.Kind == me.Kind and # is a teleporter
        s.CustomData.Get("paired") is None and # and does not have a pair
        s != me] # and is not us
    # there should be 0 or 1
    if len(potential_pairs) == 1:
        commands.IssueScriptedConsequence(TeleporterPairing(me, potential_pairs[0]))

def teleporter_connectivity(me, other):
    existing_real_connections = len([c for c in me.Connections if c.Kind.TypedID != "connection.invisible"])
    if existing_real_connections >= 1:
        return NodeConnectivity.Rejects(LS("structure.teleporter.only_one_connection"))
    else:
        return NodeConnectivity.Accepts(0)

def teleporter_validate(conn, me, other):
    if me.CustomData.Get("paired") is None: return Permission.No(LS("structure.teleporter.unpaired", "not paired"))
    if other is None: return Permission.Yes()
    my_direction = (me.CustomData.Get("paired").Position - me.Position).normalized
    conn_direction = (me.Position - other.Position).normalized
    wrong_angle = Vector2.Dot(my_direction, conn_direction) < 0.05
    if wrong_angle:
        return Permission.No(LS("structure.teleporter.wrong_side", "can't connect to this side"))
    return Permission.Yes()
        
class TeleporterPairing:
    def __init__(self, t1, t2):
        self.teleporters = (t1, t2)

    def apply(self):
        t1, t2 = self.teleporters
        # set pairing data
        t1.CustomData.Set("paired", t2)
        t2.CustomData.Set("paired", t1)
        # create an actual link between them
        self.link = world.Add(InvisibleLink(t1, t2))
        # changed both
        return [t1, t2]

    def revert(self):
        t1, t2 = self.teleporters
        # destroy the link
        self.link.Discard()
        # remove pairing data
        t1.CustomData.Clear("paired")
        t2.CustomData.Clear("paired")
        # changed both
        return [t1, t2]

##############################################
# Habitats

def habitat_chrome(node):
    if node.Level >= 2:
        return [{
            "type": NodeChrome.Text, "icon": "level_%d" % node.Level
        }]

##############################################
# Monoliths

def monolith_description(node):
    return LS("structure.monolith.desc", None, 2, 1, ":O::O:")

def monolith_upgrade(node, industry, level):
    ore_need = node.Need(Resource.All["O"])
    if ore_need.ImportCount == 2:
        return Permission.Yes()
    else:
        return Permission.No(LS("structure.monolith.more_ore", "Deliver {1}:O: to build this monolith.", 2))

def monolith_update(node):
    reachable_prosp = (n for n in game.Reachability.ReachableNodes(node) if n.Level >= 3 and n.NodeType.startswith("planet."))
    for r in reachable_prosp:
        if not r.CustomData.Has("monolith"):
            ConsUpdateNodeData().add(r, "monolith", node.NodeIdentifier).issue()

class MonolithOutput:
    def name(self): return LS("", "")
    def sentiment(self): return QualitySentiment.Positive
    def hidden(self, node): return True

    def effects(self, node):
        if node.Level < 1: return
        node_id = node.NodeIdentifier
        reachable_prosp = sum(1 for n in game.Reachability.ReachableNodes(node) if n.Level >= 3 and n.CustomData.GetOr("monolith", None) == node_id)
        # add production
        if reachable_prosp > 0:
            return [ChangeProducts.Add(reachable_prosp, Resource.Happiness, "monolith")]

##############################################
# Sensor stations

def sensor_decorations():
    return [SensorRangeRing(sensor_radius())]

def sensor_placement():
    complaint = LS("structure.teleporter.too_far", "too far away")
    radius = sensor_radius()
    return [PlaceNear(lambda n: n.Level >= 0 and n.NodeType.startswith("planet."), f(radius), complaint, "VPlaceNearRay")]

def sensor_placed(node):
    cmd = commands.MakeIrreversible()
    world.Add(DelayedAction(0.15, lambda: sensor_discover(node, cmd)))

def sensor_discover(node, parent_command):
    radius = sensor_radius(node)
    world.Add(ProbePulse(node.Position, radius, parent_command))

def sensor_radius(node = None):
    return constants.Distance("probe.radius") * 2.3

###############################################
# Extractors

EXTRACTOR_RESOURCES = "LW"
EXTRACTOR_ORBIT = 1.15

def extractor_placement():
    eligible_fn = extractor_create_node_filter()
    return [
        PlaceNear(eligible_fn, f(EXTRACTOR_ORBIT + 0.05), LS("structure.trap.place_in_orbit"), "VPlaceNear"),
        ScriptedPlacement(SnapToOrbit(EXTRACTOR_ORBIT, eligible_fn))
    ]

def extractor_obstructed_by(ps, other):
    return not isinstance(other, Planet)

def extractor_create_node_filter():
    nodes = set()
    for planet in every(Planet):
        if planet.Level < 0: continue
        if not planet.ActuallyProduces(Resource.People): continue
        if planet.CustomData.Has("extractor"): continue
        for i in planet.AvailableIndustries():
            potential_products = i.BaseLevel.BaseProducts
            if any(prod.ID in EXTRACTOR_RESOURCES for prod in potential_products):
                nodes.add(planet)
                break
    return lambda n: n in nodes

def extractor_upgrade(ext, industry, level):
    if level <= 2: return Permission.Yes()
    return Permission.NoWithNoReason()

def extractor_placed(ext):
    planet = game.Nodes.ClosestWith(ext.Position, f(EXTRACTOR_ORBIT + 0.2), lambda p: p.NodeType.startswith("planet."))
    added_products = set()
    for i in planet.AvailableIndustries():
        for p in i.BaseLevel.BaseProducts:
            if p.ID in EXTRACTOR_RESOURCES:
                added_products.add(p.ID)
    added = "".join(added_products)            
    update = ConsUpdateNodeData()
    update.add(ext, "orbiting", planet)
    update.add(planet, "extractor", ext)
    update.issue()
    ConsAttachQualityOnce(planet, "extracting", "BioExtraction(\"%s\")" % added).issue()

class BioExtraction:
    def __init__(self, which):
        self._which = which
    def name(self): return LS("quality.bioextraction")
    def desc(self): return LS("quality.bioextraction.desc")
    def sentiment(self): return QualitySentiment.Positive    
    def effects(self, planet): 
        for rid in self._which:
            yield ChangeProducts.AddOne(Resource.All[rid], "bioextraction")
    
###############################################
# Generic placement rules

class SnapToOrbit:
    """Placement rule that causes a structure to snap to a planet's orbit and rotate accordingly."""
    def __init__(self, orbit_distance, eligible_node_filter, rotate = True):
        self._distance = orbit_distance
        self._filter = eligible_node_filter
        self._rotate = rotate

    def adjust_position(self, pos, ps):
        planet = game.Nodes.ClosestWith(pos, f(self._distance + 0.2), self._filter)
        if planet is not None:
            delta = pos - planet.Position
            delta = delta.normalized * f(self._distance)
            return planet.Position + delta
        else:
            return pos

    def rotation_at(self, pos, ps):
        if not self._rotate: return 0.0
        planet = game.Nodes.ClosestWith(pos, f(self._distance + 0.2), self._filter)
        if planet is None: return -45
        delta = pos - planet.Position
        rotation = math.atan2(delta.y, delta.x) * 180.0 / math.pi        
        return f(rotation)
