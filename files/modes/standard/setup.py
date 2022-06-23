class StandardStats(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_tabs)
        self.react_to(Trigger.GameLoaded, self.setup_tabs)

    def setup_tabs(self, _):
        game.Stats.Add(StatSources.ScoringTab(0))
        game.Stats.Add(StatSources.DomainTab(5))
        game.Stats.Add(StatSources.SectorTab(10))

class StandardScoring(GlobalCondition):
    def __init__(self, exclude = None):
        self._exclude = exclude or []

    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.setup_scoring)
        self.react_to(Trigger.GameLoaded, self.setup_scoring)
    
    def setup_scoring(self, _ = None):
        for scoring_rule in self.scoring_rules():
            if scoring_rule is None: continue
            empire.Scoring.AddRule(scoring_rule)
    
    ### Internals

    def scoring_rules(self):
        excluded = self._exclude
        empire_size_rule = ScoringEmpireSize()
        for replacement in game.Conditions.Supporting("replace_scoring_empire_size"):
            empire_size_rule = replacement.PythonObject.replace_scoring_empire_size()
        scores = [
            ScoringPlanets() if not "planets" in excluded else None,
            ScoringPoliticalPower() if not "political_power" in excluded else None,
            empire_size_rule if not "empire_size" in excluded else None,
            ScoringUnfinishedQuests() if not "unfinished_quests" in excluded else None,
            ScoringHappiness() if not "happiness" in excluded else None
        ]
        return scores
    

class StandardConditions(GlobalCondition):
    def __init__(self, *skipped):
        self._skipped = skipped

    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_scenario_start)
    
    def on_scenario_start(self, _):
        skipped = set(self._skipped)
        standard_conditions = [
            (ResourceShortages,),
            (EmpireSize,),
            (SlipspaceOverload,) if "no_slipspace_overload" not in skipped else None,
            (WinTimeLimit, constants.Int("scenario.length")) if "no_time_limit" not in skipped else None,
            (LoseWhenBankrupt,),
            (LoseOnLowHappinessOverTime, constants.Int("happiness.limit"), 3),
            (ResourceAdditionalInfo,)
        ]
        standard_conditions = [sc for sc in standard_conditions if sc is not None]
        for c in standard_conditions:
            empire.Conditions.Activate(*c)
        for member in ih(empire.Council.Members):
            if not "no_race_status" in skipped:
                empire.Conditions.Activate(RaceStatus, member.Race.ID)
            member.ActivatePerks()

class StandardQuests(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ScenarioSetup, self.on_scenario_start)

    def on_scenario_start(self, _):
        empire.Conditions.Activate(MotherOfQuests)
