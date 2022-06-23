# Definitions for all the 'forebear ruins' events in the game.
# You can copy stuff from here to your mod and edit stuff to add new ones - just make sure your functions
# are called "event_ruins_<something>" so they're automatically picked up into the random pool.

##################################
## Main logic

class StationForcedEvents:
    KEY = "forced_events"

    @classmethod
    def force(cls, event):
        list = game.CustomData.GetOr(cls.KEY, [])
        list.append(event)
        game.CustomData.Set(cls.KEY, list)

    @classmethod
    def unforce(cls, event):
        list = game.CustomData.GetOr(cls.KEY, [])
        if event in list:
            list.remove(event)
        game.CustomData.Set(cls.KEY, list)

    @classmethod
    def pop_next(cls):  
        list = game.CustomData.GetOr(cls.KEY, [])
        if len(list) == 0: return None
        next_event = list[0]
        list = list[1:]
        game.CustomData.Set(cls.KEY, list)
        return next_event

def industry_hidden(): return True

def station_tooltip(me, original):
    if me.Industry is not None and me.Industry.Kind.ID == "station":
        return [original, LS("structure.forebear_station.tooltip", "Connect a planet with idle :P: on it to explore.").ToString()]
    return [original]

def station_before_trade(me):
    if me.CustomData.Has("visited"): return
    people_available = any_node_provides_people(game.Reachability.ReachableNodes(me))
    if people_available:
        station_visit(me)

def station_visit(me):
    # grant science bonus
    bonus = constants.Int("station.science_bonus")
    if bonus > 0:
        commands.IssueScriptedConsequence(ConsGrantResources(bonus, Resource.Science, node=me))
    # trigger situation
    event_id = StationForcedEvents.pop_next()
    if not event_id:
        event_id = empire.GameEvents.GetRandomFromGroup("ruins", me.RNG("stations"))
    commands.IssueScriptedConsequence(VisitStation(me))
    commands.Issue(EnableSituation(world, me, event_id))
    # once everything in this batch is done (costs of connection paid, time advanced)
    # try opening the situation
    # - but only if this was a direct connection to avoid problems with multiple stations being opened at the same time
    last_explicit = commands.LastExplicitCommand.CommandString
    direct_interaction = False
    our_identifier = me.NodeIdentifier
    if last_explicit.startswith("connect/") and (("/" + our_identifier) in last_explicit):
        direct_interaction = True
    if last_explicit.startswith("select_route/") and last_explicit.endswith(our_identifier):
        direct_interaction = True
    if direct_interaction:
        commands.IssueAfterCurrentBatch(StartSituation(world, me))

class VisitStation:
    def __init__(self, node): self._node = node
    def apply(self):
        self._node.CustomData.Set("visited", True)
    def revert(self):
        self._node.CustomData.Clear("visited")
        self._node.TriggerChange()

def any_node_provides_people(nodes):
    for partner in nodes:
        for product in partner.Products:
            if not product.IsReal or not product.IsAvailable: continue
            if product.Resource == Resource.People:
                return True
            product_id = product.Resource.ID
            if unlocks.IsUnlocked("conflate." + product_id + ".P"):
                return True
    return False            

def remain_ruined(station_node):
    station_node.CustomData.Set("ruined", True)

####################################
## Definition of station types

def event_ruins_manufacturing(evt):
    evt.SetTitle("Manufacturing Depot")
    evt.SetText("This was once a forefather *manufacturing depot*. It seems to have specialized in robots and automation.")
    evt.AddChoices(
        "[race(silthid)] Learn from it. -> learn(race=silthid)",
        "[race(baqar)] (15$) Recycle it. -> rebuild(fb_scrap)",
        "[race(silthid)] (30$) Rebuild it. -> rebuild(fb_bots+)",
        "[fallback] (30$) Patch it up. -> rebuild(fb_bots)",
        "Scavenge anything useful. -> get(percent_range=40-60,resource=$)",
        "Leave it for now."
    )

def event_ruins_power_plant(evt):
    evt.SetTitle("Power Plant")
    evt.SetText("This is a *power plant*. It once utilized advanced ancient technology to produce immense amounts of power.")
    evt.AddChoices(
        "[race(vattori)] Learn from it. -> learn(race=vattori)",
        "[race(silthid,one_race=True)] (30$) Rebuild it. -> rebuild(fb_energy+)",
        "[race(aphorian)] Scavenge anything useful. -> get(percent_range=100-125,resource=$)",
        "[fallback] Scavenge anything useful. -> get(percent_range=50-75,resource=$)",
        "Leave it for now."
    )

