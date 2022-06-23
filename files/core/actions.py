#################################
# Destroying planets (for money)

class Harvest:
    @staticmethod
    def tags(node):
        bonus = constants.Int("harvest.bonus")
        return "[s:CostBenefit]+%d:$:[/s]" % bonus

    @staticmethod
    def execute(node):
        bonus = constants.Int("harvest.bonus")
        empire.Stock.Receive(Resource.Cash, bonus)
        HVPoppingInfo.Spawn(node).Show(bonus, Resource.Cash)
        node.Discard()
        return {"bonus": bonus, "old_node": node}

    @staticmethod
    def revert(data):
        node = world.Revive(data["old_node"])
        empire.Stock.Return(Resource.Cash, data["bonus"])

    @staticmethod
    def applies(node):
        return node.NodeType.startswith("planet.") and node.Level <= 0 and node.Connections.Count == 0

#################################

class Demolish:
    @staticmethod
    def execute(node):
        node.Discard()
        return {"old_node": node}

    @staticmethod
    def revert(data):
        world.Revive(data["old_node"])

    @staticmethod
    def applies(node):
        return node.NodeType.startswith("planet.") and node.Level <= 0 and node.Connections.Count == 0

#################################
# Collapsing into protostars

class Collapse:
    @staticmethod
    def execute(node):
        position = node.Position
        node.Discard()
        star = world.Add(Structure(position, StructureKind.All["protostar"]))
        return {"star": star, "old_node": node}

    @staticmethod
    def revert(data):
        data["star"].Discard()
        world.Revive(data["old_node"])

    @staticmethod
    def applies(node):
        return node.Level <= 0 and node.Connections.Count == 0

#################################
# Collapsing into relays

class Lensify:
    STRUCTURE_SETTINGS = {"delay_view_appearance": f(0.35)}

    @staticmethod
    def execute(node):
        position = node.Position
        node.Discard()
        relay = world.Add(Structure(position, StructureKind.All["relay"], None, Lensify.STRUCTURE_SETTINGS))
        relay.CustomData.Set("lensified", True)
        return {"new": relay, "old": node, "changes": [relay]}

    @staticmethod
    def revert(data):
        data["new"].Discard()
        world.Revive(data["old"])
    
    @staticmethod
    def applies(node):
        return node.Level <= 0 and node.Connections.Count == 0

class LensifyInfra:
    @staticmethod
    def execute(node):
        position = node.Position
        node.Discard()
        relay = world.Add(Structure(position, StructureKind.All["infra_relay"], None, Lensify.STRUCTURE_SETTINGS))
        relay.CustomData.Set("lensified", True)
        return {"new": relay, "old": node, "changes": [relay]}

    @staticmethod
    def revert(data):
        data["new"].Discard()
        world.Revive(data["old"])
    
    @staticmethod
    def applies(node):
        if not game.Technology.IsInvented("infraspace"): return
        return node.Level <= 0 and node.Connections.Count == 0
            
#################################
# Industrialization

class ChangePlanetKind:
    def __init__(self, target_type):
        self.target = target_type

    @staticmethod
    def find_matching_planet(position):
        for p in every(Planet):
            if (p.Position - position).sqrMagnitude < 0.001:
                return p

    def icon(self, node): return "planet_%s" % self.target

    def execute(self, node):
        old_state = node.ChangeKind(PlanetKind.All[self.target])
        return {"old_state": old_state, "node": node}

    def revert(self, data):
        data["old_state"].RestoreOn(data["node"])

    def applies(self, node):
        return node.Level <= 0 and node.NodeType.startswith("planet.") and not node.NodeType.endswith(self.target)

Industrialize = ChangePlanetKind("factory")
Rebuild = ChangePlanetKind("factory")

#################################
# Transposing with another planet

class TransposeRules:
    def is_uncolonized_planet(self, node):
        return node.NodeType.StartsWith("planet.") and node.Level < 0       

    def repeatable(self): return True

    def defer_costs(self): return True
    def applies(self, node):
        return self.is_uncolonized_planet(node) and node.Connections.Count == 0

    def execute_with_context(self, node, context):
        command = context["command"]
        world.Add(TransposerModalOp(command, node))
        return {}

    def revert(self, data):
        # nothing here, the modal op does the actual reversion
        pass

Transpose = TransposeRules()

#################################
# Moving a planet with a tug

