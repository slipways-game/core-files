# Various qualities used by the core game
# Contains both built-in qualities and ones caused by technologies being invented.

#################################
# Core resource flow qualities

class StdExport:
    def name(self): return LS("quality.trade_income", "Trade income")
    def desc(self): return LS("quality.trade_income.desc", "Every resource delivered to another planet or structure earns :$:.")
    def sentiment(self): return QualitySentiment.Positive
    
    def effects(self, node): return list(flows_standard_export(node)) # delegate to a built-in engine function that's fast

class StdProduction:
    CASH_PER_UNIT = 6
    SCIENCE_PER_UNIT = 1
    HAPPINESS_PER_UNIT = 1

    def name(self): return LS("quality.production", "Production")
    def desc(self): return LS("quality.production.desc", "Some planets and structures produce :$:, :S: or :H: directly - these are added to your reserves each year.")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        cash = node.AmountAvailable(Resource.Cash)
        science = node.AmountAvailable(Resource.Science)
        happiness = node.AmountAvailable(Resource.Happiness)
        is_planet = node.NodeType.StartsWith("planet.")
        category = FlowCategory.PlanetProduction if is_planet else FlowCategory.StructureProduction
        happiness_category = FlowCategory.PlanetMadeHappiness if is_planet else FlowCategory.StructureMadeHappiness
        flows = []
        if cash != 0: flows.append(ResourceFlow.Cash(cash * StdProduction.CASH_PER_UNIT, category))
        if science != 0: flows.append(ResourceFlow.Science(science * StdProduction.SCIENCE_PER_UNIT, category))
        if happiness != 0: flows.append(ResourceFlow.Happiness(happiness * StdProduction.HAPPINESS_PER_UNIT, happiness_category))
        return flows

class StdUpkeep:
    def name(self): return LS("quality.upkeep", "Upkeep costs")
    def desc(self): return LS("quality.upkeep.desc", "Most planets and structures require ongoing upkeep to support them, depending on the type of industry used.")
    def sentiment(self): return QualitySentiment.Negative

    def effects(self, node):
        if node.Industry is None: return []
        upkeep_cost = node.Industry.Kind.GetCosts(node).Extract[UpkeepCost]()
        if upkeep_cost is None: return []
        upkeep_amount = upkeep_cost.AmountPerTurn
        is_planet = node.NodeType.StartsWith("planet.")
        if is_planet:
            upkeep_amount = constants.Int("planet.upkeep.$", upkeep_amount)
            modifier = constants.Int(node.NodeType + ".upkeep.$", 0)
            upkeep_amount += modifier
        category = FlowCategory.PlanetUpkeep if is_planet else FlowCategory.StructureUpkeep
        if upkeep_amount > 0:
            return [ResourceFlow.Flow(upkeep_cost.Resource, -upkeep_amount, category)]

class StdUnemployment:
    def name(self): return LS("quality.unemployment", "Unemployment")
    def desc(self): return LS("quality.unemployment.desc", 
        "Idle :P: on a populated planet cause [[delta:-1H]] each.")
    def sentiment(self): return QualitySentiment.Negative

    def effects(self, node):
        idles = node.AmountAvailable(Resource.People)
        if idles > 0:
            return [ResourceFlow.Happiness(-idles, FlowCategory.Unemployment)]

class StdNoExport:
    PENALTY = 2    
    def name(self): return LS("quality.no_export", "No trade")
    def desc(self): return LS("quality.no_export.desc", 
        "A planet that produces resources, but does not export anything receives a [[delta:-{1}H]] penalty.", StdNoExport.PENALTY)
    def sentiment(self): return QualitySentiment.Negative

    def effects(self, node):
        no_exports = all(p.IsReal and p.Resource.IsExportable and p.ExportRoute is None for p in node.Products)
        if not no_exports: return
        produces_non_people = any(p.Resource != Resource.People for p in node.Products)
        if not produces_non_people: return
        return [ResourceFlow.Happiness(-StdNoExport.PENALTY, FlowCategory.NoExport)]

