# Rules for all the "special" resources that have non-standard logic behind them, like energy or culture.

########################################
# Energy

def energy_generate_routes(product, consumer, path):
    has_needs_or_products = len(consumer.Needs) > 0 or len(consumer.Products) > 0
    if not has_needs_or_products:
        return []
    disallowed = consumer.Industry and not consumer.Industry.AcceptsSpecialResource(Resource.All["E"])
    if disallowed:
        return []
    needs_met = all(n.IsMet for n in consumer.Needs)
    if not needs_met:
        # first case: unmet needs, so the energy will fill one of them
        unmet = [n for n in consumer.Needs if not n.IsMet and n.AskingFor is not None]
        if len(unmet) > 0:
            return [PossibleRoute.ForNeed(product, unmet[0], path)]
        else:
            return []        
    else:
        # second case: all needs met, energy will add itself
        energy_needs = [n for n in consumer.Needs if (n.AskingFor is not None and n.AskingFor.ID == "E")]
        if len(energy_needs) == 0:
            return [PossibleRoute.InducingNeed(product, consumer, path)]
        else:
            return [PossibleRoute.ForNeed(product, energy_needs[0], path)]

########################################
# Culture

def culture_generate_routes(product, consumer, path):
    if consumer.Industry and not consumer.Industry.AcceptsSpecialResource(Resource.All["C"]):
        return []
    existing_needs = [n for n in consumer.Needs if (n.AskingFor is not None and n.AskingFor.ID == "C")]
    if len(existing_needs) == 0:
        if not consumer.NodeType.startswith("planet."): return []
        return [PossibleRoute.InducingNeed(product, consumer, path)]
    else:
        return [PossibleRoute.ForNeed(product, existing_needs[0], path)]

def culture_connect_route(route):
    need = route.FulfilledNeed
    if need.ImportCount > 1: return
    quality = game.Qualities.Get(CultureQuality)
    game.Qualities.AttachForTheLifetimeOf(quality, route.Consumer, route)


class CultureQuality:
    HAPPINESS_BONUS = 1

    def name(self): return LS("quality.culture")
    def desc(self): return LS("quality.culture.desc", None, self.HAPPINESS_BONUS)        
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        effects = []
        if node.Level >= 3:
            effects.append(ResourceFlow.Happiness(self.HAPPINESS_BONUS, FlowCategory.CultureHappiness, self.name()))        
        effects.append(BlockFlows.OfCategory(FlowCategory.ResourceShortages))
        effects.append(BlockFlows.OfCategory(FlowCategory.ShortageGettingWorse))
        effects.append(BlockFlows.OfCategory(FlowCategory.PastShortages))
        if node.Level < 3:
            effects += [LabelEffect.With(":C:")]
        return effects

########################################
# Luxury

def luxury_generate_routes(product, consumer, path):
    if not consumer.NodeType.startswith("planet."): return []
    if not consumer.ActuallyProduces(Resource.People): return []
    if consumer.Industry and not consumer.Industry.AcceptsSpecialResource(Resource.All["Lux"]):
        return []
    existing_needs = [n for n in consumer.Needs if (n.AskingFor is not None and n.AskingFor.ID == "Lux")]
    if len(existing_needs) == 0:
        return [PossibleRoute.InducingNeed(product, consumer, path)]
    else:
        return [PossibleRoute.ForNeed(product, existing_needs[0], path)]

def luxury_connect_route(route):
    need = route.FulfilledNeed
    if need.ImportCount > 1: return
    quality = game.Qualities.Get(LuxuryQuality)
    game.Qualities.AttachForTheLifetimeOf(quality, route.Consumer, route)

class LuxuryQuality:
    HAPPINESS_BONUS = 2

    def name(self): return LS("quality.luxury", "Receiving luxury")
    def desc(self): return LS("quality.luxury.desc", "Planets receiving :Lux: get [[delta:{1}H]].", self.HAPPINESS_BONUS)        
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        return [ResourceFlow.Happiness(self.HAPPINESS_BONUS, FlowCategory.TechBasedHappiness, self.name())]

########################################
# Conflation

def conflated_induce_needs(product, consumer, path):
    # make sure conflated products can be mixed
    produced = product.Resource.ID
    standard_results = list(Resource.StandardRouteMatching(product, consumer, path))
    if len(standard_results) > 0:
        # standard logic has found a place, so we should use that instead of inducing something new
        return standard_results
    if any(n.AskingFor is None and n.MetWith is None for n in consumer.Needs):
        # special needs detected, let's bail before we ruin something
        return standard_results
    for n in consumer.Needs:
        if not n.IsMet: continue
        asking = n.AskingFor.ID if n.AskingFor else None
        met_with = n.MetWith.ID if n.MetWith else None
        if not asking: continue
        conflated = unlocks.IsUnlocked("conflate.%s.%s" % (produced, met_with))
        if conflated:
            present_already = any(n.MetWith == product.Resource or (n.AskingFor == product.Resource and n.MetWith is None) for n in consumer.Needs)
            if not present_already:
                return [PossibleRoute.InducingNeed(product, consumer, path)]
        # the other option - this is the resource originally asked for, but met with a conflated one
        if asking == produced and met_with != produced and unlocks.IsUnlocked("conflate.%s.%s" % (met_with, asking)):
            # check if we don't have another need already
            present_already = any(n.MetWith == product.Resource or (n.AskingFor == product.Resource and n.MetWith is None) for n in consumer.Needs)
            if not present_already:
                return [PossibleRoute.InducingNeed(product, consumer, path)]
    # otherwise defer to normal handling
    return standard_results

#############################################
# Utilities

def is_product_copied(product):
    return product.SourceTag and ("[copy]" in product.SourceTag)
