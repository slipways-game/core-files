# Defines many of the interactions used in the pre-game menus.
# Other 'Pages' are defined in mode-specific files to define the pre-game flow of eg. the campaign or standard.

class PreparationPage:
    """Base class for 'menu pages', which can offer a manual or automatic choice before the game starts."""
    def bind(self, host):
        self._host = host

    def rng(self, tag = ""):
        return self._host.RNG(self.__class__.__name__ + tag)

    def initialize(self): pass
    def move_in(self): pass
    def reset(self): pass
    def complete(self): pass
    def back_out(self): return False
    def delay(self): return 0.0

    def auto_skip(self): return False

class ImplicitPage(PreparationPage):
    """Base class for 'implicit' pages where the choice happens automatically and
       we skip to the next page immediately."""
    def auto_skip(self): return True

##############################################################

class PageAskAboutFirstGame(PreparationPage):
    def __init__(self):
        self._answered = game.Selections.GetObject("cleared_quick_start", False)

    def move_in(self):
        if not self._answered:
            return prep.Views.ShowYesNoMessage(LS("menus.quick_start.header"), LS("menus.quick_start"), self.confirm, ["sure", "no_thanks"])
        else:
            prep.UI.PushAndGoTo("PageSelectGameMode()")

    def confirm(self, confirmed):
        game.Selections.Set("cleared_quick_start", True)
        game.Selections.SaveToDisk()
        if confirmed:
            prep.Configuration.GameConfig.GameMode = "standard"
            prep.UI.PushAndGoTo("modes/standard", "QuickStartFirstGame()")
        else:
            self._answered = True
            prep.UI.PushAndGoTo("PageSelectGameMode()")
    
    def back_out(self):
        return True

    def auto_skip(self):
        return self._answered


##############################################################

class PageSelectGameMode(PreparationPage):
    BUILTIN_MODES = ["modes/standard", "modes/campaign", "modes/sandbox", "modes/ranked"]
    POSITIONS = {
        "modes/standard": { "offset": Vector2(0,-12), "size": 1.1 },
        "modes/ranked": {"offset": Vector2(0,-345) },
        "modes/sandbox": {"offset": Vector2(-250,-140) },
        "modes/campaign": {"offset": Vector2(250,-140) },
    }

    def breadcrumb(self, mode_package):
        self.load_mode(mode_package)
        return BreadcrumbResult.Consume | BreadcrumbResult.SkipPage
    
    def initialize(self):
        options = [self.make_option(m) for m in self.BUILTIN_MODES]
        mode_select = prep.Views.ShowModeSelect({
            "positioning": {"pivot": Vector2(0.5, 0.5), "anchor": Vector2(0.5, 0.5), "offset": Vector2(0, 190)},
            "modes": options
        })
        mod_op_view = None
        mod_options = self.mod_options()
        if mod_options and len(mod_options) > 0:
            mod_op_view = prep.Views.ShowModOptions({
                "title": LS("menus.button.modded_game_modes"),
                "positioning": {"pivot": Vector2(0.5, 0.5), "anchor": Vector2(0.5, 0.59), "offset": Vector2(0, 190)},
                "options": mod_options
            })
        prep.Views.SetupGamepadSupport({
            "sources": [mode_select, mod_op_view],
            "bind_page_navigation": True
        })
        prep.Views.ChangeBackground("down")

    def back_out(self):
        return True # we'd like to be dropped
    
    def buttons(self):
        return [prep.UI.BackButton()]

    def mod_options(self):
        conds = conditions.Supporting("mod_new_game_mode")
        added_modes = []
        for cond in conds:
            spec = cond.PythonObject.mod_new_game_mode()
            def loader():
                self.load_mode(spec["package"], spec.get("mode_type", "standard"))
            added_modes.append({
                "label": spec["label"],
                "custom_mode": self.package_to_custom_mode(spec["package"]),
                "start_game_callback": loader
            })
        return added_modes

    def make_option(self, mode_package):
        meta = MetaProgression.find()
        mode_name = mode_package.replace("modes/", "")
        # determine if it's disabled and why
        permission = Permission.Yes()             
        unlock_permission = meta.permission("mode.%s" % mode_name)
        if FeatureFlags.Testing:
            unlock_permission = Permission.Yes()
        permission = permission.CombineWith(unlock_permission)
        # return
        option = {
            "id": mode_name,
            "start_game_callback": lambda: self.load_mode(mode_package),
            "enabled": permission
        }
        option.update(self.POSITIONS[mode_package])
        return option
    
    def load_mode(self, mode, mode_name = None):
        self._mode = mode
        mode_name = mode_name or mode.replace("modes/", "")
        prep.Configuration.GameConfig.GameMode = mode_name
        if mode.startswith("mods/"):            
            prep.Configuration.GameConfig.CustomGameMode = self.package_to_custom_mode(mode)
        else:
            prep.Configuration.SetBreadcrumbs([mode])
        if mode == "modes/standard":
            prep.Configuration.SetBreadcrumbs([mode], ["stats"])
        prep.UI.PushAndGoTo(mode, "ModeMenu()")

    def package_to_custom_mode(self, mod_package):
        mod_name = "/".join(mod_package.split("/")[:2])
        return mod_name

