class StandardMapgen(GlobalCondition):
    def __init__(self, hooks = None):
        self._hooks = hooks or MapgenDefaults()

    def activate(self):
        self._difficulty_adjustment = constants.Float("map.difficulty")
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        # --- grab 
        map_generation = data["generation"]
        # --- calculate various constants
        zone_config = self._hooks.create_zones()        
        planet_counts = zone_config["planet_counts"] # total planet counts in each zone
        link_values_per_planet = zone_config["link_values"] # target average planet link value in each zone
        planet_weights = {
            "planet.factory": 11,
            "planet.mining": 11,
            "planet.primordial": 8,
            "planet.earthlike": 5,
            "planet.remnant": 7,
            "planet.ocean": 4,
            "planet.jungle": 4,
            "planet.swamp": 4,
            "planet.arctic": 4,
            "planet.arid": 4,
            "planet.ice": 6,
            "planet.barren": 6,
            "planet.lava": 6,
        }
        planet_values = {
            "planet.factory": 0.25,
            "planet.mining": 0.25,
            "planet.primordial": 0.25,
            "planet.earthlike": 0.4,
            "planet.remnant": 0.3,
            "planet.jungle": 0.2,
            "planet.ocean": 0.3,
            "planet.swamp": 0.2,
            "planet.arctic": 0.2,
            "planet.arid": -0.1,
            "planet.ice": -1.5,
            "planet.barren": -1.5,
            "planet.lava": -1.5,
        }
        # --- adjust for difficulty
        da = self._difficulty_adjustment
        log("Map difficulty: %f" % da)
        # more useless planets if harder
        for kind in ["planet.ice", "planet.barren", "planet.lava"]:             
            planet_weights[kind] = int(round(planet_weights[kind] + da))
        # less planets overall if harder
        pc_adjustment = 1 - da/15.0
        planet_counts = [int(round(pc * pc_adjustment)) for pc in planet_counts]
        # worse connections overall when harder
        lv_adjustment = 1 - da * 0.1
        link_values_per_planet = [lv * lv_adjustment for lv in link_values_per_planet]
        # skew the 'planet mix fairness' up or down
        pv_adjustment = da * 0.08
        for kind in planet_values.keys():
            planet_values[kind] += pv_adjustment
        # --- zones where signals are generated
        map_generation.ZoneGeneration({
            "zones": zone_config["zones"],
            "distanceLeeway": 0.2
        })
        # --- signal sizes
        map_generation.SignalWeights({
            "big": 37, "medium": 37, "small": 25
        })
        if "centers" in zone_config:
            map_generation.SignalRule(self.prefer_bigger_signals_toward_center(zone_config["centers"]))
        map_generation.SignalRule(self.prefer_bigger_if_isolated)
        map_generation.SignalRule(self.enforce_variety(0.3))
        map_generation.Refinement("after_sizes", 500, refinement_avoid_isolated_smalls(0.4))
        # --- node types
        map_generation.NodeWeights("big", {
            "planet.?": 1  # big signal are always planets
        })
        map_generation.NodeWeights("medium", {
            "planet.?": 50, 
            "structure.asteroid": 25, 
            "structure.forebear_station": 9, 
            "nothing": 25            
        })
        map_generation.NodeWeights("small", {
            "planet.?": 15, 
            "structure.asteroid": 40, 
            "structure.forebear_station": 13, 
            "nothing": 45
        })
        map_generation.NodeRule(self.keep_things_apart)
        map_generation.Refinement("after_node_types", 500, refinement_avoid_planet_voids(0.7))
        map_generation.Refinement("after_node_types", 600, refinement_planet_counts_in_zones(planet_counts))
        map_generation.Refinement("after_node_types", 700, refinement_guarantee_stations(2))
        # --- planet types
        map_generation.PlanetRule(enforce_planet_type_fairness(planet_values, 2))
        map_generation.PlanetRule(self.enforce_planet_variety)
        map_generation.Refinement("after_planet_types", 500, refinement_consistent_link_values_v2(link_values_per_planet))
        map_generation.Refinement("after_planet_types", 510, refinement_ensure_loop())
        map_generation.PlanetWeights(planet_weights)

    @staticmethod
    def prefer_bigger_signals_toward_center(centers):
        def refine(signal, tag, _):
            if tag != "small": return 0
            distance = min((signal.Position - center).magnitude for center in centers)
            return 1.2 - distance / 5
        return refine

    @staticmethod
    def prefer_bigger_if_isolated(signal, tag, gen):
        if tag == "small":
            nearby_nodes = gen.CountNeighbors(signal, 1.8)
            if nearby_nodes < 4:
                return 1.0

    @staticmethod
    def enforce_variety(leeway):
        def rule(signal, tag, gen):
            prop = gen.ProportionAmongNeighbors(signal, 2, tag)
            return prop - leeway
        return rule

    @staticmethod
    def keep_things_apart(signal, tag, gen):
        if tag == "structure.forebear_station" and gen.HasNeighbor(signal, 3, "structure.forebear_station"):
            return 1.0
        if tag == "nothing":
            return gen.CountNeighbors(signal, 1.5, "nothing") * 0.4


    @staticmethod
    def enforce_planet_type_fairness(signal, tag, gen):
        pv = StandardMapgen.PLANET_VALUES
        neighborhood_sum = sum((pv[n.Contents] if n.Contents in pv else 0) for n in ih(gen.Neighbors(signal, 3)))
        my_value = pv[tag]
        penalty = my_value * neighborhood_sum * 2
        return penalty

    @staticmethod
    def enforce_planet_variety(signal, tag, gen):
        return gen.CountNeighbors(signal, 2, tag) * 0.66

