class GlobalCondition:
    """Extend this class to create your own GlobalConditions."""
    def bind(self, host_model):
        self._host = host_model
        self.data = CustomDataAccess(host_model)
        if hasattr(self, "_initial_data"):
            for k, v in self._initial_data.items():
                self.data.set_value(k, v)

    def host(self): return self._host
    def loadable_expression(self):
        cond_expr = self.host().Expression
        escaped_expr = cond_expr.replace('"', '\\"')
        return "empire.Conditions.Get(\"%s\").PythonObject" % escaped_expr

    def react_to(self, trigger, method, priority = None):
        if priority is not None:
            self._host.ReactTo(trigger, method, priority)
        else:
            self._host.ReactTo(trigger, method)

    def post_message(self, message_method, *args):
        game.Messages.PostMessage(message_method, *args)

    def signal_change(self):
        self._host.TriggerChange()

    def rng(self, tag = ""):
        return self._host.RNG(self.__class__.__name__ + tag)

def condition(name_prefix):
    for cond in game.Conditions.AllActive:
        if cond.Expression.startswith(name_prefix):
            return cond.PythonObject
    return None

#################################################
# ResourceShortages
# - this has to live in a condition to properly interact with undo
# - the paired quality applies whatever the condition sets

class ResourceShortages(GlobalCondition):
    MAX_PENALTY = 8

    def activate(self):
        self.react_to(Trigger.PlanetColonized, self.on_colonized)
        self.react_to(Trigger.NewTurn, self.on_new_year)

    def _time_since_established(self, node):
        if node.EstablishedOn is None: return 0
        return empire.Time.Date.TurnsSince(node.EstablishedOn) + 1

    def on_colonized(self, data):
        self.perform_updates([data["node"]])

    def on_new_year(self, data):
        unhappy_planets = game.Nodes.PlanetsWithLevel(0)
        self.perform_updates(unhappy_planets)

    def perform_updates(self, nodes):
        updates = ConsUpdateNodeData()
        for p in nodes:
            shortage_penalty = self._time_since_established(p)
            maxed_out = shortage_penalty >= self.MAX_PENALTY
            if maxed_out:
                shortage_penalty = self.MAX_PENALTY
            updates.add(p, "shortages", shortage_penalty)
        # all updates are actually done through a SC to play nice with undo
        commands.IssueScriptedConsequence(updates)

class StdShortages:
    def name(self): return LS("quality.resource_shortages", "Resource shortages")
    def desc(self): return LS("quality.resource_shortages.desc", 
        "If a planet is missing resources it needs, its going to be unhappy. This problem gets worse by 1% every turn, until a maximum of [[delta:-{1}H]].", ResourceShortages.MAX_PENALTY)
    def sentiment(self): return QualitySentiment.Negative

    def effects(self, node):
        if node.Level != 0 or not node.HasUnmetNeeds: return None
        penalty = node.CustomData.GetOr("shortages", 0)
        maxed_out = penalty >= ResourceShortages.MAX_PENALTY
        flows = [ResourceFlow.Happiness(-penalty, FlowCategory.ResourceShortages)]
        if not maxed_out:
            # the per turn delta, so that happiness delta can show properly on the game's resource UI
            flows.append(ResourceFlow.Happiness(-1, FlowCategory.ShortageGettingWorse))
        return flows

class StdPastShortages:
    PENALTY = 3
    def name(self): return LS("quality.past_shortages", "Past shortages")
    def desc(self): return LS("quality.past_shortages.desc", 
        "Once a planet reaches maximum unhapiness due to shortages, there is a lingering [[delta:-{1}H]] effect even after you fix the root cause.", StdPastShortages.PENALTY)
    def sentiment(self): return QualitySentiment.Negative

    def effects(self, node):
        if node.Level > 0 and node.CustomData.GetOr("shortages", 0) >= ResourceShortages.MAX_PENALTY:
            return [ResourceFlow.Happiness(-StdPastShortages.PENALTY, FlowCategory.PastShortages)]

#################################################

