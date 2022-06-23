# Defines the basic scoring rules used in the game.
# Some modes redefine this, but this contains implementation for standard.

######################################################
## Scoring - base classes

class Scoring:
    def title(self): raise Exception("Must be implemented by %s." % self.__class__)
    def description(self): raise Exception("Must be implemented by %s." % self.__class__)

    def id(self): raise Exception("Must be implemented by %s." % self.__class__)
    def kind(self): raise Exception("Must be implemented by %s." % self.__class__)
    def calculate_score(self, fraction): raise Exception("Must be implemented by %s." % self.__class__)

######################################################
## Scoring - standard scoring

class ScoringPlanets(Scoring):
    PER_LEVEL = [0, 80, 160, 320, 640]

    def __init__(self):
        self._seen_lv4 = False
    def id(self): return "scoring.planets"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("scoring.planets", "Planets")
    def description(self): 
        max_lv = 4 if self._seen_lv4 else 3
        text = L("scoring.planets.first_part", "Score *{1}*:star: for each [[ref:level.{2}]] planet", self._per_lv(max_lv), max_lv)
        for lv in range(max_lv-1, 0, -1):
            text += L("scoring.planets.more_parts", "*{1}*:star: for each [[ref:level.{2}]]", self._per_lv(lv), lv)
        text = Localization.MakeSentence(text)
        return text

    def calculate_score(self, fraction):
        counts = [math.ceil(self._get_count(lv) * fraction) for lv in range(5)]
        if counts[4] > 0: self._seen_lv4 = True
        texts = []
        total = 0
        for lv in range(1, 5):
            if counts[lv] > 0 or lv == 1:
                texts.append("%d:lv%d:" % (counts[lv], lv))
            total += counts[lv] * self._per_lv(lv)
        return Score.Add(" + ".join(texts), total)

    def _per_lv(self, lv): return self.__class__.PER_LEVEL[lv]
    def _get_count(self, lv):
        return game.Nodes.CountPlanetsWithLevel(lv)

class ScoringHappiness(Scoring):
    def id(self): return "scoring.happiness"
    def kind(self): return ScoreKind.Multiplier

    def title(self): return LS("scoring.happiness", "Happiness")
    def description(self): return LS("scoring.happiness.desc", "All score components are multiplied by the happiness (:H:) of your people.")

    def calculate_score(self, fraction):
        happiness = empire.Stock.Happiness
        effective = round(100.0 + (happiness - 100.0) * fraction)
        text = L("menus.scoring.happiness.multiplier", "x {1}% :H: *Happiness*", effective)
        return Score.Multiplier(text, effective * 0.01).WithShort("%d%%:H:" % empire.Stock.Happiness)

class ScoringPoliticalPower(Scoring):
    PER_POINT = 50
    def id(self): return "scoring.legacy"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("scoring.legacy", "Legacy")
    def description(self): return LS("scoring.legacy.desc", "Each :V: is worth *{1}*:star:. To get :V:, complete missions given to you by the races.", self.PER_POINT)

    def calculate_score(self, fraction):
        points = game.Stock.Reserve(Resource.PoliticalPower)
        return Score.Add("%d:V:" % points, points * self.PER_POINT)

class ScoringEmpireSize(Scoring):
    PER_SIZE = 400

    def id(self): return "scoring.empire_size"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("scoring.empire_size", "Empire size")
    def description(self): return LS("scoring.empire_size.desc", "Each increase in empire size is worth *{1}:star:*.", self.PER_SIZE)

    def calculate_score(self, fraction):
        empire_size_condition = empire.Conditions.Get("EmpireSize()").PythonObject
        size_level = empire_size_condition.data.level
        return Score.Add(EmpireSize.level_name(size_level), size_level * self.PER_SIZE).WithShort(EmpireSize.level_name(size_level))

class ScoringUnfinishedQuests(Scoring):
    PENALTY = 500

    def id(self): return "scoring.unfinished_quests"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("scoring.unfinished_quests", "Unfinished quests")
    def description(self): return LS("scoring.unfinished_quests.desc", "Each unfinished quest you have at the end of the game costs you *{1}*:star:.", self.PENALTY)

    def calculate_score(self, fraction):
        if game.Time.NormalizedTurn < 20: return None
        unfinished_quests = sum(1 for q in game.Quests.ActiveQuests)
        if unfinished_quests == 0: return None
        tag = Localization.Plural(unfinished_quests, "unit.task")
        return Score.Add(tag, -unfinished_quests * self.PENALTY).WithShort(LS("scoring.unfinished_tasks.short", None, unfinished_quests))

class ScoringCheat(Scoring):
    def __init__(self, how_much):
        self._amount = how_much

    def id(self): return "scoring.cheat_points"
    def kind(self): return ScoreKind.Addition

    def title(self): return LS("scoring.cheat", "Cheat")
    def description(self): return LS("scoring.cheat.desc", "Artificially increased score by *{1}*:star:.", self._amount)

    def calculate_score(self, fraction):
        return Score.Add("", self._amount).WithShort("cheat")
