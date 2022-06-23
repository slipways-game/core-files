class ModeMenu:
    def pages(self):
        seeds, message = None, None
        return [
            PageCommonSelectSector("sandbox", seeds=seeds, message=message),
            PageReloadGameDataForSeedVersion(),
            PageActivateEarlyMutatorEffects(),
            PageSetDescription("{sector}"),
            PageSetSaveFileBasedOnSector(),
            PageAddPackage('modes/sandbox-scenario'),
            PagePickPotentialTechs('012344'),
            PagePickPotentialPerks(2),
            PageSelectRacesAndPerks(segments=[
                {"name": "reroll_button", "config": {
                    "reroll_callback": reroll_techs_and_perks,
                    "tooltip": LS("button.reroll_techs_and_perks")
                }},
                {"name": "tech_badges", "config": {
                    "adjust_with": SwappingTechsOut()
                }},
                {"name": "perk_buttons", "config": {
                    "adjust_with": SwappingPerksOut()
                }}
            ]),
            PageUnlockPotentialTechs(),
            PageTechsForceUnlock('slipstream_relay'),
            PageStartScenario()
        ]

class SwappingPerksOut:
    def options(self, race, perk):
        present = game.CustomData.GetOr(PagePickPotentialPerks.key(race), [])
        others = [pk for pk in race.Perks]
        return others
    
    def option_to_string(self, perk_kind): return perk_kind.LName

    def when_selected(self, race, old_perk, new_perk_kind):
        pots = game.CustomData.GetOr(PagePickPotentialPerks.key(race), [])
        if new_perk_kind in pots: return False
        index = pots.index(old_perk)
        pots[index] = new_perk_kind
        return True


class SwappingTechsOut:
    def options(self, race, tech):
        tier = tech.BaseTier
        others = [tk for tk in TechKind.AllList if race in tk.Races and tk.BaseTier == tier]
        others.sort(key=lambda tk: tk.LName)
        return others

    def option_to_string(self, tech_kind):
        return tech_kind.LName
    
    def when_selected(self, race, old_tech, new_tech_kind):
        if new_tech_kind is None: return False
        already_present = game.CustomData.GetOr(potential_techs_key(race), [])
        if new_tech_kind in already_present: return False
        self.recursive_replace(race, old_tech, new_tech_kind)
        return True

    def recursive_replace(self, race, old_tech, new_tech_kind):
        replaced_index = self.replace_tech(race, old_tech, new_tech_kind)
        all_techs = self.grab_all_potentials()
        duplicates = [t for t in all_techs if t[1] == new_tech_kind and t[0] != race]
        if len(duplicates) > 0:
            dupe_race, dupe_tk = duplicates[0]
            dupe_tier = dupe_tk.BaseTier
            dupe_tech = game.Technology.Tech(dupe_tk)
            possibilities = set(tk for tk in TechKind.AllList if tk.BaseTier == dupe_tier and dupe_race in tk.Races)
            trimmed_possibilities = set(p for p in possibilities if not any(a[1] == p for a in all_techs))
            if len(trimmed_possibilities) > 0:
                possibilities = trimmed_possibilities
            replacement = Randomness.Pick(possibilities)
            self.recursive_replace(dupe_race, dupe_tech, replacement)

    def grab_all_potentials(self):
        all = []
        for race in Race.AllPlayable:
            pots_for_race = game.CustomData.GetOr(potential_techs_key(race), [])
            all += ((race, tech) for index, tech in enumerate(pots_for_race))
        return all

    def replace_tech(self, race, old_tech, new_tech_kind):
        pots_for_race = game.CustomData.GetOr(potential_techs_key(race), [])
        # remove old option
        index = pots_for_race.index(old_tech.Kind)
        game.Technology.Forget(old_tech)
        # add new option
        new_tech = game.Technology.Unlock(new_tech_kind, UnlockSource.FromRace(race))
        pots_for_race[index] = new_tech.Kind
        # refresh pot list
        game.CustomData.Set(potential_techs_key(race), pots_for_race)
        # return info
        return index

def reroll_techs_and_perks(race):
    rng = Randomness.DefaultRNG()
    # perks
    game.Council.Member(race).DeselectAllPerks()    
    regenerate_potential_perks(rng, race, 2)
    # techs: grab potential techs config from mutators, if any
    setup_obj = None
    for setup_cond in game.Conditions.Supporting("menu_flow_setup"):
        setup_obj = setup_cond.PythonObject
    pt_cfg = setup_obj.potential_techs() if setup_obj and hasattr(setup_obj, "potential_techs") else {}
    pattern = pt_cfg.get('pattern', None) or "012344"
    pattern_for_race = pt_cfg.get('pattern_for_race', None) or {r.ID: pattern for r in Race.AllPlayable}
    # regenerate techs
    game.Technology.Clear()
    new_techs = regenerate_potential_techs(rng, race, pattern_for_race[race.ID])
    for unlock_race in Race.AllPlayable:
        for t in game.CustomData.GetOr(potential_techs_key(unlock_race), []):
            game.Technology.Unlock(t, UnlockSource.FromRace(unlock_race))
