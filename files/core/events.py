"""Basic support for scripted events."""


########################################
# Choice conditions
# These control whether a choice is available during an event.

class ChoiceCondition(object):
    def bind(self, choice):
        self._choice = choice
        self._event = choice.Owner
        self._node = self._event.Node
    
    def choice(self): return self._choice
    def event(self): return self._event
    def node(self): return self._node

class CndRace(ChoiceCondition):
    def __init__(self, races, no_unlock_needed = False, one_race = False): 
        if isinstance(races, str):
            races = [Race.All[r] for r in races.split("/")]
        if isinstance(races, Race):
            races = [races]
        self._no_unlock_needed = no_unlock_needed
        self._one_race = one_race
        self._races = races

    def check(self):
        # which of the triggering races are present in the council?
        present_races = [r for r in self._races if empire.Council.HasActiveMember(r)]
        # if this is a one race sector/mission, does this option allow a fallback?
        if self._one_race and not any(c.IsAvailable for c in self.choice().AllAbove()):
            members = list(empire.Council.Members)
            if len(members) == 1:
                # one-race mission fallback
                present_races = [members[0].Race]
        # nothing matched?
        if len(present_races) == 0:
            return None   
        # something did match 
        race = present_races[0]
        if self._no_unlock_needed or constants.Int("%s.event_options" % race.ID, 0) > 0:
            return {"sprite": race.Assets.miniFace}
        return {
            "lockedBecause": LS("events.option_locked_race", "Advance the [[ref:race.{1}]] to level 1 to unlock this option.", race.ID),
            "sprite": race.Assets.miniFace
        }

class CndMarkRace(ChoiceCondition):
    def __init__(self, race): 
        if not isinstance(race, str):
            race = race.ID
        self._race_id = race

    def check(self):
        return {"sprite": Race.All[self._race_id].Assets.miniFace}

class CndFallback(ChoiceCondition):
    """Option only available if the previous one is unavailable."""
    def check(self):
        if not self.choice().Previous.IsAvailable:
            return {}

class CndPreviousNUnavailable(ChoiceCondition):
    """Option only available if the previous N are unavailable."""
    def __init__(self, count):
        self._count = int(count)
    def check(self):
        for n in range(1, self._count+1):
            if self.choice().NthAbove(n).IsAvailable:
                return None
        return {}

class CndNoneOfTheAbove(ChoiceCondition):
    """Option only available if all previous ones are unavailable."""
    def check(self):
        return not any(c.IsAvailable for c in self.choice().AllAbove())

class CndAlwaysHidden(ChoiceCondition):
    def check(self):
        return None #hidden

########################################
# Choice effects
# These are packaged class for what happens when you click the button.
# They are also able to describe themselves on the button, and provide
# stuff for the tooltip.

class ChoiceEffect(object):
    def bind(self, choice):
        self._choice = choice
        self._event = choice.Owner
        self._node = self._event.Node

    def is_consequential(self): return True
    def tied_condition(self): return None

    def choice(self): return self._choice
    def event(self): return self._event
    def node(self): return self._node
    

class EffLeave(ChoiceEffect):    
    def consequence(self):
        return ConsNoop()
    def is_consequential(self): return False