class MapgenDefaults:
    def create_zones(self):
        point_counts = [22, 60, 70, 78, 83, 81, 73, 56, 34] # total signal counts in each zone
        planet_counts = [15, 30, 40, 50, 50, 55, 52, 38, 22] # total planet counts in each zone
        link_values_per_planet = [6.6, 6.3, 5.2, 4.4, 3.95, 3.45, 2.55, 1.7, 0.66] # target average planet link value in each zone
        return {
            "zones": Zones.circle(Vector2.zero, 3.1, 24, point_counts),
            "centers": [Vector2.zero],
            "planet_counts": planet_counts,
            "link_values": link_values_per_planet
        }

####################################
# Logging

GENERATION_LOGS = False
def gen_log(*args):
    if GENERATION_LOGS: log(*args)

####################################
# Planet type mix enforcement, generation time

def enforce_planet_type_fairness(planet_values, strength):
    pv = planet_values
    def enforce(signal, tag, gen):
        neighborhood_sum = sum((pv[n.Contents] if n.Contents in pv else 0) for n in ih(gen.Neighbors(signal, 3)))
        my_value = pv[tag]
        penalty = my_value * neighborhood_sum * strength
        return penalty
    return enforce

####################################
# Planet count refinement

def refinement_planet_counts_in_zones(counts_per_zone):
    """The goal of this refinement is to make sure the planet count within each zone falls within certain parameters."""
    # pre-grab some stuff
    slipway_range = constants.Float("slipway.range") # not .Distance() since we use unadjusted distances in generation
    double_sw_range = slipway_range * 2
    double_sw_range_sq = double_sw_range * double_sw_range
    # the actual refinement function
    def refine(gen, _, zones):
        # helpers
        def distance_to_nearest_planet(signal):
            min_distance_sq = double_sw_range_sq
            pos = signal.Position
            for n in gen.Neighbors(signal, double_sw_range):
                distance_sq = (n.Position - pos).sqrMagnitude
                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
            return min_distance_sq
        # logic
        for zone in zones:
            desired_count = counts_per_zone[zone.Index]
            starting_count = sum(1 for s in zone.Signals if s.Contents.startswith("planet."))
            delta = desired_count - starting_count
            if delta < 0:
                # turn some planets into non-planets
                signals = list(s for s in zone.Signals if s.Size == PotentialSize.Medium and s.Contents.startswith("planet."))
                signals.sort(key=distance_to_nearest_planet) # start with ones that are most 'crowded'
                for fixable in signals:
                    fixable.Contents = "nothing"
                    delta += 1
                    if delta == 0: break
            elif delta > 0:
                # turn some non-planets into planets
                signals = list(s for s in zone.Signals if s.Size == PotentialSize.Medium and not s.Contents.startswith("planet."))
                signals.sort(key=distance_to_nearest_planet, reverse=True) # start with ones that are most isolated
                for fixable in signals:
                    fixable.Contents = "planet.?"
                    delta -= 1
                    if delta == 0: break      
            gen_log("Was: %d, Is: %d" % ((desired_count - starting_count), delta))
    # return the function
    return refine

####################################
# "Void" refinements