class StdProsperity:
    LEVELS = [0, 0, 1, 3, 6]
    def name(self): return LS("quality.prosperity", "Prosperity level")
    def desc(self): return LS("quality.prosperity.desc",
        "[[ref:level.2]] and [[ref:level.3]] planets receive happiness bonuses.")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        bonus = StdProsperity.LEVELS[node.Level]
        if bonus > 0:
            return [ResourceFlow.Happiness(bonus, FlowCategory.Prosperity)]

#################################
# Intrinsic planet/industry qualities

class HarshEnvironmentQuality:
    def __init__(self, sadness = 0, cost = 0, name = None):
        self.sadness, self.cost = sadness, cost
        self._name = name or ("quality.harsh_environment", "Harsh environment")

    def name(self): return LS(*self._name)
    def tags(self): return ["harsh"]
    def sentiment(self): return QualitySentiment.Negative    

    def effects(self, node): 
        flows = []
        if self.sadness > 0:
            flows.append(ResourceFlow.Happiness(-self.sadness, FlowCategory.Environment, self.name()))
        if self.cost > 0:
            flows.append(ResourceFlow.Cash(-self.cost, FlowCategory.PlanetUpkeep, self.name()))
        return flows

#################################
# Tech-based qualities

class LifeExtension:
    def __init__(self, bonus):
        self.bonus = bonus
    
    def name(self): return LS("quality.life_extension", "Life Extension")
    def desc(self): return LS("quality.life_extension.desc",
        "All population centers that utilize all their :P: grant an additional [[delta:{1}H]] each.", self.bonus)

    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.ActuallyProduces(Resource.People) and node.IsExportingEverything
    
    def effects(self, node):
        return [
            ResourceFlow.Happiness(self.bonus, FlowCategory.TechBasedHappiness, self.name())
        ]


class HighEnergyStudies:
    def __init__(self, science_bonus):
        self.science_bonus = science_bonus

    def name(self): return LS("quality.high_energy_studies", "High Energy Study")
    def desc(self): return LS("quality.high_energy_studies.desc", 
        "All laboratories that receive energy (:E:) get an additional [[delta:{1}S]] bonus.", self.science_bonus)

    def sentiment(self): return QualitySentiment.Positive    
    def applies(self, node):
        return node.NodeType == "structure.lab" and node.HasAllNeedsMet and any(n.AskingFor == Resource.All["E"] for n in node.Needs)
    def effects(self, node): return [ChangeProducts.Add(2, Resource.Science, "high_energy")]


class SkillImplants:
    def __init__(self, bonus): 
        self.bonus = bonus        

    def name(self): return LS("quality.skill_implants", "Skill Implants")
    def desc(self): 
        return LS("quality.skill_implants.desc",
            "Improves trade income by *+{1}%* on [[ref:level.2]] and [[ref:level.3]] planets.", self.bonus)

    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.NodeType.startswith("planet.") and node.Level >= 2
    def effects(self, node): return [PercentageBonus.TradeIncome(self.bonus)]

class SleepReplacement:
    def __init__(self, bonus): 
        self._bonus = bonus        

    def name(self): return LS("quality.sleep_replacement", "Sleep Replacement")
    def desc(self): 
        return LS("quality.sleep_replacement.desc",
            "Improves trade income by *+{1}%* across the whole sector.", self._bonus)

    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.NodeType.startswith("planet.")
    def effects(self, node): return [PercentageBonus.TradeIncome(self._bonus)]

class DeepDrilling:
    TRADE_BONUS = 30
    def name(self): return LS("quality.deep_drilling", "Deep Drilling")
    def desc(self): return LS("quality.deep_drilling.desc",
        "Mines on [[ref:planet.mining]] planets produce an additional :O: and yield *{1}%* more income.", self.TRADE_BONUS)

    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.NodeType == "planet.mining" and node.ActuallyProduces(Resource.All["O"]) 

    def effects(self, node): 
        return [
            ChangeProducts.AddOne(Resource.All["O"], "deep_drilling"),
            PercentageBonus.TradeIncome(self.TRADE_BONUS)
        ]

class Redigestion:
    def name(self): return LS("quality.redigestion", "Redigestion")
    def desc(self): return LS("quality.redigestion.desc",
        "Food processors make an additional :F:.")

    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.NodeType == "structure.food_processor" and node.ActuallyProduces(Resource.All["F"]) 

    def effects(self, node): return [ChangeProducts.AddOne(Resource.All["F"], "redigestion")]

