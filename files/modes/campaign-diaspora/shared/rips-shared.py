##############################################
# Map generation

def refinement_add_rip_effects(settings):
    applied_quirk = settings.get("apply_quirk", None)

    def refine(gen, signals, zones):
        distance_scale = constants.Float("distance.scale")

        def remove_planets_in_joint(joint):
            center = joint.Center / distance_scale
            radius = joint.Radius / distance_scale
            remove_distance = radius + 0.15
            sigs_to_remove = list(gen.SignalsNear(center, remove_distance))
            for sig in sigs_to_remove:
                gen.RemoveSignal(sig)

        def affect_planets_close_to_rip(rip_points):
            sigs_to_remove = []
            affected = {}
            for p in rip_points:
                pt = p.position / distance_scale
                remove_distance = p.width / distance_scale + 0.13
                scan_distance = remove_distance + 1.2
                for sig in gen.SignalsNear(pt, scan_distance):
                    dist = (pt - sig.Position).magnitude
                    if dist <= remove_distance:
                        sigs_to_remove.append(sig)
                        affected.pop(sig, None)
                    else:
                        affected[sig] = min(affected.get(sig, 1000), dist)            
            # remove signals that fall into the rip
            for s in sigs_to_remove:
                gen.RemoveSignal(s)
            # add quirks to planets close to the rip, if settings say so
            if applied_quirk is not None:
                quirks_added = 0
                min_distance_between_quirked = 2.2
                for sig, dist in affected.items():
                    sig_zone = rips.Zones.ZoneForPoint(sig.Position * distance_scale)
                    if sig.Contents.startswith("planet."):
                        neighbors = gen.Neighbors(sig, min_distance_between_quirked)
                        quirk_present_nearby = any(n.Quirk == applied_quirk and rips.Zones.ZoneForPoint(n.Position * distance_scale) == sig_zone for n in neighbors)
                        if not quirk_present_nearby:
                            sig.Quirk = applied_quirk
                            quirks_added += 1

        for rip in rips.RipDefinitions:
            affect_planets_close_to_rip(rip.GenerateSubdividedPoints(5))
        for joint in rips.JointDefinitions:
            remove_planets_in_joint(joint)
    # return nested method from factory function
    return refine


