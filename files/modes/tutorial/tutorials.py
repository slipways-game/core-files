##########################################################
# The workhorse class for all tutorials

class TutorialSequence(GlobalCondition):
    def __init__(self, tut_list):
        self._tutorials = tut_list
        
    def activate(self):
        self._remaining = list(self._tutorials)
        self._current = None
        self._completed = False
        self._delay = 0.0
        self._forced_advance = False
        self._was_forced = False
        self._owned_models = []
        # global overrides
        self._global_overrides = None
        self.update_global_state({})
        # cut the remaining list to size
        start_at = self.data.get_or("completed_step", 0)
        self._remaining = self._remaining[start_at:]
        # show the tutorials
        self._display = game.Dialogs.TutorialSequenceBox()
        # react
        self.react_to(Trigger.ActionTaken, self.after_action)

    def deactivate(self):
        if self._display is not None:
            self._display.Discard()
        for m in self._owned_models:
            m.Discard()
        self.data.clear_value("completed_step")
        game.Triggers.ActivateFromScript(Trigger.TutorialCompleted, {})

    def complain(self, error_text):
        if not self._display: return
        self._display.ShowError(error_text)
        return CommandReaction.Stop

    def after_action(self, _):
        if self._display:
            self._display.DismissError()

    def realtime_update(self, dt):
        # do we have a current step to check?
        step = self._current
        if step:
            completed = self._forced_advance or step.check()
            self._was_forced = self._forced_advance
            if completed:
                if self._delay > 0.0: 
                    self._delay -= dt
                    return
                self._forced_advance = False
                self._current = None
                for m in self._owned_models: m.Discard()
                self._owned_models = []
                self.data.set_value("completed_step", self.data.get_or("completed_step", 0) + 1)
                step = None
        # do we have a new step to display?
        if not step:
            if len(self._remaining) > 0:
                if self._remaining[0].allows_save_before():                    
                    self.save_checkpoint()
                self._current = self._remaining[0]
                self._remaining = self._remaining[1:]
                self._current._owner = self
                self._current.start()
                self._delay = self._current.delay()
                self.add_models(self._current.models())
                self.show(self._current)    
            else:
                # we ran out, tutorial done!
                game.CustomData.Set("tutorial_done", True)
                self._host.Deactivate()

    def add_models(self, model_list):
        self._owned_models = []
        self._tagged_models = {}
        for m in model_list:
            key, model = None, None
            if isinstance(m, tuple):
                key, model = m
            else:
                model = m
            if not model.IsInitialized:
                world.Add(model)
            self._owned_models.append(model)
            if key: self._tagged_models[key] = model
    
    def kill_model(self, tag):
        model = self._tagged_models[tag]
        if not model.WasDiscarded:
            model.Discard()
            self._owned_models.remove(model)

    def checklist_task(self, item, completed):
        if not self._display: return
        self._display.UpdateChecklist(item, completed)

    def update_global_state(self, settings):
        for k,v in settings.items():
            self.data.set_value(k, v)
        # generate new override object
        if self._global_overrides: self._global_overrides.Discard()
        overrides = GameStateOverrides.Make(50)
        if self.data.get_or("lock_transitions", False): overrides.LockScreenTransitions()
        self._global_overrides = world.Add(GameStateLimiter(overrides))

    def save_checkpoint(self):
        game.Autosave.SaveNow()

    def force_advance(self):
        self._forced_advance = True
        self._delay = 0.0

    def show(self, tut):
        manual = tut.manual_advance()
        header = tut.ls_header()
        if header is not None: 
            self.data.set_value("last_header", header.ToString())
        step_data = {
            "character": tut.character(),
            "pose": tut.pose(),
            "header": self.data.get_or("last_header", ""),
            "text": tut.ls_text(),
            "button": tut.ls_advance_button() if manual else None,
            "reset_button": LS("tutorial.button.reset") if tut.offers_reset() else None,
            "when_advanced": self.force_advance if manual else None
        }
        if hasattr(tut, "checklist"):
            step_data["checklist"] = tut.checklist()
        self._display.Update(step_data)
        if not self._was_forced: self._display.ShowCompletion()

##########################################################
# Condition for in-game pop-up tutorials