class Technocracy:
    def name(self): return LS("quality.technocracy")
    def desc(self): return LS("quality.technocracy.desc")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node): 
        if not node.NodeType.startswith("structure.") or "lab" not in node.NodeType: return False
        best_lab = max((s for s in every(Structure) if "lab" in node.NodeType), key=self._lab_production)
        return node == best_lab

    @staticmethod
    def _lab_production(lab):
        return sum(1 for p in lab.Products if p.Resource == Resource.Science)

    def effects(self, node): 
        production = self._lab_production(node)
        if production > 0:
            return [ResourceFlow.Happiness(production, FlowCategory.TechBasedHappiness, self.name())]

class EnergyDrivenQuality:
    FORBIDDEN = ["E", "progress"]
    def name(self): return LS("quality.energy_driven", "Energy-driven")
    def desc(self): return LS("quality.energy_driven.desc", "Planets and structures receiving :E: have their production *increased by one unit* of each product.")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.Receives(Resource.All["E"])
    def effects(self, node): 
        products = set(p.Resource for p in node.Products if p.IsReal and p.Resource.ID not in self.FORBIDDEN and not is_product_copied(p))  
        if len(products) > 0:
            return [ChangeProducts.AddOne(p, "energy_driven[copy]") for p in products]

class CultureGrowthQuality:
    def __init__(self, amount):
        self._amount = amount
    def name(self): return LS("quality.culture_growth", "Spiritual growth")
    def desc(self): return LS("quality.culture_growth.desc", "Planets receiving :C: increase their *trade income* by *{1}%*.", self._amount)
    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.Receives(Resource.All["C"])
    def effects(self, node):
        return [PercentageBonus.TradeIncome(self._amount)]

class CultureSpreadQuality:
    def name(self): return LS("quality.culture_spread", "Culture spread")
    def desc(self): return LS("quality.culture_spread_b.desc")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.Receives(Resource.All["C"])
    def effects(self, node):
        effects = []
        amount = node.AmountReceived(Resource.All["C"])
        if amount >= 2:
            effects += [ChangeProducts.AddOne(Resource.All["C"], "culture_spread")]
        return effects

class CultureExchangeQuality:
    def name(self): return LS("quality.culture_exchange", "Culture exchange")
    def desc(self): return LS("quality.culture_exchange.desc", "If you connect two planets producing :P:, both of them will generate one :C:.")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        if not node.ActuallyProduces(Resource.People) and not node.IndustryProduces(Resource.People): return False
        return any(r.ActuallyProduces(Resource.People) or r.IndustryProduces(Resource.People) for r in game.Reachability.ReachableNodes(node))

    def effects(self, node):
        return [ChangeProducts.AddOne(Resource.All["C"], "culture_exchange")]

class PostScarcityQuality:
    INCOME_BONUS = 50

    def name(self): return LS("quality.post_scarcity")
    def desc(self): return LS("quality.post_scarcity.desc", None, self.INCOME_BONUS)
    def sentiment(self): return QualitySentiment.Positive
    def hidden(self, node): return node.Level < 4

    def applies(self, node):
        return node.Level >= 3 and node.NodeType.startswith("planet.")

    def effects(self, node):
        if node.Level == 3:
            return [FinalUpgradeRule.Calling(self.rule_check)]
        elif node.Level == 4:
            return [PercentageBonus.TradeIncome(self.INCOME_BONUS)]

    @staticmethod
    def rule_check(node):
        permission = Permission.Yes()
        if node.HasUnmetNeeds:
            resources = [":%s:" % need.AskingFor.ID for need in node.Needs if not need.IsMet]
            resources = "".join(resources)
            problem = LS("warning.needs_unfulfilled", "Has unfulfilled needs ({1}).", resources)
            permission = permission.Disallow(problem)
        if node.ImportCount < 6:
            permission = permission.Disallow(LS("quality.post_scarcity.condition", "Establish 6 different import routes to this planet to upgrade it to [[ref:level.4]]."))
        return permission

