# The logic for all council tasks given in the core game.

def quest_difficulty(member, tweak, quest_kind = None):
    lv = member.SatisfactionLevel
    if quest_kind and quest_kind.Progression:
        # hardcoded progression available
        prog = list(quest_kind.Progression)
        if lv >= len(prog):
            delta = prog[-1] - prog[-2]
            steps = lv - len(prog) + 1
            return prog[-1] + delta * steps
        else:
            return prog[lv]
    # no hardcoded progression, calculate
    lv = min(lv, constants.Int("quests.difficulty_cap", 3))    
    difficulty = [0, 45, 70, 100][min(lv, 3)]
    difficulty += max(0, lv - 3) * 30
    difficulty += constants.Int("quests.difficulty_offset", 0)
    difficulty += tweak
    return difficulty

def quest_interpolate(minimum, maximum, difficulty):
    return round(minimum + (maximum - minimum) * 0.01 * difficulty)

def quest_focus(focus_settings):
    focus_settings["view_offset"] = Vector2(0, -0.5)
    game.Camera.Focus(focus_settings)

####################################################

class MotherOfQuests(GlobalCondition):
    """Handles the quest system as a whole and makes sure new quests are spawned when they're needed."""
    def __init__(self):
        hook_expr = constants.StringOrDefault("quests.hooks", "")
        self._hooks = eval(hook_expr) if hook_expr else None

    @staticmethod
    def find():
        return conditions.Supporting("check_for_new_quests")[0].PythonObject
    
    def activate(self):
        self._in_quest_selection = False
        self.data.wait_for_year = self.data.get_or("wait_for_year", 1)
        self.react_to(Trigger.ActionTaken, self.check_for_new_quests)

    def check_for_new_quests(self, _):
        quests_disabled = constants.Int("quests.disabled") > 0
        if self._in_quest_selection or quests_disabled: return
        if self.quests_available():
            self.offer_quests(first_time = True)

    def quests_available(self):
        active_quests = list(empire.Quests.ActiveQuests)
        late_enough = game.Time.NormalizedTurn >= self.data.wait_for_year
        no_active_quests = len(active_quests) == 0
        not_declined_yet = not empire.CustomData.Has("quests_declined")
        allowed_by_custom_logic = True
        if self._hooks and hasattr(self._hooks, "should_offer_quests"):
            allowed_by_custom_logic = self._hooks.should_offer_quests()       
        return late_enough and no_active_quests and not_declined_yet and allowed_by_custom_logic

    def offer_quests(self, first_time):
        # is the game still running?
        if empire.WinningLosing.IsEndingTripped: return
        # don't duplicate messages
        if not game.Messages.IsMessageShowing("MotherOfQuests"):
            self.post_message(self._msg_new_quests, first_time)

    def terminate_all_quests_for(self, council_member):
        matching = [q for q in game.Quests.ActiveQuests if q.Member == council_member]
        for quest in matching:
            cons = ConsTerminateQuest(council_member, quest.QuestCondition)
            commands.IssueScriptedConsequence(cons)

    def _msg_new_quests(self, first_time):
        msg = MessageContent()
        msg.Important = first_time
        # text
        msg.ShortText = LS("quests.msg.new_quests_available", "New *missions* available")
        # generate picture string
        msg.Picture = "situation"
        # callbacks
        msg.WhenClicked = self._show_quest_picker
        msg.WhenDismissed = lambda: MessageAction.NoAction
        msg.DiscardCondition = lambda: not self.quests_available()
        return msg

    def _msg_test(self):
        msg = MessageContent()
        msg.Important = True
        msg.ShortText = "Test message"
        msg.Picture = "vattori"
        msg.WhenClicked = lambda: MessageAction.Dismiss
        msg.WhenDismissed = lambda: MessageAction.Dismiss
        return msg

    def _generate_offers(self):
        total_race_level = sum(m.SatisfactionLevel for m in empire.Council.Members)
        if self._hooks and hasattr(self._hooks, "generate_quest_offers"):
            return self._hooks.generate_quest_offers(total_race_level)
        return self._generate_quest_offers(total_race_level)

    def _generate_quest_offers(self, number):
        # generate the quests
        quests = []
        for i, m in enumerate(empire.Council.Members):
            # randomize a new offer
            rng = game.RNG(m.Race.ID, number)
            qk, offer = None, None
            retries = 0
            while retries < 40:
                retries += 1
                qk = QuestKind.Random(m.Race, [], rng)
                if not qk: break
                offer = QuestOffer(m.Race.ID, qk.ID, rng)
                if offer.valid: break
            # could not find a valid offer?
            if not offer or not offer.valid: continue
            # add
            quests.append(offer)
        return quests

    def _dialog_text_and_range(self):
        # calculate totals
        endgame = empire.Time.NormalizedTurn >= constants.Int("quests.endgame_transition")
        const_prefix = "endgame_" if endgame else ""
        minimum_selectable = constants.Int("quests.%spick_min" % const_prefix)
        maximum_selectable = constants.Int("quests.%spick_max" % const_prefix)
        decline_allowed = constants.Int("quests.%sallow_decline" % const_prefix) > 0
        text = L("quests.%scouncil_has_new_tasks" % const_prefix)
        optional = "_optional" if decline_allowed else ""
        if minimum_selectable == maximum_selectable:
            pick_text = L("quests.pick_exact%s" % optional, None, minimum_selectable)
        elif minimum_selectable == 1:
            pick_text = L("quests.pick_up_to%s" % optional, None, maximum_selectable)
        else:
            pick_text = L("quests.pick_between%s" % optional, None, minimum_selectable, maximum_selectable)
        text += " " + pick_text
        if endgame:
            text = styled(text, "Warning")
        return (text, IntRange.Between(minimum_selectable, maximum_selectable), decline_allowed)
    
    def _show_quest_picker(self):
        self._in_quest_selection = True
        offers = self._generate_offers()
        text, range, allow_zero = self._dialog_text_and_range()
        start_quest_dialog(self, offers, text, range, allow_zero)
        return MessageAction.Dismiss

    def _finalize_quest_selection(self, offers, selected_offers):
        for o in offers:
            o.deactivate()
        indices = [offers.index(o) for o in selected_offers]
        commands.Issue(ExplicitScripted(world, ConsQuestsPick(indices)))
        self._in_quest_selection = False

    def _postpone_quest_selection(self, offers):
        self._deactivate_quest_selection(offers)
        self.offer_quests(first_time = False)

    def _deactivate_quest_selection(self, offers):
        for o in offers:
            o.deactivate()
        self._in_quest_selection = False

    def _downgrade_to_normal_message(self):
        self.post_message(self._msg_new_quests)
        return MessageAction.Dismiss

    def _make_irreversible_if_needed(self):
        """The first time the quest dialog is shown, it is irreversible since quests are hidden information."""
        last_seen_total = game.CustomData.GetOr("last_seen_quests", -1)
        current_total = sum(m.SatisfactionLevel for m in empire.Council.Members)
        if current_total != last_seen_total:
            game.CustomData.Set("last_seen_quests", current_total)
            commands.Issue(ExplicitScripted(world, ConsCheckCouncilTasksIrreversibly()))