class TutorialWatcher(GlobalCondition):
    def __init__(self, popup_list):
        self._popups = list(popup_list)

    def activate(self):
        # filter already seen tutorials
        tuts = game.Tutorials
        self._popups = [p for p in self._popups if not tuts.WasSeen(p.flag())]
        # react
        self.react_to(Trigger.ActionTaken, self.check_for_popups)
        self.react_to(Trigger.TutorialCompleted, self.check_for_popups)
        self.react_to(Trigger.ConnectionBuilt, self.when_connection_built)
        self.react_to(Trigger.TradeRouteEstablished, self.when_route_established)
        self.check_for_popups({"command_string": "none"})

    def when_connection_built(self, data):
        conn = data["connection"]
        if conn.From.RelaysConnections and conn.To.RelaysConnections:
            game.CustomData.Set("tutorial_chaining_relays", True)

    def when_route_established(self, data):
        route = data["route"]
        if len(route.Steps) > 2:
            game.CustomData.Set("tutorial_trade_distance", True)

    def check_for_popups(self, data):
        if game.Tutorials.TutorialsDisabled: return
        if game.Dialogs.IsATutorialOpen(): return
        command = data["command_string"] if "command_string" in data else ""
        tuts = game.Tutorials
        for p in self._popups:
            # check conditions (in order of 'expensiveness')
            if tuts.WasSeen(p.flag()): continue
            if not command.startswith(p.command_prefix()): continue
            if not p.condition(): continue
            # all conditions match, pop the tutorial!
            self._popups.remove(p)
            p.start_sequence()
            return

class PopupTutorial(TutorialSequence):
    """Base class from which pop-up tutorials should inherit."""
    def __init__(self, args=[]):
        TutorialSequence.__init__(self, [])
        self._args = args
    
    def start_sequence(self):
        game.Conditions.Activate(self.__class__, *self._args)

    def activate(self):
        self._tutorials = self.steps()
        return TutorialSequence.activate(self)

    def deactivate(self):
        game.Tutorials.MarkAsSeen(self.flag())
        return TutorialSequence.deactivate(self)

    # defaults
    def command_prefix(self): return ""
    def flag(self): return self.__class__.__name__
    def condition(self): raise Exception("condition() has to be overriden in TutorialPopup descendants.")
    def steps(self): raise Exception("steps() has to be overriden in TutorialPopup descendants.")

#########################################################
# Winning a tutorial

class WinTutorial(GlobalCondition):
    def __init__(self):
        self._delay = 0.15
    
    def realtime_update(self, dt):
        if game.Time.NormalizedTurn < 1: return
        if game.CustomData.GetOr("tutorial_done", False):
            self._delay -= dt
            if self._delay < 0:
                self._end_game()

    def _end_game(self):
        empire.WinningLosing.EndScenario({
            "outcome": "win",
            "heading": LS("tutorial.complete"),
            "shown_elements": []            
        })

##############################################
# Base tutorial step class

class TutorialStep:
    def __init__(self):
        self._character = "droid"
        self._pose = "neutral"
        self._saving = False
        self._header = None
        if not self.allows_actions():
            self.disable_actions()

    def id(self): 
        cls_name = self.__class__.__name__
        return IdentifierStyles.ToSnake(cls_name.replace("Tutorial",""))

    def start(self): pass
    def check(self): return False
    def models(self): 
        models = []
        if hasattr(self, "react"):
            overrides = GameStateOverrides.Make(50).ReactToCommands(self.react)                
            models.append(world.Add(GameStateLimiter(overrides)))
        return models

    def ls_header(self): return LS("tutorial.%s.header" % self._header) if self._header else None
    def ls_text(self): return LS("tutorial.%s" % self.id())
    def ls_advance_button(self): return LS("tutorial.button.advance")

    def allows_actions(self): return True
    def allows_save_before(self): return self._saving
    def offers_reset(self): return False
    def manual_advance(self): return False
    def delay(self): return 0.0
    def pose(self): return self._pose
    def character(self): return self._character

    def set_character(self, new_char):
        self._character = new_char
        return self
    
    def set_pose(self, new_pose):
        self._pose = new_pose
        return self

    def set_header(self, id): 
        self._header = id
        return self

    def global_state(self, dict):
        old_start = self.start
        def new_start():
            self._owner.update_global_state(dict)
            return old_start()
        self.start = new_start
        return self

    def mark(self, specs, tag="mark"): 
        if not isinstance(specs, list): specs = [specs]
        specs = [s if isinstance(s,dict) else {"thing": s} for s in specs]
        old_models = self.models
        def new_models():
            ms = old_models()
            for spec in specs:
                markable = find_thing(spec["thing"])
                ms.append((tag, markable.MakeMarker(spec)))
            return ms
        self.models = new_models
        self._marked = specs
        return self

    def mark_ui(self, thing, view_name, element_path, highlight_types, tag="ui_mark"):
        old_models = self.models
        def new_models():
            model = find_thing(thing)
            if not model: return old_models()
            view = next((v for v in model.AllViews if view_name in v.gameObject.name), None)
            element = view
            for path_segment in element_path:
                element = find_child_element(element, path_segment)
            return old_models() + [(tag, UIMUIHighlight(element, highlight_types))]
        self.models = new_models
        return self

    def mark_area(self, center, radius, tag="area_mark"):
        old_models = self.models
        def new_models():
            return old_models() + [(tag, AreaMarker(center, radius))]
        self.models = new_models
        return self

    def mark_line(self, a, b, material=None, tag="line_mark"):
        old_models = self.models
        def new_models():
            at = find_thing(a)
            bt = find_thing(b)
            return old_models() + [(tag, TutorialLineMarker(at, bt, material))]
        self.models = new_models
        return self

    def focus_first(self, zoom = None):
        return self.focus(self._marked[0]["thing"], zoom = zoom)

    def focus_all(self, zoom = None):
        return self.focus([m["thing"] for m in self._marked], zoom = zoom)

    def focus_point(self, x, y, zoom = None):
        old_start = self.start
        def new_start():
            focus_roughly(Vector2(x,y), zoom = zoom)
            return old_start()
        self.start = new_start
        return self

    def focus(self, focused, zoom = None): 
        old_start = self.start
        def new_start():
            fs = focused            
            if not isinstance(fs, list):
                fs = [fs]
            pos = sum((find_thing(t).Position for t in fs), start = Vector2.zero)
            pos /= len(fs)
            focus_roughly(pos, zoom = zoom)
            return old_start()
        self.start = new_start
        return self        

    def disable_actions(self):
        return self.limit_actions("<nothing>")

    def limit_actions(self, *actions):
        old_models = self.models
        def new_models():
            overrides = GameStateOverrides.Make(50).LimitActions(actions)
            return old_models() + [world.Add(GameStateLimiter(overrides))]
        self.models = new_models
        return self   

    def save(self):
        self._saving = True
        return self