def refinement_place_rips(count, min_length, max_length, forced_close = [], settings = None):
    distance_scale = constants.Float("distance.scale")
    settings = settings or {}
    min_distance = settings.get("min_distance", 0)
    max_distance = settings.get("max_distance", 23)
    def refine(gen, signals, zones):
        def rescale_points(points):
            return [p * distance_scale for p in points]
        def random_point_to_keypoint(p, prev_point):
            closest_sigs = list(s for s in gen.SignalsNear(p, 2))
            closest_sigs.sort(key=lambda sig: (sig.Position - p).sqrMagnitude)
            if len(closest_sigs) < 2: return None
            a = closest_sigs[0]
            b = closest_sigs[1]
            if a in total_used_sigs or b in total_used_sigs: return None
            theta = Randomness.Float(rng, 0.4, 0.6)
            # keep normals on a consistent side for easier generation
            if prev_point is not None:
                dir = (b.Position - a.Position)
                normal = Vector2(dir.y, -dir.x)
                side = Vector2.Dot(normal, prev_point - a.Position)
                if side > 0:
                    a, b = b, a
            dir = (b.Position - a.Position)
            normal = Vector2(dir.y, -dir.x).normalized
            return {"sigs": (a, b), "point": Vector2.Lerp(a.Position, b.Position, theta), "normal": normal}
        def extend_keypoint(key, direction):
            p = key["point"]
            rot_normal = rotate_vector(key["normal"], Randomness.Float(rng, -30, 30))
            base_distance = (key["sigs"][1].Position - key["sigs"][0].Position).magnitude
            new_point = p + rot_normal * f(base_distance) * f(direction) * Randomness.Float(rng, 0.2, 0.4)
            return {"sigs": key["sigs"], "point": new_point, "normal": rot_normal}
        def add_inbetweens(points, max_distance, rng, fudge):
            fudge = f(fudge)
            result = [points[0]]
            for i in xrange(len(points) - 1):
                a, b = points[i], points[i+1]
                dist = (a - b).magnitude
                if dist > max_distance:
                    cut_into = math.ceil(dist / max_distance)
                    step = 1.0 / cut_into
                    t = step
                    for cut in xrange(cut_into):
                        between_pt = Vector2.Lerp(a, b, t)
                        fudge_factor = Randomness.PointOnUnitCircle(rng) * fudge
                        result.append(between_pt + fudge_factor)
                        t += step
                else:
                    result.append(b)
            return result

        rng = gen.RNGForTask("rip_placement")
        placed_rips = []
        total_used_sigs = set()
        spatial_index = SpatialAABBIndex.Create(f(4), GeneratedRip.aabb)
        # do N rips
        for rip_index in range(count):
            retries = 40
            keys = None
            while retries > 0:
                retries -= 1
                target_length = min_length + math.pow(Randomness.Float(rng, 0, 1), 2) * (max_length - min_length)
                # new start point
                rip_max_distance = max_distance if rip_index >= len(forced_close) else forced_close[rip_index]
                rip_min_distance = min_distance
                rip_spread = rip_max_distance - rip_min_distance
                base_v = Vector2.zero
                while base_v.sqrMagnitude < 0.01:
                    base_v = Randomness.PointInsideUnitCircle(rng)
                start_point = base_v.normalized * f(rip_min_distance) + base_v * f(rip_spread)
                start_key = random_point_to_keypoint(start_point, None)
                if start_key is None: continue
                # get more points
                keys = [start_key]
                signals_used_here = set(start_key["sigs"])
                total_length = 0.0
                failed = False
                # loop: lengthen the rip until we reach target length
                while total_length < target_length:
                    # loop: look for the next point up to N times
                    inner_retries = 20
                    last_key = keys[-1]
                    base_distance = (last_key["sigs"][0].Position - last_key["sigs"][1].Position).magnitude
                    while inner_retries > 0:
                        inner_retries -= 1
                        angle = Randomness.Float(rng, -30, 30)
                        rot_normal = rotate_vector(last_key["normal"], angle)
                        distance = Randomness.Float(rng, 0.5, 1.5) * base_distance
                        ref_point = last_key["point"] + rot_normal * distance
                        new_key = random_point_to_keypoint(ref_point, last_key["point"])
                        if new_key is None: continue
                        if new_key["sigs"][0] in signals_used_here and new_key["sigs"][1] in signals_used_here:
                            continue
                        # check the implied angles to see if we're not turning too sharply
                        if len(keys) >= 2:
                            dir_1 = (keys[-1]["point"] - keys[-2]["point"]).normalized
                            dir_2 = (new_key["point"] - keys[-1]["point"]).normalized
                            angle_too_big = Vector2.Dot(dir_1, dir_2) < 0.3
                            if angle_too_big:
                                continue
                        # found a new point
                        keys.append(new_key)
                        #signals_used_here.update(new_key["sigs"])
                        total_length += (new_key["point"] - last_key["point"]).magnitude
                        break
                    # did we fail completely, or is the rip just a bit shorter than we wanted?
                    if inner_retries == 0:
                        failed = total_length < target_length and total_length < min_length
                        break
                if not failed:
                    # create the rip
                    pre_point = extend_keypoint(keys[0], -1)
                    post_point = extend_keypoint(keys[-1], 1)
                    keys = [pre_point] + keys + [post_point]
                    points = rescale_points([k["point"] for k in keys])
                    points = add_inbetweens(points, 1.7, rng, 0.4)
                    # check for collisions/problem
                    new_rip = GeneratedRip(points)
                    too_close_to_wormhole = any(p.sqrMagnitude < 1 for p in new_rip.points())
                    cross_detected = any(rip.crosses(new_rip) for rip in spatial_index.CrossingBoundingBoxesWith(new_rip))
                    if too_close_to_wormhole or cross_detected: continue
                    # everything ok, append!
                    total_used_sigs.update(signals_used_here)
                    placed_rips.append(new_rip)
                    spatial_index.Add(new_rip)
                    break
            if retries == 0:
                log("Had to finish at %d rips, can't place another one." % rip_index)
        # store the rip information for instantiation and restoring
        game.CustomData.Set("rip_placement", [pr.points() for pr in placed_rips])
    return refine

