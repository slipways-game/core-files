# Defines how science works in the base game. Probably should be left alone, but if you're adventurous,
# you can redefine how science works in a custom game mode somewhat by providing a different GlobalCondition
# for the tech system.

class SixTechLevels(GlobalCondition):
    COUNT_UPGRADES = True

    def activate(self):
        self.react_to(Trigger.TechInvented, self.when_invented)
        game.Technology.SetLogic(self.host())
    
    def initial_tech_level(self): return 0

    def effective_tier(self, tech_kind):
        if tech_kind.IsUpgrade:
            return max(self.inventable_range().LowEnd, tech_kind.BaseTier)
        else:
            return tech_kind.BaseTier
    
    def raw_inventable_range(self):
        """What levels of technologies are currently inventable."""
        effective_tl = clamp(0, 3, game.Technology.TechLevel / 2)
        low = clamp(0, 3, effective_tl)
        high = clamp(1, 4, effective_tl + 1)
        return (low, high)

    def info_for_level(self, level):
        inv_range = self.raw_inventable_range()
        if level != inv_range[1] + 1: return None
        remaining = 2 - (game.Technology.TechLevel % 2)
        tech_count_str = Localization.Plural(remaining, "unit.tech")
        tooltip = "\n".join([
            LS("tech.advance_info.desc", None, tech_count_str, inv_range[1] + 1),
            LS("tech.advance_info.lost", None, inv_range[0])
        ])
        return {
            "label": LS("tech.advance_info", None, tech_count_str),
            "tooltip": tooltip
        }

    def inventable_range(self):
        return tuple_to_int_range(self.raw_inventable_range())

    def inventability(self, tech_kind):
        lo, hi = self.raw_inventable_range()
        tier = self.effective_tier(tech_kind)
        if tier < lo:
            return Inventability.Skipped
        elif tier > hi:
            return Inventability.Locked
        else:
            return Inventability.Available

    def tech_level_info(self):
        return "TECH LEVEL: %d" % game.Technology.TechLevel

    def when_invented(self, data):
        tech = data["tech"]
        counts_for_tech_level = tech.IsRoot or self.COUNT_UPGRADES
        if "no_tech_level_increase" in tech.Kind.Tags:
            counts_for_tech_level = False
        if counts_for_tech_level:
            commands.Issue(UpgradeTechLevel(world))

def tuple_to_int_range(t):
    return IntRange(t[0], t[1])
