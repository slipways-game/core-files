# Code needed by the perks for all the core races.

class PerkStartingResources:
    """Receive additional starting resources."""
    def __init__(self, resource_id, amount):
        self._resource = Resource.All[resource_id]
        self._amount = amount

    def description(self):
        return LS("perk.starting_resources.desc", "Get an additional [[delta:+{1}{2}]] at the start of the scenario.", self._amount, self._resource.ID)

    def apply(self):
        game.Stock.Receive(self._resource, self._amount)

class PerkFlow(GlobalCondition):
    """Receive resources over time."""
    def __init__(self, resource_id, amount):
        self._resource = Resource.All[resource_id]
        self._amount = amount
    
    def effects(self):
        return [ResourceFlow.Flow(self._resource, self._amount, FlowCategory.Perks)]

class PerkStartWithStructures(GlobalCondition):
    def __init__(self, structure, amount):
        self._structure, self._amount = structure, amount

    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self._grant)

    def description(self):
        return LS("perk.structures.desc", "Lets you build a limited number ({1}) of [[ref:{2}]] from the start of the scenario.", self._amount, self._structure)

    def apply(self):
        commands.Issue(GrantLimited(world, self._structure, self._amount))

##########################################
# Quality perks

class PerkForgeworldProduction:
    def __init__(self, income_bonus):
        self._income_bonus = income_bonus

    def name(self): return LS("perk.efficient", "Efficient")
    def desc(self): return LS("perk.efficient.desc", None, self._income_bonus)

    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.NodeType == "planet.factory"
    def effects(self, node): 
        product = None
        for p in node.Products:
            if p.IsReal:
                product = p
                break
        if product is not None:
            return [
                ChangeProducts.AddOne(product.Resource, "efficient"),
                PercentageBonus.TradeIncome(self._income_bonus)
            ]

class PerkProjectIncome:
    def __init__(self, amount):
        self._amount = amount
    def name(self): return LS("perk.social_capital", "Social capital")
    def desc(self):
        return LS("perk.social_capital.desc", "Any planet with a *planetary project* earns *{1}%* more trade income*.", self._amount)
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.HasAnyProject
    def effects(self, node):
        return [PercentageBonus.TradeIncome(self._amount)]

class PerkDoubleHappyPeople:
    BONUSES = [0, 0, 1, 3, 6]
    def name(self): return LS("perk.serenity", "Serenity")
    def desc(self):
        return LS("perk.serenity.desc", "Happiness bonuses on :P:-producing planets are doubled.")
    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.Level >= 2 and node.ActuallyProduces(Resource.People)
    def effects(self, node):
        bonus = StdProsperity.LEVELS[node.Level]
        return [ResourceFlow.Happiness(bonus, FlowCategory.Prosperity)]

class PerkGrowth:
    PRODUCTS = ["P", "F"]
    def name(self): return LS("perk.growth", "Growth")
    def desc(self):
        return LS("perk.growth.desc", "Planets producing :P: or :F: pay no upkeep.")
    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return any(node.ActuallyProduces(Resource.All[p]) for p in self.PRODUCTS)
    def effects(Self, node):
        return [BlockFlows.OfCategory(FlowCategory.PlanetUpkeep)]

class PerkLuxury:
    def __init__(self, bonus):
        self._bonus = bonus
    def name(self): return LS("perk.luxury", "Luxury")
    def desc(self):
        return LS("perk.luxury.desc", "Planets receiving :G: earn {1}% more income.", self._bonus)
    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.Receives(Resource.All["G"])
    def effects(self, node):
        amount = node.AmountReceived(Resource.All["G"])
        return [PercentageBonus.TradeIncome(self._bonus * amount)]