def refinement_instantiate_rips(gen, signals, zones):
    generate_rips(rips)

def generate_rips_from_stored_points(rip_manager):
    def generate_points(rip_data):
        count = len(rip_data)
        t_step = 1.0 / (count - 1)
        point_t = 0.0
        for point_pos in rip_data:
            yield (point_pos, point_t)
            point_t += t_step
    # recreate rips from stored data, if present
    # if not, skip it (we'll generate and instantiate the rips during mapgen in a second)
    ALPHA, TENSION = 0.5, 0.0 # spline parameters
    rips_data = game.CustomData.GetOr("rip_placement", None)
    if rips_data is None: return
    length_scale = 0.1
    rng = Randomness.SeededRNG("rip_widths")
    for index, rip_data in enumerate(rips_data):
        points = list(generate_points(rip_data))
        total_length = sum((points[i+1][0] - points[i][0]).magnitude for i in range(len(points)-1))
        max_width = 0.17 + 0.35 * inverse_lerp_clamped(6, 20, total_length)
        actual_width = Randomness.Float(rng, 0.8, 1.2) * max_width    
        rip = rip_manager.AddRip("rip%d" % index, req_spline(points, length_scale, ALPHA, TENSION), f(0.0), f(length_scale), len(points) * 2)
        rip.SetBaseWidth(actual_width)
        rip.TaperBothEnds().Commit()
    # no zones or joints for this one, that's it

def req_predefined_points(points, length_scale):
    count = len(points)
    def point(point_t):
        # rescale point_t to 0-1
        point_t /= length_scale
        # bisect to find the right segment
        before, after = 0, count - 1
        while after - before > 1:
            mid = ((before + after) / 2)
            mid_t = points[mid][1]
            if mid_t <= point_t:
                before = mid
            else:
                after = mid
        # interpolate within the segment
        bpos, bt = points[before]
        apos, at = points[after]
        place_between_points = inverse_lerp(bt, at, point_t)
        return Vector2.LerpUnclamped(bpos, apos, place_between_points)
    return point

def req_spline(points, length_scale, alpha, tension):
    def make_piece(p0, p1, p2, p3):
        return CatmullRom(p0, p1, p2, p3, alpha, tension)    
    count = len(points)
    # prepare the spline
    pieces = []
    ps = [p[0] for p in points]
    pre_point = ps[0] + (ps[0] - ps[-1]).normalized
    post_point = ps[-1] + (ps[-1] -ps[0]).normalized
    pieces.append(make_piece(pre_point, ps[0], ps[1], ps[2]))
    for i in xrange(1, len(ps) - 2):        
        pieces.append(make_piece(ps[i-1], ps[i], ps[i+1], ps[i+2]))
    pieces.append(make_piece(ps[-3], ps[-2], ps[-1], post_point))
    # the actual calculation
    def evaluate(point_t):
        # rescale point_t to 0-1
        point_t /= length_scale
        # bisect to find the right segment
        before, after = 0, count - 1
        while after - before > 1:
            mid = ((before + after) / 2)
            mid_t = points[mid][1]
            if mid_t <= point_t:
                before = mid
            else:
                after = mid
        # interpolate within the segment
        bpos, bt = points[before]
        apos, at = points[after]
        piece = pieces[before]
        piece_t = inverse_lerp(bt, at, point_t)
        return piece.Evaluate(piece_t)        
    return evaluate

