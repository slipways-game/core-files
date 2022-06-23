#########################################################
# Map generation: add outposts, increase forgeworld density, change sector shape a bit

class OutpostsMapgen(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # generate rips        
        map_generation.Refinement("after_planet_types", 1000, refine_place_outposts)

class RipsMapgenSettings:
    def create_zones(self):
        settings = MapgenDefaults().create_zones()
        point_counts = [22, 60, 70, 78, 83, 81, 73, 56, 34] # total signal counts in each zone
        zones = Zones.circle(Vector2.zero, 3.1, 24, point_counts)
        diff = difficulty_ordinal()
        zones += Zones.circle(Vector2(8 + diff * 0.8, 0), 3.1, 24, point_counts)
        settings["zones"] = zones
        settings["planet_counts"] = settings["planet_counts"] + settings["planet_counts"]
        settings["link_values"] = settings["link_values"] + settings["link_values"]
        return settings

class MoreForgeworldsMapgen(MapGenGuaranteePlanets):
    def __init__(self):
        MapGenGuaranteePlanets.__init__(self, [
            ("planet.factory", 15, 12, ["planet.barren", "planet.ice", "planet.lava", "planet.primordial", "planet.arid", "planet.arctic", "planet.swamp"]),
        ])

#########################################################
# Main mission structure

class RipsMainMission(MainMission):
    def __init__(self):
        MainMission.__init__(self, "rips", [RMMReachOutpostInTime(), RMMCrossTheRips()])

    @staticmethod
    def get():
        return game.Conditions.Get("RipsMainMission()").PythonObject

    def scenario_id(self): return "m-rips"
    def scoring_rules(self): return [ScoringExpeditions(), ScoringRescues()]
    def conditions(self): return [
        (RespectZones,),
        (KeepOutpostsUpdated,),
        (ShowRipMap,),
        (WinMissionOnTime, "RipsMainMission()", 25)
    ]

    def things_to_explain(self):
        return [("custom", "mission.rip.rift.explanation"), ("structure", "bridge"), ("quality", "QuirkUnstableSpacetime()")]    
    def perks_available(self):
        return ["reciprocity", "well_prepared", "prospectors", "explorers", "social_capital", "growth", "experimental_tech", "joint_factories", "curiosity", "careful_observation"]
    
    def do_additional_setup(self):
        game.Camera.ZoomTo(16) # zoom out to maximum scale
        game.Camera.JumpTo(Vector2(10, 0))

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

class RMMReachOutpostInTime:
    def check_completion(self):
        return game.CustomData.GetOr("outposts_reached_in_time", 0) >= 1
    def description(self): return LS("mission.rip.stage.reach_outpost_in_time")

class RMMCrossTheRips:
    def check_completion(self):
        if not 'rips' in globals(): return False
        return rips.Zones.ZoneByName("right_corner").Unlocked
    def description(self): return LS("mission.rip.stage.cross_the_rips")
    def requires(self): return (0,)
        
class ShowRipMap(GlobalCondition):
    def activate(self):
        self._goal_marker = None
        self._rip_markers = None
        self.react_to(Trigger.GameLoaded, self.refresh)
        self.react_to(Trigger.ActionTaken, self.refresh)
        self.react_to(Trigger.ActionReverted, self.refresh)
        self.refresh()

    def refresh(self, _ = None):
        if not 'rips' in globals(): return
        # rips
        rips_visible = self.rips_visible()
        if rips_visible and self._rip_markers is None:
            self._rip_markers = [
                rips.CreateMarker(rips.RipByName("rhigh"), 1.0),
                rips.CreateMarker(rips.RipByName("rmid"), 1.0),
                rips.CreateMarker(rips.RipByName("rlow"), 1.0),
                rips.CreateMarker(rips.RipByName("horizright"), 2.0),
                rips.CreateMarker(rips.RipByName("horizleft"), 2.0),
                rips.CreateMarker(rips.RipByName("crossbar"), 1.0),
                rips.CreateMarker(rips.RipByName("lhigh"), 1.0),
                rips.CreateMarker(rips.RipByName("lmid"), 1.0),
                rips.CreateMarker(rips.RipByName("llow"), 1.0),
            ]
        elif not rips_visible and self._rip_markers is not None:
            for m in self._rip_markers:
                m.Discard()
            self._rip_markers = None
        # goal
        goal_visible = self.goal_visible()
        if goal_visible and self._goal_marker is None:
            rip = rips.RipByName("horizright")
            rip_point = rip.PointAt(0.05)
            position = rip_point.position + rip_point.normal * f(-12)
            marker = world.Add(AreaMarker(position, 6, "mission_target_area"))
            marker.SetChrome([
                {"type": NodeChrome.Text, "text": ":^mission: %s" % LS("label.target_area"), "bg_color": Color(0.26, 0.1, 0.3, 0.6)}
            ])
            game.Camera.ZoomTo(12)
            game.Camera.JumpTo(marker.Position - Vector2(12, 8))
            self._goal_marker = marker
        elif not goal_visible and self._goal_marker is not None:
            self._goal_marker.Discard()
            self._goal_marker = None

    def goal_visible(self):
        rmm = RipsMainMission.get()
        return rmm.goal_active(1) and not rmm.goal_finished(1)

    def rips_visible(self):
        return game.CustomData.GetOr("map_revealed", 0) > 0


#########################################################
# Story

class RipsMusic(MusicProgression):
    PROGRESS_THRESHOLD = 4
    def _check_for_transition(self, prev):
        outposts = game.CustomData.GetOr("outposts_reached_in_time", 0)
        far_end_reached = rips.Zones.ZoneByName("right_corner").Unlocked
        lv = 0
        if outposts >= 1: lv += 1
        if outposts >= 3: lv += 1
        if far_end_reached: lv += 1
        if prev == lv - 1: return lv

#########################################################
# Scoring

class ScoringExpeditions(Scoring):
    def kind(self): return ScoreKind.Addition
    def tags(self): return ["mission"]

    def title(self): return LS("scoring.rips.expeditions_found")
    def description(self): return LS("scoring.rips.expeditions_found.desc")

    def calculate_score(self, fraction):
        points = game.CustomData.GetOr("outposts_reached", 0)
        tag_text = "%d:planet:" % points
        return Score.Add(tag_text, points, 5)

class ScoringRescues(Scoring):
    def kind(self): return ScoreKind.Addition
    def tags(self): return ["mission"]

    def title(self): return LS("scoring.rips.expeditions_rescued")
    def description(self): return LS("scoring.rips.expeditions_rescued.desc")

    def calculate_score(self, fraction):
        points = game.CustomData.GetOr("outposts_reached_in_time", 0)
        tag_text = "%d:planet:" % points
        return Score.Add(tag_text, points, 5)

#########################################################
# Generating rips

class RipsMissionMapgen(GlobalCondition):
    """Makes sure that the rip manager is present and that the effects of the rip on the map are felt."""
    def activate(self):
        self.react_to(Trigger.GameWorldSetup, self.create_rip_model)
        self.react_to(Trigger.MapSetup, self.on_map_setup)

    def create_rip_model(self, data):
        RipManager.CreateIfNeeded(world)

    def on_map_setup(self, data):
        map_generation = data["generation"]
        # generate rips        
        map_generation.Refinement("after_planet_types", 1050, refinement_add_rip_effects(rip_refinement_settings()))

def rip_refinement_settings():
    return {
        "apply_quirk": "QuirkUnstableSpacetime()"
    }

def generate_rips(rips):
    # left and right vertical lines
    lcut1, lcut2, rcut1, rcut2 = -0.4, 0.06, -0.02, 0.35
    left_line_eq = req_mix(req_ellipse(-76, 2, 87, 87), req_line(4, 2, 10, 80), 0.35)
    llow = rips.AddRip("llow", left_line_eq, f(-1.5), f(lcut1), 80).Commit()
    lmid = rips.AddRip("lmid", left_line_eq, f(lcut1), f(lcut2 - 0.013), 50).Commit()
    lhigh = rips.AddRip("lhigh", left_line_eq, f(lcut2), f(1.5), 110).Commit()
    right_line_eq = req_mix(req_ellipse_inv(164, -15, 130, 130), req_line(44, -15, -10, 80), 0.45)
    rlow = rips.AddRip("rlow", right_line_eq, f(-1.5), f(rcut1 + 0.002), 115).Commit()
    rmid = rips.AddRip("rmid", right_line_eq, f(rcut1 + 0.006), f(rcut2), 40).Commit()
    rhigh = rips.AddRip("rhigh", right_line_eq, f(rcut2), f(1.5), 80).Commit()
    # middle crossbar
    cstart = left_line_eq(f(lcut2))
    cend = right_line_eq(f(rcut1))
    cdir = cend - cstart
    cstart += cdir * f(0.04)
    cdir *= f(0.92)
    cross_eq = req_line(cstart.x, cstart.y, cdir.x * 4, cdir.y * 4)
    cross_eq = req_add_wave(cross_eq, 3.14, 0.25, 1.5)
    crossbar = rips.AddRip("crossbar", cross_eq, f(0), f(0.25), 40).Commit()
    # horizontals
    hlstart = left_line_eq(f(lcut1))
    hl_eq = req_line(hlstart.x, hlstart.y, -80, 70)
    hl_eq = req_add_wave(hl_eq, 3.14, 1.6, 15)
    horizleft = rips.AddRip("horizleft", hl_eq, f(0), f(1.25), 100).Commit()
    hrstart = right_line_eq(f(rcut2))
    hr_eq = req_line(hrstart.x, hrstart.y, 100, -80)
    hr_eq = req_add_wave(hr_eq, 3.14, 1.8, 18)
    horizright = rips.AddRip("horizright", hr_eq, f(0), f(0.75), 60).Commit()
    # joints
    lcjoint = rips.AddJoint().End(lmid).Start(lhigh).Start(crossbar).Commit()
    rcjoint = rips.AddJoint().End(rlow).End(crossbar).Start(rmid).Commit()
    lhjoint = rips.AddJoint().End(llow).Start(horizleft).Start(lmid).Commit()
    rhjoint = rips.AddJoint().End(rmid).Start(rhigh).Start(horizright).Commit()
    # topological zones
    L, R = RipSide.LHS, RipSide.RHS
    left_vertical = (llow, lmid, lhigh)
    right_vertical = (rlow, rmid, rhigh)
    rips.Zones.AddZone("left").On(L, *left_vertical).On(R, horizleft).UnlockFromTheStart()
    rips.Zones.AddZone("left_corner").On(L, *left_vertical).On(L, horizleft).UnlockFromTheStart()
    rips.Zones.AddZone("top").On(R, *left_vertical).On(L, *right_vertical).On(L, crossbar)
    rips.Zones.AddZone("bottom").On(R, *left_vertical).On(L, *right_vertical).On(R, crossbar)
    rips.Zones.AddZone("right").On(R, *right_vertical).On(R, horizright)
    rips.Zones.AddZone("right_corner").On(R, *right_vertical).On(L, horizright)

#########################################################
# Excluding zones before rips are crossed

class RespectZones(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.AfterNodeDiscovered, self.assign_zone_to_node)
        self.react_to(Trigger.StructureBuilt, self.assign_zone_to_node)
        self.react_to(Trigger.GameLoaded, self.recalculate_zone_unlocks)
        game.Qualities.EstablishGlobally(LimitActionsToAccessibleZones)
    
    def recalculate_zone_unlocks(self, _):
        bridge_ends = game.Nodes.WithType("structure.bridge_end")
        for bend in bridge_ends:
            if bend.Level == 1:
                zone = rips.Zones.ZoneByName(bend.CustomData.Get("zone"))
                zone.AddUnlocker(bend)

    def global_structure_placement_rules(self, structure_kind):
        return [ScriptedPlacement(PlaceOnlyInAccessibleZones)]

    @staticmethod
    def assign_zone_to_node(data):
        node = data["node"]
        zone = rips.Zones.ZoneForPoint(node.Position)        
        node.CustomData.Set("zone", zone.Name)

class LimitActionsToAccessibleZones:
    """This quality is present globally and prevents from colonizing/performing actions 
    to nodes on the other side of an unbridged rip."""    

    def name(self): return LS("quality.zones")
    def desc(self): return LS("quality.zones.desc")
    def sentiment(self): return QualitySentiment.Negative
    def hidden(self, node): return True

    def effects(self, node): return [ActionPermission.Calling(self.check_zone)]

    def check_zone(self, node_action):        
        node = node_action.Target
        zone = rips.Zones.ZoneByName(node.CustomData.Get("zone"))
        if not zone.Unlocked:
            return Permission.No(LS("quality.zones.inaccessible_zone"))
        return Permission.Yes()

class PlaceOnlyInAccessibleZones:
    @staticmethod
    def adjust_position(pos, ps): return pos

    @staticmethod
    def is_permitted(pos, ps):
        zone = rips.Zones.ZoneForPoint(pos)
        if not zone.Unlocked:
            return Permission.No(LS("structure.zone.inaccessible"))        
        return Permission.Yes()

#########################################################
# Scientific outposts

OUTPOSTS = [
    ("crossbar", 0.12, -4, "top", 12),
    ("horizleft", 0.1, 8, "left", 5),
    ("crossbar", 0.21, 6, "bottom", 17),
    ("rmid", 0.5, -7, "top", 15),
    ("horizright", 0.07, 11, "right", 22),
]
def refine_place_outposts(gen, signals, zones):
    difficulty_modifiers = [+3, +2, +1, +1]
    difficulty_time = difficulty_modifiers[clamp(0, 3, difficulty_ordinal())]
    distance_scale = constants.Float("distance.scale")
    races = ["baqar", "dendr", "vattori", "silthid", "aphorian"]
    rng = gen.RNGForTask("outposts")
    races = Randomness.Shuffle(rng, races)
    races += races
    
    def pick_signal(rip_name, t, distance, desired_zone):
        rip = rips.RipByName(rip_name)
        rip_point = rip.PointAt(t)
        position = rip_point.position + rip_point.normal * f(distance)
        position /= distance_scale
        sigs = list(gen.SignalsNear(position, 1))
        sigs.sort(key = lambda s: (s.Position - position).sqrMagnitude)
        for s in sigs:
            scaled_pos = s.Position * distance_scale
            zone = rips.Zones.ZoneForPoint(scaled_pos)
            if zone.Name == desired_zone:
                return s
        return None

    for outpost in OUTPOSTS:
        rip_name, t, distance, desired_zone, years_until_death = outpost
        years_until_death += difficulty_time
        s = pick_signal(rip_name, t, distance, desired_zone)
        if s is None: 
            gen.RejectThisMap()
            return
        race1, race2 = races[0], races[1]
        races = races[2:]
        s.Size = PotentialSize.Medium
        s.Quirk = "QuirkUnstableSpacetime()"
        s.Script = "OutpostSignal(%d,%s,%s)" % (years_until_death, repr(race1), repr(race2))
        s.Contents = "planet.earthlike" # randomize this later

class KeepOutpostsUpdated(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.ActionTaken, self.update_outposts)
        self.react_to(Trigger.ActionReverted, self.update_outposts)

    def update_outposts(self, _):
        outpost_pots = (p for p in every(Potential) if p.ScriptObject is not None)
        for p in outpost_pots:
            p.TriggerChange()

class OutpostSignal:
    NORMAL_COLOR = Color(0.12, 0.15, 0.3, 0.83)
    WARN_COLOR = Color(0.4, 0, 0, 0.83)

    def __init__(self, years_allowed, race1, race2):
        self._fog, self._marker = None, None
        self._years_allowed = years_allowed
        self._races = [race1, race2]

    def initialize_signal(self, signal):
        if not self._fog:
            self._fog = world.Add(CircularFogRemover(signal.Position, 1.5))

    def initialize_potential(self, potential):
        if not self._marker:
            self._marker = world.Add(AreaMarker(potential.Position, 0.75))
    
    def after_potential_scanned(self, potential, node):
        if self._fog: self._fog.Discard()
        if self._marker: self._marker.Discard()
        self._fog, self._marker = None, None
        node.CustomData.Set("years_allowed", self._years_allowed)
        node.CustomData.Set("scientist_races", self._races)
        commands.Issue(EnableSituation(world, node, "event_outpost_visited"))

    def info_potential_tooltip_header(self, _, __): return L("structure.outpost.tooltip")
    def info_potential_tooltip(self, _, __): return L("structure.outpost.tooltip.desc")

    def potential_chrome(self, potential):
        years_remaining = self._years_allowed - game.Time.NormalizedTurn
        if years_remaining <= 0: return []
        return [{
            "type": NodeChrome.Text,
            "text": Localization.Plural(years_remaining, "unit.year"),
            "bg_color": self.NORMAL_COLOR if years_remaining > 1 else self.WARN_COLOR
        }]

def event_outpost_visited(evt):
    years_allowed = evt.Node.CustomData.Get("years_allowed")
    zone_name = evt.Node.CustomData.Get("zone")
    zone_available = rips.Zones.ZoneByName(zone_name).Unlocked
    too_late = game.Time.NormalizedTurn >= years_allowed
    if not zone_available:
        event_outpost_behind_rip(evt)
    elif too_late:
        event_outpost_too_late(evt)
    else:
        event_outpost_in_time(evt)

def event_outpost_behind_rip(evt):
    evt.SetLocalizedTitle(LS("event_outpost.title"))
    evt.SetLocalizedText(LS("event_outpost_behind_rip.text"))
    evt.AddChoices(
       "Return once we can cross the rift.",
    )

def event_outpost_too_late(evt):
    evt.SetLocalizedTitle(LS("event_outpost.title"))
    evt.SetLocalizedText(LS("event_outpost_too_late.text"))
    evt.AddChoices(
       "Pay your respects and move on. -> complete -> outpost_reached(0)",
    )

RACE_TO_TECH = {
    "baqar": ("rips_better_plants", 4),
    "aphorian": ("rips_cheaper", 3),
    "vattori": ("rips_connections", 4),
    "silthid": ("rips_cheap_build", 2),
    "dendr": ("rips_stabilize_planets", 3),
}
def event_outpost_in_time(evt):
    races = evt.Node.CustomData.Get("scientist_races")
    race1, race2 = races
    evt.SetLocalizedTitle(LS("event_outpost.title"))
    evt.SetLocalizedText(LS("event_outpost_in_time.text", None, "[[ref:race.%s]]" % race1, "[[ref:race.%s]]" % race2))
    map_revealed = game.CustomData.GetOr("map_revealed", 0) > 0
    map_effect = "goto(event_outpost_map)" if not map_revealed else "outpost_reached(1)"
    for r in races:
        tech_id, time_cost = RACE_TO_TECH[r]
        if game.Technology.IsInvented(TechKind.All[tech_id]):
            continue
        description = LS("choice.follow_up", None, "[[ref:race.%s]]" % r)
        evt.AddChoice("(%dmo) %s -> invent(%s) -> %s" % (time_cost, r, tech_id, map_effect), description)
    evt.AddChoice("Investigate how the rift research can be applied elsewhere. -> get(5,S) -> %s" % map_effect)

def event_outpost_map(evt):
    evt.Localized()
    evt.AddChoice("Reveal the rifts. -> outpost_reached(1) -> reveal_map")

class EffRevealMap(ChoiceEffect):
    def is_consequential(self): return True
    def consequence(self):
        cons = ConsUpdateNodeData()
        cons.inc(game, "map_revealed")
        return cons


class EffOutpostReached(ChoiceEffect):
    def __init__(self, in_time):
        self._in_time = in_time > 0
    
    def is_consequential(self): return True
    def consequence(self):
        cons = ConsUpdateNodeData()
        cons.inc(game, "outposts_reached")
        if self._in_time:
            cons.inc(game, "outposts_reached_in_time")
        cons.when_done_or_reverted(lambda: RipsMainMission.get().signal_change())
        return cons

#####################################################################
# Unstable spacetime quirk

class QuirkUnstableSpacetime:
    @staticmethod
    def eligible_planets(): return ["earthlike", "arctic", "ocean", "swamp", "mining", "primordial", "arid", "jungle"]

    def name(self): return LS("quirk.unstable_spacetime")
    def desc(self): return LS("quirk.unstable_spacetime.desc")
    def sentiment(self): return QualitySentiment.Negative
    def visibility(self, node): return 1 if node.Level < 0 else 0
    def icon(self, node): return {"type": "negative", "main_icon": "mod_rift"}
    def hidden(self, node): return True

    @staticmethod
    def industry_prohibited(industry_kind):
        for n in industry_kind.BaseLevel.BaseNeeds:
            if n.Resource == Resource.People:
                return True
        for p in industry_kind.BaseLevel.BaseProducts:
            if p == Resource.People:
                return True
        return False
    
    def effects(self, node):
        upgraded = constants.Int("flux_plant.upgraded") > 0
        industry_name = "flux_plant_upgraded" if upgraded else "flux_plant"
        return [
            ColonizationOptions.RemoveMatching(QuirkUnstableSpacetime.industry_prohibited),
            ColonizationOptions.Add(industry_name)
        ]

class ImproveFluxPlants:
    def apply(self):
        rift_plant = IndustryKind.All["flux_plant"]
        upgraded = IndustryKind.All["flux_plant_upgraded"]
        affected = [p for p in every(Planet) if p.Industry is not None and p.Industry.Kind == rift_plant]
        for a in affected:
            commands.Issue(ChangeNodeIndustry(world, a, upgraded, ChangeNodeIndustry.Flags.KeepLevel))
    
    def revert(self, data):
        pass # subcommands handle reversion

    def description(self): return LocalizedString.Empty

class Stabilize:
    @staticmethod
    def execute(node):
        game.Qualities.Detach("QuirkUnstableSpacetime()", node)
        return {"node": node}

    @staticmethod
    def revert(data):
        game.Qualities.Attach("QuirkUnstableSpacetime()", data["node"])
    
    @staticmethod
    def applies(node):
        return any(q.ScriptExpression == "QuirkUnstableSpacetime()" for q in node.GetQualities())
