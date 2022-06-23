
def refinement_generate_hole(dimensions, variation):    
    def refine(gen, signals, zones):
        points = []
        radians = 0
        radian_step = math.pi / 180.0
        rng = gen.RNGForTask("hole_generation")
        noise_y = Randomness.Float(rng, 0.0, 1.0)
        for angle in range(360):
            dir = Vector2(math.cos(radians), -math.sin(radians))
            base_pos = Vector2.Scale(dimensions, dir)
            noise = game.Noise.GetNoise(angle / 360.0, noise_y)
            depth = 1.0 + noise * variation
            pos = base_pos * f(depth)
            points.append(pos)
            radians += radian_step
        points.append(points[0]) # duplicate the first point at the end to close the loop
        # instantiate the hole
        game.CustomData.Set("hole_points", points)        
    return refine

def refine_remove_signals_in_hole(inverted):
    def remover(gen, signals, zones):
        inv_distance_scale = f(1.0 / constants.Float("distance.scale"))
        hole_pos = game.CustomData.Get("hole_position") 
        points = [(hole_pos + pt) * inv_distance_scale for pt in game.CustomData.Get("hole_points")]    
        poly = CollidingPolygon(points)
        affected = []
        for sig in signals:
            circ = CollidingCircle(sig.Position, 0.3)
            removed = not poly.FullyContainsCircle(circ) if inverted else poly.CollidesWith(circ)
            if removed:
                affected.append(sig)
        for sig in affected:
            gen.RemoveSignal(sig)
    return remover

#########################################
# Conditions

class EatSignalsOnDiscovery(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.AfterPotentialBecameVisible, self.new_potential)

    def new_potential(self, data):
        if commands.IsReverting: return
        pot = data["potential"]
        hole = game.Nodes.FirstWithType("special.hole")
        if hole.ContainsPoint(pot.Position):
            pot.Discard()

class DestroyConsumedObjects:
    def __init__(self, area):
        self._area = area
        self._hole = game.Nodes.FirstWithType("special.hole")
        self._inverted = self._hole.IsInverted

    def consume_radius(self, thing):
        if isinstance(thing, Potential):
            return thing.ObjectRadius * (0.73 if not self._inverted else 1.2)
        else:
            return thing.ObjectRadius * (0.75 if not self._inverted else 1.2)

    def node_gets_eaten(self, node):        
        is_planet = node.NodeType.startswith("planet.")
        if is_planet: return True
        is_structure = node.NodeType.startswith("structure.")
        if is_structure:
            if node.NodeType == "structure.rift_wall" or node.NodeType == "structure.pylon" or node.NodeType == "structure.powered_pylon":
                return False
            return True
        return False

    def calculate_endangered_objects(self):
        endangered_stuff = []
        poly = CollidingPolygon(self._area)
        rule = self.circle_collision_rule(poly, self._hole.IsInverted)
        things = list(game.Nodes.PotentialsWithin(self._hole.Position, self._hole.Reach))
        things += (n for n in game.Nodes.Within(self._hole.Position, self._hole.Reach) if self.node_gets_eaten(n))
        for thing in things:
            circle = CollidingCircle(thing.Position, self.consume_radius(thing))
            if rule(circle):
                endangered_stuff.append(thing)
        return endangered_stuff

    def circle_collision_rule(self, poly, inverted):
        if inverted:
            return lambda c: not poly.FullyContainsCircle(c)
        else:
            return lambda c: poly.CollidesWith(c)

    def apply(self):
        endangered = list(self.calculate_endangered_objects())
        loss_trigger = LoseBecauseSomethingGotEaten.find_loss_object_if_present(endangered)
        if loss_trigger is not None:
            commands.IssueScriptedConsequence(LoseBecauseSomethingGotEaten(loss_trigger))
            self._dead = []
        else:
            self._dead = list(endangered)
            for thing in endangered:
                if isinstance(thing, Planet):
                    AnimationEvents.TriggerAnimationWithData(thing, "ConsumedByRift", "rift", self._hole)
                    thing.Discard()
                elif isinstance(thing, Potential):
                    thing.Dissolve()
                elif thing.NodeType == "structure.asteroid":
                    AnimationEvents.TriggerAnimationWithData(thing, "ConsumedByRift")
                    thing.Discard()
                elif thing.NodeType == "structure.forebear_station":
                    thing.CustomData.Set("visited", True)
                    thing.TriggerChange()
                    self._dead.remove(thing)
                else:
                    thing.Discard()

    def revert(self):
        for n in self._dead:
            world.Revive(n)


class LoseBecauseSomethingGotEaten:
    def __init__(self, what):
        self._what = what

    @staticmethod
    def object_is_important(thing):
        # potentials, not so much
        if isinstance(thing, Potential): return False
        # colonized planets - yeah, that's a loss
        if thing.NodeType.startswith("planet.") and thing.Level >= 0:
            return True
        # structures too, except for asteroids and unexplored forebear ruins
        if thing.NodeType.startswith("structure."):
            if thing.NodeType == "structure.asteroid": return False
            if thing.NodeType == "structure.forebear_station" and (not thing.Industry or thing.Industry.Kind.ID == "station"): return False
            return True

    @classmethod
    def find_loss_object_if_present(cls, endangered_objects):
        # nodes
        for n in endangered_objects:
            if cls.object_is_important(n): return n
        # slipways
        hole = game.Nodes.FirstWithType("special.hole")
        possible_slipway_nodes = game.Nodes.Within(hole, hole.Reach)
        checked = set()
        conn_rule = cls.make_connection_rule(hole)
        for n in possible_slipway_nodes:
            for conn in n.Connections:
                if conn in checked: continue
                checked.add(conn)
                type = conn.Kind.TypedID
                if type != "connection.invisible" and type != "connection.slowship":
                    conn_shape = CollidingSegment(conn.From.Position, conn.To.Position)
                    # check collision
                    if conn_rule(conn_shape):
                        return conn
        return None

    @staticmethod
    def make_connection_rule(hole):
        poly = hole.Polygon
        if hole.IsInverted:
            return lambda s: not poly.FullyContainsSegment(s)
        else:
            return lambda s: poly.CollidesWith(s)

    def apply(self):
        empire.WinningLosing.EndScenario({
            "outcome": "loss", "defeat": True,
            "defeat_icon": "icon_mission_failed",
            "heading": LS("menus.game_end.mission_failed.header"),
            "comment": LS("mission.hole.game_end.consumed_empire"),
            "shown_elements": ["undo"],
            "focus_on": self._what
        })

    def revert(self):
        pass

#########################################
# Consequences

class ConsGrowHole:
    def __init__(self, hole, new_points, new_projection):
        self._hole = hole
        self._new = (new_points, new_projection)

    def apply(self):
        self._old = (self._hole.Points, self._hole.ProjectedPoints)
        self._hole.ResizeTo(self._new[0], self._new[1], True)

    def revert(self):
        self._hole.ResizeTo(self._old[0], self._old[1], False)
