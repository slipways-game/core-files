# Code implementing planetary projects 

class PlanetProject:
    def available(self, node): return node.NodeType.startswith("planet.")

# ---------------------------------------------------

class BrainMachineProject(PlanetProject):
    pass

class BrainMachineQuality:
    BONUS = 30

    def name(self): return LS("project.brain_machine", "Brain-machine interfaces")
    def desc(self): return LS("project.brain_machine.desc",
        "Improves trade income on this planet by *{1}%*.", BrainMachineQuality.BONUS)

    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): return [PercentageBonus.TradeIncome(BrainMachineQuality.BONUS)]

# ---------------------------------------------------

class SoylentProject(PlanetProject):
    def available(self, node): 
        if not PlanetProject.available(self, node): return False
        return node.HasUnmetNeedFor(Resource.All["F"])


class SoylentQuality:
    def name(self): return LS("project.soylent", "Soylent processors")
    def desc(self): return LS("project.soylent.desc",
        "All :F: needs for this planet are removed.") 
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        return [ChangeNeeds.Remove(Resource.All["F"])]

# ---------------------------------------------------

class WaterReclamationProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.HasUnmetNeedFor(Resource.All["W"])
    
class WaterReclamationQuality:
    def name(self): return LS("project.water_reclamation", "Water reclamation")
    def desc(self): return LS("project.water_reclamation.desc",
        "Completely removes a :W: need from a planet.") 
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        return [ChangeNeeds.Remove(Resource.All["W"])]

# ---------------------------------------------------

class IntegratedManufacturingProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.ActuallyProduces(Resource.All["O"])

class IntegratedManufacturingQuality:
    def name(self): return LS("project.integrated_manufacturing", "Integrated Manufacturing")
    def desc(self): return LS("project.integrated_manufacturing.desc",
        "Adds one unit of :T: on any planet producing :O:.") 
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        return [ChangeProducts.AddOne(Resource.All["T"], "integrated_manufacturing")]

# ---------------------------------------------------

class GenesisProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.IndustryProduces(Resource.All["L"]) or node.IndustryProduces(Resource.All["W"])

class GenesisQuality:
    def name(self): return LS("project.genesis", "Genesis Project")
    def desc(self): return LS("project.genesis.desc",
        "Adds one unit of :L: on any planet producing :W:. Adds one unit of :W: on any planet producing :L:.") 
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        effects = []
        if node.IndustryProduces(Resource.All["W"]):
            effects.append(ChangeProducts.AddOne(Resource.All["L"], "genesis"))
        if node.IndustryProduces(Resource.All["L"]):
            effects.append(ChangeProducts.AddOne(Resource.All["W"], "genesis"))
        return effects

# ---------------------------------------------------

class RepurposingProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.ActuallyProduces(Resource.All["B"]) or node.ActuallyProduces(Resource.All["G"])

class RepurposingQuality:
    def name(self): return LS("project.repurposing", "Repurposing")
    def desc(self): return LS("project.repurposing.desc",
        "Adds one unit of :G: on any planet producing :B:. Adds one unit of :B: on any planet producing :G:.") 
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        effects = []
        scripts_version = game.GameConfig.ScriptsVersion
        if scripts_version <= "v12":
            # legacy logic to prevent problems with older savefiles using older rules
            has_b = any(p.Resource == Resource.All["B"] and p.SourceTag != "repurposing" for p in node.Products)
            has_g = any(p.Resource == Resource.All["G"] and p.SourceTag != "repurposing" for p in node.Products)
        else:
            has_b = any(p.Resource == Resource.All["B"] and p.SourceTag != "repurposing" and not is_product_copied(p) for p in node.Products)
            has_g = any(p.Resource == Resource.All["G"] and p.SourceTag != "repurposing" and not is_product_copied(p) for p in node.Products)
        if has_b: effects.append(ChangeProducts.AddOne(Resource.All["G"], "repurposing"))
        if has_g: effects.append(ChangeProducts.AddOne(Resource.All["B"], "repurposing"))
        return effects

# ---------------------------------------------------

class EnlightenmentProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.ActuallyProduces(Resource.All["P"]) or node.HasNeedFor(Resource.All["G"])     
    def requirements_fulfilled(self, node):
        if not node.HasUnmetNeedFor(Resource.All["G"]):
            return Permission.No(LS("project.only_useful", None, "G"))
        return Permission.Yes()

class EnlightenmentQuality:
    def name(self): return LS("project.enlightenment")
    def desc(self): return LS("project.enlightenment.desc")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        return [
            ChangeNeeds.Remove(Resource.All["G"]),
            IntBonus.ImportsForSuccessful(-1),
            IntBonus.TradeRoutesForProsperous(-1)
        ]