def event_ruins_warehouse(evt):
    evt.SetTitle("Warehouse")
    evt.SetText("You discover a *warehouse facility*. Most of the storerooms are empty, but some remain locked and intact even after all these years.")
    evt.AddChoices(
        "[race(aphorian)] Sell it off slowly. -> rebuild(fb_money)",
        "[race(baqar,one_race=True)] (20$) Use the raw resources. -> rebuild(fb_scrap)",
        "Gather everything you can use. -> get(percent_range=100-125,resource=$)",
        "Leave it for now."
    )

def event_ruins_bio(evt):
    evt.SetTitle("Bio-Research Facility")
    evt.SetText("The forefathers used to do *biological experiments* here. The ruins of the station are now overrun with *weird, alien lifeforms*.")
    evt.AddChoices(
        "[race(dendr)] Learn how they were modified. -> learn(race=dendr)",
        "[race(vattori)] Study the lifeforms. -> get(6,S)",
        "[race(aphorian)] Make it a tourist attraction. -> rebuild(fb_tourism)",
        "[race(silthid,one_race=True)] Establish a base. -> rebuild(fb_organics+)",
        "Scavenge anything useful. -> get(percent_range=50-75,resource=$)",
        "Leave it for now."
    )

def event_ruins_cultural(evt):
    evt.SetTitle("Historical Repository")
    evt.SetText("This station stores some of the forefathers' *historical artifacts* and records. The records are unreadable, but maybe the artifacts can be of some use?")
    evt.AddChoices(
        "[race(aphorian)] Market the artifacts as novelties. -> rebuild(fb_novelty)",
        "[race(dendr)] Establish a museum. -> rebuild(fb_museum)",
        "[race(dendr,one_race=True)] Learn about the forefather culture. -> get(8,S)",
        "Sell the artifacts off. -> get(percent_range=50-75,resource=$)",
        "Leave it for now."
    )

def event_ruins_relay(evt):
    evt.SetTitle("Ruined Relay")
    evt.SetText("This used to be a *slipspace relay*, similar to our experimental designs. With some effort, perhaps it could be restored.")
    evt.AddChoices(
        "[race(silthid)] (15$) Rebuild it and reuse it. -> structure(infra_relay,1)",
        "[race(dendr)] Figure out how it was used. -> get(6,S)",
        "[race(vattori)] Learn from its construction. -> get(8,S)",
        "[race(baqar,one_race=True)] (20$) Scrap it for parts -> rebuild(fb_scrap)",
        "Scavenge anything useful. -> get(percent_range=40-60,resource=$)",
        "Leave it for now."
    )

def event_ruins_habitat(evt):
    evt.SetTitle("Ancient Habitat")
    evt.SetText("This used to be a *residential space station*. Its life support systems seem curiously similar to what we would need to live here.")
    evt.AddChoices(
        "[race(vattori)] (20$) Establish a science colony. -> rebuild(fb_habitat__s)",
        "[race(aphorian)] (20$) Sell the alien artifacts. -> rebuild(fb_habitat__$)",
        "[race(silthid)] (10$) Use the parts to build a habitat of our own. -> structure(habitat,1)",
        "[race(dendr,one_race=True)] (20$) Restore it and settle it. -> rebuild(fb_habitat__h)",
        "Scavenge anything useful. -> get(percent_range=40-60,resource=$)",
        "Leave it for now."
    )

###

def event_ruins_observatory(evt):
    evt.SetTitle("Observatory")
    evt.SetText("This looks like an *ancient observatory* used to map this sector out. With some effort, it could be used for this purpose again.")
    evt.AddChoices(
        "[race(vattori)] (20$) Rebuild it and use it to study the sector. -> rebuild(fb_auto_science)",
        "[race(baqar)] (20$) Scrap it for parts -> rebuild(fb_scrap)",
        "[race(silthid)] (20$) Boost the signal before activating a scan to reveal more planets. -> ping_scan(18)",
        "(10$) Reactivate it for a single scan to reveal nearby planets. -> ping_scan(14)",
        "Scavenge anything useful. -> get(percent_range=40-60,resource=$)",
        "Leave it for now."
    )

