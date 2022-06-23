#########################################################
# Main mission class

class FiveMainMission(MainMission):
    def __init__(self):        
        MainMission.__init__(self, "five", [FMMExamineTheArchive()])
        self._one_last = None

    @staticmethod
    def get():
        return game.Conditions.Get("FiveMainMission()").PythonObject

    def scenario_id(self): return "m-five"
    def scoring_rules(self):
        return [
            ScoringHubworldValue(),
            ScoringCampaignTime(self, [1000, 24, 23, 22, 21, 20])
        ]

    def select_screen(self):
        return {
            "races_to_pick": 5,
            "preselect_races": ["baqar", "aphorian", "dendr", "vattori", "silthid"],
            "main_position":  Vector2(0.5, 0.55), "portrait_scale": 0.8, "block_width": 330,
            "lock_races": True
        }

    def potential_techs(self):        
        #patterns = ["0234", "1234", "2344", "0124", "0134"]
        patterns = ["01234", "01234", "01234", "01234", "01234"]
        races = [r.ID for r in Race.AllPlayable]
        rng = game.RNG("potential_techs")
        Randomness.Shuffle(rng, patterns)
        per_race = {r: p for r, p in zip(races, patterns)}
        return {
            "pattern_for_race": per_race
        }

    def conditions(self): return [
        (WinMissionOnTime, "FiveMainMission()", 25),
        (RaceDemands,),
    ]

    def do_additional_setup(self):
        game.Qualities.EstablishGlobally(ArchiveEatIncome)
        game.Camera.ZoomTo(13) # zoom out to show the archive
    
    def perks_available(self):
        return ["reciprocity", "novelty_traders", "miners", "explorers", "prosperity", "social_capital", "space_architects", "joint_factories", "careful_observation", "curiosity"]

    def things_to_explain(self):
        return [
            ("custom", "mission.five.start_with_all_races"),
            ("structure", "archive"),
            ("custom", "mission.five.demands"),
            ("custom", "mission.five.lose_rule"),
        ]
    
    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

    def grant_time_extension(self):
        archive = game.Nodes.FirstWithType("structure.archive")
        eligible = archive_level() >= 3 and archive and archive.Situation is not None
        self._one_last = self._one_last or OneLastAction(["start_situation", "run_event"])
        return eligible and self._one_last.still_in_grace_period()

class FMMExamineTheArchive:
    def check_completion(self):
        lv = archive_level()
        return lv >= ARCHIVE_FINAL_LEVEL
    def description(self): return LS("mission.five.goal.examine_the_archive")
    def state(self): return (archive_level(), ARCHIVE_FINAL_LEVEL)
    def short(self): return "%d/%d" % self.state()

###############################################################
# Sector type

class FiveRacesSectorType(GlobalCondition):
    def __init__(self):
        self._proxied = FiveMainMission()
    def menu_flow_setup(self): return True
    def select_screen(self):
        return self._proxied.select_screen()
    def potential_techs(self):        
        return self._proxied.potential_techs()
    
###############################################################
# Scoring

class ScoringHubworldValue(ScoringFiveRanks):
    def id(self): return "scoring.five.hubworld_value"

    def base_number(self):
        return game.Stock.TotalFlowForCategory(FlowCategory.HubworldHappiness, Resource.Happiness)
    
    def rank_limits(self): return [0, 6, 9, 12, 14, 16]
    def rank_text(self, number): return "%d%%:H:" % number
    def number_text(self, number, rank): return "%d%%:H:" % number if number > 0 else "-"
    def tags(self): return ["mission"]

###############################################################
# Music

class FiveMusic(MusicProgression):
    def _check_for_transition(self, prev):
        lv = clamp(0, 3, archive_level())
        if prev < lv: return lv

###############################################################
# Map generation stuff

class ArchiveMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)
        self.react_to(Trigger.MapGenerated, self.on_map_generated)
    def on_map_setup(self, data):
        gen = data["generation"]
        gen.Refinement("after_planet_types", 1000, refinement_place_archive(3.5, 0.7))
    def on_map_generated(self, data):
        instantiate_archive_stuff()

