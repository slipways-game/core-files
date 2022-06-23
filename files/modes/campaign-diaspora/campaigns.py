class MainMission(GlobalCondition):
    """Keeps track of the main goal in a campaign mission."""
    def __init__(self, mission_id, goals):
        self._mission_id = mission_id
        self._goals = goals
        self._goal_state = [None for g in goals]
        GlobalCondition.__init__(self)

    def activate(self):
        game.CustomData.Set("mission_id", self._mission_id)
        self.react_to(Trigger.ActionTaken, self.after_action)
        self.react_to(Trigger.NewTurn, self.after_action)
        self.react_to(Trigger.ActionReverted, self.after_undo)
        self.react_to(Trigger.ScenarioComplete, self._tag_scenario_end, priority=0)
        self.react_to(Trigger.ScenarioSetup, self.setup_conditions)
        self.react_to(Trigger.ScenarioSetup, self.setup_secondary_goals)
        self.react_to(Trigger.ScenarioSetup, self.setup_scoring)
        self.react_to(Trigger.ScenarioSetup, self.additional_setup)
        self.react_to(Trigger.GameLoaded, self.setup_scoring)
        self.react_to(Trigger.GameLoaded, self._show_briefing)
        self._refresh()

    @staticmethod
    def find_mission_condition():
        return game.Conditions.Supporting("briefing_contents")[0].PythonObject

    def setup_scoring(self, data):
        if not hasattr(self, "scoring_rules"): return
        for rule in self.scoring_rules():
            game.Scoring.AddRule(rule)

    def setup_conditions(self, data):
        if not hasattr(self, "conditions"): return
        for cnd in self.conditions():
            if isinstance(cnd, tuple):
                game.Conditions.Activate(*cnd)
            else:
                game.Conditions.Activate(cnd)

    def setup_secondary_goals(self, data):
        if not hasattr(self, "secondary_goals"): return
        for cnd in self.secondary_goals():
            game.Conditions.Activate(*cnd)

    def additional_setup(self, data):
        if hasattr(self, "do_additional_setup"): self.do_additional_setup()
        game.GameLog.Log("LogMissionStarted", {
            "id": self._mission_id,
            "title": self.title()
        })

    def scenario_group(self): return None

    def after_action(self, data):
        self._refresh()

    def after_undo(self, data):
        self._refresh(reverting = True)

    def info(self):
        finished = self.finished()
        ci = CondInfo()
        ci.Icon = "icon_empire_completed" if finished else "icon_empire"
        ci.Important = True      
        ci.Priority = 500  
        header = LS("mission.header", None, self.title())
        short = None
        if not finished:
            goal_info = ""
            for index, goal in enumerate(self._goals):
                if self.goal_active(index):
                    desc = goal.description().ToString()
                    if hasattr(goal, "short"):
                        short_text = goal.short() 
                        short_text = RichText.StripTags(short_text)
                        short_text = short_text.replace("\n", " ")
                        desc += " [s:TooltipLightComment](%s)[/s]" % short_text
                        if short is None:
                            short = goal.short()                    
                    goal_info += "\n" + Localization.MakeSentence(desc)
            goal_desc = L("mission.goals", None, "").strip()
            goal_desc = styled(goal_desc, "TooltipLightBolded")
            goal_desc += " " + goal_info
        else:
            goal_desc = Localization.MakeSentence(L("mission.completed"))
            goal_desc = styled(goal_desc, "TooltipLightBolded")
        ci.ShortText = short
        ci.FullDescription = RichText.ParagraphSpacer().join([
            styled(header, "TooltipHeader"), 
            styled(goal_desc, "TooltipLight")
        ])
        ci.Tooltip = ci.FullDescription
        ci.WhenClicked = self._show_briefing
        return ci

    def title(self): return LS("mission.%s" % self._mission_id)
    def briefing_text(self): return LS("mission.%s.briefing" % self._mission_id)
    def completion_text(self): return LS("mission.%s.conclusion" % self._mission_id)

    def goal_finished(self, index):
        return self.host().CustomData.GetOr("goal_complete_%d" % index, False)

    def goal_active(self, index):
        if self.goal_finished(index): return False
        goal = self._goals[index]
        if hasattr(goal, "requires"):
            return all(self.goal_finished(index) for index in goal.requires())
        else:
            return True

    def finished(self):
        return all(self.goal_finished(i) for i in range(len(self._goals)))

    def finished_on(self):
        return self.data.get_or("mission_complete_on_turn", None)

    def menu_flow_setup(self):
        return True
    
    def _refresh(self, reverting = False):
        # prevent any checks from happening when this class is used in menu screens
        # they might throw exceptions since the game world is not here
        if game.GameContext != GameContext.PlayingScenario:
            return
        # check avtive goals in turn
        changed = False
        for index, goal in enumerate(self._goals):
            if not self.goal_active(index): continue
            new_state = goal.state() if hasattr(goal, "state") else None
            if self._goal_state[index] != new_state:
                self._goal_state[index] = new_state
                changed = True
            if goal.check_completion() and not reverting:
                if hasattr(goal, "when_completed"): goal.when_completed()
                self._complete_goal(index, goal)
                changed = True
        # let everybody know
        if changed:
            self.signal_change()
        return changed

    def briefing_contents(self):
        yield {"type": "briefing_text", "text": self.briefing_text()}
        for index, goal in enumerate(self._goals):
            complete = False
            comment = None
            if game.GameContext == GameContext.PlayingScenario:
                complete = self.goal_finished(index)
                comment = goal.short() if hasattr(goal, "short") else None
                if comment:
                    comment = RichText.StripTags(comment)
                    comment = comment.Replace("\n", " ")
            yield {"type": "goal", "text": goal.description(), "complete": complete, "comment": comment}
        time_limit = [c for c in self.conditions() if isinstance(c, tuple) and c[0] == WinMissionOnTime]
        for t in time_limit:
            yield {"type": "goal", "text": LS("campaign.time_limit.desc", None, t[2]), "time_limit": True}
        things_to_explain = self.things_to_explain() if hasattr(self, "things_to_explain") else ()
        for data in things_to_explain:
            kind, id = data[0], data[1]
            args = data[2:] if len(data) >= 3 else []
            yield {"type": "explain", "kind": kind, "id": id, "desc_args": args}
        if hasattr(self, "scoring_rules"):
            for scoring in self.scoring_rules():
                if hasattr(scoring, "excluded_from_briefing"):
                    if scoring.excluded_from_briefing():
                        continue
                yield {"type": "scoring", "text": scoring.briefing_description() if hasattr(scoring, "briefing_description") else scoring.description()}
    
    def _show_briefing(self, data = None):
        contents = list(self.briefing_contents())
        triggered = data is not None
        game.Dialogs.BriefingWindow(contents, triggered)

    def _complete_goal(self, index, goal):        
        how_many_remain = sum(1 for i in range(len(self._goals)) if not self.goal_finished(i))
        cons = ConsUpdateNodeData(trigger_changes=True)
        cons.add(self.host(), "goal_complete_%d" % index, True)
        if how_many_remain == 1:
            # last goal, store date
            cons.add(self.host(), "mission_complete_on_turn", game.Time.NormalizedTurn)
            cons.add(game, "mission_complete", True)
        cons.when_done(lambda: self._complete_done(index, goal))
        commands.IssueScriptedConsequence(cons)
        game.GameLog.Log("LogGoalCompletion", {
            "goal_text": goal.description()
        })

    def _complete_done(self, index, goal):
        # banner
        banner = Messaging.Banner()
        banner.Style = Messaging.BannerStyle.Big
        banner.Sound = None
        banner.MusicTransition = music.Level
        mbm = list(game.Conditions.Supporting("mission_based_music_transition"))
        if len(mbm) > 0:
            mbm = mbm[0].PythonObject
            # only transition the music if we're not going to transition to the end screen anyway
            if not game.WinningLosing.IsEndingTripped or game.WinningLosing.IsScenarioComplete:
                banner.MusicTransition = mbm.mission_based_music_transition(index, goal)
        banner.MainText = self.title()
        description = goal.description().ToString().replace("*", "")
        messages = [
            "<s><alpha=#00>I<alpha=#ff>%s<alpha=#00>I<alpha=#ff></s>" % description
        ]
        banner.AdditionalText = "\n".join(m for m in messages if m is not None)
        banner.Portrait = None
        banner.Priority = 10
        banner.Delay = 0.838
        empire.Messages.ShowBanner(banner)

    def _tag_scenario_end(self, data):
        # add to the dictionary so that campaign storage sees this
        data["scenario_id"] = self.scenario_id()
        data["scenario_group"] = self.scenario_group()
    
    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

