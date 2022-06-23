##############################################################
# Hubworlds

class HubworldQuality:
    def name(self): return LS("structure.hub_%s" % self.race_id())
    def desc(self):
        return self.desc_for_node(None)
    def desc_for_node(self, node): 
        if node:
            basis = self.basis_string(node)
            basis_text = L("quality.hub.current_base_value", None, basis)
            basis_text = styled(basis_text, "TooltipLightComment")
        else:
            basis_text = ""
        return LS("quality.hub.%s.desc" % self.race_id(), None, basis_text, *self.extra_desc_args())
    def extra_desc_args(self): return ()
    def tags(self): return ["hub"]
    def effects(self, node):
        race = Race.All[self.race_id()]
        member = game.Council.Member(race)
        if not member.IsActive: 
            yield AddChrome([
                {"type": NodeChrome.Text, "text": "", "icon": race.ID}
            ])
            return
        bonus = self.score(node)
        yield ResourceFlow.Happiness(bonus, FlowCategory.HubworldHappiness)
        yield AddChrome([
            {"type": NodeChrome.Text, "text": "+%d%%:H:" % bonus, "bg_color": race.Assets.badgeBackColor, "icon": race.ID, 
             "display": ChromeDisplay.OverridesLevelIndicator,
             "hide_text_for_node_pills": True}
        ])
    def basis_string(self, node): return str(self.score_basis(node))

class BaqarHubQuality(HubworldQuality):
    def __init__(self):
        self._scale = constants.BaseConstant("slipway.range") * constants.Float("distance.scale") * 0.7
    def race_id(self): return "baqar"
    def score_basis(self, node):
        wormhole = game.Nodes.FirstWithType("wormhole")
        return (node.Position - wormhole.Position).magnitude / self._scale
    def score(self, node):
        return math.floor(self.score_basis(node))
    def basis_string(self, node): return "%.2f" % self.score_basis(node)

class AphorianHubQuality(HubworldQuality):
    STARTING_FROM = 8
    def race_id(self): return "aphorian"
    def score_basis(self, node):
        return node.ExportCount + node.ImportCount
    def score(self, node):
        return max(0, self.score_basis(node) - self.STARTING_FROM + 1)
    def extra_desc_args(self):
        return (Localization.Ordinal(self.STARTING_FROM),)

class VattoriHubQuality(HubworldQuality):
    DIVISOR = 3
    def race_id(self): return "vattori"
    def score_basis(self, node):
        nodes = [node]
        nodes += game.Reachability.ReachableNodes(node)
        total_s = sum(n.AmountProduced(Resource.Science) for n in nodes)
        return total_s
    def score(self, node):
        return int(math.floor(self.score_basis(node) / self.DIVISOR))
    def extra_desc_args(self):
        return (self.DIVISOR,)

class SilthidHubQuality(HubworldQuality):
    DIVISOR = 2
    def race_id(self): return "silthid"
    def score_basis(self, node):
        T, B = Resource.All["T"], Resource.All["B"]
        nodes = [node]
        nodes += game.Reachability.ReachableNodes(node)
        return sum(n.AmountProduced(T) + n.AmountProduced(B) for n in nodes)
    def score(self, node):
        return int(math.floor(self.score_basis(node) / self.DIVISOR))
    def extra_desc_args(self):
        return (self.DIVISOR,)

class DendrHubQuality(HubworldQuality):
    DIVISOR = 2
    def race_id(self): return "dendr"
    def score_basis(self, node):
        P = Resource.People
        nodes = [node]
        nodes += game.Reachability.ReachableNodes(node)
        return sum(n.AmountProduced(P) - n.AmountAvailable(P) for n in nodes)
    def score(self, node):
        return int(math.floor(self.score_basis(node) / self.DIVISOR))
    def extra_desc_args(self):
        return (self.DIVISOR,)

##############################################################
# Structure used to place hubworlds

def hubstructure_model(): 
    return "Unknown"

def hubstructure_desc(kind):
    race_id = kind.ID.split("_")[-1]
    common_desc = L("structure.hub.desc.common")
    cls = globals()["%sHubQuality" % IdentifierStyles.ToUpperCamel(race_id)]
    rule_desc = cls().desc()
    return RichText.ParagraphSpacer().join((common_desc, rule_desc))

def hubstructure_available(kind):
    race_id = kind.ID.split("_")[-1]
    return not game.CustomData.Has("hub_built_%s" % race_id)

def hubstructure_closest_planet(pos):
    planet_candidates = [p for p in game.Nodes.Within(pos, 1.3) if p.NodeType.startswith("planet.")]
    if len(planet_candidates) == 0: return None
    planet = min(planet_candidates, key=lambda p: (p.Position - pos).sqrMagnitude)
    return planet

def hubstructure_placement():
    return [
        PlaceNear(is_eligible_hub_planet, f(1.3), LS("structure.hub.build_on_planet"), "VPlaceNear"),
        ScriptedPlacement(SnapToHub)
    ]

def hubstructure_obstructed_by(planned, model):
    return False # obstructions don't make sense for this

def is_eligible_hub_planet(node):
    return node.Level >= 2 and node.NodeType.startswith("planet.") and node.CustomData.GetOr("hub_placed", 0) == 0

def hubstructure_build(cmd, pos, kind):
    # find the planet
    planet = hubstructure_closest_planet(pos)
    # attach our quality to the planet
    race_id = kind.ID.split("_")[-1]
    quality_expr = "%sHubQuality()" % IdentifierStyles.ToUpperCamel(race_id)
    attach_cons = ConsAttachQualityOnce(planet, "hub_placed", quality_expr)
    ConsUpdateNodeData().add(game, "hub_built_%s" % race_id, True).issue()
    commands.IssueScriptedConsequence(attach_cons)
    # force changes to be acknowledged 
    ConsRefreshNode(planet).issue()
    # we don't actually build anything
    return []

class SnapToHub:
    @staticmethod
    def adjust_position(pos, ps):
        planet = hubstructure_closest_planet(pos)
        if planet is not None:
            return planet.Position
        else:
            return pos

    @staticmethod
    def is_permitted(pos, ps):
        return Permission.Yes()