##############################################
# Simple pageable text

class TutorialPage(TutorialStep):
    def __init__(self, id, page_no, *text_args):
        TutorialStep.__init__(self)
        self._id, self._no = id, page_no
        self._text_args = text_args or []
    
    def allows_actions(self): return False
    def id(self): return self._id
    def manual_advance(self): return True
    def ls_text(self): return LS("tutorial.%s-%d" % (self.id(), self._no), None, *self._text_args)


def TutorialPages(id, poses, header = None):
    pages = []
    for no, pose in enumerate(poses):
        page = TutorialPage(id, no+1).set_pose(pose)
        if header: page.set_header(header)
        pages.append(page)
    return pages

##############################################
# Helpers

def focus_roughly(position, zoom = None):
    """Provides a more 'natural' way to focus things."""
    cam = find("GameCamera")
    # calculate where best to go
    grace_radius = 2 / cam.EffectiveZoom
    displacement = position - cam.FocusedOn2D
    direction = displacement.normalized
    distance = displacement.magnitude
    min_move = distance * 0.5
    grace_move = distance - grace_radius
    move_distance = max(min_move, grace_move)
    target = cam.FocusedOn2D + direction * f(move_distance)
    # move
    cam.JumpTo(target)
    if zoom: cam.ZoomTo(zoom)

def find_thing(thing):
    if isinstance(thing, str):
        if thing.startswith("planet:"):
            planets = (p for p in every(Planet) if p.NodeIdentifier == thing)
            return next(planets, None)
        elif thing.startswith("pot:"):
            pots = (p for p in every(Potential) if p.NodeIdentifier == thing)
            return next(pots, None)
        elif thing.startswith("structure:"):
            kind = thing[10:]
            index = 0
            if ":" in kind:
                kind, index_str = kind.split(":")
                index = int(index_str)
            structures = [s for s in every(Structure) if s.Kind.ID == kind]
            structures.sort(key=lambda s: s.EstablishedOn)
            if index < 0 or index >= len(structures): return None
            return structures[index]
        elif thing.startswith("model:"):
            return find_with_class(thing[6:])
    elif isinstance(thing, tuple):
        a = find_thing(thing[0])
        b = find_thing(thing[1])
        return next((c for c in a.Connections if c.OtherEnd(a) == b), None)
    raise Exception("This does not specify a findable object: '%s'." % thing)

def find_child_element(element, child_spec):
    element = element.transform
    if isinstance(child_spec, tuple):
        child_name, child_index = child_spec
    else:
        child_name, child_index = child_spec, 0
    for i in range(element.childCount):
        child = element.GetChild(i)
        if child_name in child.gameObject.name: 
            if child_index == 0:
                return child
            else:
                child_index -= 1
    return None