class GeneratedRip:
    SAFETY_RADIUS = 1.5
    def __init__(self, points):
        self._ps = points
        self._collision_ps = self._extend_points(points, self.SAFETY_RADIUS)
        self._aabb = self._calculate_aabb(self._collision_ps)

    def _calculate_aabb(self, points):
        fudge = self.SAFETY_RADIUS
        base = CollidingPolygon.CalculateAABB(points)
        return Rect(base.min - Vector2(fudge, fudge), base.size + Vector2(fudge * 2, fudge * 2))

    def _extend_points(self, points, length):
        extended = list(points)
        first_dir = (points[1] - points[0]).normalized
        pre_point = points[0] - first_dir * f(length)
        last_dir = (points[-1] - points[-2]).normalized
        post_point = points[-1] + last_dir * f(length)
        extended.insert(0, pre_point)
        extended.append(post_point)
        return extended

    def crosses(self, other):
        SAFETY_RADIUS = f(self.SAFETY_RADIUS)
        ps, ops = self.collision_points(), other.collision_points()
        p_count, op_count = len(ps), len(ops)
        for pi in range(p_count - 1):
            me_a, me_b = ps[pi], ps[pi+1]
            for opi in range(op_count - 1):
                o_a, o_b = ops[opi], ops[opi+1]
                if Intersecting.SegmentsIntersect(me_a, me_b, o_a, o_b):
                    return True            
            for o_p in ops:
                if Intersecting.SegmentIntersectsCircleStrict(me_a, me_b, o_p, SAFETY_RADIUS):
                    return True
        for me_p in ps:
            for opi in range(op_count - 1):
                o_a, o_b = ops[opi], ops[opi+1]
                if Intersecting.SegmentIntersectsCircleStrict(o_a, o_b, me_p, SAFETY_RADIUS):
                    return True
        return False

    def points(self): return self._ps
    def aabb(self): return self._aabb
    def collision_points(self): return self._collision_ps

###############################################
# Rip equation functions

def req_ellipse(x, y, rx, ry):
    center = Vector2(x, y)
    cos, sin = math.cos, math.sin
    return lambda t: center + Vector2(rx * cos(t), ry * sin(t))

def req_ellipse_inv(x, y, rx, ry):
    center = Vector2(x, y)
    cos, sin = math.cos, math.sin
    return lambda t: center + Vector2(-rx * cos(t), ry * sin(t))

def req_line(x, y, dx, dy):
    start = Vector2(x, y)
    dir = Vector2(dx, dy)
    return lambda t: start + dir * t

def req_add_wave(original_eq, offset, width, amplitude):
    sin = math.sin
    coeff = 2.0 * math.pi / width
    def adjusted(t):
        pt = original_eq(t)
        pt_next = original_eq(t + f(0.005))
        dir = (pt_next - pt).normalized
        normal = Vector2(dir.y, -dir.x)
        wave = sin(t * coeff + offset) * amplitude
        return pt + normal * f(wave)
    return adjusted

def req_mix(eq1, eq2, t_limit):
    PI, cos = math.pi, math.cos
    def ease(alpha):
        return -(cos(PI * alpha) - 1) / 2
    def mixed(t):
        alpha = clamp(0, 1, abs(t) / t_limit)
        alpha = ease(alpha)
        return Vector2.Lerp(eq1(t), eq2(t), alpha)
    return mixed

#########################################################
# Bridges

def rip_zones_in_use():
    return rips.Zones.UsedInThisScenario()

def bridge_upgrade(node, industry, level):
    energy_required = constants.Int("bridge.require_energy") > 0
    if level == 1 and energy_required:
        return needs_only(node, industry, level)
    if level == 1 and not energy_required:
        return Permission.Yes() # auto-upgrade to 1st level

def bridge_placement():
    return [ScriptedPlacement(BridgePlacementRules)]

def bridge_obstructed_by(planned, model):
    return not rips.IsRip(model)

def bridge_active(node):
    return node.Level >= 1

def bridge_cuts_trees(node):
    return True

def bridge_placed(node):
    # spawn the other end
    commands.IssueScriptedConsequence(PlaceBridgeCounterpart(node))

def bridge_upkeep(node):
    if node.Level != 1: return
    counterpart = node.CustomData.Get("counterpart")

def bridge_node_tag(node, blocks):
    # hide the needs after activated
    if node.Level < 1: return blocks.DefaultText()
    return ""

def bridge_level_changed(node):
    if node.Level != 1: return
    # establish connection to counterpart
    counterpart = node.CustomData.Get("counterpart")
    build = BuildConnection(world, node, counterpart, connection_kinds.Slipway)
    build.MaterialIndex = 4
    free_build = MakeImplicitAndFree(build)
    commands.Issue(free_build)