class EffLearn(ChoiceEffect):
    def __init__(self, tech = None, race = None):
        self._tied = None
        # expand arguments
        if isinstance(tech, str):
            tech = TechKind.All[tech]
        if isinstance(race, str):
            race = Race.All[race]
        # prepare tech params
        self._tech, self._tech_params = self._resolve_tech(tech, race)
        # assign a source
        if race is not None:
            self._source = UnlockSource.FromRace(race)
        else:
            self._source = UnlockSource.FromEvent()

    def _resolve_tech(self, specific_tech, race):
        if specific_tech is not None:
            return specific_tech, None
        tp = TechParameters()
        tp.Race = race
        tp.TierRange = IntRange.Between(2, 4)
        return None, tp

    def _possible_techs(self, tech_params):
        race = tech_params.Race
        range = tech_params.TierRange
        if tech_params.Tier:
            range = IntRange.Exactly(tech_params.Tier, tech_params.Tier)
        for tk in TechKind.AllList:
            if tk.IsUpgrade: continue
            if not range.Contains(tk.BaseTier): continue
            if not tk.Races.Contains(race): continue
            if game.Technology.IsUnlocked(tk) and game.Technology.Tech(tk).IsInitialTech: continue
            yield tk

    def tied_condition(self): return self._tied
    
    def bind(self, choice):
        ChoiceEffect.bind(self, choice)
        self._storage_key = "%s:learned_tech" % choice.ChoiceID
        stored_tech = self.node().CustomData.GetOr(self._storage_key, None)
        if stored_tech is not None:
            self._tech = TechKind.All[stored_tech]
        if self._tech is None:
            options = list(self._possible_techs(self._tech_params))
            if len(options) > 0:
                self._tech = Randomness.Pick(self.event().MainRNG, options)
        if self._tech is None or game.Technology.IsUnlocked(self._tech):
            # couldn't find any free tech!
            self._tied = CndAlwaysHidden()
        else:
            self.node().CustomData.Set(self._storage_key, self._tech.ID)

    def describe(self):
        if not self._tech: return LocalizedString.Empty
        return LS("effect.unlock_tech", "Unlock {1}", self._tech.LReference)

    def tooltip(self):
        return self._tech # use the tooltip for the tech

    def consequence(self):
        return ConsLearn(self._tech, self._source)

class ConsLearn:
    def __init__(self, tech, source):
        self._tech, self._source = tech, source
    def apply(self):
        game.Technology.Unlock(self._tech, self._source)
    def revert(self):
        game.Technology.Forget(game.Technology.Tech(self._tech))


class EffGet(ChoiceEffect):
    def __init__(self, amount = None, resource = None, percent_range = None):
        if isinstance(resource, str): resource = Resource.All[resource]
        if isinstance(percent_range, int):
            self._percent_range = IntRange.Between(percent_range, percent_range)
        elif isinstance(percent_range, str):
            self._percent_range = IntRange.Parse(percent_range)      
        else:
            self._percent_range = percent_range
        self._resource, self._amount = resource, amount

    def bind(self, choice):
        ChoiceEffect.bind(self, choice)
        if self._percent_range is not None:
            actual_percent = self._percent_range.RandomNumber(self.event().MainRNG)
            income = empire.Stock.Income(self._resource)
            if self._resource == Resource.Cash:
                income = clamp(25, 50, income)
            if self._resource == Resource.Science:
                income = clamp(4, 8, income)
            self._amount = math.ceil(income * actual_percent * 0.01)

    def describe(self):
        return LS("effect.get_resource", "Get {1}:{2}:", self._amount, self._resource.ID)

    def consequence(self):
        return ConsGrantResources(self._amount, self._resource, self.node())

class EffRebuild(ChoiceEffect):
    def __init__(self, industry):
        if isinstance(industry, str): 
            if not IndustryKind.All.ContainsKey(industry):
                raise Exception("rebuild() effect specified for non-existent industry: '%s'" % industry)
            industry = IndustryKind.All[industry]
        self._industry = industry
    
    def describe(self):
        industry_string = self._industry.Levels[0].DisplayedTextForNode(self.node())
        if industry_string.strip() == "": return LocalizedString.Empty
        return LS("effect.turns_into", "Turns into <size=110%>{1}</size>", industry_string)

    def consequence(self):
        return ChangeNodeIndustry(world, self.node(), self._industry)

class EffQuality(ChoiceEffect):
    def __init__(self, quality_name, industry=None):
        self._expr = quality_name + "()"
        self._industry = industry
    
    def describe(self):
        return game.Qualities.Get(self._expr).DescriptionForNode(self.node())

    def consequence(self): return self
    def apply(self):
        if self._industry is not None:
            ik = IndustryKind.All[self._industry]
            commands.Issue(ChangeNodeIndustry(world, self.node(), ik))
        ConsAttachQualityOnce(self.node(), self._expr, self._expr).issue()
    def revert(self):
        pass # dealt with in apply

class EffStructure(ChoiceEffect):
    def __init__(self, structure, amount):
        self._structure, self._amount = structure, amount
        self._skind = StructureKind.All[self._structure]

    def describe(self):    
        return LS("effect.get_structure", None, self._amount, self._skind.LName)

    def tooltip(self):
        return self._skind

    def consequence(self): return self
    def apply(self):
        commands.Issue(GrantLimited(world, self._skind.TypedID, self._amount))
    def revert(self): pass