class SlipspaceOverload(GlobalCondition):
    def __init__(self, multiplier = 1.0):
        self._multiplier = multiplier

    def activate(self):
        self._overload, self._slipway_count = None, None
        self.react_to(Trigger.WorldStateChanged, self.after_change)
        self.after_change({})

    def after_change(self, _):
        slipway_count = count_every(Slipway)
        if slipway_count != self._slipway_count:
            self._slipway_count = slipway_count
            self._overload = self.overload_amount(slipway_count)
            self.signal_change()

    def current_overload(self): return self._overload

    def overload_amount(self, slipway_count):
        start = constants.Int("slipspace_overload.starts_at") * self._multiplier
        step = constants.Int("slipspace_overload.step") * self._multiplier
        overage = slipway_count - start
        if overage < 0: return 0
        increments = int(overage / step)
        return increments * 10
                
    def info(self):
        if self._overload <= 0: return None
        info = CondInfo()
        info.Icon = "icon_slipgate"
        info.ShortText = "+%d%%" % self._overload
        info.MediumText = LS("cond.slipspace_overload.header", "Slipspace overload: +{1}%", self._overload)
        info.FullDescription = LS("cond.slipspace_overload.desc", 
            "Because local slipspace is getting crowded, slipway building costs are *increased by +{1}%*.\n\nThis will worsen by 10% for each {2} slipways you add (now: {3}).", 
            self._overload, constants.Int("slipspace_overload.step"), self._slipway_count)
        info.Tooltip = "[s:TooltipHeader]%s[/s]\n[s:TooltipLight]\n%s[/s]" % (info.MediumText, info.FullDescription)
        info.Priority = 30
        return info

    def effects(self):
        if self._overload > 0:
            return [GlobalBonus.SlipwayCost(self._overload)]
    

class EmpireSize(GlobalCondition):
    STANDARD_LVS = [
        {"n": 8, "ac": 0},
        {"n": 16, "ac": 1},
        {"n": 24, "ac": 2},
        {"n": 32, "ac": 3},
        {"n": 40, "ac": 4},
        {"n": 50, "ac": 5},
        {"n": None, "ac": 6},
    ]
    SANDBOX_LVS = [
        {"n": 8, "ac": 0},
        {"n": 20, "ac": 1},
        {"n": 40, "ac": 2},
        {"n": 60, "ac": 3},
        {"n": 80, "ac": 4},
        {"n": 100, "ac": 5},
        {"n": 120, "ac": 6},
        {"n": 140, "ac": 7},
        {"n": 160, "ac": 8},
        {"n": 180, "ac": 9},
        {"n": None, "ac": 10}
    ]
    @staticmethod
    def _standard_lv(lv): return EmpireSize.STANDARD_LVS[lv]
    @staticmethod
    def _sandbox_lv(lv): return EmpireSize.SANDBOX_LVS[lv]

    def __init__(self, preset = "standard"):
        self._lv_access = getattr(self, "_%s_lv" % preset)
    
    def current_size(self): return self.data.level
    
    def activate(self):
        self.data.level = self.data.level or 0
        self._planets = self._count_planets()
        self.react_to(Trigger.WorldStateChanged, self.after_change)

    def after_change(self, data):
        colonized_planets = self._count_planets()
        if colonized_planets != self._planets:
            self._planets = colonized_planets
            implied_level = self._implied_level(colonized_planets)
            if implied_level != self.data.level:
                previous = self.data.level
                self.data.level = implied_level
                if implied_level > previous:
                    self._log_increase()
                    self._show_increase_message()
                empire.Stock.UpdateAllInfluences() # manually trigger this for now, think through for later
            self.signal_change()

    def effects(self):
        lv_data = self.level(self.data.level)
        ac = lv_data["ac"]
        ac = constants.Float("admin_cost.$", ac)
        effs = []
        if ac > 0:
            colonized_planets = game.Nodes.CountPlanetsWithLevelOrHigher(0)
            actual_cost = math.floor(ac * colonized_planets)
            effs.append(ResourceFlow.Flow(Resource.Cash, -actual_cost, FlowCategory.AdminCosts))
        return effs
        
    def threshold_for(self, lv):
        base_value = self.level(lv)["n"]
        if base_value is None: return None
        multiplier = constants.Float("admin_cost.interval_length")
        return round(base_value * multiplier)

    def info(self):
        lv = self.data.level
        ac = self.level(lv)["ac"]
        next_at = self.threshold_for(lv)
        info = CondInfo()
        info.Icon = "icon_prosperity"        
        info.MediumText = LS("cond.empire_size.header", "Empire size: {1}", self.level_name(lv))
        desc = LS("cond.empire_size.desc").ToString() + "\n\n"
        if ac >= 0:
            desc += LS("cond.empire_size.admin_effects", None, repr(ac)).ToString() + "\n\n"
        if next_at:
            desc += LS("cond.empire_size.next_increase", None, next_at, self._planets).ToString()
            info.ShortText = "%d/%d" % (self._planets, next_at)
        info.FullDescription = desc
        info.Tooltip = "[s:TooltipHeader]%s[/s]\n[s:TooltipLight]\n%s[/s]" % (info.MediumText, info.FullDescription)
        info.Priority = 50
        return info

    @staticmethod
    def level_name(lv): 
        if lv <= 7:
            return LS("cond.empire_size.lv%d" % lv)
        else:
            return LS("cond.empire_size.lv+", None, lv - 7)

    def level(self, lv):
        return self._lv_access(lv)
    
    def _log_increase(self):
        log = game.GameLog
        if not log: return
        log.Log("LogEmpireSize", {
            "size": self.data.level,
            "size_name": self.level_name(self.data.level)
        })

    def _show_increase_message(self):
        lv = self.data.level
        # message 
        self.post_message(self._msg_size_increased, lv)

    def _msg_size_increased(self, lv):
        msg = MessageContent()
        msg.Picture = "icon_prosperity"
        msg.ShortText = LS("cond.empire_size.msg.increase", "Empire size increased: *{1}*.", self.level_name(lv))
        msg.ExpiresIn = 6
        return msg

    def _implied_level(self, planets):
        lv = 0
        while planets >= (self.threshold_for(lv) or 1000000):
            lv += 1
        return lv

    def _count_planets(self): return sum(1 for p in every(Planet) if p.HasIndustry)