##########################################################################
# Delivering story

class StoryBits(GlobalCondition):
    def __init__(self, popup_list):
        self._popups = [(i, p) for i, p in enumerate(popup_list)]

    def activate(self):        
        # remove already seen popups
        seen = self.data.get_or("seen", [])
        seen = set(seen)
        self._popups = [p for p in self._popups if p[0] not in seen]
        # react
        self.react_to(Trigger.ActionTaken, self.check_for_popups)
        self.react_to(Trigger.TutorialCompleted, self.check_for_popups)

    def check_for_popups(self, data):
        if game.Dialogs.IsATutorialOpen(): return
        command = data["command_string"] if "command_string" in data else ""
        for index, p in self._popups:
            # check conditions (in order of 'expensiveness')
            if not command.startswith(p.command_prefix()): continue
            if not p.condition(): continue
            # all conditions match, pop the tutorial!
            p.start_sequence()
            # ensure we won't see it again this run
            seen = self.data.get_or("seen", [])
            seen.append(index)
            self.data.seen = seen
            self._popups = [p for p in self._popups if p[0] != index]
            return

class StoryBit(TutorialStep):
    def __init__(self, id, characters, *text_args):
        TutorialStep.__init__(self)
        self._id, self._characters = id, characters
        self._text_args = text_args or []
        self._last = None
    
    def id(self): return self._id
    def manual_advance(self): return True
    def ls_text(self): return LS(self._id, None, *self._text_args)
    def character(self):
        return self._characters[0]