class UniversalHarmony:
    def name(self): return LS("quality.universal_harmony", "Universal harmony")
    def desc(self): return LS("quality.universal_harmony.desc", "Every [[ref:level.2]] :P:-producing planet generates one unit of :C:.")
    def sentiment(self): return QualitySentiment.Positive
    def hidden(self, node): return node.Level < 4

    def applies(self, node):
        return node.Level >= 2 and node.NodeType.startswith("planet.") and (node.ActuallyProduces(Resource.People) or node.IndustryProduces(Resource.People))

    def effects(self, node):
        return [ChangeProducts.AddOne(Resource.All["C"], "universal_harmony")]

class LuxuryManufacture:
    def name(self): return LS("quality.luxury_manufacture", "Luxury manufacture")
    def desc(self): return LS("quality.luxury_manufacture.desc", "Every [[ref:level.3]] forgeworld produces two units of :Lux:.")
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.Level >= 3 and node.NodeType == "planet.factory"

    def effects(self, node):
        return [ChangeProducts.Add(2, Resource.All["Lux"], "luxury_manufacture")]

class EconomicZones:
    def __init__(self, bonus):
        self._bonus = bonus

    def name(self): return LS("quality.economic_zones", "Economic zone")
    def desc(self): return LS("quality.economic_zones.desc", "When you connect a planet to another one producing the same resource, trade income increases by *{1}%* on both planets.", self._bonus)
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        if not node.NodeType.startswith("planet."): return False
        our_products = []
        for p in node.Products:
            if p.IsReal and p.Resource.ID not in our_products:
                our_products.append(p.Resource.ID)
        reachables = game.Reachability.ReachableNodes(node)
        for r in reachables:
            if not r.NodeType.startswith("planet."): continue
            for p in r.Products:
                if p.IsReal and p.Resource.ID in our_products:
                    return True
        return False

    def effects(self, node):
        return [PercentageBonus.TradeIncome(self._bonus)]

class GeneticAdjustments:
    REDUCTION = 1
    def name(self): return LS("quality.genetic_adjustments")
    def desc(self): return LS("quality.genetic_adjustments.desc", None, self.REDUCTION)
    def sentiment(self): return QualitySentiment.Positive

    def applies(self, node):
        return node.Level >= 0 and node.NodeType.startswith("planet.")
    def effects(self, node):
        if not node.Industry: return
        base_upkeep = node.Industry.Kind.BaseCost.CashUpkeep
        if base_upkeep >= 2:
            return [ResourceFlow.Cash(self.REDUCTION, FlowCategory.PlanetUpkeep)]

class TourismSentienceFix:
    """Interaction between tourism and machine sentience would normally require you to deliver 2:B: to advance to prosperous. This tweak fixes that."""
    def name(self): return LS("", "")
    def desc(self): return LS("", "")
    def sentiment(self): return QualitySentiment.Neutral
    def hidden(self, node): return True

    def effects(self, node):
        B, P = Resource.All["B"], Resource.People
        if node.Level < 2: return
        already_has_a_tweaked_B_need = any(n.AskingFor == P and n.MetWith == B for n in node.Needs)
        has_induced_need_for_B = any(q.ScriptExpression == "InduceNeed('B')" for q in node.GetQualities())
        should_skip_normal_B_need = already_has_a_tweaked_B_need or has_induced_need_for_B
        if should_skip_normal_B_need:
            return [ChangeNeeds.Remove(B)]

####################################################################
# Utility qualities

class AnonymousHiddenQuality:
    def name(self): return LS("", "")
    def desc(self): return LS("", "")
    def sentiment(self): return QualitySentiment.Neutral
    def hidden(self, node): return True

class InduceNeed(AnonymousHiddenQuality):
    def __init__(self, resource_id):
        self._resource = Resource.All[resource_id]
    def effects(self, node):
        return [ChangeNeeds.AddOne(self._resource)]

class DetermineUnknownOutput(AnonymousHiddenQuality):
    def __init__(self, resource_id, limit_to_index = None):
        self._resource = Resource.All[resource_id]
        self._limit_to_index = limit_to_index

    def effects(self, node):
        return [ChangeProducts.DetermineOutput(self._resource, None, self._limit_to_index)]

class CheatProduction(AnonymousHiddenQuality):
    def __init__(self, resource_id, amount):
        self._resource = Resource.All[resource_id]
        self._amount = amount

    def effects(self, node):
        return [ChangeProducts.Add(self._amount, self._resource, "cheated")]