class EffPingScan(ChoiceEffect):
    def __init__(self, range):
        self._range = range

    def consequence(self): return self

    def apply(self):
        self.node().CustomData.Set("reveal_radius", self._range)
        self.node().CustomData.Set("ruined", True)
        self.node().ChangeIndustry(IndustryKind.All["fb_observatory"], 0)
        cmd = commands.MakeIrreversible()
        game.FOW.AnimatedDiscover(self.node())
        world.Add(DelayedAction(0.15, lambda: self.send_pulse(cmd)))

    def send_pulse(self, parent_command):
        world.Add(ProbePulse(self.node().Position, self._range, parent_command))

def observatory_radius(node):
    return node.CustomData.Get("reveal_radius")

###

def event_ruins_research_facility(evt):
    evt.SetTitle("Research Facility")
    evt.SetText("This is a former *research facility* that could still contain vital clues to help our own scientific efforts.")
    evt.AddChoices(
        "[race(vattori)] (30$) Set up a permanent research base here. -> rebuild(fb_auto_science)",
        "(50$) Investigate every single inch of the place. -> get(12, S)",
        "(20$) Perform a thorough search. -> get(8, S)",
        "Do a cursory search for information. -> get(4, S)",
        "Leave it for now."
    )

###

def event_ruins_replicator(evt):
    evt.SetTitle("Matter Replicator")
    evt.SetText("This looks like an *automated matter replication facility*. If rebuilt and supplied with robots, it could be used to create resources of various types.")
    evt.AddChoices(
        "[race(baqar)] (20$) Rebuild it and set it up. -> rebuild(fb_replicator_raw)",
        "[race(aphorian)] (20$) Rebuild it and set it up. -> rebuild(fb_replicator_goods)",
        "[race(silthid)] (20$) Rebuild it and set it up. -> rebuild(fb_replicator_tech)",
        "[race(dendr)] (20$) Rebuild it and set it up. -> rebuild(fb_replicator_bio)",
        "[race(baqar)] Just scrap it for parts -> rebuild(fb_scrap)",
        "Dismantle it and scavenge anything useful. -> get(percent_range=50-70,resource=$)",
        "Leave it for now."
    ),

###

def event_ruins_experimental_terraformer(evt):
    evt.SetTitle("Remote Terraformer")
    evt.SetText("This experimental facility was apparently used to *terraform entire planets*. We should be able to use it one last time if we can figure out the right settings.")
    evt.AddChoices(
        "[race(baqar)] (12$) Turn a nearby planet into a mineral world. -> terraform_nearby(mining)",
        "[race(aphorian)] (12$) Turn a nearby planet into an ocean world. -> terraform_nearby(ocean)",
        "[race(silthid)] (12$) Turn a nearby planet into a forgeworld. -> terraform_nearby(factory)",
        "[race(dendr,one_race=True)] (12$) Turn a nearby planet into an earthlike world. -> terraform_nearby(earthlike)",
        "Dismantle it and scavenge anything useful. -> get(percent_range=50-70,resource=$)",
        "Leave it for now."
    )

class EffTerraformNearby(ChoiceEffect):
    RANGE = 13
    def __init__(self, target_kind):
        self._kind = target_kind

    def consequence(self): return self
    def apply(self):
        command = self.event().RunCommand
        source_node = self.node()
        all_nodes = game.Nodes.Within(source_node, self.RANGE)
        possible_nodes = [n for n in all_nodes if n.NodeType.startswith("planet.") and n.Level < 0]
        world.Add(SelectNodeModalOp(command, possible_nodes, self.finalize, 
            LS("event_action.terraform.explanation")))

    def revert(self):
        pass # everything downstream is reversible, and our apply does no destructive changes

    def finalize(self, node):
        commands.IssueScriptedConsequence(ConsTerraform(node, self._kind))


class ConsTerraform:
    def __init__(self, node, target_kind):
        self._kind = PlanetKind.All[target_kind]
        self._node = node
    
    def apply(self):
        target_type = self._kind
        previous_state = self._node.ChangeKind(target_type)
        self._old_state = previous_state
        return [self._node]

    def revert(self):
        self._old_state.RestoreOn(self._node)
        return [self._node]

###