class WinTimeLimit(GlobalCondition):
    def __init__(self, turns):
        self._turns = turns
    
    def scenario_time_limit(self): return self._turns

    def activate(self):
        self._remaining = self._turns - empire.Time.NormalizedTurn
        self.react_to(Trigger.NewTurn, self.after_new_year, priority=1000)
        self.react_to(Trigger.ActionTaken, self.after_action, priority=1000)
        self.react_to(Trigger.ActionReverted, self.refresh)

    def refresh(self, data = None):
        remaining = self._turns - empire.Time.NormalizedTurn
        if remaining != self._remaining:
            self._remaining = remaining
            empire.WinningLosing.SetEndingTripped(self._remaining <= 0)
            self.signal_change()
    
    def after_new_year(self, data):
        self._remaining = self._turns - empire.Time.NormalizedTurn
        empire.WinningLosing.SetEndingTripped(self._remaining <= 0)
        self.signal_change()

    def after_action(self, data):        
        if empire.WinningLosing.IsEndingTripped:
            if not commands.AreAllQueuesEmpty: return
            if self._check_for_time_extension(): return
            self._end_game()

    def _msg_game_ending(self):
        msg = MessageContent()
        msg.Picture = "icon_time"
        msg.ShortText = LS("message.last_year", "*One year* remains!")
        msg.ExpiresIn = 1 # transient message
        return msg

    def turn_end_message(self):
        remaining = self._turns - empire.Time.NormalizedTurn
        if remaining <= 5:
            return L("banner.time_remaining", None, remaining)

    def effects(self):
        months = empire.Time.Date.MonthsUntilNextTurn
        years = self._turns - empire.Time.NormalizedTurn - 1
        if years > 0:
            text = LStr("ui.time_remaining.with_years", months, years)
        elif years == 0:
            text = LStr("ui.time_remaining.run_end", months)
        else:
            text = None
        if text:
            return [GlobalInfo("date", text)]
        else:
            return []
    
    def _check_for_time_extension(self):
        for te_cond in game.Conditions.Supporting("grant_time_extension"):
            extended = te_cond.PythonObject.grant_time_extension()
            if extended: 
                return True
        return False

    def _end_game(self):
        # is the game done already?
        if game.WinningLosing.IsScenarioComplete: return
        # is there anything still on the command queue?
        if not commands.AreAllQueuesEmpty: return
        # is something preventing the win?
        wincons = [c.PythonObject for c in game.Conditions.AllActive if hasattr(c.PythonObject, "check_win_condition")]
        for wincon in wincons:
            override = wincon.check_win_condition()
            if override:
                empire.WinningLosing.EndScenario(override)
                return
        # nope, let's go!
        self._win()

    def _win(self):
        seed_info = game.GameConfig.Sector.Seed
        if game.GameConfig.RankedInfo is not None:
            seed_info = L("menus.ranked.week_no", None, game.GameConfig.RankedInfo.Week)
        empire.WinningLosing.EndScenario({
            "outcome": "win",
            "heading": LS("menus.game_end.complete", "Run complete"),
            "summary_items": [seed_info]
        })

