# Contains code for all the core sector quirks available.

def mut_contents(mutator_id, data, desc_data = None):
    new_data = {
        "id": mutator_id,
        "label": LS("mutator.%s" % mutator_id),
        "description": LS("mutator.%s.desc" % mutator_id, None, *(desc_data if desc_data else []))
    }
    for k, v in data.items():
        new_data[k] = v
    return new_data

class MutatorQuality:
    def name(self): return LS("mutator.%s" % self.id())
    def desc(self): return LS("mutator.%s.desc" % self.id(), None, *(self.desc_data() if hasattr(self, "desc_data") else []))

#############################################################################
# Setup for mutator-based scoring

class QuirkScoringSetup(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_scoring, 600)
        self.react_to(Trigger.GameLoaded, self.setup_scoring, 600)
    
    def setup_scoring(self, _ = None):
        empire.Scoring.AddRule(ScoringQuirks())    

class ScoringQuirks(Scoring):
    def id(self): return "scoring.quirks"
    def kind(self): return ScoreKind.Multiplier

    def title(self): return LS("scoring.quirks", "Sector difficulty")
    def description(self): 
        text = L("scoring.quirks.desc", "The following conditions modify your score:")
        for m in self.relevant_mutators():
            if m.ScoreModifier < 0:
                bonus_text = "[s:Bad]%d%%[/s]" % m.ScoreModifier
            else:
                bonus_text = "[s:Good]+%d%%[/s]" % m.ScoreModifier
            text += "\n*%s* (%s)" % (m.Label.ToString(), bonus_text)
        return text
        
    @staticmethod
    def relevant_mutators():
        for m in game.GameConfig.AllConfiguredMutators():
            if m.ScoreModifier != 0:
                yield m

    def calculate_score(self, fraction):
        total_mod = 0
        had_any = False
        for m in self.relevant_mutators():
            total_mod += m.ScoreModifier
            had_any = True
        if not had_any: return None
        effective = round(100.0 + total_mod * fraction)
        text = L("scoring.quirks.multiplier", "x {1}% *Sector Conditions*", effective)
        quirk_percent = effective - 100
        quirk_percent_str = "+%d%%" % quirk_percent if quirk_percent > 0 else "%d%%" % quirk_percent
        return Score.Multiplier(text, effective * 0.01).WithShort(quirk_percent_str)

#############################################################################
# Sector types

def mut_st_unstable_izzium():
    return mut_contents("sector.izzium", {
        "kind": "sector_type",
        "packages": ["modes/campaign-diaspora/m-izzium/st-izzium"]
    })

def mut_st_anomalies():
    return mut_contents("sector.anomalies", {
        "kind": "sector_type",
        "score_modifier": +10,
        "packages": ["modes/campaign-diaspora/m-dark/st-dark"]
    })

def mut_st_rips():
    return mut_contents("sector.rips", {
        "kind": "sector_type",
        "score_modifier": +15,
        "packages": ["modes/campaign-diaspora/m-babyrips/st-babyrips"]
    })

def mut_st_hub():
    return mut_contents("sector.hub", {
        "kind": "sector_type",
        "score_modifier": -10,
        "packages": ["modes/campaign-diaspora/m-five/st-five"],
        "effects": ["cond_early(FiveRacesSectorType())"]
    })

def mut_st_one_race():
    return mut_contents("sector.one_race", {
        "kind": "sector_type",
        "score_modifier": +10,
        "packages": ["modes/campaign-diaspora/st-onerace/st-onerace"],
        "effects": ["cond_early(OneRaceSectorType())"]       
    })

#############################################################################
# Actual mutator rules
#

def mut_increased_tech_costs(increases):
    """Common mutator for changing tech costs in modes."""
    effects = []
    for lv in range(5):
        letter = chr(ord("a") + lv)
        effects.append("increase(tech.cost.%s.low, %d%%)" % (letter, increases[lv] - 100))
        effects.append("increase(tech.cost.%s.high, %d%%)" % (letter, increases[lv+1] - 100))
    return mut_contents("increased_tech_costs", {
        "hidden": True,
        "effects": effects
    })

def mut_quest_difficulty(cap, offset):
    """Common mutator for changing quest difficulties."""
    return mut_contents("quest_difficulty", {
        "hidden": True,
        "effects": [
            "increase(quests.difficulty_cap, %d)" % cap,
            "increase(quests.difficulty_offset, %d)" % offset
        ]
    })

#############################################################################

def mut_skilled_scientists():
    return mut_contents("skilled_scientists", {
        "kind": "positive",
        "score_modifier": -15,
        "effects": ["quality(SkilledScientistsQuality())"]
    }, [1])

class SkilledScientistsQuality(MutatorQuality):
    def id(self): return "skilled_scientists"
    def desc_data(self): return [1]
    def sentiment(self): return QualitySentiment.Positive    

    def applies(self, node):
        if node.NodeType != "structure.lab": return False
        researcher_need = node.Need(Resource.People)
        if researcher_need is None: return False
        return researcher_need.ImportCount >= 2

    def effects(self, node):
        return [ChangeProducts.AddOne(Resource.Science, "skilled_scientists")]

#############################################################################

def mut_rich_deposits():
    return mut_contents("rich_deposits", {
        "kind": "positive",
        "score_modifier": -5,
        "effects": ["quality(RichDepositsQuality())"]
    })