class PageSetSaveFileBasedOnSector(ImplicitPage):
    """Changes the save file used for saving/loading."""
    def move_in(self):
        cfg = prep.Configuration.GameConfig
        name = "%s-%d" % (cfg.Sector.Seed.lower(), Randomness.RandomSeed)
        cfg.SaveName = name

class PageSetDescription(ImplicitPage):
    def __init__(self, pattern):
        self._pattern = pattern

    def move_in(self):
        prep.Configuration.GameConfig.ScenarioDescription = self._resolve_description()

    def _resolve_description(self):
        cfg = prep.Configuration.GameConfig
        desc = self._pattern
        desc = desc.replace("{mode}", LS("mode.%s" % cfg.GameMode))
        desc = desc.replace("{sector}", cfg.Sector.Seed)
        desc = desc.replace("{difficulty}", cfg.Difficulty.LName)
        if cfg.RankedInfo is not None:
            desc = desc.replace("{week}", LS("menus.ranked.week_no", None, cfg.RankedInfo.Week))
        return desc

class PageSetDifficulty(ImplicitPage):
    """Sets a hardcoded difficulty level."""
    def __init__(self, difficulty_id):
        self._difficulty = difficulty_id
    def initialize(self):
        game.Configuration.SetDifficulty(self._difficulty)

class PageCredits(PreparationPage):
    def initialize(self):
        credits = prep.Views.ShowCredits()
        prep.Views.SetupGamepadSupport({
            "sources": [credits],
            "bind_page_navigation": True
        })
        prep.Views.ChangeBackground("close")

    def back_out(self):
        return True # we'd like to be dropped

    def buttons(self):
        return [prep.UI.BackButton()]    

class PageSelectDifficulty(PreparationPage):
    """Lets the player select a difficulty level from a menu."""
    DIFFICULTIES = ["forgiving", "reasonable", "challenging", "tough"]

    def initialize(self):
        options = [self.make_option(diff) for diff in self.DIFFICULTIES]
        prep.Views.ShowMenu({
            "header": LS("menu.header.difficulty", "Choose difficulty"),
            "frameless": True,
            "options": options
        })
        prep.Views.ChangeBackground("main")

    def buttons(self):
        return [prep.UI.BackButton()]
    
    def make_option(self, diff):
        return {
            "label": LS("difficulty.%s" % diff),
            "callback": lambda: self.set_difficulty(diff)
        }

    def set_difficulty(self, diff):
        prep.Configuration.SetDifficulty(diff)
        prep.UI.CompleteAndGoForward()