def refinement_avoid_isolated_smalls(distance_in_slipway_lengths):
    """Bumps up small signals to medium ones in place where there is a danger of creating a 'void' with no planets."""
    # pre-calc
    check_distance = constants.Float("slipway.range") * distance_in_slipway_lengths
    # logic
    def refine(gen, signals, _):
        SIZE_S = PotentialSize.Small
        adjustments_done = 0
        for s in signals:
            # is it ok already?
            if s.Size != SIZE_S: continue
            if any(n.Size != SIZE_S for n in gen.Neighbors(s, check_distance)): continue
            # no, bump it up
            s.Size = PotentialSize.Medium
            s.Contents = "medium"
            adjustments_done += 1
        gen_log("Size bumps: %d" % adjustments_done)
    # return closure
    return refine


def refinement_avoid_planet_voids(distance_in_slipway_lengths):
    """Looks for non-planet medium signals that could only reach two or less planets, then bumps them up to a planet.
    This is an attempt to prevent planet voids from happening, where you scan and get a whole empty region."""
    # pre-calc
    check_distance = constants.Float("slipway.range") * distance_in_slipway_lengths
    # logic
    def refine(gen, signals, _):
        adjustments_done = 0
        SIZE_M = PotentialSize.Medium
        for s in signals:
            # is it ok already?
            if s.Size != SIZE_M: continue
            planet_neighbors = sum(1 for p in gen.Neighbors(s, check_distance) if p.Contents.startswith("planet."))
            if planet_neighbors > 2: continue
            # no, bump it to a planet
            s.Contents = "planet.?"
            adjustments_done += 1
        gen_log("Empty->planet bumps: %d" % adjustments_done)
    # return closure
    return refine

def refinement_avoid_planet_voids_v2(max_distance_in_slipway_lengths):
    check_distance = constants.Float("slipway.range") * max_distance_in_slipway_lengths
    def refine(gen, signals, _):
        adjustments_done = 0
        SIZE_M = PotentialSize.Medium
        for s in signals:
            # is it ok already?
            if s.Size != SIZE_M: continue
            if any(n for n in gen.Neighbors(s, check_distance) if n.Contents.startswith("planet.")): continue
            # no, bump it to a planet
            s.Contents = "planet.?"
            adjustments_done += 1
        gen_log("Empty->planet bumps: %d" % adjustments_done)
    return refine

####################################################
# Node type refinement to ensure forebear stations appearing

def refinement_guarantee_stations(max_distance_between):
    station = "structure.forebear_station"
    slipway_range = constants.Float("slipway.range")
    max_distance = max_distance_between * slipway_range
    def refine(gen, signals, zones):
        # ensure a station in the starting zone
        has_starting_station = any(s.Contents == station for s in zones[0].Signals)
        if not has_starting_station:
            upgraded = next((s for s in zones[0].Signals if s.Contents == "nothing"), None)
            if upgraded:
                upgraded.Contents = station
                gen_log("Added a station to the starting zone.")
        # ensure a consistent minimum density
        stations = [s for s in signals if s.Contents == station]
        added = 0
        for signal in (s for s in signals if s.Size == PotentialSize.Small and s.Contents == "nothing"):
            closest_station = min(stations, key=lambda station: (signal.Position - station.Position).sqrMagnitude)
            distance = (signal.Position - closest_station.Position).magnitude
            if distance > max_distance:
                signal.Contents = station
                added += 1
        gen_log("Added stations: %d" % added)
    return refine


###############################################################
# Node type refinement for placing custom structures

def refinement_place(node_type, distance_range, pot_size):
    """Replaces a random potential of the right size in the given distance range with a node of the given type."""
    slipway_range = constants.Float("slipway.range")
    min_dsr, max_dsr = distance_range
    min_distance = slipway_range * min_dsr
    max_distance = slipway_range * max_dsr
    def refine(gen, signals, zones):
        candidate = None
        retries = 8
        min_distance_sq = min_distance * min_distance
        max_distance_sq = max_distance * max_distance
        while candidate is None and retries > 0:
            for s in signals:
                if s.Size != pot_size: continue
                if s.Contents != "nothing": continue
                dist_sq = s.Position.sqrMagnitude
                if dist_sq < min_distance_sq or dist_sq > max_distance_sq: continue
                candidate = s
                break
            if candidate is None:
                min_distance_sq *= 0.8
                max_distance_sq *= 1.25
                retries -= 1
        if candidate is None:
            raise Exception("Could not place %s anywhere." % node_type)
        candidate.Contents = node_type
        gen_log("Placed %s." % node_type)
    return refine