class RichDepositsQuality(MutatorQuality):
    def id(self): return "rich_deposits"
    def sentiment(self): return QualitySentiment.Positive    

    def applies(self, node):
        return node.NodeType == "planet.mining" and node.ActuallyProduces(Resource.All["O"])

    def effects(self, node):
        return [ChangeProducts.AddOne(Resource.All["O"], "rich_deposits")]

#############################################################################

def mut_miners_union(upkeep):
    return mut_contents("miners_union", {
        "kind": "negative",
        "score_modifier": +5,
        "effects": ["quality(MinersUnionQuality(%d))" % upkeep]
    }, [upkeep])

class MinersUnionQuality(MutatorQuality):
    def __init__(self, upkeep):
        self._upkeep = upkeep

    def id(self): return "miners_union"
    def desc_data(self): return [self._upkeep]
    def sentiment(self): return QualitySentiment.Negative

    def applies(self, node):
        return node.NodeType == "planet.mining"

    def effects(self, node):
        return [ResourceFlow.Cash(-self._upkeep, FlowCategory.PlanetUpkeep, self.name())]

#############################################################################

def mut_weak_slipspace(how_much):
    return mut_contents("weak_slipspace", {
        "kind": "negative",
        "score_modifier": +10,
        "effects": [
            "reduce(slipspace_overload.starts_at, 15%)"
        ]
    }, [how_much])

#############################################################################

def mut_score(label, rule_expr):
    desc = eval(rule_expr).description()
    return {
        "id": label,
        "label": LS(label),
        "description": LS("mutator.scoring_replacement.desc", "Replaces the scoring for empire size with the following rule:\n{1}", desc),
        "kind": "score_replacing",
        "conditions": [
            "MutReplaceEmpireSizeScoring(%s)" % rule_expr
        ]
    }

class MutReplaceEmpireSizeScoring(GlobalCondition):
    """Replaces the third scoring rule at setup time with something else."""
    def __init__(self, replacement):
        self._replacement = replacement

    def replace_scoring_empire_size(self):
        return self._replacement

class MutScoringPopulation(Scoring):
    BONUS = 80

    def id(self): return "mutator.score_for_population"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("mutator.score_for_population")
    def description(self): return LS("scoring.mut.population.desc", "Each employed :P: is worth *{1}:star:*.", self.BONUS)

    def calculate_score(self, fraction):
        total_delivered = sum(1 for tr in every(TradeRoute) if tr.Resource.ID == "P")
        return Score.Add("%d :P:" % total_delivered, total_delivered * self.BONUS)

class MutScoringProduction(Scoring):
    def __init__(self, id, resource, bonus):
        self._id = id
        self._resource = Resource.All[resource]
        self._bonus = bonus

    def id(self): return self._id
    def kind(self): return ScoreKind.Addition
    
    def title(self): return LS(self._id)
    def description(self): return LS("scoring.mut.production.desc", "Each unit of {1} produced is worth *{2}:star:*.", ":%s:" % self._resource.ID, self._bonus)

    def calculate_score(self, fraction):
        total_made = game.Nodes.TotalProduction(self._resource)
        return Score.Add("%d :%s:" % (total_made, self._resource.ID), total_made * self._bonus)

class MutScoringProjects(Scoring):
    def __init__(self, bonus):
        self._bonus = bonus

    def id(self): return "mutator.score_for_projects"
    def kind(self): return ScoreKind.Addition
    
    def title(self): return LS("mutator.score_for_projects")
    def description(self): return LS("scoring.mut.projects.desc", "Each planet with a planetary project is worth *{1}:star:*.", self._bonus)

    def calculate_score(self, fraction):
        total = sum(1 for p in every(Planet) if p.HasAnyProject)
        return Score.Add("%d :project:" % total, total * self._bonus)

class MutScoringSuccessfulOfType(Scoring):
    def __init__(self, id, kind, bonus):
        self._id = id
        self._kind = PlanetKind.All[kind]
        self._bonus = bonus

    def id(self): return self._id
    def kind(self): return ScoreKind.Addition
    
    def title(self): return LS(self._id)
    def description(self): return LS("scoring.mut.successful_of_type.desc", "Each [[ref:planet.{1}]] planet that is [[ref:level.2]] or better is worth *{2}:star:*.", 
        self._kind.ID, self._bonus)

    def calculate_score(self, fraction):
        total = sum(1 for p in every(Planet) if p.Level >= 2 and p.Kind == self._kind)
        return Score.Add("%d :planet:" % total, total * self._bonus)

class MutScoringTechs(Scoring):
    def __init__(self, bonus):
        self._bonus = bonus

    def id(self): return "mutator.score_for_techs"
    def kind(self): return ScoreKind.Addition
    
    def title(self): return LS("mutator.score_for_techs")
    def description(self): return LS("scoring.mut.techs.desc", "Each invented technology is worth *{1}:star:*.", self._bonus)

    def calculate_score(self, fraction):
        total = sum(1 for t in game.Technology.AllInvented)
        return Score.Add("%d :tech:" % total, total * self._bonus)

class MutScoringExports(Scoring):
    def __init__(self, exports, bonus):
        self._exports = exports
        self._bonus = bonus

    def id(self): return "mutator.score_for_exports"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("mutator.score_for_exports")
    def description(self): return LS("scoring.mut.exports.desc", "Each planet with at least {1} exports is worth *{2}:star:*.", self._exports, self._bonus)

    def calculate_score(self, fraction):
        total = sum(1 for p in every(Planet) if p.ExportCount >= self._exports)
        return Score.Add("%d :planet:" % total, total * self._bonus)