class PageSelectRacesAndPerks(PreparationPage):
    """Lets the player manually select races."""
    def __init__(self, races = None, perks = None, segments = None):
        self._specified_race_count = races
        self._specified_perk_count = perks
        self._confirmed_warning = False
        self._segments = segments or [
            {"name": "tech_badges"},
            {"name": "perk_buttons"}
        ]
        self._setup_obj = None
        self._select_cfg = {}

    def initialize(self):
        # clear council, select anew
        game.Council.Clear()
        # setup
        if self._setup_obj is None:
            for setup_cond in game.Conditions.Supporting("menu_flow_setup"):
                self._setup_obj = setup_cond.PythonObject
                self._select_cfg = self._setup_obj.select_screen() if hasattr(self._setup_obj, "select_screen") else {}            
        # use the configuration provided
        self._perks_to_select = self._specified_perk_count or self._select_cfg.get("perks_to_pick", None) or constants.Int("perks.to_pick")
        self._perks_per_race = self._select_cfg.get("perks_per_race", 1)
        self._races_to_select = self._specified_race_count or self._select_cfg.get("races_to_pick", None) or constants.Int("races.to_pick")
        # ensure techs exist (since the selector now relies on them having KnownTech)
        races = list(Race.AllPlayable)
        for race in races:
            key = potential_techs_key(race)
            techs = game.CustomData.GetOr(key, [])
            for tech_kind in techs:
                game.Technology.Unlock(tech_kind, UnlockSource.FromRace(race), True)
        # show UI
        prep.Views.ShowHeader({
            "height": 600,
            "live_text": self.header_text
        })
        prep.Views.ShowFooter({
            "height": 700
        })
        race_select = prep.Views.ShowRaceSelect({
            "footer_position": Vector2(0.5, 0.04),
            "main_position": self._select_cfg.get("main_position", Vector2(0.5, 0.5)),
            "race_count": self._races_to_select, "perk_count": self._perks_to_select, 
            "max_perks_per_race": self._perks_per_race,
            "callback": self.confirm_races,
            "race_segments": self._segments,
            "preselect": self._select_cfg.get("preselect_races", None),
            "lock_races": self._select_cfg.get("lock_races", False),
            "block_width": self._select_cfg.get("block_width", None),
            "portrait_scale": self._select_cfg.get("portrait_scale", None)
        })
        prep.Views.SetupGamepadSupport({
            "sources": [race_select],
            "bind_page_navigation": True
        })
        prep.Views.ChangeBackground("close")

    def reset(self):
        game.Council.Clear()

    def back_out(self):
        game.Technology.Clear()
        self._setup_obj, self._select_cfg = None, {}

    def complete(self):
        perks_selected = any(m.SelectedPerks.Count > 0 for m in game.Council.Members)
        if not perks_selected and not self._confirmed_warning:
            return prep.Views.ShowYesNoMessage(LS("warning.no_perks.header"), LS("warning.no_perks"), self.confirm)
        game.Technology.Clear()
    
    def confirm(self, confirmed):
        if confirmed:
            self._confirmed_warning = True
            prep.UI.CompleteAndGoForward()

    def buttons(self):
        start = self._select_cfg.get("forward_button_text", LS("menus.start_game"))
        permitted = Permission.Yes()
        if sum(1 for m in game.Council.Members) != self._races_to_select:
            permitted = Permission.No(LS("menus.race_select_condition", "Select *{1}* races to proceed.", self._races_to_select))
        return [prep.UI.BackButton(), prep.UI.ForwardButton(start, permitted)]

    def show_highscore(self):
        difficulty = game.GameConfig.Difficulty
        highscore = StandardStorage.find().get_highscore(difficulty)
        if highscore is not None:
            prep.Views.ShowHighscore({
                "position": {"offset": Vector2(0, 365), "pivot": Vector2(0.5, 0), "anchor": Vector2(0.5, 0) },
                "label": LS("menus.highscore.header", "Your best ({1}):", difficulty.LName),
                "score": highscore["score"],
                "stars": highscore["stars"]
            })

    def header_text(self):
        selected_races = sum(1 for m in game.Council.Members)
        selected_perks = sum(len(list(m.SelectedPerks)) for m in game.Council.Members)
        header = L("menus.race_selection.header", "Select your council")
        subheader = L("menus.race_selection.subheader", "{1}/{2} races :separator: {3}/{4} perks", selected_races, self._races_to_select, selected_perks, self._perks_to_select)
        subheader = "[s:PrepSubheader]" + subheader + "[/s]"
        return header + "\n" + subheader
    
    def confirm_races(self, races):
        prep.UI.CompleteAndGoForward()