def refinement_place_archive(desired_distance, eradication_distance):
    BOOSTING_TARGETS = {
        "planet.ice": ["planet.arctic", "planet.ocean"], 
        "planet.barren": ["planet.arid", "planet.remnant"],
        "planet.lava": ["planet.mining", "planet.factory"],
    }
    DUPLICATES_ORDER = ["planet.earthlike", "planet.remnant", "planet.mining", "planet.factory", "planet.arctic", "planet.primordial", "planet.arid", "planet.swamp", "planet.ocean"]
    def refine(gen, signals, zones):
        attempts = 50
        rng = gen.RNGForTask("archive")
        points = []
        for _ in xrange(attempts):
            point = Randomness.PointInsideUnitRing(rng, 0.8) * f(1.2) * f(desired_distance)
            neighbors = [s for s in gen.SignalsNear(point, 1.5) if s.Contents.startswith("planet.")]
            if len(neighbors) >= 2:
                min_distance = min((s.Position - point).magnitude for s in neighbors)
                score = len(neighbors) * len(neighbors) * min_distance
                points.append((point, score))
        # pick best
        best_point = max(points, key=lambda p: p[1])[0]
        # eradicate surrounding signals that are too close
        removed_sigs = list(gen.SignalsNear(best_point, eradication_distance))
        gen.RemoveSignals(removed_sigs)
        # find nearby planets
        range = 1.65
        while True:
            nearby_planets = list(s for s in gen.SignalsNear(best_point, range) if s.Contents.startswith("planet."))
            if len(nearby_planets) >= 6: break
            range += 0.2
        # boost planets to better types around the archive
        boosted = list(s for s in nearby_planets if s.Contents in BOOSTING_TARGETS)
        for b in boosted:
            b.Contents = Randomness.Pick(rng, BOOSTING_TARGETS[b.Contents])
        # look for duplicates and try your best to avoid them
        used_types = [s.Contents for s in nearby_planets]
        for index, sig in enumerate(nearby_planets):
            if sig.Contents in used_types[:index]:
                for replacement in DUPLICATES_ORDER:
                    if replacement not in used_types:
                        sig.Contents = replacement
                        used_types[index] = replacement
                        break
        # store
        game.CustomData.Set("archive_pos", best_point)
    return refine

def instantiate_archive_stuff():
    distance_scale = constants.Float("distance.scale")
    archive_pos = game.CustomData.Get("archive_pos") * distance_scale
    world.Add(Structure(archive_pos, StructureKind.All["archive"]))

###############################################################
# Races, demands and losing races

class RaceDemands(GlobalCondition):
    def activate(self):
        self._subconds = None
        # create subconditions
        for r in game.Council.Members:
            game.Conditions.Activate(RaceDemand, r.Race.ID)            
        # events
        self.react_to(Trigger.ActionTaken, self.refresh_subs)
        self.react_to(Trigger.ActionReverted, self.refresh_subs)
    
    def subconds(self):
        if self._subconds is None:
            self._subconds = [game.Conditions.Get(RaceDemand, r.ID) for r in Race.AllPlayable]
            self._subconds = [c.PythonObject for c in self._subconds if c is not None]
        return self._subconds

    def refresh_subs(self, data):
        for sub in self.subconds():
            sub.refresh()
    
    def advance_all_demands(self):
        # at this point, the archive_level should be increased, so we just reactivate the demands
        lv = archive_level()
        for r in game.Council.Members:
            cond = game.Conditions.Get(RaceDemand, r.Race.ID).PythonObject
            cond.activate_demands(lv)

    def fulfilled_races(self):
        for r in game.Council.Members:
            cond = game.Conditions.Get(RaceDemand, r.Race.ID).PythonObject
            yield r.Race

    def count_met_demands(self):
        return sum(1 for fr in self.fulfilled_races())