#########################################################################

class WinMissionOnTime(WinTimeLimit):
    def __init__(self, mission_expr, turns):
        self._mission_expr = mission_expr
        WinTimeLimit.__init__(self, turns)

    def turns(self): return self._turns

    def _mission(self):
        return game.Conditions.Get(self._mission_expr).PythonObject
    
    def _win(self):
        mission = self._mission()
        empire.WinningLosing.EndScenario({
            "outcome": "win",
            "shown_elements": ["undo", "screenshot", "scoring_summary", "picks", "breakdown", "end_banner"],
            "summary_items": [L("mission.completed")],
            "banner_contents": mission.completion_text(),
            "heading": mission.title()
        })

class OneLastAction:
    """Helper to easily implement grant_time_extension() for missions that allows a single extra action, conditionally."""
    def __init__(self, ignored_actions):
        self._ignored = ignored_actions
        self._saved_index = None

    def last_explicit_action_index(self):
        cmds = commands.RecordedCommands
        index = len(cmds) - 1
        while index >= 0:
            cmd = cmds[index]
            if not cmd.IsImplicit:
                cmd_str = cmd.CommandString
                ignored = any(cmd_str.startswith(ia) for ia in self._ignored)
                if not ignored:
                    return index
            index -= 1
        # if we got here, we return -1 since there are no explicit commands yet
        return index

    def still_in_grace_period(self):
        cmd_index = self.last_explicit_action_index()
        if self._saved_index is None or cmd_index <= self._saved_index:
            if self._saved_index is None:
                ConsSetProp(self, "_saved_index", cmd_index).issue()
            return True
        return False

#########################################################################

class CampaignStats(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_tabs)
        self.react_to(Trigger.GameLoaded, self.setup_tabs)

    def setup_tabs(self, _):
        game.Stats.Add(StatSources.ScoringTab(0))
        game.Stats.Add(StatSources.DomainTab(5))

class SecondaryGoal(GlobalCondition):
    def __init__(self, order):
        self._order = order

    def secondary_goal_info(self):
        return {
            "order": self._order,
            "description": self.desc(),
            "completed": self._check_goal()
        }

class SGHappinessAbove(SecondaryGoal):
    def __init__(self, pri, above):
        SecondaryGoal.__init__(self, pri)
        self._above = above
    def desc(self): return LS("goal.achieve_happiness", None, self._above)
    def _check_goal(self): return game.Stock.Happiness >= self._above

class SGCouncilTasks(SecondaryGoal):
    def __init__(self, pri, above):
        SecondaryGoal.__init__(self, pri)
        self._above = above
    def desc(self): return LS("goal.complete_council", None, self._above)
    def _check_goal(self): 
        total_completed = sum(m.SatisfactionLevel for m in game.Council.Members)
        return total_completed >= self._above

class SGFinishBefore(SecondaryGoal):
    def __init__(self, pri, turn):
        SecondaryGoal.__init__(self, pri)
        self._turn = turn
    def desc(self): 
        year = game.Time.NormalizedTurnToYear(self._turn)
        return LS("goal.finish_before", None, year)
    def _check_goal(self): 
        return False # NOT IMPLEMENTED

###############################################################

