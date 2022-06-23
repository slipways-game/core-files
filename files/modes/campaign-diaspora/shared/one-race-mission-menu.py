###############################################
# "Borrow techs" menu flow

if "StdMissionMenuFlow" in globals():
    class OneRaceMissionMenuFlow(StdMissionMenuFlow):
        def __init__(self, *args):
            StdMissionMenuFlow.__init__(self, *args)
        def pages(self):
            pages = StdMissionMenuFlow.pages(self)
            added_pages = [
                PageBorrowTechs(2)
            ]
            for idx, p in enumerate(pages):
                if p.__class__ == PageSelectRacesAndPerks:
                    insert_index = idx + 1
                    pages[insert_index:insert_index] = added_pages
                    break
            return pages

class PageBorrowTechs(PreparationPage):
    def __init__(self, max_borrowed):
        self._setup_obj = None
        self._max_borrowed = max_borrowed

    def initialize(self):
        game.Technology.Clear()
        # setup
        for setup_cond in game.Conditions.Supporting("menu_flow_setup"):
            self._setup_obj = setup_cond.PythonObject
            self._offered_techs = self._setup_obj.borrowed_techs() if hasattr(self._setup_obj, "borrowed_techs") else {}
        # set selectable stuff for each race
        played_race = list(game.Council.Members)[0].Race
        for race in Race.AllPlayable:
            if race.ID in self._offered_techs:
                entries = self._offered_techs[race.ID]
                techs = []
                for entry in entries:
                    if isinstance(entry, str):
                        techs.append(TechKind.All[entry])
                    else:
                        for option in entry:
                            tk = TechKind.All[option]                            
                            if not played_race in tk.Races:
                                techs.append(tk)
                                break
                for tk in techs:
                    game.Technology.Unlock(tk, UnlockSource.FromRace(race))
                game.CustomData.Set("selectable_techs_%s" % race.ID, [game.Technology.Tech(tk) for tk in techs])
        # show the options
        races = [r for r in Race.AllPlayable if game.Council.Member(r) is None]
        self._option_view = prep.Views.ShowAdditionalRaceOptions({
            "shown_races": races,
            "race_segments": [
                {"name": "selectable_techs", "config": {}}
            ],
            "block_width": 350,
            "portrait_scale": f(0.7),
            "action_handler": self.handle_action
        })
        prep.Views.ShowHeader({
            "height": 600,
            "live_text": self.header_text
        })
        prep.Views.SetupGamepadSupport({
            "sources": [self._option_view],
            "bind_page_navigation": True
        })
        prep.Views.ChangeBackground("close")

    def handle_action(self, action):
        if isinstance(action, KnownTech):
            tech = action
            selected = game.CustomData.GetOr("selectable_techs_selection", [])
            if tech in selected:
                selected.remove(tech)
            else:
                selected = [s for s in selected if s.Source.Race != tech.Source.Race]
                selected.append(tech)
                selected = selected[-self._max_borrowed:]
            game.CustomData.Set("selectable_techs_selection", selected)
            self._option_view.TriggerChange()

    def reset(self):
        game.Technology.Clear()

    def back_out(self):
        game.Technology.Clear()

    def complete(self):
        borrowed = game.CustomData.GetOr("selectable_techs_selection", [])
        game.Technology.Clear()
        for kt in borrowed:
            game.Technology.Unlock(kt.Kind, kt.Source)
    
    def buttons(self):
        selected_count = len(game.CustomData.GetOr("selectable_techs_selection", []))
        start = LS("menus.start_game", "Start game")
        permitted = Permission.Yes()
        if selected_count < self._max_borrowed:
            permitted = Permission.No(LS("menus.borrow_techs.too_few"))
        
        return [prep.UI.BackButton(), prep.UI.ForwardButton(start, permitted)]

    def header_text(self):
        selected_count = len(game.CustomData.GetOr("selectable_techs_selection", []))
        header = L("menus.borrow_techs.header", "Borrow techs")
        subheader = L("menus.borrow_techs.subheader", "{1}/{2} techs selected", selected_count, self._max_borrowed)
        subheader = "[s:PrepSubheader]" + subheader + "[/s]"
        return header + "\n" + subheader    