class PerkJointFactories:
    def name(self): return LS("perk.joint_factories", "Joint factories")
    def desc(self):
        return LS("perk.joint_factories.desc", "Replaces the :O::arrow::T: and :O::arrow::B: options on [[ref:planet.factory]] planets with [[ref:industry.fac_joint]].")
    def sentiment(self): return QualitySentiment.Positive
    def hidden(self, node): return True
    def applies(self, node):
        return node.NodeType == "planet.factory"
    def effects(self, node):
        return [
            ColonizationOptions.Remove("fac_nano"),
            ColonizationOptions.AddFirst("fac_joint")
        ]
    
##########################################
# Node-swapping perks

class PerkProspectorsSwap(GlobalCondition):    
    def __init__(self, chance):
        self._chance = chance

    def activate(self):
        self.react_to(Trigger.BeforeSignalRevealed, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.prospectors.desc", "*{1}%* of empty signals become asteroids", self._chance)
        return info

    def check(self, data):
        signal = data["signal"]
        if signal.Contents == "nothing":
            swapped = Randomness.WithProbability(self.rng(str(signal.Position)), self._chance * 0.01)
            if swapped:
                signal.Contents = "structure.asteroid"

class PerkGeologySwap(GlobalCondition):    
    ELIGIBLE = ["planet.barren", "planet.ice", "planet.lava"]
    def __init__(self, chance):
        self._chance = chance

    def activate(self):
        self.react_to(Trigger.BeforeSignalRevealed, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.geology.desc", "It will be possible to establish mines on *{1}%* of all *lava, desert and ice planets*.", self._chance)
        return info

    def check(self, data):
        signal = data["signal"]
        eligible = signal.Contents.startswith("planet.") and signal.Contents in self.ELIGIBLE
        if eligible and signal.Quirk is None:
            added = Randomness.WithProbability(self.rng(str(signal.Position)), self._chance * 0.01)
            if added:
                signal.Quirk = "QuirkMineralRich()"

##########################################
# Trigger perks

class PerkXenology(GlobalCondition):
    def __init__(self, amount):
        self._amount = amount
    
    def activate(self):
        self.react_to(Trigger.PlanetColonized, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.xenology.desc", "Whenever you colonize a planet producing :L:, you receive [[delta:{1}S]]", self._amount)
        return info

    def check(self, data):
        if not data["node"].NodeType.startswith("planet."): return
        triggered = data["node"].IsProducerOf(Resource.All["L"])
        if triggered:
            commands.IssueScriptedConsequence(ConsGrantResources(self._amount, Resource.Science, data["node"]))

class PerkMiners(GlobalCondition):
    def __init__(self, amount):
        self._amount = amount        

    def activate(self):
        self.react_to(Trigger.TradeRouteEstablished, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.miners.desc", "When you deliver :O:, gain [[delta:{1}$]]", self._amount)
        return info

    def check(self, data):
        if data["resource"].ID == "O":
            commands.IssueScriptedConsequence(ConsGrantResources(self._amount, Resource.Cash, data["from"]))

class PerkExplorers(GlobalCondition):
    def __init__(self, maximum):
        self._max = maximum
        self._bonus = 1

    def activate(self):
        self._bonus = 1
        self.react_to(Trigger.ProbeStarted, self.reset)
        self.react_to(Trigger.AfterNodeDiscovered, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.explorers.desc", None, self._max)
        return info

    def reset(self, data):
        self._bonus = 1

    def check(self, data):
        if data["node"].NodeType.startswith("planet."):
            commands.IssueScriptedConsequence(ConsGrantResources(self._bonus, Resource.Cash, data["node"]))
            self._bonus = min(self._max, self._bonus + 1)

class PerkCuriosity(GlobalCondition):
    def __init__(self, every):
        self._every = every        

    def activate(self):
        self.react_to(Trigger.AfterNodeDiscovered, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.curiosity.desc", None, self._every, 1)
        return info

    def check(self, data):
        if data["node"].NodeType.startswith("planet."):
            self.data.planets = self.data.get_or("planets", 0) + 1
            if self.data.planets % self._every == 0:
                commands.IssueScriptedConsequence(ConsGrantResources(1, Resource.Science, data["node"]))

class PerkProsperity(GlobalCondition):
    def __init__(self, amount):
        self._amount = amount
    
    def activate(self):
        self.react_to(Trigger.NodeUpgraded, self.check)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.prosperity.desc", "When you upgrade a planet to [[ref:level.3]], you receive [[delta:{1}S]]", self._amount)
        return info

    def check(self, data):
        triggered = data["node"].NodeType.startswith("planet.") and data["level"] == 3
        if triggered:
            commands.IssueScriptedConsequence(ConsGrantResources(self._amount, Resource.Science, data["node"]))

class PerkTwoWays(GlobalCondition):
    def __init__(self, amount):
        self._amount = amount
        self._queue = []
        self._pending = {}
    
    def activate(self):
        self.react_to(Trigger.TradeRouteEstablished, self.queue)
        self.react_to(Trigger.ActionTaken, self.check_queued)

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.reciprocity.desc", "Every time two-way trade between a new pair of planets is established, you receive [[delta:{1}$]]", self._amount)
        return info

    def queue(self, data):
        a, b = data["from"], data["to"]
        self._queue.append((a, b))

    def check_queued(self, _):
        if len(self._queue) == 0: return
        for a, b in self._queue:
            self.check(a, b)
        del self._queue[:]
        self._pending = {}

    def check(self, a, b):        
        ids = [a.NodeIdentifier, b.NodeIdentifier]
        ids.sort()
        key = "%s+%s" % tuple(ids)
        if self.data.has_value(key) or key in self._pending: return
        two_way = any(er.Consumer == a for er in b.ExportRoutes)
        if two_way:
            self._pending[key] = True
            half_amount = self._amount / 2
            commands.IssueScriptedConsequence(ConsGrantResources(half_amount, Resource.Cash, node=a))            
            commands.IssueScriptedConsequence(ConsGrantResources(half_amount, Resource.Cash, node=b))            
            update = ConsUpdateNodeData()
            update.add(self.host(), key, True)
            commands.IssueScriptedConsequence(update)            

class PerkGoldenAge(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.NodeUpgraded, self.node_upgrade)
    
    def node_upgrade(self, data):
        node = data["node"]
        if node.NodeType.startswith("planet.") and node.Level >= 2:
            ConsGrantResources(1, Resource.Science, node).issue()

    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.golden_age.desc", None, 1)
        return info

class PerkAppliedScience(GlobalCondition):
    BONUS = [60, 50, 40, 30]
    def activate(self):
        self.react_to(Trigger.TechInvented, self.new_tech)

    def new_tech(self, _):
        amount = self.BONUS[difficulty_ordinal()]
        ConsGrantResources(amount, Resource.Cash).issue()

    def info(self):
        amount = self.BONUS[difficulty_ordinal()]
        info = CondInfo()
        info.FullDescription = LS("perk.applied_science.desc", None, amount)
        return info
    
##########################################
# Condition-based perks

class PerkRemoveEmptySignals(GlobalCondition):
    DELAY = 1.0

    def activate(self):
        self._timer = self.DELAY * 2
        self.react_to(Trigger.ActionTaken, self.after_action)
        
    def info(self):
        info = CondInfo()
        info.FullDescription = LS("perk.careful_observation.desc")
        return info

    def after_action(self, data):
        self._timer = max(self._timer, self.DELAY)

    def realtime_update(self, dt):
        if dt > 0.1: dt = 0.1
        if self._timer > 0:
            self._timer -= dt
            if self._timer < 0:
                self.perform_check()

    def perform_check(self):
        empty_potentials = [p for p in every(Potential) if p.Signal.Contents == "nothing"]
        for p in empty_potentials:
            # let swaps happen
            game.Triggers.Activate(Trigger.BeforeSignalRevealed, "potential", p, "signal", p.Signal)
            # are we still empty?
            if p.Signal.Contents == "nothing":
                # yeah, reveal
                p.Reveal()

class PerkResearchers(GlobalCondition):
    USES_LIMIT = 3
    def activate(self):
        self.react_to(Trigger.BeforeTechInvented, self.when_inventing_tech)

    def info(self):
        info = CondInfo()
        additional_text = ""
        if game.GameContext == GameContext.PlayingScenario:
            additional_text = styled("(%d/%d)" % (game.CustomData.GetOr("researchers_used", 0), self.USES_LIMIT), "TooltipLightComment")
        info.FullDescription = LS("perk.researchers.desc", None, additional_text)
        return info

    def when_inventing_tech(self, data):
        tech = data["tech"]
        if not game.Technology.InventableRange.Contains(tech.EffectiveTier):
            update = ConsUpdateNodeData()
            update.inc(game, "researchers_used")
            commands.IssueScriptedConsequence(update)

    def used_up(self): return game.CustomData.GetOr("researchers_used", 0) >= self.USES_LIMIT

    def modify_invent_permission(self, tech, inventability, permission):
        if self.used_up(): return permission
        if permission.Allowed: return permission
        modified_permission = game.Technology.CanInvent(tech, InventabilityConditions.ScriptedModifiers | InventabilityConditions.TierRange)
        if modified_permission.Allowed and not permission.Allowed:
            return Permission.YesWithReason(LS("perk.researchers.message", "Available thanks to the *Researchers* perk."))
        else:
            return permission

class PerkEnergyFocusedTechDiscounts(GlobalCondition):
    AFFECTED_TECHS = [
        "solar_superconductors", "geothermals", "mass_reactors", "plasma_containment", "starbirth",
        "energy_driven"
    ]
    def __init__(self, pct):
        self._pct = pct

    def tech_discount(self, tech):
        if tech.ID in self.AFFECTED_TECHS:
            reason = LS("perk.energy_focused.discount", None, self._pct)
            return Discount("perk", reason, self._pct * 0.01)

class PerkSurplus(GlobalCondition):
    def __init__(self, cash_discount):
        self._cash_discount = cash_discount

    def info(self):
        ci = CondInfo()
        ci.FullDescription = LS("perk.surplus.desc", None, self._cash_discount)
        return ci

    def activate(self):
        self.react_to(Trigger.ConnectionBuilt, self.new_connection)

    def global_cost_adjustment(self, thing):
        if isinstance(thing, PlannedConnection):
            return self.adjust_connection_cost
        return None

    def new_connection(self, data):
        planned = data["planned"]
        if planned and planned.CustomData.Has("marked_off"):
            marked = planned.CustomData.Get("marked_off")
            update = ConsUpdateNodeData()
            for node, resource in marked:
                key = "xcs_" + resource
                update.add(node, key, True)
            update.issue()

    def adjust_connection_cost(self, cost, conn):
        a, b = conn.StartNode, conn.EndNode
        if not a or not b: 
            conn.CustomData.Clear("marked_off")
            return cost
        a_set = set([a])
        b_set = set([b])
        if a.RelaysConnections: a_set.update(game.Reachability.ReachableNodes(a))
        if b.RelaysConnections: b_set.update(game.Reachability.ReachableNodes(b))
        a_set.difference_update(b_set)
        b_set.difference_update(a_set)
        marked_off = set()    
        for an in a_set:
            for bn in b_set:
                marked_off.update(self.check(an, bn))
                marked_off.update(self.check(bn, an))
        if len(marked_off) > 0:
            cost = cost.Multiply(Resource.Cash, 1.0 - self._cash_discount * 0.01)
            cost = cost.ModifyTime(lambda months: months - 1)
            conn.CustomData.Set("marked_off", marked_off)
        else:
            conn.CustomData.Clear("marked_off")
        return cost

    def check(self, src, dest):
        if not dest.NodeType.startswith("planet."): return
        for n in dest.Needs:
            if n.ImportCount != 1: continue
            for p in src.Products:
                if not (p.IsReal and p.IsAvailable): continue
                if p.Resource == n.MetWith and not dest.CustomData.Has("xcs_" + p.Resource.ID):
                    yield (dest, p.Resource.ID)