class TowRules:
    def is_uncolonized_planet(self, node):
        return node.NodeType.StartsWith("planet.") and node.Level < 0       

    def defer_costs(self): return True
    def repeatable(self): return True

    def cost(self, node):
        if node.NodeType == "structure.asteroid":
            return CompoundCost.Parse("10$, 1mo")
        else:
            return CompoundCost.Parse("20$, 1mo")

    def applies(self, node):
        if node.Connections.Count > 0: return False
        return self.is_uncolonized_planet(node) or node.NodeType == "structure.asteroid"

    def execute_with_context(self, node, context):
        command = context["command"]
        world.Add(TowModalOp(command, node))
        return {}

    def revert(self, data): pass # delegated to the ModalOp

Tow = TowRules()

#################################
# Terraforming - various kinds

def planet_type(node):
    return node.NodeType.split(".")[1]

class TerraformingAction:
    def __init__(self, props):
        self.props = props

    def _target_type(self, node):
        type_name = self.props["chains"][planet_type(node)]
        return PlanetKind.All[type_name]

    def icon(self, node):
        target = self._target_type(node)
        return "planet_%s" % target

    def applies(self, node):
        return node.Level <= 0 and node.NodeType.startswith("planet.") and planet_type(node) in self.props["chains"]

    def displayed_name(self, node):
        target_type = self._target_type(node)
        return LS("action.turn_into", "Turn into {1}", target_type.LName)
    
    def execute(self, node):
        target_type = self._target_type(node)
        previous_state = node.ChangeKind(target_type)
        return {"node": node, "old_state": previous_state}

    def revert(self, data):
        data["old_state"].RestoreOn(data["node"])

WeatherManipulation = TerraformingAction({
    "chains": {
        "arid": "earthlike",
        "barren": "arid",
        "arctic": "earthlike",
        "ice": "arctic",
        "swamp": "earthlike"
    }
})

LifeSeeding = TerraformingAction({
    "chains": {
        "lava": "swamp",
        "mining": "swamp",
        "primordial": "swamp"
    }
})

Remake = TerraformingAction({
    "chains": {
        "ocean": "earthlike",
        "arid": "earthlike",
        "arctic": "earthlike",
        "ice": "earthlike",
        "barren": "earthlike",
        "swamp": "earthlike",
        "jungle": "earthlike",
        "primordial": "earthlike"
    }
})

Mineralize = TerraformingAction({
    "chains": {
        "ice": "mining",
        "barren": "mining",
        "lava": "mining"
    }
})

#################################
# Exploiting asteroids for money

class ExploitAsteroid:
    @staticmethod
    def tags(node):
        bonuses = ExploitAsteroid.calc_bonuses(node)
        texts = ["+%d:%s:" % (amount, resource.ID) for resource, amount in bonuses.iteritems()]
        return "[s:CostBenefit]%s[/s]" % "\n".join(texts)

    @staticmethod
    def influences(node):
        influences = []
        for other in asteroid_possible_planets(node):
            itype = InfluenceType.Output if other.HasIndustry else InfluenceType.Inactive
            isent = InfluenceSentiment.Positive if other.HasIndustry else InfluenceSentiment.Neutral
            infl = NodeInfluence(node, other, itype, isent)
            influences.append(infl)
        return influences

    @staticmethod
    def execute(node):
        bonuses = ExploitAsteroid.calc_bonuses(node)
        for resource, amount in bonuses.iteritems():
            empire.Stock.Receive(resource, amount)
            HVPoppingInfo.Spawn(node).Show(amount, resource)
        node.Discard()
        return {"old_node": node, "bonuses": bonuses}

    @staticmethod
    def revert(data):
        bonuses = data["bonuses"]
        for resource, amount in bonuses.iteritems():
            empire.Stock.Return(resource, amount)
        world.Revive(data["old_node"])

    @staticmethod
    def calc_bonuses(node):
        cash_bonus = constants.Int("asteroid.bonus") * len(asteroid_actual_planets(node))
        bonuses = {Resource.Cash: cash_bonus}
        return ValueChange.ResolveValue(node, "asteroid_bonus", bonuses)

    @staticmethod
    def applies(node):
        return node.NodeType == "structure.asteroid" and node.Connections.Count == 0


def asteroid_possible_planets(node):
    pos = node.Position
    max_range = constants.Distance("asteroid.range")
    max_range *= max_range
    return [p for p in every(Planet) if (p.Position-pos).sqrMagnitude < max_range]

def asteroid_actual_planets(node):
    return [p for p in asteroid_possible_planets(node) if p.HasIndustry]
