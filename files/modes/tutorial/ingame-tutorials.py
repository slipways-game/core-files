######################################################################
# The full collection of in-game popups

class IngamePopupTutorials(TutorialWatcher):
    def __init__(self):
        TutorialWatcher.__init__(self, self.popups())
    
    def popups(self):
        return [
            FirstGamePopup(), # pointing the player to the hotop
            LowHappinessPopup(), # warn people before happiness loss is inevitable
            ProjectPopup(), # planetary projects
            EnergyPopup(), # energy properties
            CulturePopup(), # culture properties
            GrabbingPopup(), # grabbing resources
            EmpireSizePopup(), # empire size
            OverloadPopup(), # slipspace overload
            ConnectionsPopup(), # how to change connection types
            RelayPopup(), InfraspacePopup(), # relay explanations
            DiminishingReturnsPopup(), # lab diminishing returns
            TasksPopup(), DecliningTasksPopup(), # explaining council tasks
            TradeDistancePopup(), ChainingRelaysPopup(), # relay fixes
            HubworldsPopup()
        ]

######################################################################
# Individual tutorials

class FirstGamePopup(PopupTutorial):
    def condition(self):
        return True
    def steps(self):
        return [
            TutorialFirstGame().set_header("first_game").limit_actions().mark_ui("model:UIMTabHUD", "VTabHUD", ["RightWing", "TabButton5", "Images", ("Icon", 1)], ["big_corners"])        
        ]

class LowHappinessPopup(PopupTutorial):
    def __init__(self):
        self._warning_level = constants.Int("happiness.limit") + 15
        PopupTutorial.__init__(self)
    def condition(self):
        return game.Stock.Happiness <= self._warning_level
    def steps(self):
        return [
            TutorialPage("low_happiness", 1, constants.Int("happiness.limit")).set_header("low_happiness").mark_ui("model:Empire", "VResourcesHUD", ["HappinessResource"], ["big_corners"]),
        ]

class TutorialFirstGame(TutorialStep):
    def manual_advance(self):
        return True
    def check(self):
        return find_with_class("UIMHowToPlay") is not None

class ProjectPopup(PopupTutorial):
    def command_prefix(self): return "invent/"
    def condition(self):
        return any(p for p in unlocks.GlobalUnlocks("project"))
    def steps(self):
        return [
            TutorialPage("projects", 1).set_header("projects")
        ]

class GrabbingPopup(PopupTutorial):
    def condition(self):
        return world.Any[RouteOffer]() is not None
    def steps(self):
        return [
            TutorialPage("grabbing", 1).set_header("grabbing")
        ]

class EnergyPopup(PopupTutorial):        
    def condition(self):
        return game.Nodes.TotalProduction(Resource.All["E"]) > 0
    def steps(self):
        return [
            TutorialPage("energy", 1).set_header("energy")
        ]

class CulturePopup(PopupTutorial):        
    def condition(self):
        return game.Nodes.TotalProduction(Resource.All["C"]) > 0
    def steps(self):
        return [
            TutorialPage("culture", 1).set_header("culture")
        ]

class DiminishingReturnsPopup(PopupTutorial):
    def condition(self):
        return game.CustomData.Has("diminishing_returns_seen")
    def steps(self):
        return [
            TutorialPage("diminishing_returns", 1).set_header("diminishing_returns")
        ]

class EmpireSizePopup(PopupTutorial):
    def __init__(self):
        self._es = None
        PopupTutorial.__init__(self)

    def command_prefix(self): return "colonize/"
    def condition(self):
        if self._es is None:
            self._es = condition("EmpireSize") or False
        if not self._es: return False
        return self._es.current_size() > 0

    def steps(self):
        return [
            TutorialPage("empire_size", 1).set_header("empire_size")
        ]

class OverloadPopup(PopupTutorial):
    def __init__(self):
        self._so = None
        PopupTutorial.__init__(self)

    def command_prefix(self): return "connect/"
    def condition(self):
        if self._so is None:
            self._so = condition("SlipspaceOverload") or False
        if not self._so: return False
        return self._so.current_overload() > 0

    def steps(self):
        return [
            TutorialPage("slipspace_overload", 1).set_header("slipspace_overload")
        ]

class ConnectionsPopup(PopupTutorial):
    def command_prefix(self): return "invent/"
    def condition(self):
        return sum(1 for c in unlocks.GlobalUnlocks("connection")) >= 2
    def steps(self):
        return [TutorialPage("connections", 1).set_header("connections")]

class RelayPopup(PopupTutorial):
    def command_prefix(self): return "invent/"
    def condition(self):
        return unlocks.IsUnlocked("structure.relay")
    def steps(self):
        return [TutorialPage("relays", 1).set_header("relays")]

class InfraspacePopup(PopupTutorial):
    def command_prefix(self): return "invent/"
    def condition(self):
        return unlocks.IsUnlocked("structure.infra_relay")
    def steps(self):
        return [TutorialPage("infraspace", 1).set_header("infraspace")]

class TasksPopup(PopupTutorial):
    def condition(self):
        return any(msg.SourceExpression.Contains("MotherOfQuests") for msg in every(Message))
    def steps(self):
        return [TutorialTasks().set_header("tasks")]

class DecliningTasksPopup(PopupTutorial):
    def condition(self):
        return game.Time.NormalizedTurn >= 20 and any(msg.SourceExpression.Contains("MotherOfQuests") for msg in every(Message))
    def steps(self):
        return [TutorialPage("declining_tasks", 1).set_header("declining_tasks")]

class TutorialTasks(TutorialStep):
    def id(self): return "tasks-1"
    def manual_advance(self):
        return True
    def check(self):
        return find_with_class("ModalDialog") is not None

class TradeDistancePopup(PopupTutorial):
    def condition(self):
        return game.CustomData.Has("tutorial_trade_distance")
    def steps(self):
        return [TutorialPage("trade_distance", 1).set_header("trade_distance")]

class ChainingRelaysPopup(PopupTutorial):
    def condition(self):
        return game.CustomData.Has("tutorial_chaining_relays")
    def steps(self):
        return [TutorialPage("chaining_relays", 1).set_header("chaining_relays")]

class HubworldsPopup(PopupTutorial):
    def condition(self):
        return game.CustomData.GetOr("hubworlds_unlocked", 0) > 0
    def steps(self):
        return [TutorialPage("hubworlds", 1).set_header("hubworlds")]

### The hint tutorials

class HintStartingSetup(PopupTutorial):
    def steps(self):
        return [StartingSetupPage()]

class StartingSetupPage(TutorialStep):
    def __init__(self):
        TutorialStep.__init__(self)
    
    def allows_actions(self): return True
    def id(self): return "hint_starting_setup"
    def manual_advance(self): return True
    def ls_header(self): return LS("hint.starting_setup")
    def ls_text(self): 
        main_text = L("hint.starting_setup.desc")
        sub_text = L("hint.turn_hints_off")
        return main_text + "\n" + styled(sub_text, "TooltipLightComment")
