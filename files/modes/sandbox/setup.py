################################################################
# Initial conditions

class SandboxConditions(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_scenario_start)
    
    def on_scenario_start(self, _):
        sandbox_conditions = [
            (ResourceShortages,),
            (EmpireSize, "sandbox"),
            (SlipspaceOverload, 2),
            (ManualRetirement,),
            (ResourceAdditionalInfo,)
        ]
        for c in sandbox_conditions:
            empire.Conditions.Activate(*c)
        for member in ih(empire.Council.Members):
            empire.Conditions.Activate(RaceStatus, member.Race.ID)
            member.ActivatePerks()

class SandboxResources(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_scenario_start)

    def on_scenario_start(self, _):
        empire.Stock.Receive(Resource.Cash, math.ceil(constants.Int("starting.cash") * 0.5)) # 1.5x money

class SandboxStats(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_tabs)
        self.react_to(Trigger.GameLoaded, self.setup_tabs)

    def setup_tabs(self, _):
        game.Stats.Add(StatSources.SummaryTab(0))
        game.Stats.Add(StatSources.DomainTab(5))
        game.Stats.Add(StatSources.SectorTab(10))

################################################################
# Quests (missions)

class SandboxQuests(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_scenario_start)

    def on_scenario_start(self, _):
        empire.Conditions.Activate(SandboxMotherOfQuests)

class SandboxMotherOfQuests(MotherOfQuests):
    """Overrides for the standard class."""

    def _dialog_text_and_range(self):
        # calculate totals
        text = LS("quests.sandbox.message", "The council has new missions for you.\nYou can accept as many as you want, or decline taking any.")
        return (text, IntRange.Between(0, 3))

    def _reroll_quests(self, quests):
        self._deactivate_quest_selection(quests)
        self.data.rerolls = self.data.get_or("rerolls", 0) + 1
        self._show_quest_picker()

    def _generate_offers(self):
        total_race_level = sum(m.SatisfactionLevel for m in empire.Council.Members)  
        return self._generate_quest_offers(total_race_level + self.data.get_or("rerolls", 0))

    def _show_quest_picker(self):
        self._in_quest_selection = True
        offers = self._generate_offers()
        text, range = self._dialog_text_and_range()
        sandbox_quest_dialog(self, offers, text, range)
        return MessageAction.Dismiss

    def _make_irreversible_if_needed(self):
        # checking quests is not irreversible in Endless, we don't care about hidden info that much here
        # and you can reroll the quests anyway
        pass

def sandbox_quest_dialog(mother_of_quests, quests, text, selectable_range):
    def when_selection_changes(selected_offers, dialog):
        dialog.Change({
            "buttons": determine_buttons(selected_offers)
        })
    def when_done(button, selected_offers):
        if button == "accept":
            mother_of_quests._finalize_quest_selection(quests, selected_offers)
        if button == "reroll":
            mother_of_quests._reroll_quests(quests)
        elif button == "postpone":
            mother_of_quests._postpone_quest_selection(quests)
    def determine_buttons(selected_offers):
        count = len(selected_offers)
        button_text = LS("quests.button.accept", "Accept missions", count)
        enabled = True
        if selectable_range.NumberIsBelow(count):
            button_text = LS("quests.button.too_few", "Select {1} more", selectable_range.LowEnd - count)
            enabled = False
        elif selectable_range.NumberIsAbove(count):
            button_text = LS("quests.button.too_many", "Select {1} less", count - selectable_range.HighEnd)
            enabled = False   
        elif count == 0:
            button_text = LS("quests.sandbox.button.decline", "Decline missions")   
        return [
            {"id": "accept", "text": button_text, "width": -15, "enabled": enabled},
            {"id": "reroll", "text": LS("quests.sandbox.button.reroll", "Reroll"), "width": -15},
            {"id": "postpone", "text": LS("quests.button.postpone", "Postpone"), "width": -15}
        ]    
    # start the dialog window
    dialog = {
        "width": 740,
        "positioning": {"pivot": Vector2(0.5, 0), "anchor": Vector2(0.5, 0), "offset": Vector2(0, 20)},
        "header": LS("quests.new_missions.header", "New missions"),
        "text": text,
        "options": quests,
        "buttons": determine_buttons([]),
        "dismiss_action": "postpone",
        "show_conversation": True,
        "when_done": when_done,
        "when_selection_changes": when_selection_changes
    }    
    mother_of_quests._make_irreversible_if_needed()
    game.Dialogs.MultiChoice(dialog)

################################################################
# Years in power - cost happiness

