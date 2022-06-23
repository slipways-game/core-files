# Contains implementations for the "planet quirks" - these are just special qualities that are outwardly visible as an icon.

###################################################################
# Various helper classes for quirks

class PlanetQuirkAdder(GlobalCondition):
    def __init__(self, quirk, chance, new_chance = None):
        self._quirk = quirk
        eligible = eval(quirk).eligible_planets()
        self._eligible = [("planet." + kind if not "." in kind else kind) for kind in eligible]
        seed_version = game.GameConfig.Sector.SeedVersion if game.GameConfig.Sector else 4
        self._chance = chance
        if new_chance and seed_version >= 4:
            self._chance = new_chance

    def activate(self):
        self.react_to(Trigger.BeforeSignalRevealed, self.check, 600)

    def check(self, data):
        signal = data["signal"]
        chance = self._chance * 0.01
        seed_version = game.GameConfig.Sector.SeedVersion
        if seed_version >= 4:
            # increase density closer to the start for more impact
            distance = signal.Position.magnitude
            density_increase = inverse_lerp_clamped(21, 4, distance)
            chance *= (1 + density_increase)
            chance = min(chance, 0.85)
        eligible = signal.Quirk is None and signal.Contents in self._eligible
        if eligible:
            added = Randomness.WithProbability(self.rng(str(signal.Position)), chance)
            if added:
                signal.Quirk = self._quirk

###################################################################
# Quirk qualities

class QuirkMineralRich:
    """Quality adding minerals to a planet."""

    @staticmethod
    def eligible_planets(): return ["arid", "earthlike", "arctic", "jungle", "swamp"]

    def name(self): return LS("quirk.mineral_rich", "Mineral rich")
    def desc(self): return LS("quirk.mineral_rich.desc", "Enables [[ref:industry.mining_mine]] on this planet.")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "neutral", "text": ":O:", "sub_icon": "mod_nplus"}
    def hidden(self, node): return True

    def effects(self, node):
        return [ColonizationOptions.Add(IndustryKind.All["mining_mine"])]


class QuirkIrradiated:
    """Quality adding upkeep for P planets."""
    PENALTY = 2

    @staticmethod
    def eligible_planets(): return ["arid", "swamp", "earthlike", "arctic", "jungle", "ocean"]

    def name(self): return LS("quirk.irradiated", "Irradiated")
    def desc(self): return LS("quirk.irradiated.desc", "Settling :P: on this planet costs an additional [[delta:{1}$]] in upkeep.", -self.PENALTY)
    def sentiment(self): return QualitySentiment.Negative

    def visibility(self, node): 
        if node.Level < 0: return 1
        return 1 if node.ActuallyProduces(Resource.People) else 0
    def icon(self, node): return {"text": ":P:", "type": "negative", "sub_icon": "mod_negdown"}

    def effects(self, node):
        if not node.ActuallyProduces(Resource.People): return None
        return [ResourceFlow.Cash(-self.PENALTY, FlowCategory.PlanetUpkeep)]

class QuirkUnstableCore:
    """Removes P options, adds B->E."""

    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "ocean", "swamp", "mining", "primordial", "arid", "jungle"]

    def name(self): return LS("quirk.unstable_core")
    def desc(self): return LS("quirk.unstable_core.desc")
    def sentiment(self): return QualitySentiment.Negative
    def visibility(self, node): return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "neutral", "text": ":E:"}
    def hidden(self, node): return True

    @staticmethod
    def industry_prohibited(industry_kind):
        for n in industry_kind.BaseLevel.BaseNeeds:
            if n.Resource == Resource.People:
                return True
        for p in industry_kind.BaseLevel.BaseProducts:
            if p == Resource.People:
                return True
        return False
    
    def effects(self, node):
        return [
            ColonizationOptions.RemoveMatching(QuirkUnstableCore.industry_prohibited),
            ColonizationOptions.Add("core_plant"),
        ]

class QuirkAbundantResources:
    RESOURCES = ["O", "L", "W"]
    BONUS = 2

    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "ocean", "swamp", "primordial", "jungle", "mining"]

    def name(self): return LS("quirk.abundant_resources")
    def desc(self): return LS("quirk.abundant_resources.desc", None, self.BONUS)
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): 
        if node.Level < 0: return 1
        return 1 if self.is_working(node) else 0
    def icon(self, node): return {"type": "positive", "text": ":$:", "sub_icon": "mod_posup"}

    def is_working(self, node):
        return any((p.Resource.ID in self.RESOURCES) for p in node.Products if p.IsReal)

    def effects(self, node):
        if not self.is_working(node): return
        bonus = node.ExportCount * 2
        if bonus > 0:
            return [ResourceFlow.Cash(bonus, FlowCategory.SpecialBonuses)]