# ---------------------------------------------------

class DiseaseEradicationProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.ActuallyProduces(Resource.People)

class DiseaseQuality:
    def __init__(self, bonus):
        self._bonus = bonus
    def name(self): return LS("project.disease_eradication", "Disease eradication")
    def desc(self): 
        return LS("project.disease_eradication.desc",
            "Improves the production of a populated planet by one :P: and adds a [[delta:+{1}H]] bonus.",
            self._bonus)
            
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node): 
        return [
            ChangeProducts.AddOne(Resource.All["P"], "disease"),
            ResourceFlow.Happiness(self._bonus, FlowCategory.TechBasedHappiness, self.name())
        ]

class Immortality:
    def __init__(self, bonus):
        self._bonus = bonus
    def name(self): return LS("project.immortality", "Immortality")
    def desc(self):
        return LS("project.immortality.desc",
            "Adds [[delta:+{1}H]] on any planet where [[ref:project.disease_eradication]] is built.", self._bonus)
    
    def applies(self, node):
        return node.HasProject(ProjectKind.All["disease_eradication"])
    def effects(self, node):
        return [ResourceFlow.Happiness(self._bonus, FlowCategory.TechBasedHappiness, self.name())]

# ---------------------------------------------------

class SkillDownloadProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return any(p.Resource.ID in SkillDownloadQuality.IMPROVED_RESOURCES for p in node.Products if p.IsReal)

class SkillDownloadQuality:
    IMPROVED_RESOURCES = "FOGTBLW"
    def name(self): return LS("project.skill_download", "Skill-up facilities")
    def desc(self): return LS("project.skill_download.desc",
        "Improves this planet's production by one additional unit of each product.")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        products = set(p.Resource for p in node.Products if p.IsReal and p.Resource.ID in self.IMPROVED_RESOURCES and not is_product_copied(p))
        if len(products) > 0:
            return [ChangeProducts.AddOne(p, "skill_download[copy]") for p in products]

# ---------------------------------------------------

class MindControlProject(PlanetProject):
    pass

class MindControlQuality:
    def name(self): return LS("project.mind_control", "Mind control")
    def desc(self): return LS("project.mind_control.desc", "Blocks any :H: penalties from resource shortages, missing export or unemployment.")
    def sentiment(self): return QualitySentiment.Neutral

    def effects(self, node):
        return BlockFlows.NegativeHappiness()

# ---------------------------------------------------

class OrbitalLabsProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.IsProducerOf(Resource.People)

    def requirements_fulfilled(self, node):
        if not node.HasAvailable(Resource.People):
            return Permission.No(LS("project.no_idle_people", "There are no idle :P: on this planet."))
    
class OrbitalLabsQuality:
    def name(self): return LS("project.orbital_labs", "Orbital labs")
    def desc(self): return LS("project.orbital_labs.desc", "Converts one of the idle :P: on this planet into [[delta:+{1}S]].", self.bonus())

    def bonus(self):
        return constants.Int("orbital_lab.bonus", 1)
    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): 
        bonus_science = self.bonus()
        return [
            ChangeProducts.ReduceProduction(1, Resource.People),
            ChangeProducts.Add(bonus_science, Resource.Science, "orbital_labs")
        ]

class CultureHubProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.IsProducerOf(Resource.People)

    def requirements_fulfilled(self, node):
        if not node.HasAvailable(Resource.People):
            return Permission.No(LS("project.no_idle_people", "There are no idle :P: on this planet."))
    
class CultureHubQuality:
    def name(self): return LS("project.culture_hub")
    def desc(self): return LS("project.culture_hub.desc", None, 1)
    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): 
        return [
            ChangeProducts.ReduceProduction(1, Resource.People),
            ChangeProducts.AddOne(Resource.All["C"], "culture_hub")
        ]

# ---------------------------------------------------

class VirtualAfterlifeProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.IsProducerOf(Resource.People)

    def requirements_fulfilled(self, node):
        if not node.HasAvailable(Resource.People):
            return Permission.No(LS("project.no_idle_people", "There are no idle :P: on this planet."))
    
class VirtualAfterlifeQuality:
    def name(self): return LS("project.virtual_afterlife", "Virtual Afterlife")
    def desc(self): return LS("project.virtual_afterlife.desc", "Converts one of the idle :P: on this planet into :H:.")

    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): 
        return [
            ChangeProducts.ReduceProduction(1, Resource.People),
            ChangeProducts.AddOne(Resource.Happiness, "virtual_afterlife")
        ]

# ---------------------------------------------------