class RaceDemand(GlobalCondition):
    def __init__(self, race_id):
        self._race_id = race_id
        self._race = Race.All[race_id]

    def activate(self):
        self._state = None
        self._member = empire.Council.Member(Race.All[self._race_id])
        self.react_to(Trigger.CouncilMemberStatusChanged, self.when_status_changes)
        current_level = game.CustomData.GetOr("archive_level", 0)
        self.activate_demands(current_level)
        if self._demands:
            self._state = self._demands.state()

    def refresh(self):
        if not self._demands: return
        new_state = self._demands.state()
        if new_state != self._state:
            self._state = new_state
            self.signal_change()
    
    def activate_demands(self, level):
        if level < ARCHIVE_FINAL_LEVEL:
            demand_class_name = IdentifierStyles.ToUpperCamel(self._race_id) + "Demands"
            DemandClass = globals()[demand_class_name]
            self._demands = DemandClass(level)
        else:
            self._demands = None
        self.signal_change()

    def when_status_changes(self, data):
        if data["member"] == self._member:
            self.signal_change()
    
    def info(self):
        if not self._member.IsActive: return None
        ci = CondInfo()
        ci.Icon = self._race_id
        ci.Important = True
        if self._demands:
            ci.ShortText = self._demands.short()
            ci.FullDescription = self._demands.description()
        ci.Tooltip = [self._member, LazyTooltip(self.failing_tooltip)]
        return ci

    def failing_tooltip(self):
        failing = find_failing_race()
        if failing == self._race_id:
            text = L("ui.info.this_race_will_leave")
            return styled(styled(text, "Bad"), "TooltipLight")
        else:
            return None

    def additional_race_info(self, race):
        if race == self._race:
            prefix = styled(L("demand.prefix"), "TooltipLightBolded")
            demand_text = styled(self._demands.description(), "TooltipLight")
            return "*%s* %s" % (prefix, demand_text)

    def fulfilled(self):
        return self._demands.completed()
    def failure_margin(self):
        return self._demands.failure_margin()


class ConsLoseCouncilMember:
    def __init__(self, race_id):
        self._member = game.Council.Member(Race.All[race_id])

    def apply(self):
        self._member.DeactivatePerks()
        self._member.Deactivate()
        self.forget_techs()
        MotherOfQuests.find().terminate_all_quests_for(self._member) # reverts itself
        if sum(1 for m in game.Council.Members) < 3:
            empire.WinningLosing.EndScenario({
                "outcome": "loss", "defeat": True,
                "defeat_icon": "icon_mission_failed",
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("mission.five.game_end.council_left"),
                "shown_elements": []
            })

    def revert(self):
        self._member.Activate()
        self._member.ActivatePerks()
        self.unforget_techs()

    def forget_techs(self):
        race = self._member.Race
        techs_to_lose = [kt for kt in game.Technology.AllUnlocked if kt.Source.Race == race]
        for tech in techs_to_lose:
            game.Technology.Forget(tech)
        self._lost_techs = techs_to_lose

    def unforget_techs(self):
        race = self._member.Race
        for tech in self._lost_techs:
            game.Technology.Unlock(tech.Kind, UnlockSource.FromRace(race))

class UnlockAllRaceEventOptions(GlobalCondition):
    def activate(self):
        for m in game.Council.Members:
            empire.Conditions.Activate(EventOptionUnlock, m.Race.ID)

##############################################################
# Specific demands of the five races