class PageRacesAutoAssign(ImplicitPage):
    """Automatically selects races."""
    def __init__(self, count):
        self._count = count

    def initialize(self):
        rng = self.rng()
        possible_races = list(Race.AllPlayable)
        races = Randomness.PickMany(rng, possible_races, self._count)
        for race in races:
            game.Council.Add(race)

    def reset(self):
        game.Council.ClearMembers()

class PageRacesForce(ImplicitPage):
    """Force selection of certain races."""
    def __init__(self, *race_ids):
        self._race_ids = race_ids

    def initialize(self):
        for rid in self._race_ids:
            race = Race.All[rid]
            game.Council.Add(race)

    def reset(self):
        game.Council.ClearMembers()

class PageTechsForceUnlock(ImplicitPage):
    """Unlocks hardcoded technologies for this scenario."""
    def __init__(self, *tech_ids):
        self._tech_ids = tech_ids
    
    def initialize(self):
        for tech_id in self._tech_ids:
            game.Technology.Unlock(TechKind.All[tech_id], UnlockSource.FromScenario(), True)
    
    def reset(self):
        for tech_id in self._tech_ids:
            game.Technology.Forget(TechKind.All[tech_id])

class PageTechsAutoAssign(ImplicitPage):
    """Automatically assigns technologies from given tech levels using pattern strings."""
    def __init__(self, *level_patterns):
        self._patterns = level_patterns

    def initialize(self):
        rng = self.rng()
        unlocked = []
        races = Randomness.PickMany(rng, [m.Race for m in game.Council.Members], len(self._patterns)) 
        for index, race in enumerate(races):
            tp = TechParameters()
            tp.Race = race
            level_pattern = self._patterns[index]
            race_techs = list(game.Technology.Randomization.RandomTechs(tp, level_pattern, unlocked, rng))
            race_techs.sort(key=lambda t: -t.BaseTier) # hack: reverse tier order ensures that we don't get already unlocked techs as descendants of low tier techs
            for tech in race_techs:
                game.Technology.Unlock(tech, UnlockSource.FromRace(race), True)
            unlocked += race_techs
        self._unlocked = unlocked

    def reset(self):
        for tech in self._unlocked:
            game.Technology.Forget(tech)

class PageAddPackage(ImplicitPage):    
    """Adds a package that the main engine will have to load for the scenario to work."""
    def __init__(self, pkg):
        self._pkg = pkg

    def complete(self):
        game.Configuration.AddScenarioPackage(self._pkg)
    def reset(self):
        game.Configuration.DropScenarioPackage(self._pkg)

class PageLoadPackageNow(ImplicitPage):
    """Loads a package right now."""
    def __init__(self, pkg):
        self._pkg = pkg

    def complete(self):
        log("Loading package %s" % self._pkg)
        game.Setup.LoadPackageNow(self._pkg)

    def reset(self):
        log("Unloading package %s" % self._pkg)
        game.Setup.UnloadPackageNow(self._pkg)

### Starting the game, from scratch or from a save file.

class PageStartScenario(ImplicitPage):
    """Starts the game."""
    def initialize(self):
        game.StartScenario()    

class PageAddMutator(ImplicitPage):
    def __init__(self, mutator_fn):
        self.mutator_fn = mutator_fn

    def initialize(self):
        fn = self.mutator_fn
        game.Configuration.AddMutator(fn())

class PageSetSavefile(ImplicitPage):
    """Sets a hardcoded savefile to start the game from."""
    def __init__(self, filename):
        self._filename = filename
    def initialize(self):
        game.Configuration.CustomData.Set("savefile", self._filename)

