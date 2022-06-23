#########################################################
# Map generation: add the computer structure

class ComputerMapgen(GlobalCondition):
    def activate(self):
        game.Qualities.EstablishGlobally(EatIncome)
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # add the computer structure
        map_generation.Refinement("after_node_types", 1000, refinement_place("structure.computer", (2.2, 2.5), PotentialSize.Medium))

class ComputerResources(GlobalCondition):
    BONUS = {
        "forgiving": 0, "reasonable": 0, "challenging": 10, "tough": 20
    }
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_scenario_start)

    def on_scenario_start(self, _):
        empire.Stock.Receive(Resource.Cash, self.BONUS[game.GameConfig.Difficulty.ID])

#########################################################
# Main mission structure

class ComputerMainMission(MainMission):
    def __init__(self):
        MainMission.__init__(self, "forebear_computer", [CMMFindIt(), CMMActivateIt(), CMMDetermineIt()])
        self._one_last = None

    @staticmethod
    def get():
        return game.Conditions.Get("ComputerMainMission()").PythonObject

    def scenario_id(self): return "m-computer"
    def scoring_rules(self): return [ScoringStudyingComputer()]
    def conditions(self): return [
        (WinMissionOnTime, "ComputerMainMission()", 25)
    ]
    def things_to_explain(self):
        return [("structure", "triangulator"), ("structure", "computer")]
    def secondary_goals(self):
        return [
            (SGHappinessAbove, 0, 110),
            (SGCouncilTasks, 1, 6)
        ]
    
    def perks_available(self):
        return ["luxury", "well_prepared", "geology", "explorers", "social_capital", "nutrition", "efficient", "joint_factories", "careful_observation", "curiosity"]

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

    def grant_time_extension(self):
        computer = game.Nodes.FirstWithType("structure.computer")        
        eligible = computer is not None and computer.Situation is not None
        self._one_last = self._one_last or OneLastAction(["start_situation", "run_event"])
        return eligible and self._one_last.still_in_grace_period()

class CMMFindIt:
    def check_completion(self):
        for _ in nodes_of_type("structure.computer"):
            return True
        return False
    def description(self): return LS("mission.computer.stage.find")

class CMMActivateIt:
    def __init__(self):
        self._computer_node = None

    def _computer(self):
        if not self._computer_node:
            self._computer_node = next(nodes_of_type("structure.computer"), None)
        return self._computer_node

    def requires(self): return (0,)
    def description(self): return LS("mission.computer.stage.activate")
    def state(self): 
        progress = NumericProgress.For(self._computer())
        return progress.ProgressValue if progress else -1
    def short(self):
        c = self._computer()
        if not c: return None
        progress = NumericProgress.For(c)
        if not progress: return ""
        return "<size=80%%>%d/%d:res_progress:" % (progress.ProgressValue, progress.Goal)

    def check_completion(self):
        if game.WinningLosing.IsScenarioComplete: return
        return NumericProgress.For(self._computer()).IsCompleted

class CMMDetermineIt:
    def requires(self): return(0, 1)
    def check_completion(self):
        computer = list(game.Nodes.WithType("structure.computer"))
        computer = computer[0] if len(computer) > 0 else None
        return computer and computer.CustomData.Has("event_complete")    
    def description(self): return LS("mission.computer.stage.determine")

#########################################################
# Story

class ComputerMusic(MusicProgression):
    PROGRESS_THRESHOLD = 4
    def _check_for_transition(self, prev):
        if prev != 1: return None
        computer = next(nodes_of_type("structure.computer"), None)
        if not computer: return None
        yearly = NumericProgress.For(computer).CalculateYearlyProgress()
        if yearly >= self.PROGRESS_THRESHOLD: return 2

    def mission_based_music_transition(self, goal_index, goal):
        if goal_index == 0: 
            return 1
        if goal_index == 2:
            return 3
        return music.Level

class ComputerStory(StoryBits):
    def __init__(self):
        StoryBits.__init__(self, [
            FoundItPopup()
        ])