class SpecificDemands:
    def __init__(self, level):
        self._level = level
        self.prepare()
    def level(self): return self._level
    def description(self):
        params = self.desc_params() + self.state()
        return LS("five.demands.%s.desc" % self.race_id(), None, *params)
    def short(self):
        style = "GoodLight" if self.completed() else "BadLight"
        return styled(self.short_template() % self.state(), style)
    def desc_params(self): return (self._required,)
    def state(self): return (self.current(), self._required)
    def difficulty_modifier(self, lv): 
        adjustments = self.DIFF_ADJUSTMENTS[difficulty_ordinal()]
        lv = clamp(0, len(adjustments) - 1, lv)
        return adjustments[lv]
    def prepare(self):
        lv = self.level()
        diff_mod = self.difficulty_modifier(lv)
        reference = self.get_checkpoint() 
        if reference is None: reference = self.current()
        self.set_checkpoint(reference)
        self._required = reference + self.LEVELS[lv] + diff_mod     
    def completed(self):
        state = self.state()
        return state[0] >= state[1]
    def failure_margin(self):
        state = self.state()
        improvement = state[0] - self.get_checkpoint()
        required_improvement = state[1] - self.get_checkpoint()
        if required_improvement == 0:
            return 1.0
        return 1.0 - improvement / float(required_improvement)
    def checkpoint_key(self):
        return "demand_checkpoint_%s_%d" % (self.race_id(), self.level())
    def get_checkpoint(self): return game.CustomData.GetOr(self.checkpoint_key(), None)
    def set_checkpoint(self, chk): game.CustomData.Set(self.checkpoint_key(), chk)


class AphorianDemands(SpecificDemands):
    LEVELS = [100, +75, +75, +75]
    DIFF_ADJUSTMENTS = [(0,), (0,), (0,), (0,)]
    def race_id(self): return "aphorian"
    def short_template(self): return "%d/%d:$:"
    def current(self):
        return game.Stock.TotalExportIncome

class DendrDemands(SpecificDemands):
    LEVELS = [90, +10, +10, +10]
    DIFF_ADJUSTMENTS = [(-10, -4), (0, -2), (0, 0), (0, 0)]

    def race_id(self): return "dendr"
    def short_template(self): return "%d/%d%%:H:"
    def current(self): return game.Stock.Happiness
    def prepare(self):
        lv = self.level()
        diff_mod = self.difficulty_modifier(lv)
        reference = self.get_checkpoint()
        if reference is None: reference = self.current()
        if lv > 0:
            self.set_checkpoint(reference)
            self._required = reference + self.LEVELS[lv] + diff_mod
        else:
            self._required = self.LEVELS[0] + diff_mod
            self.set_checkpoint(self._required - 10)

class SilthidDemands(SpecificDemands):
    LEVELS = [6, +6, +5, +5]
    DIFF_ADJUSTMENTS = [(-1, -2), (-1, -1), (0, 0), (0, 0)]
    def race_id(self): return "silthid"
    def short_template(self): return "%d/%d:B::T:"
    def current(self):
        B, T = Resource.All["B"], Resource.All["T"]
        return game.Nodes.TotalProduction(B) + game.Nodes.TotalProduction(T)

class BaqarDemands(SpecificDemands):
    LEVELS = [12, +9, +8, +7]
    DIFF_ADJUSTMENTS = [(-1, -2), (-1, -1), (0, 0), (0, 0)]
    def race_id(self): return "baqar"
    def short_template(self): return "%d/%d:planet:"
    def current(self):
        return sum(1 for p in game.Nodes.PlanetsWithLevelOrHigher(0))

class VattoriDemands(SpecificDemands):
    LEVELS = [3, +4, +5, +6]
    DIFF_ADJUSTMENTS = [(-1, -1), (0, -1), (0, 0), (0, 0)]
    def race_id(self): return "vattori"
    def short_template(self): return "%d/%d:S:"
    def current(self):
        return game.Stock.Income(Resource.Science)

###############################################################
# Broken relays

def ruined_relay_connectivity(node, other):
    return NodeConnectivity.Rejects(LS("structure.ruined_relay.rebuild_first"), 1)

class RepairRelay:
    @staticmethod
    def execute(node):
        node.EstablishIndustry(IndustryKind.All["subspace_relay"])

    @staticmethod
    def revert(data):
        node.AbandonIndustry()

    @staticmethod
    def applies(node):
        return node.NodeType == "structure.ruined_relay"

###############################################################
# Archive logic

ARCHIVE_FINAL_LEVEL = 4

def archive_level():
    return game.CustomData.GetOr("archive_level", 0)

def archive_init(me):
    progress_rules = ArchiveProgress()
    me.AddElement(NumericProgress(progress_rules))

def archive_radius(me):
    return 1.5