class PageConfigure(ImplicitPage):
    def __init__(self, configurator):
        self._configurator = configurator
    def initialize(self):
        self._configurator(game.Configuration.GameConfig)

class PageRandomSector(ImplicitPage):
    def __init__(self, sector_props = None, preset_seeds = None):
        self._preset_seeds = preset_seeds
        self._sector_props = sector_props or {}
    def initialize(self):
        if self._preset_seeds:
            seed = Randomness.Pick(self._preset_seeds)
            game.Configuration.SetSectorFromSeed(seed)
        else:
            game.Configuration.RandomizeSector(self._sector_props)

class PageLoadState(ImplicitPage):
    """Starts a game basing it on a save state, defined in the configuration."""
    def initialize(self):
        savefile = game.Configuration.CustomData.Get("savefile")
        game.LoadGame(savefile)

################################################################
# Potential techs

class PagePickPotentialTechs(ImplicitPage):
    def __init__(self, pattern):
        self._pattern = pattern

    def initialize(self):
        cfg = {}
        setup_obj = None
        # outside config?
        for setup_cond in game.Conditions.Supporting("menu_flow_setup"):
            setup_obj = setup_cond.PythonObject
            if hasattr(setup_obj, "potential_techs"):
                cfg = setup_obj.potential_techs()
        # configure stuff
        rng = self.rng()
        races = Randomness.Shuffle(rng, list(Race.AllList))
        pattern = cfg.get('pattern', None) or self._pattern
        pattern_for_race = cfg.get('pattern_for_race', None) or {r.ID: pattern for r in races}
        # regenerate
        for race in races:
            game.CustomData.Clear(potential_techs_key(race))
        for race in races:
            regenerate_potential_techs(rng, race, pattern_for_race[race.ID])
        if setup_obj and hasattr(setup_obj, "forced_techs"):
            for race_id, tech_id in setup_obj.forced_techs():
                race = Race.All[race_id]
                existing = game.CustomData.Get(potential_techs_key(race))
                existing.append(TechKind.All[tech_id])
                game.CustomData.Set(potential_techs_key(race), existing)

def regenerate_potential_techs(rng, race, pattern):
    already_used = []
    races = list(Race.AllList)
    for r in races:
        if r != race:
            already_used += game.CustomData.GetOr(potential_techs_key(r), [])
    # technology
    race_techs = []
    if pattern == "all":
        race_techs = [tk for tk in TechKind.AllList if race in tk.Races and tk.IsRoot]
    else:
        tp = TechParameters()
        tp.Race = race
        race_techs = list(game.Technology.Randomization.RandomTechs(tp, pattern, already_used, rng))
    race_techs.sort(key=lambda tk: "%02d%02d%s" % (tk.BaseTier, tk.Sublevel, tk.LName))
    game.CustomData.Set(potential_techs_key(race), race_techs)                        
    return race_techs            

def potential_techs_key(race):
    return "potential_techs_%s" % race.ID

class PageUnlockPotentialTechs(ImplicitPage):
    def complete(self):
        for m in game.Council.Members:
            race = m.Race
            key = potential_techs_key(race)
            techs = game.CustomData.Get(key)
            game.CustomData.Clear(key)
            for tech_kind in techs:
                game.Technology.Unlock(tech_kind, UnlockSource.FromRace(race), True)

    def reset(self):
        game.Technology.Clear()

################################################################
# Perks

class PagePickPotentialPerks(ImplicitPage):
    def __init__(self, count_per_race):
        self._count = count_per_race

    def initialize(self):
        if self.set_predefined_perks(): return
        rng = self.rng()
        for race in Race.AllPlayable:
            regenerate_potential_perks(rng, race, self._count)

    def set_predefined_perks(self):
        for gc in conditions.Supporting("menu_flow_setup"):
            gc = gc.PythonObject
            if hasattr(gc, "perks_available"):
                perks = list(gc.perks_available())
                perks_by_race = {r: [] for r in Race.AllPlayable}
                for perk_id in perks:
                    perk = PerkKind.All[perk_id]
                    perks_by_race[perk.Race] += [perk]
                for race, perk_list in perks_by_race.items():
                    game.CustomData.Set(PagePickPotentialPerks.key(race), perk_list)
                return True
        return False
    
    @staticmethod
    def key(race):
        return "potential_perks_%s" % race.ID