def event_ruins_science_archive(evt):
    evt.SetTitle("Archive")
    evt.SetText("The data stored in this *scientific archive* seems particularly relevant to our current lines of research.")
    node = evt.Node
    rng = evt.RNG("techs")
    discount = 40 # 40% discount
    for cm in game.Council.Members:
        race = cm.Race
        tech_id = node.CustomData.GetOr("archive_tech_%s" % race.ID, None)
        if tech_id is None:
            level = game.Technology.InventableRange.LowEnd + 1
            racial_tech = [t for t in game.Technology.AllUnlocked if t.Source.IsFrom(race) and 
                t.BaseTier >= level and t.BaseTier <= level + 1 and
                t.IsRoot and
                not any(d.Kind == "event" for d in t.GetDiscounts())
            ]
            if len(racial_tech) == 0:
                tech_id = "<n/a>"
            else:
                tech = Randomness.Pick(rng, racial_tech)
                tech_id = tech.Kind.ID
            node.CustomData.Set("archive_tech_%s" % race.ID, tech_id)
        if tech_id != "<n/a>":
            evt.AddChoice("[race(%s)] (15$) %s -> discount_tech(science_archive,%s,%d)" % (race.ID, race.ID, tech_id, discount), 
                LS("choice.get_a_discount_on_tech", None, TechKind.All[tech_id].LName, discount))
            
    evt.AddChoices(
        "Just scavenge it for parts. -> get(percent_range=60-80,resource=$)",
        "Leave it for now."
    )

###

def event_ruins_depot(evt):
    evt.SetTitle("Repair Depot")
    evt.SetText("This station is a former *repair depot*, full of broken-down forebear devices. Not much research value, but with some effort we could repair them and sell them off as curiosities.")
    evt.AddChoices(
        "[race(dendr)] Make this a museum with exhibits about forebear culture. -> rebuild(fb_museum)",
        "[race(vattori)] Study the few artifacts that have scientific value -> get(4,S)",
        "[race(aphorian)] Take it slow and sell the artifacts off over time. -> rebuild(fb_money)",
        "[race(baqar)] Scrap it for parts. -> rebuild(fb_scrap)",
        "(6S) Repair and sell everything you can. -> get(percent_range=220-270,resource=$)",
        "(3S) Repair the devices that are already in good shape. -> get(percent_range=130-150,resource=$)",
        "Scavenge what's already in fully-working condition. -> get(percent_range=40-60,resource=$)",
        "Leave it for now."
    )

###

def event_ruins_time_loop(evt):
    evt.SetTitle("Experimental Facility")
    evt.SetText("This *experimental facility* dealt with establishing stable *time loops*. It does not appear it was entirely successful, but we might get it to affect the time flow one last time.")
    months = game.Time.Date.Month
    cost = int((1 + months) * months * 0.5)
    evt.AddChoice("[not_start_of_year] (%d$) Rewind time to the beginning of this year. -> rewind(%d)" % (cost, months))
    evt.AddChoices(
        "Just scavenge it for parts. -> get(percent_range=60-80,resource=$)",
        "Leave it for now."
    )

class CndNotStartOfYear(ChoiceCondition):
    def check(self):
        if game.Time.Date.Month == 0:
            return {
                "lockedBecause": LS("events.option_locked_start_of_year")
            }
        else:
            return {}
    
class EffRewind(ChoiceEffect):
    def __init__(self, months):
        self._months = int(months)
    def consequence(self): return self
    def apply(self):
        game.Time.RewindByMonths(self._months)
    def revert(self):
        game.Time.AdvanceByMonths(self._months)
    def describe(self):
        if self._months == 0: return LocalizedString.Empty
        return LS("effect.rewind_time", None, self._months)

###

def event_ruins_communication_hub(evt):
    evt.SetTitle("Communication Hub")
    evt.SetText("This former *communication hub* can still offer instantaneous communication across light years, boosting our planets. The type of boost depends on what we use the limited bandwidth for. Only planets that are at least [[ref:level.1]] or better can benefit.")
    evt.AddChoices(
        "[race(dendr)] Use the communication hub for cultural exchange. -> spread(1000,Happiness)",
        "[race(silthid)] Use the communication hub to boost productivity. -> spread(1000,Production)",
        "[race(aphorian)] Use the communication hub for an interplanetary stock exchange. -> spread(1000,Income,40)",
        "[race(vattori)] Use the communication hub for scientific discourse. -> spread(1000,Science)",
        "[race(baqar)] Dismantle the hub and use the raw resources. -> get(percent_range=150-200,resource=$)",
        "Just scavenge it for parts. -> get(percent_range=60-80,resource=$)",
        "Leave it for now."
    )