#############################################################################

def mut_old_ruins():
    return mut_contents("old_ruins", {
        "kind": "industries",
        "score_modifier": +10,
        "effects": ["quality(MutOldRuins())"]
    })

def mut_high_birth_rate():
    return mut_contents("high_birth_rate", {
        "kind": "industries",
        "score_modifier": -5,
        "effects": ["quality(MutHighBirthRate())"]
    })

def mut_radiation():
    return mut_contents("radiation", {
        "kind": "quirk",
        "score_modifier": +5,
        "conditions": ["PlanetQuirkAdder('QuirkIrradiated()', 35)"]
    }, desc_data=[2])

def mut_unstable_planets():
    return {
        "id": "unstable_planets",
        "label": LS("mutator.unstable_planets"),
        "description": LS("mutator.planets_affected.desc", None, LS("quirk.unstable_core"), LS("quirk.unstable_core.desc")),
        "kind": "quirk",
        "score_modifier": +0,
        "conditions": ["PlanetQuirkAdder('QuirkUnstableCore()', 20, 28)"]
    }

def mut_abundant():
    return {
        "id": "abundant_resources",
        "label": LS("quirk.abundant_resources"),
        "description": LS("mutator.planets_affected.desc", None, LS("quirk.abundant_resources"), LS("quirk.abundant_resources.desc", None, QuirkAbundantResources.BONUS)),
        "kind": "quirk",
        "score_modifier": -5,
        "conditions": ["PlanetQuirkAdder('QuirkAbundantResources()', 15, 25)"]
    }

def mut_sights():
    return {
        "id": "beautiful_sights",
        "label": LS("quirk.beautiful_sights"),
        "description": LS("mutator.planets_affected.desc", None, LS("quirk.beautiful_sights"), LS("quirk.beautiful_sights.desc", None, QuirkSights.BONUS)),
        "kind": "quirk",
        "score_modifier": -5,
        "conditions": ["PlanetQuirkAdder('QuirkSights()', 12, 20)"]
    }



class MutOldRuins:
    def name(self): return LS("mutator.old_ruins")
    def desc(self): return LS("mutator.old_ruins.desc")
    def sentiment(self): return QualitySentiment.Negative
    def hidden(self, node): return True
    def applies(self, node):
        return node.NodeType == "planet.remnant"
    def effects(self, node):
        return [
            ColonizationOptions.Remove("remnant_bots"),
        ]

class MutHighBirthRate:
    def name(self): return LS("mutator.high_birth_rate")
    def desc(self): return LS("mutator.high_birth_rate.desc")
    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        if node.Industry is None: return False
        if not node.ActuallyProduces(Resource.People) and not node.IndustryProduces(Resource.People): return False
        if not node.HasUnmetNeeds: return True
        # some unmet needs might be OK if they're additional ones, eg. resulting from a tech like elysium
        industry_needs = [ns.Resource for ns in node.Industry.Needs]
        has_unmet_industry_needs = any(not n.IsMet and n.AskingFor in industry_needs for n in node.Needs)
        return not has_unmet_industry_needs
        
    def effects(self, node):
        return [
            ChangeProducts.AddOne(Resource.People, "high_birth_rate")
        ]

#############################################################################

def mut_more_fw_mining():
    return {
        "id": "mutator.industrial_zone",
        "label": LS("mutator.industrial_zone", "Former industrial zone"),
        "description": LS("mutator.more_planets_of_two_types.desc", None, "planet.factory", "planet.mining"),
        "kind": "composition",
        "score_modifier": -5,
        "conditions": [
            "MapGenGuaranteeMiningForgeworld()"
        ]
    }

def mut_more_cold():
    return {
        "id": "mutator.faint_suns",
        "label": LS("mutator.faint_suns", "Faint suns"),
        "description": LS("mutator.more_planets_of_two_types.desc", None, "planet.ice", "planet.arctic"),
        "kind": "composition",
        "score_modifier": +5,
        "conditions": [
            "MapGenGuaranteeCold()"
        ]
    }

def mut_more_hot():
    return {
        "id": "mutator.dry_sand",
        "label": LS("mutator.dry_sand", "Dry sand"),
        "description": LS("mutator.more_planets_of_two_types.desc", None, "planet.barren", "planet.arid"),
        "kind": "composition",
        "score_modifier": +10,
        "conditions": [
            "MapGenGuaranteeHot()"
        ]
    }

def mut_more_earth():
    return {
        "id": "mutator.hospitable",
        "label": LS("mutator.hospitable", "Hospitable"),
        "description": LS("mutator.more_planets_of_one_type.desc", None, "planet.earthlike"),
        "kind": "composition",
        "score_modifier": -10,
        "conditions": [
            "MapGenGuaranteeEarth()"
        ]
    }

def mut_more_young():
    return {
        "id": "mutator.young",
        "label": LS("mutator.young", "Young planets"),
        "description": LS("mutator.more_planets_of_two_types.desc", None, "planet.primordial", "planet.lava"),
        "kind": "composition",
        "score_modifier": 0,
        "conditions": [
            "MapGenGuaranteeYoung()"
        ]
    }