def regenerate_potential_perks(rng, race, count):
    possible = list(race.Perks)
    perks = list(Randomness.PickMany(rng, possible, count))
    game.CustomData.Set(PagePickPotentialPerks.key(race), perks)

#################################################################
# Sectors

class PageCommonSelectSector(PreparationPage):
    def __init__(self, mode, seeds=None, message=None):
        self._mode = mode
        self._seeds = seeds
        self._message = message
        self._auto_show_stats = False
        self._auto_seed = None
        self._restarted_seed = False

    DIFFICULTIES = ["forgiving", "reasonable", "challenging", "tough"]
    SANDBOX_DIFFICULTIES = ["sandbox"]
    
    def breadcrumb(self, crumb):
        if crumb == "stats" and not FeatureFlags.StableBranch:
            self._auto_show_stats = True
        if crumb.startswith("seed:"):
            self._auto_seed = crumb[5:]
        return BreadcrumbResult.Consume
    
    def initialize(self):
        if self._mode == "sandbox":
            self._difficulties = self.SANDBOX_DIFFICULTIES
        else:
            self._difficulties = self.DIFFICULTIES
        prep.Views.ChangeBackground("galaxy")
        custom_mode = game.GameConfig.CustomGameMode
        raw_name = custom_mode.replace("mods/", "") if custom_mode else ""
        prep.Views.ShowHeader({
            "height": 600,
            "text": LS("mode.%s.title" % raw_name) if custom_mode else LS("mode.%s" % self._mode)
        })
        prep.Views.ShowFooter({
            "height": 700
        })
        self._known_seed_msg = None
        if self._mode == "standard":
            self._known_seed_msg = prep.Views.ShowMessage({
                "positioning": {"anchor": Vector2(0.5, 1), "pivot": Vector2(0.5, 1), "offset": Vector2(0, -200)},
                "text": "",
                "initially_visible": False
            })
        difficulty_select = prep.Views.ShowDifficultySelect({
            "positioning": {
                "anchor": Vector2(0.5, 1),
                "pivot": Vector2(0.5, 1),
                "offset": Vector2(0, -180)
            },
            "delay": 0.5,
            "storage_key": "%s_difficulty" % self._mode,
            "levels": self._generate_difficulty_levels()
        })
        # message?
        if self._message:
            prep.Views.ShowMessage({
                "positioning": {
                    "anchor": Vector2(0.5, 1), "pivot": Vector2(0.5, 1), "offset": Vector2(0, -200)
                },
                "text": self._message.ToString()
            })
        # actual seed selectors
        allowed_sector_types = [st["seed_index"] for st in Seeds().sector_types()]
        options = prep.Selections.GetObject("seed_select")
        self._seed_select = prep.Views.ShowSeedSelection({
            "sector_types": allowed_sector_types,
            "locked_to_seeds": self._seeds,
            "quirks_unlocked": MetaProgression.find().permission("quirks") if not FeatureFlags.Testing else Permission.Yes(),
            "sector_changed_callback": self._when_sector_changes
        }, options)
        self._seed_map = prep.Views.ShowSeedMap({
            "position": Vector3(0, 0.75, 20),
            "size": 5.37,
            "rotation": Vector3(60, 0, 0),
            "is_locked_down": self._seeds is not None
        })
        buttons = [{
            "icon": "icon_randomize",
            "callback": self.randomize,
            "tooltip": LS("menus.randomize_sector.tooltip")
        }]
        if not FeatureFlags.StableBranch:
            buttons.append({
                "icon": "icon_statistics",
                "callback": self.show_stats,
                "tooltip": LS("button.stats_achievements.tooltip")
            })
        button_footer = prep.Views.ShowButtonFooter({"buttons": buttons})
        if self._auto_show_stats:
            self.show_stats()
            self._auto_show_stats = False
        prep.Views.RecheckAchievements(self._mode)
        # gamepad support
        prep.Views.SetupGamepadSupport({
            "sources": [self._seed_select, self._seed_map, button_footer, difficulty_select],
            "bind_page_navigation": True
        })
        # fake initial update
        self._when_sector_changes(self._seed_select.CurrentSector)

    def _generate_difficulty_levels(self):
        levels = [{"id": d, "available": Permission.Yes(), "is_default": False} for d in self._difficulties]
        levels[min(len(levels)-1, 1)]["is_default"] = True
        for lv in range(4, len(levels)):
            levels[lv]["available"] = Permission.No(LS("difficulty.tough_plus.locked"))
        return levels
        
    def complete(self): self.save_options()        
    def back_out(self):
        self.save_options()
        return False
    
    def save_options(self):
        prep.Selections.SetObject("seed_select", self._seed_select.ExtractSelections())
        prep.Selections.SaveToDisk()

    def randomize(self):
        if self._seeds:
            if len(self._seeds) > 1:
                seed = Randomness.PickExcluding(self._seeds, lambda s: self._seed_select.CurrentSector and self._seed_select.CurrentSector.Seed == s)
            else:
                seed = self._seeds[0]
            self._seed_select.MoveToSeed(seed)
        else:
            self._seed_select.MoveToRandomSector()

    def show_stats(self):
        prep.Views.ShowStatsAchievementsWindow()
        
    def move_in(self):
        if self._auto_seed:
            self._seed_select.MoveToSeed(self._auto_seed)
        else:
            self.randomize()

    def buttons(self):
        start = LS("menus.sector_selection.accept", "Accept sector")
        permitted = Permission.Yes()
        sector_type = self._seed_select.SelectedSectorType
        if sector_type and not sector_type.Permission.Allowed:
            permitted = permitted.CombineWith(sector_type.Permission)
        return [prep.UI.BackButton(), prep.UI.ForwardButton(start, permitted)]

    def _when_sector_changes(self, sector):
        if not sector: return
        if self._auto_seed is not None and sector.Seed != self._auto_seed:
            self._auto_seed = None
        if self._known_seed_msg is None: return
        if sector.KnownSeed:
            msg_text = L("achievement.ui.known_seed_warning") if self._auto_seed is None else L("achievement.ui.restart_warning")
            msg_text = "<align=center>" + msg_text
            msg_text = styled(msg_text, "Bad")
            self._known_seed_msg.SetText(msg_text)
        self._known_seed_msg.SetVisibility(sector.KnownSeed)

class PageActivateEarlyMutatorEffects(ImplicitPage):
    def complete(self):
        self._activations = []
        for mutator in game.GameConfig.Sector.Mutators:
            for pkg in mutator.Packages:                
                game.Setup.LoadPackageNow(pkg)
            a = world.Add(MutatorActivation(mutator, earlyEffectsOnly = True))
            self._activations.append((mutator, a))        

    def reset(self):
        for mutator, activation in self._activations:
            activation.Discard()
        for mutator, activation in self._activations:
            for pkg in mutator.Packages:
                game.Setup.UnloadPackageNow(pkg)

class PageAlterFlowIfRequested(ImplicitPage):
    def complete(self):
        alters = list(game.Conditions.Supporting("altered_menu_flow"))
        if len(alters) > 0:
            alter = alters[0]
            prep.UI.InterruptAndGoTo(*alter.PythonObject.altered_menu_flow())

class PageReloadGameDataForSeedVersion(ImplicitPage):
    def complete(self):
        seed_version = game.GameConfig.Sector.SeedVersion
        prep.ReconfigureGameBasedOnSeedVersion(seed_version)

    def reset(self):
        prep.ReconfigureGameToDefaultVersion()