def refinement_sprinkle_quirk(quirk, node_types, zone_density, maximize_distances = False):
    """Adds a quirk to planets."""
    def refine(gen, signals, zones):
        rng = gen.RNGForTask("sprinkle_%s" % quirk)
        total_added = 0
        for z in zones:
            density = zone_density
            if callable(density): density = density(z.Index)
            candidates, all = [], []
            for s in z.Signals:
                if s.Contents.startswith("planet."):
                    all.append(s)
                    if s.Contents in node_types:
                        candidates.append(s)
            gen_log("%d / %d" % (len(candidates), len(all)))
            added_count = math.ceil(len(all) * density)
            if len(candidates) < added_count:
                log("Warning: Not enough candidates in zone %s to add the '%s' quirk." % (z, quirk))
                added_count = len(candidates)
            if added_count == 0: continue
            if maximize_distances:
                best_set, best_dist = None, 0
                for i in range(10):
                    targets = list(Randomness.PickMany(rng, candidates, added_count))
                    closest_dist = 100000.0
                    for j in range(len(targets)):
                        for k in range(j+1, len(targets)):
                            a, b = targets[j], targets[k]
                            dist = (a.Position - b.Position).sqrMagnitude
                            if dist < closest_dist: closest_dist = dist
                    if closest_dist > best_dist:
                        best_set, best_dist = targets, closest_dist
                targets = best_set
            else:
                targets = Randomness.PickMany(rng, candidates, added_count)
            for t in targets:
                t.Quirk = quirk
                total_added += 1
        gen_log("Added '%s' quirk %d times." % (quirk, total_added))
    return refine

####################################################
# Planet type refinement for consistent link values

def refinement_consistent_link_values_v2(target_lvpp_per_zone):
    """Tries to make planet combinations more consistent and fair by pulling
       the average 'link value' per planet in each zone to a target number."""
    # pre-calc
    planet_types = ["planet." + kind for kind in [
        "earthlike", "mining", "remnant", "ocean", "factory", "primordial", "jungle",
        "ice", "barren", "arid", "swamp", "arctic", "lava"
    ]]
    planet_change_dislike = {}
    for pt in planet_types:
        planet_change_dislike[pt] = 0.0
    planet_change_dislike["planet.factory"] = 0.6
    planet_change_dislike["planet.remnant"] = 0.2
    planet_change_dislike["planet.arid"] = -0.5
    check_distance = constants.Float("slipway.range")
    distance_scale = constants.Float("distance.scale")
    obstruction_radius = constants.Float("planet.obstruction.radius")
    # logic
    def refine(gen, signal, zones):
        # neighbors cache
        neighbors_cache = {}        
        values_cache = {}
        # helpers
        def obstructed(a, b, obstacles):
            apos, bpos = a.Position, b.Position
            for o in obstacles:                
                if Intersecting.SegmentIntersectsCircleLenient(apos, bpos, o.Position, obstruction_radius) and o != a and o != b:
                    return True
            return False
        def get_neighbors_for(signal):
            if not signal in neighbors_cache:
                all_ns = [n for n in gen.Neighbors(signal, check_distance) if n.Contents.startswith("planet.")]                
                unobstructed_ns = [n for n in all_ns if not obstructed(signal, n, all_ns)]       
                neighbors_cache[signal] = unobstructed_ns
            return neighbors_cache[signal]
        def get_total_link_value(signal):
            if not signal in values_cache:
                neighbors = get_neighbors_for(signal)
                value = sig_total_linkv2_value_with(signal, neighbors, check_distance)
                values_cache[signal] = value
            return values_cache[signal]
        def invalidate_caches(changed_node):
            neighbors = get_neighbors_for(changed_node)
            del values_cache[changed_node]
            for n in neighbors:
                del values_cache[n]
        def assess_change_effect(signal, new_planet_type):
            # get neighbors            
            neighbors = get_neighbors_for(signal)
            # calculate old link value
            old_value = get_total_link_value(signal)
            old_neighbors = sum(get_total_link_value(n) for n in neighbors)
            # store old contents and swap them
            old_contents = signal.Contents
            signal.Contents = new_planet_type
            # calculate the new link value for this signal
            new_value = sig_total_linkv2_value_with(signal, neighbors, check_distance)
            new_neighbors = sum(sig_total_linkv2_value_with(n, get_neighbors_for(n), check_distance) for n in neighbors)
            # restore old state
            signal.Contents = old_contents
            # return global change
            # THIS IS NOT ENTIRELY CORRECT, since the neighbors might belong to other zones
            # (thus not influencing our zone's total link value). We do count other-zone neighbors
            # here (despite it being technically incorrect), for performance and design reasons -
            # improving other-zone neighbors is almost as good as in-zone ones and much easier to track.
            return new_value - old_value + new_neighbors - old_neighbors       
        def total_link_value(signals):
            return sum(sig_total_linkv2_value_with(s, get_neighbors_for(s), check_distance) for s in signals)
        # actual logic
        zones = list(zones)
        zones.reverse() # work from the outside
        for zone in zones:
            planets = [p for p in zone.Signals if p.Contents.startswith("planet.")]
            planet_count = len(planets)
            total_lv = total_link_value(planets)
            desired_lv = planet_count * target_lvpp_per_zone[zone.Index]
            lv_per_planet = total_lv / (planet_count if planet_count > 0 else 1)
            gen_log("%s: %.2f link value, %.2f desired, %.2f per planet" % (zone, total_lv, desired_lv, lv_per_planet))
            changes = 0
            planets.sort(key = lambda p: planet_change_dislike[p.Contents] + (p.Position.x - math.floor(p.Position.x)))
            for p in planets:
                # calculate what effect we want
                delta = desired_lv - total_lv
                if abs(delta) < 3.5: break
                desired_fraction = lerp_clamped(1, 0.25, inverse_lerp(2.5, 20, abs(delta)))
                desired_change = delta * desired_fraction
                # look for the best possible change to make
                best_change, best_error = (p.Contents, 0), abs(desired_change)
                for potential_type in planet_types:
                    if potential_type == p.Contents: continue
                    effect = assess_change_effect(p, potential_type)
                    error = abs(desired_change - effect)
                    if error < best_error:
                        # increase error for repetitions and check again (we try to avoid too many repeated planet types)
                        repeated_planet_types = sum(1 for n in get_neighbors_for(p) if n.Contents == potential_type)
                        error += repeated_planet_types * 2
                        if error < best_error:
                            best_change, best_error = (potential_type, effect), error
                # did we find a good change?
                target_kind, effect = best_change
                if abs(effect) >= 3.5:
                    actual_effect = effect
                    gen_log("Changing %s[%s] -> %s, %.1f -> %.1f" % (p.Contents, p.Position * f(distance_scale), target_kind, total_lv, total_lv + actual_effect))
                    changes += 1
                    p.Contents = target_kind
                    invalidate_caches(p)
                    total_lv += actual_effect
            if GENERATION_LOGS:
                final_total = total_link_value(planets)    
                gen_log("Total planet type changes: %d, final link value: %.2f" % (changes, final_total))
    # return closure
    return refine        