def mut_no_bad():
    return {
        "id": "mutator.no_bad",
        "label": LS("mutator.no_bad", "Teeming with life"),
        "description": LS("mutator.no_bad.desc", "This sector contains no uninhabitable planets."),
        "kind": "composition",
        "score_modifier": -15,
        "conditions": [
            "MapGenNoBadPlanets()"
        ]
    }

def mut_no_earth():
    return {
        "id": "mutator.no_earth",
        "label": LS("mutator.no_earth", "Inhospitable"),
        "description": LS("mutator.no_planet_of_one_type.desc", "This sector contains no [[ref:{1}]] planets.", "planet.earthlike"),
        "kind": "composition",
        "score_modifier": +5,
        "conditions": [
            "MapGenNoEarth()"
        ]
    }

def mut_quickstart_favorable():
    return {
        "id": "quickstart",
        "label": LS("", ""),
        "description": LS("", ""),
        "kind": "composition",
        "score_modifier": 0,
        "conditions": [
            "MapGenQuickstartFavorable()"
        ]
    }

class MapGenGuaranteePlanets(GlobalCondition):
    def __init__(self, pairs):
        self._pairs = pairs

    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)
    def on_map_setup(self, data):
        map_generation = data["generation"]
        map_generation.Refinement("after_planet_types", 600, self.refinement_replace_some_planets)

    def refinement_replace_some_planets(self, gen, signals, zones):
        kinds = [p[0] for p in self._pairs]
        for kind, percent_first, percent, preferred_victims in self._pairs:
            rng = gen.RNGForTask("replace_planets")
            total_replaced = 0
            for z_no, z in enumerate(zones):
                preferred, victims, preexisting = [], [], 0
                planet_count = 0
                for s in z.Signals:
                    if not s.Contents.startswith("planet."): continue
                    planet_count += 1
                    if s.Contents == kind:
                        preexisting += 1
                    elif s.Contents.startswith("planet.") and s.Contents not in kinds:
                        if s.Contents in preferred_victims:
                            preferred.append(s)
                        else:
                            victims.append(s)
                # how many planets should we switch to get by X%?                
                ratio = (percent_first if z.Index == 0 else percent) * 0.01
                goal = round(planet_count * ratio)
                to_add = max(0, goal - preexisting)
                selected_victims = []
                selected_victims += Randomness.PickMany(rng, preferred, min(len(preferred), to_add))
                if len(selected_victims) < to_add:
                    selected_victims += Randomness.PickMany(rng, victims, min(len(victims), to_add - len(selected_victims)))
                # actually replace them
                for v in selected_victims:
                    v.Contents = kind
                    total_replaced += 1
                gen_log("Planet replaced in zone %d: %d planets." % (z_no, len(selected_victims)))
            gen_log("Planet replacement refinement ran, replaced: %d planets." % total_replaced)

class MapGenReducePlanets(GlobalCondition):
    def __init__(self, pairs):
        self._pairs = pairs

    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)
    def on_map_setup(self, data):
        map_generation = data["generation"]
        map_generation.Refinement("after_planet_types", 610, self.refinement_replace_some_planets)

    def refinement_replace_some_planets(self, gen, signals, zones):
        for kind, percent_first, percent, target_types in self._pairs:
            rng = gen.RNGForTask("replace_planets")
            total_replaced = 0
            for z in zones:
                preexisting, planet_count = [], 0
                for s in z.Signals:
                    if not s.Contents.startswith("planet."): continue
                    planet_count += 1
                    if s.Contents == kind:
                        preexisting.append(s)
                # how many planets should we switch to get down to X%?                
                ratio = (percent_first if z.Index == 0 else percent) * 0.01
                goal = round(planet_count * ratio)
                to_remove = max(0, len(preexisting) - goal)
                if to_remove == 0: continue
                selected_victims = []
                selected_victims += Randomness.PickMany(rng, preexisting, min(len(preexisting), to_remove))
                # actually replace them
                for v in selected_victims:
                    v.Contents = Randomness.Pick(rng, target_types)
                    total_replaced += 1
            log("Planet replacement refinement ran, replaced: %d planets." % total_replaced)

class MapGenGuaranteeMiningForgeworld(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.factory", 18, 15, ["planet.barren", "planet.ice", "planet.lava", "planet.remnant"]),
            ("planet.mining", 15, 13, ["planet.barren", "planet.ice", "planet.lava", "planet.remnant"])
        ])

class MapGenGuaranteeCold(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.ice", 15, 15, ["planet.arctic", "planet.barren", "planet.arid", "planet.lava"]),
            ("planet.arctic", 15, 15, ["planet.earthlike", "planet.swamp", "planet.ocean", "planet.arid", "planet.jungle"])
        ])

class MapGenGuaranteeHot(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.barren", 15, 15, ["planet.arctic", "planet.ice", "planet.arid", "planet.lava"]),
            ("planet.arid", 15, 15, ["planet.earthlike", "planet.swamp", "planet.ocean", "planet.arctic", "planet.jungle"])
        ])

class MapGenGuaranteeEarth(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.earthlike", 15, 15, ["planet.swamp", "planet.ocean", "planet.jungle", "planet.arctic", "planet.arid"]),
        ])

class MapGenGuaranteeYoung(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.lava", 15, 15, ["planet.ice", "planet.barren", "planet.arid", "planet.earthlike"]),
            ("planet.primordial", 15, 15, ["planet.barren", "planet.arid", "planet.arctic", "planet.ice", "planet.remnant"])
        ])