class FoundItPopup(PopupTutorial):
    def condition(self):
        return ComputerMainMission.get().goal_finished(0)
    def steps(self):
        race = list(game.Council.Members)[0].Race.ID
        return [
            StoryBit("mission.cmp.tidbit.1", [race]),
            StoryBit("mission.cmp.tidbit.2", [race]),
        ]

#########################################################
# Scoring

class ScoringStudyingComputer(Scoring):
    def kind(self): return ScoreKind.Addition
    def tags(self): return ["mission"]

    def title(self): return LS("scoring.computer.studying")
    def description(self): return LS("scoring.computer.studying.desc")

    def calculate_score(self, fraction):
        computer = list(game.Nodes.WithType("structure.computer"))
        computer = computer[0] if len(computer) > 0 else None
        if not computer:
            return Score.Add("", 0, 10)
        connected = game.Reachability.ReachableNodes(computer)
        points = 0
        by_lv = {}
        for c in connected:
            if c.Level >= 2:
                points_here = c.Level - 1
                points += points_here
                by_lv[c.Level] = by_lv.get(c.Level, 0) + 1
        tag_text = "+".join("%d:lv%d:" % (by_lv[lv], lv) for lv in sorted(by_lv.keys()))
        points = clamp(0, 10, points)
        return Score.Add(tag_text, points, 10)

#########################################################
# Triangulation

TRIANGULATOR_PRECISION = 80

def triangulator_desc_data(kind):
    return [":P::B:"]

def triangulator_chrome(node):
    if node.Level == 0: return None
    return [{
        "type": NodeChrome.DirectionDisc,
        "direction": triangulator_shown_direction(node),
        "width": TRIANGULATOR_PRECISION
    }]

def triangulator_lv_change(node):
    if node.Level == 1:
        commands.MakeIrreversibleExceptEmergency()

def triangulator_shown_direction(node):
    rng = Randomness.SeededRNG(node.Seed)
    mistake = Randomness.Float(rng, -TRIANGULATOR_PRECISION * 0.5, TRIANGULATOR_PRECISION * 0.5)
    return triangulator_true_direction(node) + mistake

def triangulator_true_direction(node):
    _, computer_pos = find_computer()
    true_dir = (computer_pos - node.Position).normalized
    true_angle_rad = math.atan2(true_dir.y, true_dir.x)
    true_angle_deg = true_angle_rad * 180.0 / math.pi
    return true_angle_deg

def triangulator_node_tag(node, blocks):
    if node.Level < 1: return blocks.DefaultText()
    return ""

def find_computer():
    signal = next((s for s in game.Map.Signals if s.Contents == "structure.computer"), None)
    if signal: return ("signal", signal.Position)
    potential = next((p for p in every(Potential) if p.Signal.Contents == "structure.computer"), None)
    if potential: return ("potential", potential.Position)
    node = next(nodes_of_type("structure.computer"), None)
    if node: return ("node", node.Position)
    raise Exception("Could not find the computer in any of the places.")

#########################################################
# Computer structure logic

def computer_desc_data(kind):
    return [math.floor(EatIncome.PROPORTION * 100), 1, 2, ComputerProgress.BUILD_TIME[game.GameConfig.Difficulty.ID]]

def computer_init(me):
    progress_rules = ComputerProgress()
    me.AddElement(NumericProgress(progress_rules))

def computer_after_trade(me):
    reachable = game.Reachability.ReachableNodes(me)
    for node in reachable:
        has_quality = node.CustomData.GetOr("computer_connected", False)
        if has_quality: continue
        if not node.NodeType.startswith("planet."): continue
        ConsUpdateNodeData().add(node, "computer_connected", True).issue()

def computer_tooltip(me, text):
    progress = NumericProgress.For(me)
    if not progress: return [text]
    per_year = progress.CalculateYearlyProgress()
    current = progress.ProgressValue
    goal = progress.Goal
    if progress.IsCompleted:
        return [LS("structure.computer.completed")]
    elif per_year > 0:
        years = progress.TicksToCompletion
        new_text = LS("structure.computer.progress_report", None,
            current, goal, years)
        return [new_text.ToString()]
    else:
        return [LS("structure.computer.how_to_start", None, current, goal)]