class SlipAmpProject(PlanetProject):
    pass

class SlipAmpQuality:    
    def __init__(self, range_bonus, cost_bonus = 15): 
        self._range_bonus, self._cost_bonus = range_bonus, cost_bonus
    def name(self): return LS("project.slip_amp", "Slip amplifier")
    def desc(self): return LS("project.slip_amp.desc", "Improves the range of slipways connecting to this planet by *{1}%*.", self._range_bonus, self._cost_bonus)

    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node): 
        return [
            PercentageBonus.SlipwayRange(self._range_bonus),
            PercentageBonus.SlipwayCost(-self._cost_bonus)
        ]

# ---------------------------------------------------

class ElysiumProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.IsProducerOf(Resource.People)

class ElysiumQuality:
    CULTURE = 2
    ADDED_NEEDS = "BTOLW"

    def name(self): return LS("project.elysium")
    def desc(self): return LS("project.elysium.desc", None, self.CULTURE) 
    def sentiment(self): return QualitySentiment.Positive

    def hidden(self, node): return True

    def effects(self, node):
        preexisting = set(n.Resource.ID for n in node.Industry.Needs)
        effects = []
        for r in self.ADDED_NEEDS:
            if not r in preexisting:
                effects += [ChangeNeeds.AddOne(Resource.All[r])]
        if node.Level == 3:
            effects.append(FinalUpgradeRule.Calling(self.rule_check))
        elif node.Level == 4 and not node.HasUnmetNeeds:
            effects.append(ChangeProducts.Add(2, Resource.All["C"], "elysium"))
        return effects

    @staticmethod
    def rule_check(node):
        if node.HasUnmetNeeds:
            return Permission.No(LS("quality.elysium.condition"))
        return Permission.Yes()

# ---------------------------------------------------

class QuantumComputersProject:
    def available(self, node):
        # override the default completely, since we want to be available on structures
        is_lab = node.NodeType.startswith("structure.") and node.NodeType.endswith("lab")
        return is_lab

class QuantumComputersQuality:
    def name(self): return LS("project.quantum_computers")
    def desc(self): return LS("quality.quantum_computers.desc", None, self.bonus(), self.upkeep_change())
    def sentiment(self): return QualitySentiment.Positive

    def bonus(self):
        return constants.Int("quantum_computing.bonus")
    def upkeep_change(self):
        return constants.Int("quantum_computing.upkeep")

    def effects(self, node): 
        return [
            ChangeProducts.Add(self.bonus(), Resource.Science, "quantum"),
            PercentageBonus.StructureUpkeep(self.upkeep_change(), hidden=True)
        ]

# ---------------------------------------------------

class InterstellarNetworkProject(PlanetProject):
    pass

class InterstellarNetworkQuality:
    def name(self): return LS("project.interstellar_network")
    def desc(self): return LS("project.interstellar_network.desc_alternate")
    def effects(self, node):
        return [ChangeProducts.AddOne(Resource.All["Info"])]
    
def information_generate_routes(product, consumer, path):
    if not consumer.HasProject(ProjectKind.All["interstellar_network"]): return []
    # do they already have a need for info?
    Info = Resource.All["Info"]
    have_info_need = any(n.AskingFor == Info for n in consumer.Needs)
    if have_info_need:
        info_need = [n for n in consumer.Needs if n.AskingFor == Info][0]
        return [PossibleRoute.ForNeed(product, info_need, path)]
    else:
        return [PossibleRoute.InducingNeed(product, consumer, path)]

# ---------------------------------------------------

class TailoredEvolutionProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.ActuallyProduces(Resource.People)
    
    def requirements_fulfilled(self, node):
        reachable = game.Reachability.ReachableNodes(node)
        has_lab = any(n.NodeType.endswith("lab") for n in reachable)
        if not has_lab:
            return Permission.No(LS("project.requirement.needs_lab"))

class TailoredEvolutionQuality:
    def __init__(self, happiness, income):
        self._happiness = happiness
        self._income = income
    def name(self): return LS("project.tailored_evolution")
    def desc(self): return LS("project.tailored_evolution.desc", None, self._happiness, self._income)
    def effects(self, node):
        return [
            ResourceFlow.Happiness(self._happiness, FlowCategory.TechBasedHappiness),
            PercentageBonus.TradeIncome(self._income),
        ]

# ---------------------------------------------------

class MegastructuresProject(PlanetProject):
    def available(self, node):
        if not PlanetProject.available(self, node): return False
        return node.ActuallyProduces(Resource.People)        