class MapGenNoBadPlanets(MapGenReducePlanets):
    def __init__(self):
        MapGenReducePlanets.__init__(self, [
            ("planet.lava", 0, 0, ["planet.mining", "planet.primordial"]),
            ("planet.barren", 0, 0, ["planet.arid", "planet.swamp"]),
            ("planet.ice", 0, 0, ["planet.arctic", "planet.ocean"])
        ])

class MapGenNoEarth(MapGenReducePlanets):
    def __init__(self):
        MapGenReducePlanets.__init__(self, [
            ("planet.earthlike", 0, 0, ["planet.arctic", "planet.arid", "planet.ocean", "planet.jungle", "planet.swamp"]),
        ])

class MapGenQuickstartFavorable(MapGenReducePlanets):
    def __init__(self):
        MapGenReducePlanets.__init__(self, [
            ("planet.lava", 0, 0.03, ["planet.mining", "planet.primordial", "planet.earthlike", "planet.ocean", "planet.jungle", "planet.remnant"]),
            ("planet.barren", 0, 0.03, ["planet.arctic", "planet.swamp", "planet.factory", "planet.earthlike", "planet.arid", "planet.remnant"]),
            ("planet.ice", 0, 0.03, ["planet.earthlike", "planet.ocean", "planet.arctic", "planet.mining", "planet.remnant"])
        ])

########################################################################
# SECOND UPDATE MUTATORS start here.
# Mutators added in the second update and valid for seed versions 3+


### Toxic water

def mut_toxic_water():
    return {
        "id": "toxic_water",
        "label": LS("mutator.toxic_water"),
        "description": LS("mutator.toxic_water.desc", None, QToxicWaterQuality.INCOME_BONUS),
        "kind": "industries",
        "score_modifier": +5,
        "effects": ["quality(QToxicWaterQuality())"]
    }

class QToxicWaterQuality:
    INCOME_BONUS = 3
    def name(self): return LS("mutator.toxic_water")
    def desc(self): return LS("mutator.toxic_water.desc", None, QToxicWaterQuality.INCOME_BONUS)
    def sentiment(self): return QualitySentiment.Neutral    
    def applies(self, node):
        return node.NodeType.startswith("planet.") and node.Industry and node.Industry.Kind.BaseLevel.HasProduct(Resource.All["W"])    
    def effects(self, node):
        W = Resource.All["W"]
        # production reduced
        effects = [ChangeProducts.ReduceProduction(1, W)]
        # cash earned
        traded = node.AmountProduced(W) - node.AmountAvailable(W)
        bonus = self.INCOME_BONUS * traded
        if bonus > 0: effects.append(ResourceFlow.Cash(bonus, FlowCategory.SpecialBonuses))
        # done!
        return effects

### Rust and ruin

def mut_rust_and_ruin():
    return {
        "id": "rust_and_ruin",
        "label": LS("mutator.rust_and_ruin"),
        "description": LS("mutator.rust_and_ruin.desc"),
        "kind": "industries",
        "score_modifier": +10,
        "effects": ["quality(QRustAndRuinQuality())"]
    }

class QRustAndRuinQuality:
    def name(self): return LS("mutator.rust_and_ruin")
    def desc(self): return LS("mutator.rust_and_ruin.desc")
    def sentiment(self): return QualitySentiment.Negative
    def applies(self, node):
        return node.NodeType == "planet.factory"
    def effects(self, node):
        T = Resource.All["T"]
        if node.Level == 0:
            ikind = node.Industry.Kind
            if ikind.MaxLevel > 0 and ikind.Levels[1].HasNeed(T): 
                yield ChangeNeeds.AddOne(T)        
        yield EditDisplayedIndustry(QRustAndRuinQuality.edit_industry)
    @staticmethod
    def edit_industry(displayed):
        T = Resource.All["T"]
        if displayed.Level != 0: return displayed
        ikind = displayed.Kind
        if ikind.MaxLevel > 0 and ikind.Levels[1].HasNeed(T):
            displayed.ShownNeeds.Add(NeedSpec.Simple(T))
        return displayed

### Depleted soil

def mut_depleted_soil():
    return {
        "id": "depleted_soil",
        "label": LS("mutator.depleted_soil"),
        "description": LS("mutator.depleted_soil.desc"),
        "kind": "industries",
        "score_modifier": +15,
        "effects": ["quality(QDepletedSoilQuality())"]
    }