def start_quest_dialog(mother_of_quests, quests, text, selectable_range, allow_zero):
    def when_selection_changes(selected_offers, dialog):
        dialog.Change({
            "buttons": determine_buttons(selected_offers)
        })
    def when_done(button, selected_offers):
        if button == "accept":
            mother_of_quests._finalize_quest_selection(quests, selected_offers)
        elif button == "postpone":
            mother_of_quests._postpone_quest_selection(quests)
    def determine_buttons(selected_offers):
        count = len(selected_offers)
        button_text = LS("quests.button.accept", "Accept missions", count)
        enabled = True
        if count == 0 and allow_zero:
            button_text = LS("quests.button.decline", "Decline")
        elif selectable_range.NumberIsBelow(count):
            button_text = LS("quests.button.too_few", "Select {1} more", selectable_range.LowEnd - count)
            enabled = False
        elif selectable_range.NumberIsAbove(count):
            button_text = LS("quests.button.too_many", "Select {1} less", count - selectable_range.HighEnd)
            enabled = False
        return [
            {"id": "accept", "text": button_text, "width": 200, "enabled": enabled},
            {"id": "postpone", "text": LS("quests.button.postpone", "Postpone"), "width": 200}
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
    # irreversible the first time you check
    mother_of_quests._make_irreversible_if_needed()
    game.Dialogs.MultiChoice(dialog)

####################################################

class QuestOffer:
    """Gives the right environment for quest logic (QL***) classes so that
    they can determine their properties when they're offered to the player,
    without actually creating a GlobalCondition yet."""
    def __init__(self, race_id, quest_id, rng):
        self._race_id = race_id
        self._quest_id = quest_id
        self._rng = rng
        self._vitals = None
        self._last_interaction = None
        self.data = TemporaryDataAccess()
        self.activate()
    
    def activate(self):
        # instantiate quest logic
        quest_kind = QuestKind.All[self._quest_id]
        self._quest = quest_kind.InstantiateLogic()  
        self._quest.bind(self)
        # generate tweak
        difficulty_tweak = Randomness.Int(self._rng, *self._quest.tweak_range())
        self._tweak = difficulty_tweak
        # initialize the quest and check validity
        if not self.data.has_value("initialized"):
            member = empire.Council.Member(Race.All[self._race_id])
            difficulty = quest_difficulty(member, self._tweak, QuestKind.All[self._quest_id])
            result = self._quest.initialize(difficulty)
            self.valid = result != "invalid"
            self.data.initialized = True
        if not self.valid: return
        # create any markers required
        self._quest.create_markers()
        # grab data for later (formatting will use it)
        self._vitals = self._quest.vital_data()
        self.data.bonus = QuestV3.calculate_pp_bonus(self._quest, difficulty)

    def deactivate(self):
        self._quest.destroy_markers()

    def react_to(self, trigger, callback): pass
    def vital_data(self): return self._vitals
    def tweak(self): return self._tweak
    def quest_reward(self):
        if self.data.bonus > 0:
            return ConsQuestReward(self.data.bonus)
        else:
            return None

    def info(self):
        info = CondInfo()
        info.ShortText = self._quest.short_text()
        info.FullDescription = self._quest.full_text()
        return info
    
    def member(self): return game.Council.Member(self.race())
    def race(self): return Race.All[self._race_id]

    def button_contents(self):
        info = self.info()
        # explain the reward(s)
        race_reward = self.race().RewardFor(self.member().SatisfactionLevel + 1)        
        quest_reward = self.quest_reward()
        reward_text = ""
        if race_reward:
            reward_text += race_reward.LDescription 
        if quest_reward:
            if reward_text: reward_text += ", "
            reward_text += self.quest_reward().description()
        if reward_text:
            reward_text = LS("quest.reward", "Reward: ").ToString() + " " + reward_text
        else:
            reward_text = "<alpha=#00>."
        # create the button
        contents = {
            "text": info.FullDescription,
            "sub_text": reward_text,
            "icon": self._race_id,
            "selected_dialog": LS("dialog.quest_selected.%s" % self.race().ID),
            "deselected_dialog": LS("dialog.quest_deselected.%s" % self.race().ID)
        }
        if hasattr(self._quest, "jump_to_location"):
            contents["additional"] = {
                "icon": "icon_eye",
                "tooltip": LS("quests.tooltip.jump_to_location"),
                "callback": self._quest.jump_to_location
            }
        return contents

    def start_quest(self):
        realtime_needed = self._quest.realtime_check()
        quest_cond = empire.Conditions.Activate(QuestV3Realtime if realtime_needed else QuestV3, self._race_id, self._quest_id, self.tweak(), unique_id())
        return quest_cond.PythonObject

class QuestV3(GlobalCondition):
    """Main quest condition class. Can run any quest when provided with the right logic."""
    def __init__(self, race_id, quest_id, tweak, condition_id):
        self._race_id = race_id
        self._quest_id = quest_id
        self._tweak = tweak
        self._condition_id = condition_id
        self._vitals = None
        self._last_interaction = None
    
    def activate(self):
        # reinstantiate quest logic
        quest_kind = QuestKind.All[self._quest_id]
        self._quest = quest_kind.InstantiateLogic()  
        use_instead = self._quest.bind(self)
        while use_instead is not None:
            self._quest = eval(use_instead)
            use_instead = self._quest.bind(self)
        # grab the race status condition
        self._race_status = empire.Conditions.Get(RaceStatus, self._race_id)
        # grab access to some stuff
        self._member = empire.Council.Member(Race.All[self._race_id])
        # do quest initialization if it was never done
        if not self.data.has_value("initialized"):
            difficulty = quest_difficulty(self._member, self._tweak, QuestKind.All[self._quest_id])
            self._quest.initialize(difficulty)
            self.data.initialized = True
            self.data.bonus = QuestV3.calculate_pp_bonus(self._quest, difficulty)
        # refresh once
        self._refresh(reverting=True)
        # markers
        self._quest.create_markers()
        # reactions
        self.react_to(Trigger.ActionTaken, self.after_player_action)
        self.react_to(Trigger.ActionReverted, self.after_undo)
        self.react_to(Trigger.EndScreenReached, self._log_incomplete)
        # register
        empire.Quests.Register(self.host())
        # notify
        self._race_status.TriggerChange()
    
    def deactivate(self):
        self._quest.destroy_markers()
        # register
        empire.Quests.Deregister(self.host())

    @staticmethod
    def calculate_pp_bonus(quest_logic, difficulty):
        multiplier = constants.FloatOrDefault("quests.esteem", 1.0)        
        base_bonus = lerp(5, 15, difficulty * 0.01)
        inherent_mod = 1 + quest_logic.relative_difficulty(difficulty) * 0.16
        bonus = base_bonus * inherent_mod * multiplier
        bonus = round(bonus)
        return bonus

    def vital_data(self):
        return self._vitals

    def quest_reward(self):
        return ConsQuestReward(self.data.bonus)

    def quest_id(self): return self._quest_id
    def race_id(self): return self._race_id
    
    def info(self):
        member = empire.Council.Member(Race.All[self._race_id])
        info = CondInfo()
        info.ShortText = self._quest.short_text()
        info.MediumText = ""
        info.FullDescription = self._quest.full_text() 
        # build tooltip
        info.Tooltip = member
        return info

    def after_player_action(self, data):
        self._last_interaction = "action"
        self._refresh()

    def after_undo(self, data):
        self._last_interaction = "undo"
        self._refresh(reverting = True)

    def trigger_fake_advance(self):
        self._when_quest_advances()

    def _refresh(self, reverting = False):
        old_data = self._vitals
        new_data = self._quest.vital_data()
        if old_data != new_data:
            self._vitals = new_data
            if not reverting and self._quest.check_completion():
                self._when_quest_advances()
            self.signal_change()
            self._race_status.TriggerChange()

    def _when_quest_advances(self):
        # music
        reached_level = self._member.SatisfactionLevel + 1
        qbm = list(game.Conditions.Supporting("quest_based_music_transition"))
        if len(qbm) > 0:
            total_race_level_achieved = sum(m.SatisfactionLevel for m in game.Council.Members) + 1        
            target_music_level = qbm[0].PythonObject.quest_based_music_transition(total_race_level_achieved)
        else:
            target_music_level = music.Level
        # banner
        banner = Messaging.Banner()
        banner.Style = Messaging.BannerStyle.Big
        banner.Sound = None
        banner.MusicTransition = target_music_level
        banner.MainText = LS("quests.mission_complete", None)
        reward = self._member.Race.RewardFor(reached_level)
        effects = reward.LDescription if reward else ""
        messages = [
            self.info().FullDescription.ToString() + "</size>",
            "[s:LevelEffects]" + effects + "[/s]"
        ]
        banner.AdditionalText = "\n".join(m for m in messages if m is not None)
        banner.Portrait = self._member.Race
        banner.Priority = 5
        banner.Delay = 0.838
        empire.Messages.ShowBanner(banner)
        # actual effect
        commands.IssueScriptedConsequence(ConsFinishQuest(self._member, self.host()))

    def _log_incomplete(self, data):
        self.log_quest_completion(incomplete = True)
    
    def log_quest_completion(self, incomplete = False):
        data = {
            "race": self._race_id,
            "quest_text": self._quest.full_text(),
            "esteem": int(self.data.bonus)
        }
        if incomplete: data["incomplete"] = True
        game.GameLog.Log("LogQuestCompletion", data)
        if not incomplete:
            game.Odo.Bump(OdoStat.TasksCompleted, 1)
            game.Odo.Bump(OdoStat.MostTasksCompleted, game.CustomData.GetOr("tasks_completed", 0))

class QuestV3Realtime(QuestV3):
    def realtime_update(self, dt):
        if self._quest.force_realtime_refresh():
            self._vitals = None
            self._refresh()
            return
        else:
            new_data = self._quest.vital_data()
            old_data = self._vitals
            if new_data != old_data:
                self._refresh()

    def blocks_endgame(self):
        if hasattr(self._quest, "blocks_endgame"):
            return self._quest.blocks_endgame()
        else:
            return False
            
class QuestBasedMusic(MusicProgression):
    def __init__(self, every):
        self._every = every
    def _check_for_transition(self, prev): return None
    def quest_based_music_transition(self, quests_completed):
        target_music_level = math.floor(quests_completed / self._every)
        return target_music_level

###########################################################
## Various consequence classes

class ConsQuestsPick:
    def __init__(self, picked_offers):
        self._picked = picked_offers
        self._quests = []

    def apply(self):
        moq = MotherOfQuests.find()
        offers = moq._generate_offers()
        for o in offers:
            o.deactivate()
        if len(self._picked) == 0:
            game.CustomData.Set("quests_declined", True)
        quests = []
        for index in self._picked:
            offer = offers[index]
            quest = offer.start_quest()
            quests.append(quest)
            hooks = moq._hooks
            if hooks and hasattr(hooks, "quest_started"):
                hooks.quest_started(quest)
        self._quests = quests

    def revert(self):
        for quest in self._quests:
            quest.host().Deactivate()
            empire.Conditions.Get(RaceStatus, quest.race_id()).TriggerChange()
        game.CustomData.Clear("quests_declined")
        commands.OnceFullyReverted(self._repop_quests)
    
    def _repop_quests(self):
        moq = MotherOfQuests.find()
        moq.offer_quests(first_time = False)

    def reproduce(self):
        picked = repr(self._picked)
        return "ConsQuestsPick(%s)" % picked

    def undo_description(self): 
        if len(self._quests) > 0:
            return LS("ui.command.pick_quests")
        else:
            return LS("ui.command.decline_quests")

class ConsCheckCouncilTasksIrreversibly:
    def apply(self):
        pass
    def reproduce(self): return "ConsCheckCouncilTasksIrreversibly()"
    def undo_description(self): return LS("ui.command.check_council_tasks")

class ConsQuestReward:
    def __init__(self, amount):
        self._amount = amount

    def apply(self):
        game.Stock.Receive(Resource.PoliticalPower, self._amount)
    def revert(self):
        game.Stock.Return(Resource.PoliticalPower, self._amount)
    def description(self):
        return "[[delta:+%dV]]" % self._amount

class ConsTerminateQuest:
    """Finishes a quest unsuccessfully, just removing it from the quest list. This can sometimes trigger a new quest selection if this was the last one."""
    def __init__(self, member, quest_cond):
        self._member, self._quest_cond, self._quest = member, quest_cond, quest_cond.PythonObject
    def apply(self):
        self._quest_cond.Deactivate()
    def revert(self):
        self._quest_cond.Activate()

class ConsFinishQuest:
    def __init__(self, member, quest_cond):
        self._member, self._quest_cond, self._quest = member, quest_cond, quest_cond.PythonObject

    def apply(self):
        self._member.AdvanceToNextLevel()  # reverts itself    
        quest_reward = self._quest.quest_reward()
        if quest_reward:
            commands.IssueScriptedConsequence(quest_reward) # reverts itself
        empire.CustomData.Inc("tasks_completed")
        self._quest.log_quest_completion()
        self._quest_cond.Deactivate()
        empire.Conditions.Get(RaceStatus, self._member.Race.ID).TriggerChange()
        commands.IssueScriptedConsequence(ConsFinishQuestTrigger(self._quest_cond))
    
    def revert(self):
        self._quest_cond.Activate()
        empire.CustomData.Dec("tasks_completed")
        empire.Conditions.Get(RaceStatus, self._member.Race.ID).TriggerChange()

class ConsFinishQuestTrigger:
    def __init__(self, quest_cond):
        self._cond = quest_cond
    def apply(self):
        game.Triggers.ActivateFromScript(Trigger.TaskCompleted, {"condition": self._cond, "quest": self._cond.PythonObject})
    def revert(self):
        pass

###########################################################
## Specific quest rules

class QuestLogicV3:
    def initialize(self, stage): raise Exception("Has to be overriden in quest logic subclasses.")
    def check_completion(self): raise Exception("Has to be overriden in quest logic subclasses.")
    def short_text(self): raise Exception("Has to be overriden in quest logic subclasses.")
    def full_text(self): raise Exception("Has to be overriden in quest logic subclasses.")
    def text_key_full(self): return "quests.%s.full" % self._id
    def text_data(self): return ()  
    def relative_difficulty(self, stage): return 0
    def tweak_range(self): return (-10, 10)
    def create_markers(self): pass
    def destroy_markers(self): pass
    def realtime_check(self): return False
    def force_realtime_refresh(self): return False

class QLImproveNumber(QuestLogicV3):
    def bind(self, quest_cond):
        self._cond = quest_cond
        self._id = quest_cond._quest_id
        self.data = quest_cond.data
    
    def initialize(self, stage):        
        self.data.base = self.current()
        req = self.requirements(stage)
        if req <= 0: return "invalid"
        self.data.target = self.data.base + req

    def vital_data(self): return self.progress()

    def progress(self):
        current = self.current()
        return current - self.data.base, self.data.target - self.data.base

    def short_text(self):
        n, out_of = self._cond.vital_data()
        return LS("quests.progress", "{1}/{2}{3}", n, out_of, self.icon(), *self.text_data())  

    def full_text(self):
        n, out_of = self._cond.vital_data()
        return LS(self.text_key_full(), None, n, out_of, *self.text_data())

    def check_completion(self):
        n, out_of = self._cond.vital_data()
        return n >= out_of

class QLCountEvents(QuestLogicV3):
    def bind(self, quest_cond):
        self._cond = quest_cond
        self._id = quest_cond._quest_id
        self.data = quest_cond.data
        # call concrete logic that will make us react to events
        self.bind_events(quest_cond)

    def initialize(self, stage):
        self.data.count = 0
        req = self.requirements(stage)
        if req <= 0: return "invalid"
        self.data.target = req

    def increase_count(self):
        "Intended to be called from the concrete quest logic class when the 'trigger' event is detected."
        ConsUpdateNodeData().inc(self._cond.host(), "count").when_done_or_reverted(self._cond.signal_change).issue()

    def vital_data(self): return (self.data.count, self.data.target)
    def short_text(self):
        n, out_of = self._cond.vital_data()
        return LS("quests.progress", "{1}/{2}{3}", n, out_of, self.icon(), *self.text_data())
    def full_text(self):
        n, out_of = self._cond.vital_data()
        return LS(self.text_key_full(), None, n, out_of, *self.text_data())
    def check_completion(self):
        n, out_of = self._cond.vital_data()
        return n >= out_of


class QLSuccessful(QLImproveNumber):
    def __init__(self, base_requirement):
        self._req = base_requirement
    def initialize(self, stage):
        self.data.req_level = 3 if stage > 50 else 2
        QLImproveNumber.initialize(self, stage)
    def current(self):
        return sum(1 for p in every(Planet) if p.Level >= self.data.req_level and self.qualifier(p))
    def requirements(self, stage):
        return round(1 + (stage % 60 / 60.0))
    def tweak_range(self): return (0, 1)

class QLSuccessfulProducing(QLSuccessful):
    def __init__(self, req, resource_id):
        self._product = Resource.All[resource_id]
        QLSuccessful.__init__(self, req)        
    def qualifier(self, planet):
        return planet.ActuallyProduces(self._product)
    def text_key_full(self): return "quests.successful_producing.full"
    def text_data(self): return (self._product.ID, self.data.req_level)
    def icon(self):
        return ":lv%d::%s:" % (self.data.req_level, self._product.ID)
    def relative_difficulty(self, stage): return +1

class QLSuccessfulWithType(QLSuccessful):
    def __init__(self, req, node_type):
        self._type = node_type
        QLSuccessful.__init__(self, req)     
    def initialize(self, stage):
        QLSuccessful.initialize(self, stage)   
        required_planets = self.requirements(stage)
        available = sum(1 for p in every(Planet) if p.NodeType == self._type and p.Level < self.data.req_level)
        if available < required_planets: return "invalid"
    def qualifier(self, planet):
        return planet.NodeType == self._type
    def text_key_full(self): return "quests.successful_with_type.full"
    def text_data(self): return (self._type, self.data.req_level)
    def icon(self):
         return ":lv%d:" % self.data.req_level
    def relative_difficulty(self, stage): return +1

class QLProsperousProducing(QLSuccessful):
    def __init__(self, req, resource_id):
        self._product = Resource.All[resource_id]
        QLSuccessful.__init__(self, req)     
    def initialize(self, stage):
        QLSuccessful.initialize(self, stage)
        self.data.req_level = 3
    def qualifier(self, planet):
        return planet.ActuallyProduces(self._product)
    def text_key_full(self): return "quests.successful_producing.full"
    def text_data(self): return (self._product.ID, self.data.req_level)
    def icon(self):
        return ":lv%d::%s:" % (self.data.req_level, self._product.ID)
    def relative_difficulty(self, stage): return +1

class QLProsperousWithTypeForced(QLSuccessful):
    def __init__(self, req, node_type):
        self._type = node_type
        QLSuccessful.__init__(self, req)     
    def initialize(self, stage):
        QLSuccessful.initialize(self, stage)
        self.data.req_level = 3  
    def requirements(self, stage):
        return max(1, int(stage / 50))
    def qualifier(self, planet):
        return planet.NodeType == self._type
    def text_key_full(self): return "quests.successful_with_type.full"
    def text_data(self): return (self._type, self.data.req_level)
    def icon(self):
         return ":lv%d:" % self.data.req_level
    def relative_difficulty(self, stage): return +1

class QLProduction(QLImproveNumber):
    def __init__(self, req, resource_id):
        self._req = req
        self._product = Resource.All[resource_id]
        QLImproveNumber.__init__(self)
    def current(self):
        return empire.Nodes.TotalProduction(self._product)
    def requirements(self, stage):
        return quest_interpolate(self._req, self._req * 3, stage)
    def full_text(self):
        if self._product.ID == "P": return QLImproveNumber.full_text(self)
        n, out_of = self._cond.vital_data()
        return LS("quests.production.full", None, n, out_of, self._product.ID) 
    def icon(self):
        return ":%s:" % self._product.ID
    def relative_difficulty(self, stage): return 0
    def tweak_range(self): return (0, 15)

class QLDiscoverPlanetsCE(QLCountEvents):
    def __init__(self, req, forced=False):
        self._req = req
        self._forced = forced
        QLCountEvents.__init__(self)

    def bind(self, quest_cond):
        # conditionally load the old version of this quest
        if not isinstance(quest_cond, QuestOffer) and quest_cond.data.has_value("target") and not quest_cond.data.has_value("count"):
            return "QLDiscoverPlanets(%d)" % self._req
        return QLCountEvents.bind(self, quest_cond)

    def initialize(self, stage):
        if stage > 60 and not self._forced: return "invalid"
        QLCountEvents.initialize(self, stage)

    def bind_events(self, cond):
        cond.react_to(Trigger.AfterNodeDiscovered, self.node_discovered)

    def node_discovered(self, data):
        node = data["node"]
        if node.NodeType.startswith("planet."):
            self.increase_count()

    def requirements(self, stage):
        return quest_interpolate(self._req, self._req * 2.5, stage)
    def icon(self):
        return ":planet:"
    def relative_difficulty(self, stage): return -1.5
    def tweak_range(self): return (-15, 15)


class QLSpecificLab(QLImproveNumber):
    def initialize(self, stage):
        # make a list of resources which don't have labs yet
        resources = [Resource.All[r] for r in ["L", "W", "O", "T", "B"]]
        labs = list(empire.Nodes.WithType("structure.lab"))
        lab_resources = [lab_study_subject(l) for l in labs]
        for lr in lab_resources:
            if lr in resources: resources.remove(lr)
        # pick the "worst" one
        if len(resources) == 0:
            return "invalid"
        resources.sort(key=lambda r: empire.Nodes.TotalProduction(r))
        worst_resource = resources[0]
        self.data.resource_id = worst_resource.ID
        # determine how much science needed
        self.data.science_req = quest_interpolate(2.5, 6.7, stage)
        # rest of initialization
        QLImproveNumber.initialize(self, stage)
    def text_data(self): return (":%s:" % self.data.resource_id, self.data.science_req)
    def current(self):
        labs = list(empire.Nodes.WithType("structure.lab"))
        resource = Resource.All[self.data.resource_id]
        matching_labs = [l for l in labs if lab_study_subject(l) == resource]
        enough_science_labs = [l for l in matching_labs if l.AmountProduced(Resource.Science) >= self.data.science_req]
        return len(enough_science_labs)                
    def requirements(self, stage):
        return 1
    def icon(self):
        return " labs"
    def relative_difficulty(self, stage): return +2

class QLPlanetsWithImports(QLImproveNumber):
    def initialize(self, stage):
        self.data.imports = 3
        QLImproveNumber.initialize(self, stage)
    def current(self):
        return sum(1 for p in every(Planet) if p.ImportCount >= self.data.imports)
    def requirements(self, stage):
        return quest_interpolate(1, 5, stage)
    def text_data(self): return (self.data.imports,)
    def icon(self): return ":planet:"
    def relative_difficulty(self, stage): return 0

class QLPlanetsWithNonPeopleProducts(QLImproveNumber):
    def initialize(self, stage):
        self.data.products = 4
        QLImproveNumber.initialize(self, stage)
    def current(self):
        threshold = self.data.products
        return sum(1 for p in every(Planet) if self.product_count(p) >= threshold)
    @staticmethod
    def product_count(node):
        return node.Products.Count - node.AmountProduced(Resource.People)
    def requirements(self, stage):
        return quest_interpolate(1, 5, stage)
    def text_data(self): return (self.data.products,)
    def icon(self): return ":planet:"
    def relative_difficulty(self, stage): return +1

class QLInventedTechs(QLImproveNumber):
    def initialize(self, stage):
        required = self.requirements(stage)
        currently_unlocked = sum(1 for t in empire.Technology.AllUnlocked)
        if currently_unlocked < required:
            return "invalid"
        QLImproveNumber.initialize(self, stage)
    def current(self):
        return sum(1 for t in empire.Technology.AllInvented)
    def requirements(self, stage):
        return quest_interpolate(1, 3, stage)
    def icon(self): return ":tech:"
    def relative_difficulty(self, stage): return +1

class QLFixUnhappy(QLImproveNumber):
    def initialize(self, stage):
        unhappy = -self.current()
        if unhappy < self.requirements(stage):
            return "invalid"
        QLImproveNumber.initialize(self, stage)
    def current(self):
        return -game.Nodes.CountPlanetsWithLevel(0)
    def requirements(self, stage):
        return quest_interpolate(1, 4, stage)
    def icon(self): return ":H::planet:"
    def relative_difficulty(self, stage): return +1

class QLTwoWayTrades(QLImproveNumber):
    def current(self): return sum(self._two_way_trades(planet) for planet in every(Planet)) / 2
    def requirements(self, stage):
        return quest_interpolate(2, 8, stage)
    def icon(self): return ""
    def relative_difficulty(self, stage): return -1

    @staticmethod
    def _two_way_trades(node):
        export_destinations = set(er.Consumer for er in node.ExportRoutes if er.Consumer.NodeType.startswith("planet."))
        import_sources = set(ir.Producer for ir in node.ImportRoutes if ir.Consumer.NodeType.startswith("planet."))
        return len(export_destinations.intersection(import_sources))

class QLTotalScience(QLImproveNumber):
    def current(self): return game.Stock.Income(Resource.Science)
    def requirements(self, stage):
        return quest_interpolate(3, 8, stage)
    def icon(self): return ":S:"
    def relative_difficulty(self, stage): return 0

class QLProsperousPlanets(QLImproveNumber):
    def initialize(self, stage):
        required = self.requirements(stage)
        if required < 1: 
            return "invalid"
        QLImproveNumber.initialize(self, stage)
    def current(self): return sum(1 for p in every(Planet) if p.Level >= 3)
    def requirements(self, stage):
        return quest_interpolate(-0.5, 4, stage)
    def icon(self): return ":lv3:"
    def relative_difficulty(self, stage): return +1

class QLProjects(QLImproveNumber):
    def initialize(self, stage):
        projects_unlocked = sum(1 for p in unlocks.GlobalUnlocks("project"))
        if projects_unlocked == 0: return "invalid"
        QLImproveNumber.initialize(self, stage)

    def current(self): return sum(1 for p in every(Planet) if p.HasAnyProject)
    def requirements(self, stage):
        return quest_interpolate(1, 7, stage)
    def icon(self): return ":project:"
    def relative_difficulty(self, stage): return -1

class QLEnergy(QLImproveNumber):
    def __init__(self, forced = False):
        self._forced = forced

    def initialize(self, stage):
        if not self._forced:
            if len(list(game.Nodes.Producing(Resource.All["E"]))) == 0: return "invalid"
            if stage <= 0: return "invalid"
        QLImproveNumber.initialize(self, stage)
    
    def current(self): return game.Nodes.TotalProduction(Resource.All["E"])
    def requirements(self, stage):
        return quest_interpolate(1, 7, stage)
    def icon(self): return ":E:"
    def relative_difficulty(self, stage): return 1

class QLColonizedPlanets(QLImproveNumber):
    def current(self): return game.Nodes.CountPlanetsWithLevelOrHigher(0)
    def requirements(self, stage):
        return quest_interpolate(4, 10, stage)
    def icon(self): return ":planet:"
    def relative_difficulty(self, stage): return quest_interpolate(-1, 2, stage)

###############################################################
# Deliver N different resources (new trade routes)

class QLDeliverDifferentResources(QuestLogicV3):
    def bind(self, cond):
        self._cond = cond
        self.data = cond.data
        self._cond.react_to(Trigger.TradeRouteEstablished, self.on_new_route)

    def initialize(self, stage):
        self.data.resources = []
        self.data.required = self.requirements(stage)
    
    def requirements(self, stage):
        return min(quest_interpolate(6, 8, stage), 8)
    def tweak_range(self): return (0, 1)

    def vital_data(self): return self.progress()
    def progress(self):
        return (len(self.data.resources), self.data.required, self.data.resources)

    def short_text(self):
        current, out_of, _ = self.progress()
        return "%d/%d" % (current, out_of)
    
    def full_text(self):
        current, out_of, used_resources = self.progress()
        used_text = "".join(":%s:" % r for r in used_resources)
        subkey = "used" if (current > 0 and current < out_of) else "full"
        return LS("quests.deliver_different_resources.%s" % subkey, None, current, out_of, used_text)
    
    def check_completion(self):
        current, out_of, _ = self.progress()
        return current >= out_of

    def on_new_route(self, data):
        resource = data["resource"].ID
        if resource not in self.data.resources:
            update = ConsUpdateNodeData()
            update.add(self._cond.host(), "resources", lambda r: r + [resource])
            update.issue()

#########################################################
# Colonize N different planet types

class QLColonizeDifferentPlanets(QuestLogicV3):
    def bind(self, cond):
        self._cond = cond
        self.data = cond.data
        self._cond.react_to(Trigger.PlanetColonized, self.on_colonized)

    def initialize(self, stage):
        self.data.kinds = []
        self.data.required = self.requirements(stage)
    
    def requirements(self, stage):
        return min(quest_interpolate(6, 10, stage), 10)

    def tweak_range(self): return (0, 1)

    def vital_data(self): return self.progress()
    def progress(self):
        return (len(self.data.kinds), self.data.required, self.data.kinds)

    def short_text(self):
        current, out_of, _ = self.progress()
        return "%d/%d" % (current, out_of)
    
    def full_text(self):
        current, out_of, used_kinds = self.progress()
        used_text = ", ".join(PlanetKind.All[kind_id].LName.lower() for kind_id in used_kinds)
        subkey = "used" if (current > 0 and current < out_of) else "full"
        return LS("quests.colonize_different_planets.%s" % subkey, None, current, out_of, used_text)
    
    def check_completion(self):
        current, out_of, _ = self.progress()
        return current >= out_of

    def on_colonized(self, data):
        if not data["node"].NodeType.startswith("planet."): return
        kind = data["node"].Kind.ID
        if kind not in self.data.kinds:
            update = ConsUpdateNodeData()
            update.add(self._cond.host(), "kinds", lambda k: k + [kind])
            update.issue()

####################################################
# Discover a marked area

class QLExploreArea(QuestLogicV3):
    def bind(self, cond):
        self._cond = cond
        self.data = cond.data
    
    def initialize(self, stage):
        attempts = 0
        location = None
        while attempts < 5:
            location = self.determine_location(stage, attempts)
            if location is not None: break
            attempts += 1
        if location is None:
            return "invalid"
        self.data.location = location

    def determine_location(self, stage, retry):
        # determine distance based on difficulty
        distance = min(180, quest_interpolate(70, 230, stage)) * 0.01
        # determine angle
        total_race_level = sum(m.SatisfactionLevel for m in empire.Council.Members)
        rng = Randomness.SeededRNG(game.GameSeed, total_race_level, "QLExploreArea", retry)
        angle = Randomness.Float(rng, 0.0, math.pi * 2)
        angle = Randomness.Float(rng, 0.0, math.pi * 2)
        direction = Vector2(math.cos(angle), math.sin(angle))
        # find an "anchor" planet
        try:
            candidates = list(p for p in every(Planet) if p.Level >= 0)
            candidates += list(game.Nodes.WithType("wormhole"))
            node = max(candidates, key=lambda p: Vector2.Dot(direction, p.Position))
        except ValueError:
            return None
        # move us away from that node
        target_location = node.Position + f(node.DiscoveryRadius * (1 + distance)) * direction
        # is it reachable?
        if not self.verify_location_viability(node, target_location):
            return None
        return target_location

    def verify_location_viability(self, node, target_location):
        # not in FOW?
        if not game.FOW.PresentAt(target_location): return False
        # check if reachable via a chain of planets
        slipway_range = constants.Distance("slipway.range") * 0.95
        current = node
        last_distance = (current.Position - target_location).magnitude
        while True:
            # are we close enough?
            if last_distance < slipway_range: return True
            # find candidates for moving closer to target
            candidates = [n for n in game.Nodes.Within(current.Position, slipway_range) if n.NodeType.startswith("planet.")]
            candidates += (p for p in game.Nodes.PotentialsWithin(current.Position, slipway_range) if p.Signal.Contents.startswith("planet."))
            candidates += (s for s in game.Map.SignalsWithin(current.Position, slipway_range) if s.Contents.startswith("planet."))
            if len(candidates) == 0:
                return False
            best = min(candidates, key=lambda c: (c.Position - target_location).sqrMagnitude)
            best_distance = (best.Position - target_location).magnitude
            if best_distance >= last_distance - 0.01:
                return False # can't improve anymore
            current = best
            last_distance = best_distance

    def vital_data(self): return (self.check_completion(),)
    def short_text(self): return "0/1:res_?:"
    def full_text(self): return LS("quests.explore_area.full")

    def realtime_check(self): return True

    def jump_to_location(self):
        quest_focus({
            "target_position": self.data.location,
            "minimum_zoom": 10,            
        })

    def blocks_endgame(self):
        return not game.FOW.IsUpToDate

    def force_realtime_refresh(self): return self.check_completion()
    def check_completion(self):
        return game.FOW.IsUpToDate and not game.FOW.PresentAt(self.data.location)

    def create_markers(self):
        self._marker = world.Add(AreaMarker(self.data.location, 1, "quest_target_area"))
    
    def destroy_markers(self):
        if self._marker:
            self._marker.Discard()

    def relative_difficulty(self, stage): return -1
