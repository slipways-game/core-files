class ModeMenu:
    def pages(self):
        scenario_base_package = CampaignContents.SCENARIO_BASE_PACKAGE
        return [
            PageRandomSector(),
            PageAddPackage(scenario_base_package),
            PageSelectCampaignScenario(),
        ]

class StdMissionMenuFlow:
    def __init__(self, mission_pkg, main_mission_class):
        self._mission_pkg = mission_pkg
        self._main_mission_class = main_mission_class
    def pages(self):        
        mission_package = self._mission_pkg
        return [
            PageLoadPackageNow(mission_package),
            PageRandomSector(),
            PageActivateEarlyMutatorEffects(),
            PageMissionBriefing(self._main_mission_class),
            PagePickPotentialTechs('012344'),
            PageSetSavefileForMission(self._main_mission_class),
            PageSetPerksForMission(self._main_mission_class),
            PageSelectRacesAndPerks(),
            PageUnlockPotentialTechs(),
            PageTechsForceUnlock('slipstream_relay'),
            PageStartScenario()
        ]

class PageSelectCampaignScenario(PreparationPage):
    DIFFICULTIES = ["forgiving", "reasonable", "challenging", "tough"]

    def __init__(self):
        self._scenarios = CampaignContents.SCENARIOS
        self._scenario_select, self._header = None, None

    def initialize(self):
        # difficulty setting and data load
        diff = game.Selections.GetObject("campaign_difficulty", "reasonable")
        game.Configuration.SetDifficulty(diff)
        game.Setup.SetRuntimeVariant("difficulty", diff)
        game.Conditions.Activate('CampaignStorage()')
        # views
        prep.Views.ChangeBackground("galaxy")
        self._header = prep.Views.ShowHeader({
            "height": 600,
            "text": self._generate_header(),
            "delay": 0.2
        })
        prep.Views.ShowFooter({
            "height": 700
        })        
        button_footer = prep.Views.ShowButtonFooter({
            "buttons": [
                {
                    "icon": "icon_statistics",
                    "callback": self.show_stats,
                    "tooltip": LS("button.stats_achievements.tooltip")
                }
            ]
        })
        difficulty_select = prep.Views.ShowDifficultySelect({
            "positioning": {
                "anchor": Vector2(0.5, 1),
                "pivot": Vector2(0.5, 1),
                "offset": Vector2(0, -211)
            },
            "delay": 0.5,
            "storage_key": "campaign_difficulty",
            "levels": [{"id": d, "available": Permission.Yes(), "is_default": d == "reasonable"} for d in self.DIFFICULTIES],
            "when_selected": self.when_difficulty_changes
        })
        self._scenario_select = prep.Views.ShowScenarioSelector({
            "position": Vector3(0, 0.2, 20),
            "size": 5.22,
            "rotation": Vector3(63, 0, 0),
            "scenarios": list(self._generate_mission_selectors())
        })
        prep.Views.SetupGamepadSupport({
            "sources": [self._scenario_select, difficulty_select, button_footer],
            "bind_page_navigation": True
        })
        self._check_campaign_achievements()

    def complete(self):
        selected_id = self._scenario_select.Selected.ID
        mission = CampaignContents.SCENARIOS[selected_id]
        game.Configuration.ClearMutators()
        game.Configuration.AddMutator(mission["main_mutator"])
        prep.Views.ChangeBackground("close")
        prep.UI.PushAndGoTo(None, mission["menu_flow"])

    def back_out(self):
        game.Configuration.ClearMutators()
        return False

    def buttons(self):
        start = LS("campaign.button.start")
        start_permission = Permission.Yes()
        permitted = self._scenario_select and self._scenario_select.Selected
        if not permitted:
            start_permission = Permission.No(LS("campaign.warning.select_scenario"))
        return [prep.UI.BackButton(), prep.UI.ForwardButton(start, start_permission)]

    def show_stats(self):
        prep.Views.ShowStatsAchievementsWindow()

    def when_difficulty_changes(self, _):
        if not self._scenario_select: return
        game.Setup.SetRuntimeVariant("difficulty", game.GameConfig.Difficulty.ID)
        self._header.UpdateText(self._generate_header())
        scenarios = list(self._generate_mission_selectors())
        self._scenario_select.UpdateScenarios(scenarios)
        self._check_campaign_achievements()

    def _generate_header(self):
        custom_mode = game.GameConfig.CustomGameMode
        raw_name = custom_mode.replace("mods/", "") if custom_mode else ""
        if custom_mode:
            header_text = LPlainStr("mode.%s.title" % raw_name)
        else:
            header_text = LPlainStr("campaign.select_scenario.header")
        sub_text = ""
        header_text += "\n[s:PrepSubheader]%s[/s]" % sub_text
        return header_text

    def _check_campaign_achievements(self):
        stored_data = CampaignStorage.find()
        rank_counts = {}
        for scenario_id, scenario in self._scenarios.items():
            best = stored_data.status_for(scenario_id)
            if best and (best["rank"] is not None):
                for rank in xrange(0, best["rank"] + 1):
                    rank_counts[rank] = rank_counts.get(rank, 0) + 1
        for a in game.Achievements.Achievements:
            if hasattr(a.PythonObject, "campaign_menu_check"):
                a.PythonObject.campaign_menu_check(rank_counts)
        
    UNKNOWN_SCENARIO = {
        "label": "???",
        "description": "This scenario is not yet available - coming soon!"
    }
    def _generate_mission_selectors(self):
        stored_data = CampaignStorage.find()        
        for id, scenario in self._scenarios.items():
            s = scenario.copy()
            best = stored_data.status_for(id)
            # generate tag
            tag = None
            if best is not None:
                tag = ScoreRanks.SpriteString(stored_data.stars_for(id), False, "campaign")
            # icon name
            icon_name = s["icon"] if "icon" in s else "scenario_%s" % id[2:]            
            # is locked?
            permission = Permission.Yes()            
            prerequisites_unlocked = all(stored_data.is_completed_on_any_difficulty(prereq) for prereq in s.get("requires", []))
            if FeatureFlags.Testing:
                prerequisites_unlocked = True
            if not prerequisites_unlocked:
                permission = Permission.No(LS("locked.previous_missions"))
            # set up data
            is_info_node = False
            hidden = False
            mutator = s.get("main_mutator")
            if mutator:
                mutator = mutator()
                if "missing" in mutator:
                    icon_name = "missing"
            elif s.get("info_node") is not None:
                is_info_node = True
                mutator = s.get("info_node")()
                permission = Permission.NoWithNoReason()
                tag = ""
                if not prerequisites_unlocked:
                    hidden = True
            else:
                mutator = self.UNKNOWN_SCENARIO
                permission = Permission.No(LS("locked.mission_act%d" % s["act"]))
                tag = ""
            s["id"] = id
            s["normalized_position"] = Vector2(*s["position"])
            s["label"] = mutator["label"]
            s["tag"] = tag
            s["icon"] = icon_name if permission.Allowed else "scenario_locked"
            s["description"] = mutator["description"] if (permission.Allowed or is_info_node) else permission.ToString()
            s["best_score"] = best["score"] if best else None
            s["best_rank"] = best["rank"] if best else None
            s["available"] = permission
            s["hidden"] = hidden
            if is_info_node:
                s["label"] = None
                s["icon"] = "scenario_info"
            yield s