class CampaignScoring(GlobalCondition):
    def __init__(self, *exclusions):
        self._exclusions = exclusions

    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_scoring)
        self.react_to(Trigger.GameLoaded, self.setup_scoring)
    
    def setup_scoring(self, _ = None):
        for scoring_rule in self.scoring_rules():
            if scoring_rule:
                empire.Scoring.AddRule(scoring_rule)
    
    ### Internals

    def scoring_rules(self):
        scores = [
            ScoringCampaignPlanets([0, 1, 3, 5, 7, 9]) if "no_planets" not in self._exclusions else None,          
            ScoringCampaignTasks([0, 2, 3, 4, 5, 6]) if "no_tasks" not in self._exclusions else None,
            ScoringCampaignHappiness([0, 90, 100, 110, 125, 140]) if "no_happiness" not in self._exclusions else None
        ]
        return scores

class ScoringFiveRanks(Scoring):
    OPS = {
        ">=": (lambda x, y: x >= y),
        "<=": (lambda x, y: x <= y)
    }
    def kind(self): return ScoreKind.Addition
    def title(self): return LS(self.id())
    def description(self): 
        explanation = L(self.id() + ".desc", None, *self.desc_args())
        rank_texts = [self.rank_text(l) for r, l in enumerate(self.rank_limits()) if r != 0]
        rank = self.rank(self.base_number())
        for i in range(1, len(rank_texts)):
            if rank_texts[i-1] == rank_texts[i]:
                del rank_texts[i]
                if rank >= i: rank -= 1
        if rank > 0:
            rank_texts[rank-1] = "[s:TooltipLightBolded]%s[/s]" % rank_texts[rank-1]
        rank_string = "/".join(rank_texts)
        rank_string += self.post_rank_text()
        explanation = Localization.MakeSentence(explanation)
        explanation += RichText.ParagraphSpacer(f(0.2))
        explanation += RichText.Aligned(rank_string, "center")
        return explanation
    def desc_args(self): return ()
    
    def briefing_description(self):
        explanation = L(self.id() + ".desc", None, *self.desc_args())
        return Localization.MakeSentence(explanation)

    def rank_op(self): return ">="
    def rank_text(self, limit): return str(limit)
    def post_rank_text(self): return ""

    def rank(self, number):
        if number is None: return 0
        limits = self.rank_limits()
        op = self.OPS[self.rank_op()]
        for rank, limit in enumerate(limits):
            if not op(number, limit):
                return rank - 1
        return len(limits) - 1

    def rank_count(self): return 5

    def calculate_score(self, fraction):
        number = self.base_number()
        score = self.rank(number)
        return Score.Add(self.number_text(number, score), score, self.rank_count())

class ScoringCampaignPlanets(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.campaign.prosperity"
    def current(self):
        per_lv = {}
        for p in every(Planet):
            if p.Level >= 3:
                per_lv[p.Level] = per_lv.get(p.Level, 0) + 1
        points = 0
        texts = []
        for lv in range(3, 5):
            planets_of_this_level = per_lv.get(lv, 0)
            value = planets_of_this_level if lv == 3 else planets_of_this_level * 2
            points += value
            if planets_of_this_level > 0:
                texts.append("%d:lv%d:" % (planets_of_this_level, lv))
        desc = " + ".join(texts)
        if desc == "":
            desc = "0:lv3:"
        return points, desc
    def base_number(self):
        return self.current()[0]
    def post_rank_text(self): return ":lv3:"
    def rank_limits(self): return self._limits
    def number_text(self, number, rank): return self.current()[1]

class ScoringCampaignTasks(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.campaign.council_tasks"
    def base_number(self):
        return sum(m.SatisfactionLevel for m in game.Council.Members)
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def number_text(self, number, rank): return Localization.Plural(number, "unit.task")
    def excluded_from_briefing(self): return True

class ScoringCampaignHappiness(ScoringFiveRanks):
    def __init__(self, limits):
        self._limits = limits
    def id(self): return "scoring.campaign.happiness"
    def base_number(self):
        return game.Stock.Happiness
    def rank_limits(self): return self._limits
    def post_rank_text(self): return "%:H:"
    def number_text(self, number, rank): return "%d%%:H:" % number

class ScoringCampaignTime(ScoringFiveRanks):
    def __init__(self, main_mission, limits):
        self._mission = main_mission
        self._limits = limits
    def id(self): return "scoring.campaign.time"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return None
        return self._mission.finished_on()
    def rank_op(self): return "<="
    def rank_limits(self): return self._limits
    def rank_text(self, number): return str(game.Time.NormalizedTurnToYear(number))
    def number_text(self, number, rank): return str(game.Time.NormalizedTurnToYear(number)) if number is not None else "-"
    def tags(self): return ["mission"]