class YearsInPower(GlobalCondition):
    def activate(self):
        self._amount, self._big = 0, False
        self.react_to(Trigger.ActionTaken, self._refresh)
        self.react_to(Trigger.ActionReverted, self._refresh)
        self._refresh({})

    def _refresh(self, _):
        amount, big = self.calculate_effect_size()
        if amount != self._amount:
            self._amount, self._big = amount, big
            self.signal_change()
            
    def info(self):
        info = CondInfo()
        info.Icon = "icon_years_in_power"
        info.ShortText = "-%d%%:H:" % self._amount if self._amount > 0 else None
        info.MediumText = LS("cond.years_in_power.header", "In power: {1|unit:year}", game.Time.NormalizedTurn)
        if self._big:
            info.FullDescription = LS("cond.years_in_power.big", "Each year you hold on to power makes it harder to maintain happiness.\nYou lose 2%:H: each year.")
        else:
            info.FullDescription = LS("cond.years_in_power.small", "Each year you hold on to power makes it harder to maintain happiness.\nYou lose 1%:H: each year.")    
            threshold = self._threshold()
            if threshold > 0:
                info.FullDescription += " " + L("cond.years_in_power.deadline", "This will become 2%:H: in {1|unit:year}.", threshold - game.Time.NormalizedTurn)
        info.Tooltip = "[s:TooltipHeader]%s[/s]\n[s:TooltipLight]\n%s[/s]" % (info.MediumText, info.FullDescription)
        info.Priority = 20
        return info
    
    def _threshold(self):
        return constants.Int("years_in_power.threshold")

    def calculate_effect_size(self):
        threshold = self._threshold()
        time = game.Time.NormalizedTurn
        if time >= threshold and threshold > 0:
            amount = threshold + (time - threshold) * 2
            big = True
        else:
            amount = time
            big = False
        return amount, big

    def effects(self):
        flows = [
            ResourceFlow.Happiness(-self._amount, FlowCategory.YearsInPower),
            ResourceFlow.Happiness(-2 if self._big else -1, FlowCategory.YearsInPowerChange)
        ]
        return flows

class Discontent(GlobalCondition):
    def activate(self):
        self._percent, self._amount = 0, 0
        self.react_to(Trigger.ActionTaken, self._refresh)
        self.react_to(Trigger.ActionReverted, self._refresh)
        self._refresh({})

    def _refresh(self, _):
        percent, amount = self.calculate_effect_size()
        if amount != self._amount or percent != self._percent:
            self._percent, self._amount = percent, amount
            self.signal_change()

    def info(self):
        if self._percent <= 0: return None
        info = CondInfo()
        info.Icon = "icon_discontent"
        info.ShortText = "-%d%%" % self._percent
        info.MediumText = LS("cond.discontent.header", "Discontent: -{1}%:$:", self._percent)
        info.FullDescription = LS("cond.discontent.desc", 
            "In Endless mode, low happiness reduces your trade income. On this difficulty level, each point of happiness below {1}% reduces your trade income.",
            constants.Int("discontent.threshold"))
        info.Tooltip = "[s:TooltipHeader]%s[/s]\n[s:TooltipLight]\n%s[/s]" % (info.MediumText, info.FullDescription)
        info.Priority = 20
        return info

    def calculate_effect_size(self):
        happiness = game.Stock.Happiness
        threshold = constants.Int("discontent.threshold")
        under = max(threshold - happiness, 0)
        if under == 0: return 0, 0
        trade_income = game.Stock.TradeIncome
        return under, math.ceil(under * 0.01 * trade_income)

    def effects(self):
        if self._percent <= 0: return None
        penalty = self._amount
        return [
            ResourceFlow.Cash(-penalty, FlowCategory.Discontent)
        ]

################################################################
# Retiring the game

class ManualRetirement(GlobalCondition):
    def ingame_menu_options(self):
        return [{
            "label": LS("menus.sandbox.button.retire", "Retire this empire"),
            "callback": self.retire
        }]

    def retire(self): 
        commands.Issue(ExplicitScripted(world, self))

    def apply(self):   
        # let's go!
        empire.WinningLosing.EndScenario({
            "outcome": "win",
            "heading": LS("menus.sandbox.retired", "Empire retired"),
            "comment": LS("menus.sandbox.retired.comment", "You retired after {1|unit:year} in power.", game.Time.NormalizedTurn),
            "shown_elements": ["undo", "screenshot", "picks", "breakdown"],
            "summary_items": [game.GameConfig.Sector.Seed]
        })

    def revert(self):
        pass

    def reproduce(self): return "ManualRetirement()"
    def undo_description(self): return LS("ui.command.retire")

#########################################################
# Music

class SizeBasedMusic(MusicProgression):
    THRESHOLDS = [3, 5, 7]
    def __init__(self, every):
        self._every = every
        self._es = None
    def _empire_size(self):
        if self._es is not None: return self._es
        self._es = find_cond("EmpireSize(")
        return self._es
    def _check_for_transition(self, prev):
        if prev >= len(self.THRESHOLDS): return
        es = self._empire_size()
        if es is None: return
        if prev > len(self.THRESHOLDS): return None
        if es.current_size() >= self.THRESHOLDS[prev]:
            return prev + 1