class PageMissionBriefing(PreparationPage):
    def __init__(self, main_mission_class):
        self._main_mission_class = main_mission_class
        self._mission = None

    def initialize(self):
        if self._mission is None:
            self._mission = game.Conditions.GetOrCreate(self._main_mission_class)
            self._mission.Activate()
            self._mission_obj = self._mission.PythonObject
        prep.Views.ShowHeader({
            "height": 600,
            "text": self._mission_obj.title()      
        })
        prep.Views.ShowFooter({
            "height": 700
        })
        # briefing
        briefing_items = list(self._mission_obj.briefing_contents())
        prep.Views.ShowBriefingComputer()
        briefing_scroll = prep.Views.ShowBriefingContents(briefing_items)
        prep.Views.SetupGamepadSupport({
            "sources": [briefing_scroll],
            "bind_page_navigation": True
        })
        prep.Views.ChangeBackground("close")

    def complete(self):
        pass

    def back_out(self):
        self._mission.DeactivateAndKill()
        self._mission = None
        return False

    def buttons(self):
        button_text = LS("campaign.button.select_council")
        return [prep.UI.BackButton(), prep.UI.ForwardButton(button_text, Permission.Yes())]

class PageSetPerksForMission(ImplicitPage):
    def __init__(self, main_mission_class):
        self._main_mission_class = main_mission_class

    def initialize(self):
        mission = game.Conditions.Get(self._main_mission_class).PythonObject
        if hasattr(mission, "perks_available"):
            perks = list(mission.perks_available())
            perks_by_race = {r: [] for r in Race.AllPlayable}
            for perk_id in perks:
                perk = PerkKind.All[perk_id]
                perks_by_race[perk.Race] += [perk]
            for race, perk_list in perks_by_race.items():
                game.CustomData.Set(PagePickPotentialPerks.key(race), perk_list)
        else:
            log("No perk list in mission.")

class PageSetSavefileForMission(ImplicitPage):
    def __init__(self, main_mission_class):
        self._main_mission_class = main_mission_class

    def initialize(self):
        mission = game.Conditions.Get(self._main_mission_class).PythonObject
        cfg = prep.Configuration.GameConfig
        cfg.SaveName = mission.scenario_id()
        cfg.ScenarioDescription = mission.title()