def bridge_end_level_changed(node):
    if node.Level == 1:
        if rip_zones_in_use():
            commands.IssueScriptedConsequence(ConsUnlockZone(node))
        game.FOW.AnimatedDiscover(node)
    elif node.Level == 0 and node.CustomData.GetOr("last_level_seen", -1) > 0:
        game.FOW.Rebuild()
    node.CustomData.Set("last_level_seen", node.Level)

def bridge_end_model(): return "Bridge"

def bridge_end_upgrade(node, industry, level):
    if level == 1:
        counterpart = node.CustomData.Get("counterpart")
        if game.Reachability.AreConnected(node, counterpart):
            return Permission.Yes()
        else:
            return Permission.No(LS("structure.bridge.power_up_other_end"))
    else:
        return Permission.NoWithNoReason()

def bridge_connectivity(node, other):
    if node.NodeType == "structure.bridge_end" and node.Level < 0:
        return NodeConnectivity.Rejects(LS("structure.bridge.inactive"))
    counterpart = node.CustomData.Get("counterpart")
    connection_count = sum(1 for c in node.Connections if c.OtherEnd(node) != counterpart)
    if connection_count >= constants.Int("bridge.connections_per_side"):
        return NodeConnectivity.Rejects(LS("structure.relay.too_many_connections"), 0)
    else:
        return NodeConnectivity.Accepts(0)

class RipEdgePlacementRules:
    @staticmethod
    def point_parameters(rip_point, pos):
        normal = rip_point.normal
        dist_along_normal = Vector2.Dot(pos - rip_point.position, normal)
        reference_point = pos - rip_point.normal * dist_along_normal
        absolute_dist = (reference_point - rip_point.position).magnitude
        return (reference_point, normal, dist_along_normal, absolute_dist)
    
    @staticmethod
    def beyond_end_of_the_rip(rip_point, reference_point):
        if rip_point.rip.IsFirst(rip_point):
            if Vector2.Dot(rip_point.direction, reference_point - rip_point.position) < 0:
                return True, "first"
        if rip_point.rip.IsLast(rip_point):
            if Vector2.Dot(rip_point.direction, reference_point - rip_point.position) > 0:
                return True, "last"
        return False, None

    @staticmethod
    def adjust_position(pos, ps, iterations = 4):
        rip_point = rips.ClosestRipPoint(pos, allowJoints = True)
        if not rip_point or not rip_point.rip: return pos
        reference_point, normal, dist_along_normal, absolute_dist = RipEdgePlacementRules.point_parameters(rip_point, pos)
        beyond_end, which_end = RipEdgePlacementRules.beyond_end_of_the_rip(rip_point, reference_point)
        # special casing for the very tips of rips
        if beyond_end:
            if absolute_dist > 0.3:
                return pos
            else:
                pos = rip_point.position
                sign = -1 if which_end == "first" else 1
                return rip_point.position + rip_point.direction * f(0.07) * f(sign)
        # not on the tip, but rather along the edge
        sign = -1 if dist_along_normal < 0 else 1 
        if (abs(dist_along_normal) - rip_point.width <= 0.9):
            factor = 1.06 * sign
            while True:
                adjusted = reference_point + normal * rip_point.width * f(factor)
                collision_point = CollidingCircle(adjusted, 0.001)
                obstructions = game.Collisions.FindCollidingObstructions(collision_point, lambda other: rips.IsRip(other.Owner))
                if sum(1 for o in obstructions) == 0: break
                factor += 0.02 * sign
                if factor >= 1.5:
                    return pos
            # did we switch to a different point?
            new_closest = rips.ClosestRipPoint(adjusted, allowJoints = True)
            if new_closest != rip_point and iterations > 0:
                return RipEdgePlacementRules.adjust_position(adjusted, ps, iterations - 1)
            else:
                return adjusted
        else:
            return pos

    @staticmethod
    def is_permitted(pos, ps):
        rip_point = rips.ClosestRipPoint(pos, allowJoints = True)
        if not rip_point: return Permission.No(LS("structure.bridge.build_on_edge"))
        if not rip_point.rip: return Permission.No(LS("structure.bridge.not_on_junctions"))
        reference_point, normal, dist_along_normal, absolute_dist = RipEdgePlacementRules.point_parameters(rip_point, pos)
        beyond_end, which_end = RipEdgePlacementRules.beyond_end_of_the_rip(rip_point, reference_point)
        if beyond_end and absolute_dist > 0.15:
            return Permission.No(LS("structure.bridge.build_on_edge"))
        # are we properly on an edge?
        dist = dist_along_normal / rip_point.width
        #log("%s %s %s -> %.2f[%.2f] @ %s // %.2f" % (rip_point.index, rip_point.t, rip_point.direction, dist_along_normal, dist, normal, absolute_dist))
        if abs(dist) > 1.6:
            return Permission.No(LS("structure.bridge.build_on_edge"))
        # everything checks out
        return Permission.Yes()