class EffInvent(ChoiceEffect):
    def __init__(self, tech_id):
        self._tech_id = tech_id
        self._kind = TechKind.All[tech_id]

    def describe(self):
        return LS("effect.invent", None, self._kind.LName)
    def tooltip(self):
        return self._kind
    def consequence(self): return self
    def apply(self):
        commands.Issue(GrantTech(world, self._kind))
    def revert(self): pass

class EffInc(ChoiceEffect):
    def __init__(self, flag):
        self._flag = flag

    def consequence(self):
        return ConsUpdateNodeData().add(self.node(), self._flag, lambda value: (value or 0) + 1)

class EffIncGlobal(ChoiceEffect):
    def __init__(self, flag):
        self._flag = flag

    def consequence(self):
        return ConsUpdateNodeData().inc(game, self._flag)

class EffComplete(ChoiceEffect):
    def consequence(self):
        return ConsUpdateNodeData().add(self.node(), "event_complete", True)

class EffDesc(ChoiceEffect):
    def __init__(self, desc):
        self._text = desc

    def describe(self):
        text_id = Localization.TextToID("effect", self._text)
        return LS(text_id, self._text)
    
    def is_consequential(self): return False
    def consequence(self): return ConsNoop()

class EffRestart(ChoiceEffect):
    def is_consequential(self): return False
    def consequence(self): return ConsRestartEvent(self.event())

class EffGoto(ChoiceEffect):
    def __init__(self, event_id):
        self._target = event_id

    def is_consequential(self): return False
    def consequence(self): return self
    def apply(self):
        self._event.GoTo(self._target)
    def revert(self):
        pass # no need to revert this

class EffEnableSituation(ChoiceEffect):
    def __init__(self, event_id):
        self._event_id = event_id
    def consequence(self): 
        return EnableSituation(world, self.node(), self._event_id)

class EffEnableAndStart(ChoiceEffect):
    def __init__(self, event_id):
        self._event_id = event_id
    def consequence(self): return self
    def apply(self):
        commands.Issue(EnableSituation(world, self.node(), self._event_id))
        world.Add(DelayedAction(0.05, self.start_again))
    def start_again(self):
        commands.Issue(StartSituation(world, self.node()))
    def revert(self):
        pass # subcommands handle reversion

class EffIrreversible(ChoiceEffect):
        def consequence(self): return IrreversibleBarrier(world)

class ConsRestartEvent:
    def __init__(self, event): self._event = event
    def apply(self):
        self._event.RestartFromBeginning()
    def revert(self):
        pass

### Tech discounts

class EffDiscountTech(ChoiceEffect):
    def __init__(self, source, tech_id, percent):
        self._source = source
        self._tech_id = tech_id
        self._percent = percent
        self._tied = CndTechUnlockedAndNoDiscount(source, tech_id)
        self._was_already_present = False

    def tied_condition(self): return self._tied
    def consequence(self): return self
    def apply(self):
        cond = conditions.Get(self.expr())
        self._was_already_present = cond and cond.IsActive
        if not self._was_already_present:
            conditions.Activate(self.expr())
    def revert(self):
        cond = conditions.Get(self.expr())
        if cond:
            cond.DeactivateAndKill()
    def expr(self):
        return "EventTechDiscountN(\"%s\", \"%s\", %d)" % (self._source, self._tech_id, self._percent)
    def tooltip(self):
        return TechKind.All[self._tech_id]

class CndTechUnlockedAndNoDiscount(ChoiceCondition):
    def __init__(self, source, tech_id):
        self._sub = CndTechStatus(tech_id, TechStatus.Unlocked)
        self._expr_prefix = "EventTechDiscountN(\"%s\", \"%s\"" % (source, tech_id)

    def check(self):
        already_present = any(c.Expression.startswith(self._expr_prefix) for c in conditions.AllActive)
        if already_present: return None
        return self._sub.check()

class CndTechStatus(ChoiceCondition):
    def __init__(self, tech_id, status):
        self._tech_id = tech_id
        self._status = status

    def check(self):
        status = game.Technology.Status(TechKind.All[self._tech_id])
        if status == self._status:
            return {} # ok to show