def progress_node_tag(node, blocks):
    # we assume the text has just the input stuff
    progress = NumericProgress.For(node)    
    if not progress: return blocks.DefaultText()
    progress_made = progress.CalculateYearlyProgress()
    if progress.IsCompleted:
        return ""
    text = blocks.CountedResource("+%d" % progress_made, Resource.All["progress"])
    return text

class ComputerProgress:
    BUILD_TIME = {"forgiving": 30, "reasonable": 45, "challenging": 55, "tough": 60}
    def loadable_expression(self): return "ComputerProgress()"
    def goal_number(self, node): 
        return self.BUILD_TIME[game.GameConfig.Difficulty.ID]
    def when_goal_complete(self, node, progress):        
        commands.IssueScriptedConsequence(ConsUpdateNodeData().add(node, "completed", True))
        commands.Issue(EnableSituation(world, node, "event_computer_decision"))

#########################################################
# Qualities

class ComputerProgressFlow:
    def name(self): return LS("quality.progress", "Yearly progress")
    def desc(self): return LS("quality.computer_progress.desc", 
        "How much progress we make depends on how much income is redirected to that purpose.")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):    
        # done?
        if NumericProgress.For(node).IsCompleted: return
        # nope, let's see who's connected
        others = game.Reachability.ReachableNodes(node)
        total = sum(max(0, node.Level - 1) for node in others if node.NodeType.startswith("planet."))
        if total > 0:
            return [ResourceFlow.Flow(Resource.All["progress"], total, FlowCategory.Progress)]

class EatIncome:
    PROPORTION = 0.5
    """This quality is attached once income is redirected from a node."""
    def name(self): return LS("quality.computer_eat_income", "Income redirected")
    def desc(self): return LS("quality.computer_eat_income.desc", "*{1}%* of the trade income from this planet has been redirected towards studying the forebear computing platform.", self.PROPORTION * 100)

    def applies(self, node):
        return node.CustomData.GetOr("computer_connected", False)
    
    def sentiment(self): return QualitySentiment.Negative
    def effects(self, node): 
        export_flows = list(flows_standard_export(node))
        income = export_flows[0].delta if len(export_flows) > 0 else 0
        redirected_part = math.ceil(income * self.PROPORTION)
        if income > 0:
            return [ResourceFlow.Cash(-redirected_part, FlowCategory.SpecialCosts, LS("quality.computer_eat_income", "Income redirected"))]

#########################################################
# Scripted stuff

def event_computer_decision(evt):
    evt.SetTitle("Ghost in the machine")
    evt.SetText("It looks like the purpose of this structure was *storing the uploaded minds of the forebears*, granting them a new life in a virtual universe.\nThe system is locked down, preventing any interference from the outside world. The computing cores are processing *something* now, but they were powered down for ages. There is no way to know if any of the minds survived.")
    evt.AddChoices(
        "[race(aphorian,no_unlock_needed=True)] We can't afford the cost to our economy. Shut it down and reuse what we can. -> complete -> rebuild(computer_income) -> inc(shutdown) -> stop_redirection",
        "[race(baqar,no_unlock_needed=True)] Resources are better used by the living. Let's scrap it. -> rebuild(computer_nothing) -> complete -> get(120,$) -> inc(shutdown) -> stop_redirection",
        "[race(silthid,no_unlock_needed=True)] There might be a whole civilization in there. We can't risk turning it off. -> rebuild(computer_happy) -> complete",
        "[race(dendr,no_unlock_needed=True)] Their lives are our responsibility now. We must protect them. -> rebuild(computer_happy) -> complete",
        "[race(vattori,no_unlock_needed=True)] There is no limit to what we can learn here. Keep it for experiments. -> rebuild(computer_science) -> complete",
        "Leave it for now."
    )

class EffStopRedirection(ChoiceEffect):
    def describe(self):
        return LS("effect.stop_income_redirection", "Stop income redirection")
    def is_consequential(self): return True
    def consequence(self):
        update = ConsUpdateNodeData()
        for r in game.Reachability.ReachableNodes(self.node()):
            update.add(r, "computer_connected", False)
        return update
        