class QDepletedSoilQuality:
    def name(self): return LS("mutator.depleted_soil")
    def desc(self): return LS("mutator.depleted_soil.desc")
    def sentiment(self): return QualitySentiment.Negative
    def applies(self, node):
        return node.NodeType.startswith("planet.") and (node.Level < 0 or node.IndustryProduces(Resource.All["F"]))
    def effects(self, node):
        F = Resource.All["F"]
        yield EditDisplayedIndustry(QDepletedSoilQuality.edit_industry)
        if node.IndustryProduces(F):
            if node.Level == 0:
                yield ChangeProducts.ReduceProduction(1, F)
            if node.Level == 0 and node.Industry.Kind.MaxLevel > 0:
                lv0 = node.Industry.Kind.Levels[0]
                lv1 = node.Industry.Kind.Levels[1]
                lv0_resources = list(n.Resource for n in lv0.BaseNeeds)
                for index, need in enumerate(lv1.BaseNeeds):
                    if need.IsSimple and need.Resource not in lv0_resources:
                        yield ChangeNeeds.AddOne(need)

    @staticmethod
    def edit_industry(displayed):
        F = Resource.All["F"]
        ikind = displayed.Kind
        # remove one F product if possible
        if displayed.Level == 0:
            foods = [index for index, p in enumerate(displayed.ShownProducts) if p == F]
            if len(foods) >= 2:
                displayed.ShownProducts.RemoveAt(foods[0])
            elif len(foods) == 1:
                displayed.ShownAsProducing = False
        # add needs from LV1, if possible
        if displayed.Level == 0 and ikind.MaxLevel > 0:
            lv0 = ikind.Levels[0]
            if F not in lv0.BaseProducts: return displayed
            lv1 = ikind.Levels[1]
            lv0_resources = list(n.Resource for n in lv0.BaseNeeds)
            for need in lv1.BaseNeeds:
                if need.IsSimple and need.Resource not in lv0_resources:
                    displayed.ShownNeeds.Add(need)
        return displayed

### Perk mutators

def mut_gifted_council():
    return {
        "id": "gifted_council",
        "label": LS("mutator.gifted_council"),
        "description": LS("mutator.gifted_council.desc"),
        "kind": "perks",
        "score_modifier": -10,
        "effects": ["increase(perks.to_pick,1)"]
    }

def mut_inept_council():
    return {
        "id": "inept_council",
        "label": LS("mutator.inept_council"),
        "description": LS("mutator.inept_council.desc"),
        "kind": "perks",
        "score_modifier": +10,
        "effects": ["reduce(perks.to_pick,1)"]
    }

### Engineers

def mut_engineers():
    discount = 50
    return {
        "id": "engineers",
        "label": LS("mutator.engineers"),
        "description": LS("mutator.engineers.desc", None, discount),
        "kind": "costs",
        "score_modifier": -10,
        "effects": ["reduce(structure.cost.$,%d%%)" % discount]
    }

### Charged slipspace

def mut_charged_slipspace():
    range, cost = 15, 10
    return {
        "id": "charged_slipspace",
        "label": LS("mutator.charged_slipspace"),
        "description": LS("mutator.charged_slipspace.desc", None, range, cost),
        "kind": "costs",
        "score_modifier": -10,
        "effects": [
            "increase(slipway.range,%d%%)" % range,
            "reduce(connection.slipway.cost.$,%d%%)" % cost
        ]
    }

### Incompetent scientists

def mut_incompetent_scientists():
    return {
        "id": "incompetent_scientists",
        "label": LS("mutator.bad_scientists"),
        "description": LS("mutator.bad_scientists.desc"),
        "kind": "science",
        "score_modifier": 15,
        "effects": ["quality(QIncompetentScientistsQuality())"]
    }

class QIncompetentScientistsQuality:
    def name(self): return LS("mutator.bad_scientists")
    def desc(self): return LS("mutator.bad_scientists.desc")
    def sentiment(self): return QualitySentiment.Negative
    
    def applies(self, node):
        return node.NodeType == "structure.lab"

    def effects(self, node):
        if node.Level == 0: return
        S = Resource.All["S"]
        researchers = lab_count_researchers(node)
        penalty = max(0, 3 - researchers)
        return [ChangeProducts.ReduceProduction(penalty, S)]

### Mad scientists

def mut_mad_science():
    return {
        "id": "mad_science",
        "label": LS("mutator.mad_science"),
        "description": LS("mutator.mad_science.desc"),
        "kind": "science",
        "score_modifier": 0,
        "effects": ["cond_early(QMadScience())"]
    }

class QMadScience(GlobalCondition):
    RANGES = [40, 30, 25, 20, 15]

    def activate(self):
        self.recreate_orderings()
    
    def recreate_orderings(self):
        rng = game.RNG("mad_science")
        race_ids = list(r.ID for r in Race.AllPlayable)
        mod_list = [-1, -1, 0, 1, 1]
        Randomness.Shuffle(rng, mod_list)
        Randomness.Shuffle(rng, race_ids)
        modifiers = [{} for _ in range(5)]
        for race in race_ids:
            for tier, mod in enumerate(mod_list):
                modifiers[tier][race] = mod
            mod_list = mod_list[-1:] + mod_list[:-1] # rotate list
        self._modifiers_by_tier = modifiers

    def global_cost_adjustment(self, thing):
        if isinstance(thing, KnownTech):
            return self.manipulate_tech_cost
        return None
 
    def manipulate_tech_cost(self, current_cost, known_tech):
        tier = known_tech.EffectiveTier
        try:
            tier_modifiers = self._modifiers_by_tier[tier]
        except IndexError:
            return current_cost
        race_id = known_tech.Source.Race.ID if known_tech.Source.IsFromRace else None
        modifier = tier_modifiers.get(race_id, 0.0)
        modifier *= self.RANGES[tier]
        modified_cost = current_cost.Multiply(Resource.Science, 1.0 + 0.01 * modifier)
        return modified_cost

### Consumerist

def mut_consumerist_society():
    return mut_contents("consumerist_society", {
        "id": "consumerist_society",
        "kind": "prosperity",
        "score_modifier": +10,
        "effects": ["increase(prosperous.import_export,1)"]
    })

