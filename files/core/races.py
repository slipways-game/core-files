# Rules for all the core races. Mostly defines what rewards you get for upgrading a race to level X.

class RaceRules:
    def __init__(self, race_id):
        self._race_id = race_id

    def race(self): return Race.All[self._race_id]

    def reward_for_level(self, lv):
        if lv == 1: return RewardEventOptions(self.race())
        if lv == 3: return RewardTechDiscount(self.race(), 20)
        if lv == 4: return RewardHub(self.race())

class BaqarRules(RaceRules):
    def __init__(self): RaceRules.__init__(self, "baqar")
    
    def reward_for_level(self, lv):
        if lv == 2: return RewardImmediate(60, 2)
        return RaceRules.reward_for_level(self, lv)

class SilthidRules(RaceRules):
    def __init__(self): RaceRules.__init__(self, "silthid")
    
    def reward_for_level(self, lv):
        if lv == 2: return RewardImmediate(20, 6)
        return RaceRules.reward_for_level(self, lv)

class DendrRules(RaceRules):
    def __init__(self): RaceRules.__init__(self, "dendr")
    
    def reward_for_level(self, lv):
        if lv == 2: return RewardImmediate(40, 4)
        return RaceRules.reward_for_level(self, lv)

class VattoriRules(RaceRules):
    def __init__(self): RaceRules.__init__(self, "vattori")
    
    def reward_for_level(self, lv):
        if lv == 2: return RewardImmediate(0, 8)
        return RaceRules.reward_for_level(self, lv)

class AphorianRules(RaceRules):
    def __init__(self): RaceRules.__init__(self, "aphorian")
    
    def reward_for_level(self, lv):
        if lv == 2: return RewardImmediate(80, 0)
        return RaceRules.reward_for_level(self, lv)

#################################################
## Reward implementations

class RewardTechDiscount:
    def __init__(self, race, discount): 
        self._race = race
        self._discount = discount

    def description(self):
        return LS("reward.tech_discount", "{1} tech discounted by *{2}%*", self._race.LReference, self._discount) 
    def apply(self):
        self._cond = empire.Conditions.Activate(TechDiscount, self._race.ID, self._discount * 0.01)        
    def revert(self):
        self._cond.Deactivate()

class RewardEventOptions:
    def __init__(self, race):
        self._race = race

    def description(self):
        return LS("reward.options", "{1} options unlocked in events", self._race.LReference)
    def apply(self):
        self._cond = empire.Conditions.Activate(EventOptionUnlock, self._race.ID)
    def revert(self):
        self._cond.Deactivate()

class RewardQuality:
    def __init__(self, id, quality, *params):
        self._id, self._quality, self._params = id, quality, params
    def description(self):
        return LS("reward.%s" % self._id)
    def apply(self):
        self._qty = empire.Qualities.EstablishGlobally(self._quality, *self._params)
    def revert(self):
        empire.Qualities.Unestablish(self._qty)


class RewardNegate:
    def __init__(self, id, quality_expr):
        self._id, self._quality_expr = id, quality_expr
    def description(self):
        return LS("reward.%s" % self._id)
    def apply(self):
        empire.Qualities.Negate(self._quality_expr, True)
    def revert(self):
        empire.Qualities.Negate(self._quality_expr, False)

class RewardCondition:
    def __init__(self, id, cond_class, *params):
        self._id, self._cond_class, self._params = id, cond_class, params
    def description(self):
        return LS("reward.%s" % self._id)
    def apply(self):
        self._cond = empire.Conditions.Activate(self._cond_class, *self._params)
    def revert(self):
        self._cond.Deactivate()

class RewardHub:
    def __init__(self, race):
        self._race = race
        self._race_id = race.ID
    def description(self):
        hub_name = L("structure.hub_%s" % self._race_id)
        hub_name = RichText.WithColor(hub_name, self._race.Assets.textColor)
        return LS("reward.access_to_hub", None, hub_name)
    def apply(self):
        self._cond = empire.Conditions.Activate(HubUnlock, self._race_id)
        ConsUpdateNodeData().inc(game, "hubworlds_unlocked").issue()
    def revert(self):
        self._cond.Deactivate()

class RewardImmediate:
    def __init__(self, cash, science):
        self._bonuses = []
        scale = constants.Float("rewards.immediate_reward_scale")
        cash = int(math.ceil(cash * scale))
        science = int(math.ceil(science * scale))
        if cash > 0: self._bonuses += [(Resource.Cash, cash)]
        if science > 0: self._bonuses += [(Resource.Science, science)]

    def description(self):
        if len(self._bonuses) == 1:
            return LS("reward.single_resource", "Get [[delta:{1}{2}]]", self._bonuses[0][1], self._bonuses[0][0].ID)
        else:
            return LS("reward.two_resources", "Get [[delta:{1}{2}]] and [[delta:{3}{4}]]", self._bonuses[0][1], self._bonuses[0][0].ID, self._bonuses[1][1], self._bonuses[1][0].ID)

    def apply(self):
        for resource, amount in self._bonuses:
            empire.Stock.Receive(resource, amount)

    def revert(self):
        for resource, amount in self._bonuses:
            empire.Stock.Return(resource, amount)

class TechDiscount(GlobalCondition):
    def __init__(self, race_id, amount):
        self._effects = [GlobalBonus.TechDiscount(Race.All[race_id], amount)]
    def effects(self): return self._effects

class EventOptionUnlock(GlobalCondition):
    def __init__(self, race_id):
        self._effects = [GlobalBonus.UnlockEventOptions(Race.All[race_id])]
    def effects(self): return self._effects

class HubUnlock(GlobalCondition):
    def __init__(self, race_id):
        self._effects = [AddUnlock.Globally("structure.hub_%s" % race_id)]
    def effects(self): return self._effects

#################################################
## Race status (condition used only for display)

class RaceStatus(GlobalCondition):
    def __init__(self, race_id):
        self._race_id = race_id

    def activate(self):
        self._member = empire.Council.Member(Race.All[self._race_id])
        self.react_to(Trigger.CouncilMemberStatusChanged, self.when_status_changes)

    def when_status_changes(self, data):
        if data["member"] == self._member:
            self.signal_change()
    
    def info(self):
        if not self._member.IsActive: return None
        ci = CondInfo()
        quests = empire.Quests.QuestsAssignedTo(self._member)
        shorts = [q.Info.ShortText for q in quests]
        fulls = [q.Info.FullDescription for q in quests]
        ci.Icon = self._race_id
        ci.Important = True
        ci.ShortText = "\n".join(shorts)
        ci.FullDescription = "\n".join(fulls)
        ci.Tooltip = self._member
        return ci