####################################################
# Guaranteeing a loop

def refinement_ensure_loop():
    replacements = [
        ("ice", "arctic"),
        ("barren", "arid"),
        ("lava", "factory"),
        ("mining", "remnant"),
        ("arid", "remnant"),
        ("ocean", "primordial"),
        ("jungle", "primordial"),
        ("primordial", "earthlike"),
        ("swamp", "earthlike"),
        ("arctic", "earthlike"),
        ("ice", "primordial"),
        ("ice", "remnant"),
        ("lava", "primordial"),
        ("lava", "remnant")
    ]
    def refine(gen, signals, zones):
        if gen.SeedVersion < 2:
            return
        gen_log("Loop guarantee enabled.")
        last_speculation = None
        loop_found = False
        rng = gen.RNGForTask("ensure_loop")
        retries = 100
        max_distance = constants.Float("map.loop_range")
        if max_distance <= 0:
            return
        while (not loop_found) and (retries > 0):
            retries -= 1
            loop = gen.FindViableLoop(zones[0], max_distance)
            if not loop:
                extension = gen.FindExtensionForViableLoop(rng, zones[0], 0.82)
                if extension:
                    gen_log("Refining with a loop: %s[%s] -> %s." % (extension.victim.Signal.Contents, extension.victim.Signal.Position, extension.planetKind))
                    extension.victim.Signal.Contents = "planet." + extension.planetKind
                    loop_found = True
                else:
                    gen_log("Failed to loop a map, looking for replacement.")
                    # undo last speculative change
                    if last_speculation is not None:
                        last_speculation[0].Contents = last_speculation[1]
                        last_speculation = None
                    # try new change
                    replacement_order = Randomness.Pick(rng, replacements)
                    replaced_kind = "planet.%s" % replacement_order[0]
                    target_kind = "planet.%s" % replacement_order[1]
                    possible_victims = [s for s in zones[0].Signals if s.Contents == replaced_kind]
                    if len(possible_victims) == 0:
                        continue
                    victim = Randomness.Pick(rng, possible_victims)
                    victim.Contents = target_kind
                    gen_log("Tried %s[%s] -> %s" % (replaced_kind, victim.Position, target_kind))
                    last_speculation = (victim, replaced_kind)
            else:
                loop_found = True                
        if retries == 0:
            log("Loop guarantee was not upheld.")
        else:
            gen_log("Stable loop found.")
    return refine