class MegastructuresQuality:
    TRADE_BONUS = 25
    HAPPINESS = 1
    def name(self): return LS("project.megastructures")
    def desc(self): return LS("project.megastructures.desc", None, self.HAPPINESS, self.TRADE_BONUS)
    def effects(self, node):
        O = Resource.All["O"]
        already_has_o_need = any(ns.Resource == O for ns in node.Industry.Needs)
        if not already_has_o_need:
            yield ChangeNeeds.AddOne(O)
        if node.Receives(O):
            amount = node.AmountReceived(O)
            yield ResourceFlow.Happiness(self.HAPPINESS, FlowCategory.PlanetMadeHappiness)
            yield PercentageBonus.TradeIncome(self.TRADE_BONUS * amount)

# ---------------------------------------------------

class MassReactorsProject(PlanetProject):
    ALLOWED_STRUCTURES = ["structure.asteroid"]
    def available(self, node):
        if not node.NodeType.startswith("planet."):
            if node.NodeType not in self.ALLOWED_STRUCTURES: return False
        return node.ActuallyProduces(Resource.All["O"])

    def requirements_fulfilled(self, node):
        if not node.HasAvailable(Resource.All["O"]):
            return Permission.No(LS("project.requirement.no_free_resource", None, ":O:"))

class MassReactorsQuality:
    def name(self): return LS("project.mass_reactors")
    def desc(self): return LS("project.mass_reactors.desc")
    def effects(self, node): 
        return [
            ChangeProducts.ReduceProduction(1, Resource.All["O"]),
            ChangeProducts.AddOne(Resource.All["E"], "mass_reactors")
        ]

# ---------------------------------------------------

class HyperdenseArchProject(PlanetProject):
    pass

class HyperdenseArchQuality:
    def name(self): return LS("project.hyperdense_arch")
    def desc(self): return LS("project.hyperdense_arch.desc")
    def effects(self, node): 
        return [
            LabelEffect.With(":project:")
        ]

class HyperdenseTradeRoutes(GlobalCondition):
    EXCLUDED_RESOURCES = ""

    def activate(self):
        game.Trade.RegisterCondition(self.host())
        self.react_to(Trigger.TradeRouteEstablished, self.new_trade_route)

    def new_trade_route(self, data):
        consumer = data["to"]
        proj = consumer.Project
        if not proj or proj.Kind.ID != "hyperdense_arch": return
        route = data["route"]
        consumer = route.Consumer
        identical_routes = sum(1 for r in consumer.ImportRoutes if r.Producer == route.Producer and r.Resource == route.Resource)
        if identical_routes >= 2:
            ConsUpdateNodeData().add(consumer, "used_hyperdense", True).issue()

    def additional_trade_routes(self, product, consumer, path):
        if not consumer.HasProject(ProjectKind.All["hyperdense_arch"]): return
        producer = product.Producer
        resource = product.Resource
        if resource.ID in self.EXCLUDED_RESOURCES: return
        extras = []
        # check if tech already used at this consumer
        if consumer.CustomData.GetOr("used_hyperdense", False):
            return []
        # generate offers
        for route in consumer.ImportRoutes:
            if route.Resource != product.Resource: continue
            if route.Producer != producer: continue
            need = first(n for n in consumer.Needs if n.MetWith == product.Resource)
            offer = PossibleRoute.ForNeed(product, need, path).MakeOfferOnly()
            extras.append(offer)
        return extras


class EmpathicLinks:
    IMPROVED_RESOURCES = "FOGTBLW"
    HAPPINESS_BONUS = 1
    def name(self): return LS("quality.empathic_links")
    def desc(self): return LS("quality.empathic_links.desc", None, self.HAPPINESS_BONUS)
    def applies(self, node):
        return node.NodeType.startswith("planet.") and node.AmountReceived(Resource.People) >= 2
    def effects(self, node):
        yield ChangeProducts.AddOne(Resource.Happiness, "emp_links")

class EmpathicLinksTradeRoutes(GlobalCondition):
    def activate(self):
        game.Trade.RegisterCondition(self.host())

    def additional_trade_routes(self, product, consumer, path):
        producer = product.Producer
        resource = product.Resource
        if resource != Resource.People: return
        extras = []
        # generate offers
        for route in consumer.ImportRoutes:
            if route.Resource != product.Resource: continue
            if route.Producer != producer: continue
            existing_links = sum(1 for ir in consumer.ImportRoutes if ir.Resource == product.Resource and ir.Producer == producer)
            if existing_links >= 2: continue
            need = first(n for n in consumer.Needs if n.MetWith == product.Resource)
            offer = PossibleRoute.ForNeed(product, need, path).MakeOfferOnly()
            extras.append(offer)
        return extras