class BridgePlacementRules:
    @staticmethod
    def adjust_position(pos, ps):
        return RipEdgePlacementRules.adjust_position(pos, ps)

    @staticmethod
    def is_permitted(pos, ps):
        standard = RipEdgePlacementRules.is_permitted(pos, ps)
        if standard.Allowed:
            # check if we have room for the terminal
            other_edge = rips.OtherEdgeOfTheRip(pos)
            other_edge = BridgePlacementRules.adjust_position(other_edge, None)
            collision_point = CollidingCircle(other_edge, 0.4)
            obstructions = game.Collisions.FindCollidingObstructions(collision_point, lambda other: not rips.IsRip(other.Owner) and not other.Owner == ps)
            if sum(1 for o in obstructions) > 0:
                return Permission.No(LS("structure.bridge.obstructed_on_the_other_end"))
            # everything checks out
            return Permission.Yes()
        else:
            return standard # standard rules already disallow this

class PlaceBridgeCounterpart:
    def __init__(self, bridge_node):
        self._bridge = bridge_node

    def apply(self):
        other_edge = rips.OtherEdgeOfTheRip(self._bridge.Position)
        other_edge = BridgePlacementRules.adjust_position(other_edge, None) # prevent obstruction by rip itself
        self._counterpart = Structure(other_edge, StructureKind.All["bridge_end"])
        world.Add(self._counterpart)
        # assign counterpart to the right zone (if using zones)
        if rip_zones_in_use():
            RespectZones.assign_zone_to_node({"node": self._counterpart})
        # safe to do it like that, since revert will just delete both
        self._bridge.CustomData.Set("counterpart", self._counterpart)
        self._counterpart.CustomData.Set("counterpart", self._bridge)

    def revert(self):
        self._counterpart.Discard()

class BridgeUpkeep:
    MIN_COST, MAX_COST = 6, 15
    MIN_DISTANCE, MAX_DISTANCE = 0.5, 1.5
    def name(self): return LS("quality.bridge_upkeep", "Bridge upkeep")
    def desc(self): return LS("quality.bridge_upkeep.desc",
        "Rift bridge upkeep depends on the distance between the two terminals.")

    def effects(self, node):
        if node.Level < 1: return
        counterpart = node.CustomData.Get("counterpart")
        total_distance = (counterpart.Position - node.Position).magnitude
        cost_factor = (total_distance - self.MIN_DISTANCE) / (self.MAX_DISTANCE - self.MIN_DISTANCE)
        cost_factor = clamp(0.0, 1.0, cost_factor)
        cost = lerp(self.MIN_COST, self.MAX_COST, cost_factor)
        cost *= constants.Float("bridge.upkeep_factor")
        cost = round(cost)
        return [ResourceFlow.Cash(-cost, FlowCategory.StructureUpkeep)]

class ConsUnlockZone:
    def __init__(self, node):
        self._node = node
    def zone(self):
        return rips.Zones.ZoneByName(self._node.CustomData.Get("zone"))
    def apply(self):
        self.zone().AddUnlocker(self._node)
    def revert(self):
        self.zone().RemoveUnlocker(self._node)