class LoseWhenBankrupt(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.NewTurn, self.after_new_year)

    def after_new_year(self, data):
        no_money = empire.Stock.Cash < constants.Int("probe.cost.$")
        negative_income = empire.Stock.Income(Resource.Cash) <= 0        
        if no_money and negative_income:
            self._end_game()
    
    def _end_game(self):
        empire.WinningLosing.EndScenario({
            "outcome": "loss", "defeat": True,
            "defeat_icon": "icon_bankrupt",
            "heading": LS("menus.game_end.bankruptcy.header", "Bankrupt"),
            "comment": LS("menus.game_end.bankruptcy", "After {1} years, our economy has faltered. You have been forced out of office.", empire.Time.NormalizedTurn),
            "shown_elements": ["undo"]
        })

class LoseOnLowHappinessOverTime(GlobalCondition):
    def __init__(self, limit, years):
        self._limit, self._years = limit, years

    def activate(self):
        self.react_to(Trigger.NewTurn, self.perform_checks)
        self.react_to(Trigger.ActionReverted, lambda x: self.signal_change())

    def perform_checks(self, _):
        distance = empire.Stock.Happiness - self._limit
        losing_range = distance < 0
        if losing_range: 
            if self.data.get_or("since", None) is None:
                self.update_state(empire.Time.NormalizedTurn)
                self.post_message(self._msg_happiness_low)
            else:
                duration = empire.Time.NormalizedTurn - self.data.since
                if duration >= self._years:
                    self._end_game()
        else:
            if self.data.get_or("since", None) is not None:
                self.update_state(None)
        self.signal_change()

    def update_state(self, value):
        changes = ConsUpdateNodeData(trigger_changes = True)        
        changes.add(self.host(), "since", value)
        commands.IssueScriptedConsequence(changes)
    
    def info(self):
        if self.data.get_or("since", None) is None: return None
        duration = empire.Time.NormalizedTurn - self.data.since
        remaining = self._years - duration
        ci = CondInfo()
        ci.Icon = "icon_revolt"
        ci.ShortText = "[s:Bad]%dy[/s]" % remaining        
        ci.FullDescription = LS("menus.game_lost.happiness.warning", "The happiness of your people is dangerously low.\nIf you don't get it above *{1}%* in *{2}*, your game will end.", self._limit, Localization.Plural(remaining, "unit.year"))
        ci.MediumText = LS("menus.game_lost.happiness.header", "Unrest")
        ci.Tooltip = "[s:TooltipHeader]%s[/s]\n[s:TooltipLight]\n%s[/s]" % (ci.MediumText, ci.FullDescription)
        return ci

    def _msg_happiness_low(self):
        msg = MessageContent()
        msg.Picture = "icon_revolt"
        msg.ShortText = LS("message.happiness_low", "Happiness is dangerously low.")
        return msg

    def _end_game(self):
        empire.WinningLosing.EndScenario({
            "outcome": "loss", "defeat": True,
            "defeat_icon": "icon_revolt",
            "heading": LS("menus.game_end.unhappy.header", "Thrown out of office"),
            "comment": LS("menus.game_end.unhappy", "After {1} years, the people of the empire forced your resignation.", empire.Time.NormalizedTurn),
            "shown_elements": ["undo"]
        })


class ResourceAdditionalInfo(GlobalCondition):
    def resource_info_S(resource_id):
        subjects = [lab_study_subject(l) for l in game.Nodes.WithType("structure.lab") if l.Level >= 1]
        subject_icons = [":^%s:" % r.ID for r in subjects if r is not None]
        if len(subject_icons) == 0: return []
        subject_icons.sort()
        subjects_text = "<space=-0.4em>".join(subject_icons)
        text = L("menus.ui.laboratories_present")
        text += "<line-height=0>\n<align=right>" + subjects_text
        return [text]

