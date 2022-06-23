#########################################################
# Science system

class SandboxTechLevels(GlobalCondition):
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
        return (0, 4)

    def info_for_level(self, level):
        return None

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
        if tech.IsRoot:
            commands.Issue(UpgradeTechLevel(world))

def tuple_to_int_range(t):
    return IntRange(t[0], t[1])