class QuirkSights:
    BONUS = 2

    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "ocean", "swamp", "jungle", "arid"]

    def name(self): return LS("quirk.beautiful_sights")
    def desc(self): return LS("quirk.beautiful_sights.desc", None, self.BONUS)
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): 
        if node.Level < 0: return 1
        return 1 if node.ActuallyProduces(Resource.People) else 0
    def icon(self, node): return {"type": "positive", "text": ":H:", "sub_icon": "mod_posup"}

    def effects(self, node):
        if node.Level < 2: return
        if not node.ActuallyProduces(Resource.People): return
        return [ResourceFlow.Happiness(self.BONUS, FlowCategory.PlanetMadeHappiness)]


class QuirkThinAtmo:
    PENALTY = 150

    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "ocean", "swamp", "jungle", "arid"]
    def name(self): return LS("quirk.thin_atmo")
    def desc(self): return LS("quirk.thin_atmo.desc", None, self.PENALTY)
    def sentiment(self): return QualitySentiment.Negative
    def visibility(self, node):
        return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "negative", "text": ":P:", "sub_icon": "mod_negdown"}
    
    def effects(self, node):
        if node.Level < 0:
            return [ActionCost.Calling(QuirkThinAtmo.cost_adjustment)]
    @staticmethod
    def cost_adjustment(action, prev_cost):
        action_type = action.TypeSpecifier
        if action_type.startswith("colonize/"):
            industry_id = action_type.split('/')[2]
            industry_kind = IndustryKind.All[industry_id]
            if industry_kind.BaseLevel.HasProduct(Resource.People):
                return prev_cost.Multiply(Resource.Cash, 1.0 + 0.01 * QuirkThinAtmo.PENALTY)


class QuirkForebearArtifacts:
    BOT_PLANETS = ["mining", "barren", "iceball", "lava"]

    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "ocean", "swamp", "jungle", "arid", "remnant", "mining", "barren", "iceball", "lava"]
    def name(self): return LS("quirk.forebear_artifacts")
    def desc(self): return LS("quirk.forebear_artifacts.desc")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node):
        return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "positive", "text": ":S:"}
    
    def effects(self, planet):
        if planet.Level < 0:
            planet_type = planet.Kind.ID
            industry_id = "artifact_study_b" if planet_type in self.BOT_PLANETS else "artifact_study_p"
            return [ColonizationOptions.Add(industry_id)]

class QuirkAncientRuins:
    PLANETS = ["earthlike", "arid", "swamp", "jungle", "arctic"]

    @staticmethod
    def eligible_planets(): return QuirkAncientRuins.PLANETS
    def name(self): return LS("mutator.ancient_ruins")
    def desc(self): return LS("mutator.ancient_ruins.desc")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node):
        visible = node.Level < 0 or node.Level == 0 and node.ActuallyProduces(Resource.People)
        return 1 if visible else 0
    def icon(self, node): return {"type": "positive", "text": ":C:"}
    
    def effects(self, planet):
        if planet.Level >= 1 and planet.ActuallyProduces(Resource.People):
            return [ChangeProducts.AddOne(Resource.All["C"], "ancient_ruins")]


class QuirkIntactTech:
    BOT_PLANETS = ["iceball", "barren"]

    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "arid", "barren", "iceball"]
    def name(self): return LS("mutator.intact_tech")
    def desc(self): return LS("quirk.intact_tech.desc")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node):
        return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "neutral", "text": ":T:"}
    
    def effects(self, planet):
        if planet.Level < 0:
            planet_type = planet.Kind.ID
            industry_id = "intact_tech_b" if planet_type in self.BOT_PLANETS else "intact_tech_p"
            return [ColonizationOptions.Add(industry_id)]


class StandardPlanetQuirks(GlobalCondition):
    QUIRK_OPTIONS = [
        QuirkAncientRuins, QuirkForebearArtifacts, QuirkThinAtmo, QuirkSights, QuirkAbundantResources, QuirkUnstableCore,
        QuirkIrradiated, QuirkMineralRich, QuirkIntactTech
    ]
    """Adds a very small amount of quirks on standard maps."""
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # generate rips     
        map_generation.Refinement("after_planet_types", 2000, self.refinement_add_some_quirks)

    def refinement_add_some_quirks(self, gen, signals, zones):
        if gen.SeedVersion < 4: return # only in v4 or later games
        rng = gen.RNGForTask("std_quirks")
        chance = Randomness.Float(rng, 4.0, 8.0) / (len(zones) - 1)
        for i, z in enumerate(zones):
            if i == 0: continue
            add_something = Randomness.WithProbability(rng, chance)
            if not add_something: continue
            quirk_cls = Randomness.Pick(rng, self.QUIRK_OPTIONS)
            eligible = set("planet.%s" % pkind for pkind in quirk_cls.eligible_planets())
            possible = [s for s in z.Signals if s.Contents in eligible and s.Quirk is None]
            if len(possible) == 0: continue
            selected = Randomness.Pick(rng, possible)
            selected.Quirk = quirk_cls.__name__ + "()"
            gen_log("Adding quirk: %s -> %s" % (selected.Position, selected.Quirk))