class SpreadQuality:
    def name(self): return LS("structure.forebear_station")
    def desc(self): return LS("quality.%s.desc" % IdentifierStyles.ToSnake(self.__class__.__name__))
    def sentiment(self): return QualitySentiment.Positive
    def effects(self, node):
        if node.NodeType == "structure.forebear_station": return [LabelEffect.With(":^structure:")]
        return self.actual_effects(node)

class SpreadHappiness(SpreadQuality):
    def actual_effects(self, node):        
        if node.ActuallyProduces(Resource.People):
            return [ChangeProducts.Add(2, Resource.All["H"], "spread_happiness")]
class SpreadIncome(SpreadQuality):
    TRADE_BONUS = 40
    def desc(self): return LS("quality.spread_income.desc", None, self.TRADE_BONUS)
    def actual_effects(self, node):
        return [PercentageBonus.TradeIncome(self.TRADE_BONUS)]
class SpreadScience(SpreadQuality):
    def actual_effects(self, node):
        if node.ActuallyProduces(Resource.People):
            return [ChangeProducts.Add(2, Resource.All["S"], "spread_science")]
class SpreadProduction(SpreadQuality):
    def actual_effects(self, node):
        products = set(p.Resource for p in node.Products if p.IsReal and not is_product_copied(p) and p.Resource.ID != "P")
        if len(products) > 0:
            return [ChangeProducts.AddOne(p, "spread_production[copy]") for p in products]            

class EffSpread(ChoiceEffect):
    def __init__(self, limit, quality_type, *desc_args):
        self._limit = limit
        self._expr = "Spread%s()" % quality_type
        self._desc_id = "quality.spread_%s.desc" % quality_type.lower()
        self._desc_args = desc_args

    def consequence(self): return self
    def describe(self): return LS(self._desc_id, None, *self._desc_args)
    def apply(self):
        self.node().CustomData.Set("quality_remaining", self._limit)
        self.node().CustomData.Set("quality_expr", self._expr)
        self.node().CustomData.Set("quality_min_level", 0)
        commands.Issue(ChangeNodeIndustry(world, self.node(), IndustryKind.All["fb_quality_spread"]))
        commands.IssueScriptedConsequence(ConsAttachQualityOnce(self.node(), "started_spreading", self._expr))
        quality_spread_resolution(self.node()) # initial spread

    def revert(self):
        pass # enough to just revert the industry

def quality_spread_resolution(node):
    remaining = node.CustomData.GetOr("quality_remaining", 0)
    expr = node.CustomData.Get("quality_expr")
    min_level = node.CustomData.Get("quality_min_level")
    for other in game.Reachability.ReachableNodes(node):
        if not other.NodeType.startswith("planet."): continue
        if other.Level < min_level: continue
        if any(q.ScriptExpression == expr for q in other.GetQualities()): continue
        if remaining == 0: continue
        commands.IssueScriptedConsequence(ConsAttachQualityOnce(other, "quality_granted", expr))
        commands.IssueScriptedConsequence(ConsUpdateNodeData().dec(node, "quality_remaining"))
        remaining -= 1

###

def event_ruins_tiered_power_plant(evt):
    evt.SetTitle("Power Plant")
    evt.SetText("This is a *power plant* in good shape. It wouldn't take much to get it running again.")
    evt.AddChoices(
        "[race(baqar)] (30$) Use its full potential. -> rebuild(fb_energy++)",
        "[race(baqar,one_race=True)] (20$) Rebuild it carefully and restore most of its output. -> rebuild(fb_energy+)",
        "[race(silthid)][previous_n_unavailable(1)] (25$) Rebuild it carefully and restore most of its output. -> rebuild(fb_energy+)",
        "(10$) Rebuild it cheaply for bare minimum output. -> rebuild(fb_energy)",
        "Scavenge anything useful. -> get(percent_range=50-75,resource=$)",
        "Leave it for now."
    )

###

def event_ruins_weapon(evt):
    evt.SetTitle("Planet Crusher")
    evt.SetText("This powerful *ancient weapon* was a tool of war in the past. If we rebuild it, it could be used more peacefully to crush nearby uninhabited planets and harvest resources from them.")
    evt.AddChoices(
        "[race(baqar/aphorian/silthid)] (20$) Rebuild the planet crusher. -> rebuild(fb_weapon) -> enable_and_start(event_rebuilt_weapon_reversible)",
        "[race(dendr/vattori)] Dismantle it to make it sure it can never be used. -> rebuild(fb_dismantled)",
        "[race(baqar)] Scrap it for parts. -> rebuild(fb_scrap)",
        "Leave it for now."
    )