### Eager colonists

def mut_eager_colonists():
    return mut_contents('eager_colonists', {
        "id": "eager_colonists",
        "kind": "time",
        "score_modifier": -5,
        "effects": ["quality(QEagerColonistsQuality())"]
    })

class QEagerColonistsQuality:
    def name(self): return LS("mutator.eager_colonists")
    def desc(self): return LS("mutator.eager_colonists.desc")
    def sentiment(self): return QualitySentiment.Positive
    def applies(self, node):
        return node.NodeType.startswith("planet.")
    def effects(self, node):
        if node.Level < 0:
            return [ActionCost.Calling(QEagerColonistsQuality.cost_adjustment)]
    @staticmethod
    def cost_adjustment(action, prev_cost):
        action_type = action.TypeSpecifier
        if action_type.startswith("colonize/"):
            industry_id = action_type.split('/')[2]
            industry_kind = IndustryKind.All[industry_id]
            if industry_kind.BaseLevel.HasProduct(Resource.People):
                return prev_cost.ChangeTime(1)

### Asteroid belt

def mut_asteroid_belts():
    return mut_contents('asteroid_belts', {
        "kind": "composition",
        "score_modifier": -5,
        "effects": ["cond(EmptySignalSwap('structure.asteroid', 45))"]
    })

### Administration

def mut_efficient_admin():
    slowdown = 25
    return mut_contents('efficient_admin', {
        "kind": "admin_costs",
        "score_modifier": -15,
        "effects": ["increase(admin_cost.interval_length,%d%%)" % slowdown]
    }, [slowdown])

### Doubled needs

def mut_large_needs():
    return mut_contents('large_needs', {
        "kind": "cash",
        "score_modifier": +0,
        "effects": ["quality(QLargeNeedsQuality())"]
    }, [QLargeNeedsQuality.BONUS, QLargeNeedsQuality.PENALTY])

class QLargeNeedsQuality:
    PENALTY = 15
    BONUS = 15
    def name(self): return LS("mutator.large_needs")
    def desc(self): return LS("mutator.large_needs.desc", None, self.BONUS, self.PENALTY)
    def sentiment(self): return QualitySentiment.Negative
    def applies(self, node):
        return node.NodeType.startswith("planet.")
    def effects(self, node):
        if node.Level >= 0:
            has_a_double = any(n.ImportCount >= 2 for n in node.Needs)
            modifier = self.BONUS if has_a_double else -self.PENALTY
            return [PercentageBonus.TradeIncome(modifier)]

### Quirk-based mutators

def mut_contents_quirk(id, quirk_class, chance, more_data):
    data = {
        "id": id,
        "label": LS("mutator.%s" % id),
        "description": LS("mutator.planets_affected.desc", None, quirk_class().name(), quirk_class().desc()),
        "kind": "quirk",
        "conditions": ["PlanetQuirkAdder('%s()', %d)" % (quirk_class.__name__, chance)]
    }
    for k, v in more_data.items():
        data[k] = v
    return data

def mut_oxygen_poor():
    return mut_contents_quirk('oxygen_poor', QuirkThinAtmo, 60, {
        "score_modifier": +5
    })

def mut_former_core_sector():
    return mut_contents('former_core_sector', {        
        "kind": "quirk",
        "score_modifier": -10,
        "effects": [
            "cond(PlanetQuirkAdder('QuirkForebearArtifacts()',14,21))",
            "cond(EmptySignalSwap('structure.forebear_station',10))",
        ]
    })

################################################################
# Third update mutators

def mut_low_birth_rate():
    return mut_contents('low_birth_rate', {
        "kind": "industries",
        "score_modifier": +10,
        "effects": [
            "quality(QLowBirthRate())"
        ]
    })

class QLowBirthRate:
    def name(self): return LS("mutator.low_birth_rate")
    def desc(self): return LS("mutator.low_birth_rate.desc")
    def applies(self, node):
        if node.Level == -1: return True
        produces_people = node.ActuallyProduces(Resource.People)
        if not produces_people: return False
        has_unmet_industry_needs = any(node.HasUnmetNeedFor(ns.Resource) for ns in node.Industry.Needs)
        return has_unmet_industry_needs
    def effects(self, node):
        if node.Level >= 0:
            p_produced = sum(1 for p in node.Industry.Products if p == Resource.People)
            if p_produced >= 2:
                yield ChangeProducts.ReduceProduction(1, Resource.People, "low_birth_rate")
        yield EditDisplayedIndustry(self.edit_industry)
    @staticmethod
    def edit_industry(displayed):
        people = sum(1 for r in displayed.ShownProducts if r == Resource.People)
        if people >= 2:
            idx = displayed.ShownProducts.IndexOf(Resource.People)
            displayed.ShownProducts.RemoveAt(idx)
        return displayed

###

def mut_robot_dependence():
    return mut_contents('robot_dependence', {
        "kind": "industries",
        "score_modifier": +10,
        "effects": [
            "quality(QRobotDependence())"
        ]
    })