class OdoCounting(GlobalCondition):
    """Reacts to in-game events and bumps various 'odometer' counters."""
    def activate(self):
        self.react_to(Trigger.AfterNodeDiscovered, self.odo_signal)
        self.react_to(Trigger.PlanetColonized, self.odo_planet)
        self.react_to(Trigger.NewTurn, self.odo_year)
        self.react_to(Trigger.ConnectionBuilt, self.odo_connection)
        self.react_to(Trigger.ScenarioComplete, self.odo_scenario, priority = 1)
        self.react_to(Trigger.TradeRouteEstablished, self.odo_trade_route)
        self.react_to(Trigger.TechInvented, self.odo_tech)
        self.react_to(Trigger.StructureBuilt, self.odo_structure)

    def odo_signal(self, _): game.Odo.Bump(OdoStat.SignalsScanned, 1)
    def odo_connection(self, _): game.Odo.Bump(OdoStat.ConnectionsBuilt, 1)

    def odo_trade_route(self, _):
        game.Odo.Bump(OdoStat.TradeRoutesEstablished, 1)
        routes_in_this_game = world.Count[TradeRoute]()
        game.Odo.Bump(OdoStat.MostTradeRoutes, routes_in_this_game)

    def odo_tech(self, _):
        game.Odo.Bump(OdoStat.TechsInvented, 1)
        techs_in_this_game = sum(1 for t in game.Technology.AllInvented)
        game.Odo.Bump(OdoStat.MostTechsInvented, techs_in_this_game)

    def odo_structure(self, data):
        count = data["count"]
        game.Odo.Bump(OdoStat.StructuresBuilt, count)
        total_built = sum(1 for s in every(Structure) if s.WasBuilt)
        game.Odo.Bump(OdoStat.MostStructuresBuilt, total_built)

    def odo_scenario(self, data):
        game.Odo.Bump(OdoStat.GamesFinished, 1)

    def odo_planet(self, _):
        colonized_planets = game.Nodes.CountPlanetsWithLevelOrHigher(0)
        game.Odo.Bump(OdoStat.PlanetsColonized, 1)
        game.Odo.Bump(OdoStat.MostPlanets, colonized_planets)

    def odo_year(self, data):
        science_earned, money_earned = 0, 0
        happiness = game.Stock.Happiness
        for chg in data["changes"]:
            if chg.Item1 == Resource.Cash:
                money_earned = chg.Item2
            if chg.Item1 == Resource.Science:
                science_earned = chg.Item2
        # counters
        game.Odo.Bump(OdoStat.MoneyEarned, money_earned)
        game.Odo.Bump(OdoStat.ScienceGenerated, science_earned)
        # maxes
        game.Odo.Bump(OdoStat.MostMoneyPerYear, money_earned)
        game.Odo.Bump(OdoStat.MostSciencePerYear, science_earned)
        game.Odo.Bump(OdoStat.MaximumHappiness, happiness)



class EmptySignalSwap(GlobalCondition):    
    """Common condition that causes a percentage of empty signals to be swapped with new contents."""
    def __init__(self, new_contents, chance):
        self._new_contents = new_contents
        self._chance = chance

    def activate(self):
        self.react_to(Trigger.BeforeSignalRevealed, self.check_signal)

    def check_signal(self, data):
        signal = data["signal"]
        if signal.Contents == "nothing":
            swapped = Randomness.WithProbability(self.rng(str(signal.Position)), self._chance * 0.01)
            if swapped:
                signal.Contents = self._new_contents


class EventTechDiscount(GlobalCondition):
    """Deprecated, use the new EventTechDiscountN."""
    def __init__(self, tech_id, pct):
        self._tech_id = tech_id
        self._pct = pct

    def tech_discount(self, tech):
        if tech.ID == self._tech_id:
            reason = LS("event.tech_discounted", None, self._pct)
            return Discount("event", reason, self._pct * 0.01)

# The new version of this GC includes a source so discounts from various sources can be distinguished.
# The old version was kept to keep saves from before the change working.
class EventTechDiscountN(EventTechDiscount):
    def __init__(self, source, tech_id, pct):
        EventTechDiscount.__init__(self, tech_id, pct)
        self._source = source