def event_rebuilt_weapon_reversible(evt):
    evt.SetTitle("Planet Crusher")
    evt.SetText("The weapon is *ready to fire*.")
    evt.AddChoices(
        "Destroy a nearby planet and harvest the debris. -> fire_weapon",
        "Leave it for now."
    )

class EffFireWeapon(ChoiceEffect):
    RANGE = 13
    BONUS = 20

    def consequence(self): return self
    def apply(self):
        command = self.event().RunCommand
        source_node = self.node()
        all_nodes = game.Nodes.Within(source_node, self.RANGE)
        possible_nodes = [n for n in all_nodes if n.NodeType.startswith("planet.") and n.Level < 0]
        world.Add(SelectNodeModalOp(command, possible_nodes, self.finalize, 
            LS("event_action.destroy_planet.explanation")))

    def revert(self):
        pass # everything downstream is reversible, and our apply does no destructive changes

    def describe(self): return LS("effect.destroy_planet", None, self.BONUS)

    def finalize(self, target_node):
        source_node = self.node()
        commands.IssueScriptedConsequence(ConsGrantResources(self.BONUS, Resource.Cash, target_node))
        commands.IssueScriptedConsequence(ConsDestroyPlanet(target_node))
        commands.Issue(EnableSituation(world, source_node, "event_rebuilt_weapon_reversible"))        

class ConsDestroyPlanet:
    def __init__(self, node):
        self._node = node
    
    def apply(self):
        AnimationEvents.TriggerAnimation(self._node, "ActionTaken:harvest")
        self._node.Discard()
        return [self._node]

    def revert(self):
        world.Revive(self._node)
        return [self._node]

###

def event_ruins_matter_printer(evt):
    evt.SetTitle("Matter Synth")
    evt.SetText("This forebear facility looks like it can *synthesize various resources out of vacuum*. It's seen better days, but we can probably still rebuild it.")
    evt.AddChoices(
        "[race(baqar)] (15$) Scrap the synthesizer for parts. -> rebuild(fb_ore+)",
        "[race(silthid)] (20$) Rebuild the synthesizer. -> rebuild(fb_tb)",
        "[race(dendr)] (25$) Rebuild the synthesizer. -> rebuild(fb_lwf)",
        "[race(aphorian)] (25$) Rebuild the synthesizer. -> rebuild(fb_novelty)",
        "[race(vattori)] (20$) Set up a permanent research base here. -> rebuild(fb_auto_science)",
        "Leave it for now."
    )

###

def event_ruins_former_hub(evt):
    evt.SetTitle("Former Hub")
    evt.SetText("This enormous space station was once a *forebear meeting hub* for the whole sector. It could probably serve this function once again, providing benefits based on [[ref:level.2]] planets connected to it.")
    evt.AddChoices(
        "(25$) Use it as a commerce hub. -> quality(QFormerHubMoney,industry=fb_former_hub)",
        "(25$) Use it as a gathering place for scientists. -> quality(QFormerHubScience,industry=fb_former_hub)",
        "(25$) Use it as a center for cultural exchange. -> quality(QFormerHubHappiness,industry=fb_former_hub)",
        "Scavenge anything useful. -> get(percent_range=50-75,resource=$)",
        "Leave it for now."
    )

class QFormerHub:
    def desc(self): return LS("quality.former_hub.desc", None, (":%s:" % self.product()) * self.count())    
    def effects(self, node):
        succ_planets = sum(1 for p in game.Reachability.ReachableNodes(node) if p.Level >= 2 and p.NodeType.startswith("planet."))
        if succ_planets > 0:
            return [
                ChangeProducts.Add(succ_planets * self.count(), Resource.All[self.product()], "former_hub"),
                LabelEffect.ReplaceLabelWith(":%s:" % self.product())
            ]
        else:
            return [LabelEffect.ReplaceLabelWith("-")]

class QFormerHubMoney(QFormerHub):
    def name(self): return LS("quality.former_hub.money")
    def product(self): return "$"
    def count(self): return 1

class QFormerHubScience(QFormerHub):
    def name(self): return LS("quality.former_hub.science")
    def product(self): return "S"
    def count(self): return 1

class QFormerHubHappiness(QFormerHub):
    def name(self): return LS("quality.former_hub.happiness")
    def product(self): return "H"
    def count(self): return 2