class QRobotDependence:
    def name(self): return LS("mutator.robot_dependence")
    def desc(self): return LS("mutator.robot_dependence.desc")
    def applies(self, node):
        if not node.NodeType.startswith("planet."): return False
        return node.Level == -1 or (node.HasNeedFor(Resource.People))
    def effects(self, node):
        B = Resource.All["B"]
        if node.Level >= 1 and not any(n.Resource == B for n in node.Industry.Needs) and not any(p == B for p in node.Industry.Products):
            yield ChangeNeeds.AddOne(B)
        yield EditDisplayedIndustry(self.edit_industry)
    @staticmethod
    def edit_industry(displayed):
        B = Resource.All["B"]
        if displayed.Level < 1: return displayed
        if not any(n.Resource == Resource.People for n in displayed.ShownNeeds): return displayed
        if any(p == B for p in displayed.ShownProducts): return displayed 
        displayed.ShownNeeds.Add(NeedSpec.Simple(B))
        return displayed

###

def mut_efficient_probes():
    return mut_contents('efficient_probes', {
        "kind": "probes",
        "score_modifier": -5,
        "effects": [
            "increase(probe.radius,20%)",
            "increase(probe.range,20%)"
        ]
    }, [20])

###

def mut_interference():
    return mut_contents('interference', {
        "kind": "signals",
        "score_modifier": +5,
        "effects": ["cond(MapGenOnlyMedium())"]
    })

class MapGenOnlyMedium(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        map_generation.Refinement("after_planet_types", 2000, self.refinement_signal_size)

    def refinement_signal_size(self, gen, signals, zones):
        for s in signals:
            s.Size = PotentialSize.Medium

###

def mut_ancient_ruins():
    return mut_contents_quirk('ancient_ruins', QuirkAncientRuins, 30, {
        "score_modifier": -10
    })

def mut_metal_deposits():
    return mut_contents_quirk('metal_deposits', QuirkMineralRich, 30, {
        "score_modifier": -10
    })

###

def mut_long_assignment():
    return mut_contents('long_assignment', {
        "kind": "time",
        "score_modifier": -30,
        "effects": ["increase(scenario.length,3)"]
    }, [3])

def mut_short_assignment():
    return mut_contents('short_assignment', {
        "kind": "time",
        "score_modifier": +20,
        "effects": ["reduce(scenario.length,3)"]
    }, [3])

###

def mut_curved_slipspace():
    return mut_contents('curved_slipspace', {
        "kind": "costs",
        "score_modifier": 0,
        "effects": ["cond(CurvedSlipspace())"]
    })

class CurvedSlipspace(GlobalCondition):
    def global_cost_adjustment(self, conn):
        if isinstance(conn, PlannedConnection) and conn.Kind.TypedID.endswith("slipway"):
            return self.make_adjuster()
        return None

    def make_adjuster(self):
        def adjust(cost, conn):            
            cash = cost.Cash
            cash = round(cash * 0.381 + 4.5)
            return cost.Replace(Resource.Cash, cash)
        return adjust

###

def mut_population_boom():
    return mut_contents('population_boom', {
        "kind": "industries",
        "score_modifiers": -5,
        "effects": ["quality(QPopulationBoom())"]
    })

class QPopulationBoom:
    def name(self): return LS("mutator.population_boom")
    def desc(self): return LS("mutator.population_boom.desc")
    def applies(self, node):
        return node.AmountReceived(Resource.All["F"]) >= 2 and node.ActuallyProduces(Resource.People)
    def effects(self, node):
        F = Resource.All["F"]
        bonus = node.AmountReceived(F) - 1
        return [ChangeProducts.Add(bonus, Resource.People, "pop_boom")]

###

def mut_gemstone_asteroids():
    return mut_contents_quirk('gemstone_asteroids', QuirkGemAsteroid, 23, {
        "score_modifier": -10,
        "description": LS("mutator.gemstone_asteroids.desc")
    })

class QuirkGemAsteroid:
    @staticmethod
    def eligible_planets(): return ["structure.asteroid"]

    def name(self): return LS("quirk.gemstone_asteroid")
    def desc(self): return LS("quirk.gemstone_asteroid.desc")
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "neutral", "text": ":Lux:"}
    def hidden(self, node): return True

    def effects(self, node):
        return [
            ColonizationOptions.Add(IndustryKind.All["gem_mine"]),
            ColonizationOptions.Add(IndustryKind.All["gem_mine_lux"]),
        ]

###

def mut_rare_earth_asteroids():
    return mut_contents_quirk('rare_earth_asteroids', QuirkRareEarthAsteroid, 20, {
        "score_modifier": -10,
        "description": LS("mutator.rare_earth_asteroids.desc")
    })

class QuirkRareEarthAsteroid:
    PER_PLANET = 2
    @staticmethod
    def eligible_planets(): return ["structure.asteroid"]

    def name(self): return LS("quirk.rare_earth_asteroid")
    def desc(self): return LS("quirk.rare_earth_asteroid.desc", None, self.PER_PLANET)
    def sentiment(self): return QualitySentiment.Positive
    def visibility(self, node): return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "neutral", "text": ":S:"}
    def hidden(self, node): return True

    def effects(self, node):
        return [ValueChange.With("rare_earth", "asteroid_bonus", self.add_science)]
    
    @staticmethod
    def add_science(node, bonuses):
        planets = sum(1 for p in asteroid_actual_planets(node) if p.ActuallyProduces(Resource.People))        
        if planets > 0:
            bonuses[Resource.Science] = planets * QuirkRareEarthAsteroid.PER_PLANET
        return bonuses

###

def mut_intact_tech():
    return mut_contents_quirk('intact_tech', QuirkIntactTech, 25, {
        "score_modifier": -5
    })