def archive_after_trade(me):
    reachable = game.Reachability.ReachableNodes(me)
    for node in reachable:
        has_quality = node.CustomData.GetOr("archive_connected", False)
        if has_quality: continue
        if not node.NodeType.startswith("planet."): continue
        ConsUpdateNodeData().add(node, "archive_connected", True).issue()

def archive_tooltip(me, text):
    progress = NumericProgress.For(me)    
    if not progress: 
        return [LS("structure.archive.completed_all_levels")]
    per_year = progress.CalculateYearlyProgress()
    current = progress.ProgressValue
    goal = progress.Goal
    if progress.IsCompleted:
        return [LS("structure.archive.click_to_read")]
    elif per_year > 0:
        years = progress.TicksToCompletion
        new_text = LS("structure.archive.progress_report", None, current, goal, years)
        return [new_text]
    else:
        return [LS("structure.archive.how_to_start", None, current, goal)]

def archive_info_on_upgrades(node):
    progress = NumericProgress.For(node)
    per_year = progress.CalculateYearlyProgress() if progress is not None else 0
    if per_year == 0: 
        return
    header = LS("structure.archive.progress_panel.header")
    info = archive_tooltip(node, "")
    return InfoBlock(header, info)

def progress_node_tag(node, blocks):
    progress = NumericProgress.For(node)    
    if not progress: return blocks.DefaultText()
    progress_made = progress.CalculateYearlyProgress()
    text = blocks.CountedResource("+%d" % progress_made, Resource.All["progress"])
    return text

class ArchiveProgress:
    BASE_TIME = {"forgiving": 9, "reasonable": 11, "challenging": 12, "tough": 13}
    INCREMENTS = [1.0, 1.6, 2.3, 3.1, 100]

    def loadable_expression(self): return "ArchiveProgress()"
    def goal_number(self, node):
        base = self.BASE_TIME[game.GameConfig.Difficulty.ID]
        increment = self.INCREMENTS[archive_level()]
        total = int(math.floor(base * increment))
        return total
    def when_goal_complete(self, node, progress):        
        commands.Issue(EnableSituation(world, node, "event_advance_archive"))

class ArchiveEatIncome:
    PROPORTION = 0.5
    def name(self): return LS("quality.archive_eat_income", "Income redirected")
    def desc(self): return LS("quality.archive_eat_income.desc", "*{1}%* of the trade income from this planet has been redirected towards studying the archive.", self.PROPORTION * 100)

    def applies(self, node):
        return node.CustomData.GetOr("archive_connected", False)
    
    def sentiment(self): return QualitySentiment.Negative
    def effects(self, node): 
        export_flows = list(flows_standard_export(node))
        income = export_flows[0].delta if len(export_flows) > 0 else 0
        redirected_part = math.ceil(income * self.PROPORTION)
        if income > 0:
            return [ResourceFlow.Cash(-redirected_part, FlowCategory.SpecialCosts, LS("quality.computer_eat_income", "Income redirected"))]

def event_advance_archive(evt):
    lv = archive_level()
    first = lv == 0
    exhausted = lv >= ARCHIVE_FINAL_LEVEL - 1
    evt.SetLocalizedTitle(LS("event.studying_the_archive"))
    evt.SetLocalizedText(LS("event.studying_the_archive.intro.%d" % (1 if first else 2)))
    # archive text
    archive_text = L("mission.five.archive_text.%d" % (lv + 1))
    archive_text = "*%s*" % archive_text
    evt.AppendParagraph(archive_text)
    # outgoing choices
    if exhausted:
        evt.AppendLocalizedParagraph(LS("event.studying_the_archive.exhausted"))
    else:
        evt.AppendLocalizedParagraph(LS("event.studying_the_archive.more_remains"))
    final_effects = "-> check_for_races_leaving"
    if not exhausted:
        evt.AddChoice("Keep studying the archive." + final_effects)
    else:
        evt.AddChoice("Close the archive for now." + final_effects)

def additional_funding(race_count):
    reward_bases = [0, 10, 12, 14, 16]
    lv = archive_level()
    basis = reward_bases[lv]
    return basis * race_count

def do_rewards(evt):
    advancing_races = game.Conditions.Get(RaceDemands).PythonObjects.fulfilled_races()
    for race in advancing_races:
        commands.Issue(AdvanceRaceToNextLevel(world, game.Council.Member(race)))

def event_all_races_stay(evt):
    evt.SetLocalizedTitle(LS("event.all_races_stay"))
    evt.SetLocalizedText(LS("event.all_races_stay.text"))
    # add final choice
    evt.AddChoice("Carry on. -> advance_archive_level -> advance_all_demands")

def make_lose_race_event(race_id):
    def event_logic(evt):
        evt.SetLocalizedTitle(LS("event.a_race_leaves"))
        evt.SetLocalizedText(LS("event.a_race_leaves.intro", None, race_id))
        #evt.AppendLocalizedParagraph(LS("event.race_leaving_dialogue.%s" % race_id))
        evt.AppendParagraph(styled(LS("event.what_losing_a_race_means", None, race_id), "EventComment"))
        # add final choice
        evt.AddChoice("Accept their decision. -> advance_archive_level -> lose_race(%s) -> advance_all_demands" % race_id)
    return event_logic

for event_race in ["vattori", "dendr", "baqar", "silthid", "aphorian"]:
    globals()["event_lose_%s" % event_race] = make_lose_race_event(event_race) 

def find_failing_race():
    failed_race, biggest_margin = None, -100.0
    for member in game.Council.Members:
        race_id = member.Race.ID
        cond = game.Conditions.Get(RaceDemand, race_id).PythonObject
        if not cond.fulfilled():
            # is this failure worse than previous ones?
            # we use the 'margin of failure', which is how far percentage-wise the player
            # is from reaching the goal
            race_margin = cond.failure_margin()
            if race_margin > biggest_margin:
                biggest_margin, failed_race = race_margin, race_id
    return failed_race

class EffAdvanceArchiveLevel(ChoiceEffect):
    def consequence(self): return self
    def apply(self):
        node = self.node()
        # increase level
        game.CustomData.Inc("archive_level")
        new_level = archive_level()
        # restart or remove progress
        more_to_go = new_level < ARCHIVE_FINAL_LEVEL
        if more_to_go:
            NumericProgress.For(node).ResetProgress()
        else:
            NumericProgress.For(node).Discard()            
        commands.MakeIrreversible()

class EffCheckForRacesLeaving(ChoiceEffect):
    def consequence(self): return self
    def apply(self):
        failed_race = find_failing_race()
        if failed_race:
            self.event().GoTo("event_lose_%s" % failed_race)
        else:
            self.event().GoTo("event_all_races_stay")

class EffLoseRace(ChoiceEffect):
    def __init__(self, race_id):
        self._race_id = race_id
    def consequence(self): 
        return ConsLoseCouncilMember(self._race_id)

class EffAdvanceAllDemands(ChoiceEffect):
    def consequence(self): return self
    def apply(self):
        advancing_races = game.Conditions.Get(RaceDemands).PythonObject.fulfilled_races()
        for race in advancing_races:
            commands.Issue(AdvanceRaceToNextLevel(world, game.Council.Member(race)))
        game.Conditions.Get(RaceDemands).PythonObject.advance_all_demands()

class EffGetFunding(ChoiceEffect):
    def __init__(self, cash):
        self._cash = cash
    def consequence(self): return ConsGrantResources(self._cash, Resource.Cash)

class ArchiveProgressFlow:
    def name(self): return LS("quality.progress", "Yearly progress")
    def desc(self): return LS("quality.archive_progress.desc")
    def sentiment(self): return QualitySentiment.Positive

    def effects(self, node):
        # nope, let's see who's connected
        progress = NumericProgress.For(node)
        if not progress: return
        others = game.Reachability.ReachableNodes(node)
        total = sum(max(0, node.Level - 1) for node in others if node.NodeType.startswith("planet."))
        if total > 0:
            return [ResourceFlow.Flow(Resource.All["progress"], total, FlowCategory.Progress)]
