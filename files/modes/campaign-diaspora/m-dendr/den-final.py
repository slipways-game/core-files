#########################################################
# Main mission class

O_PERCENT = 50
O_YEARS = 2
TB_YEARS = 2
L_BONUS = 1
LW_BONUS = 3
LWF_BONUS = 5

class DendrMainMission(OneRaceMainMission):
    def __init__(self):
        OneRaceMainMission.__init__(self, "dendr", [DMMEnoughSealed()])

    def scoring_rules(self):
        return [
            ScoringCampaignTasks([0, 1, 2, 3, 4, 4]),
            ScoringGenesSurplus([2, 4, 6, 9, 12]),
            ScoringCultureSurplus([2, 4, 6, 8, 10]),
        ]

    def conditions(self): return [
        (WinMissionOnTime, "DendrMainMission()", 28),
        VaultProgress
    ]

    def do_additional_setup(self):
        game.Stock.Receive(Resource.Cash, 20) # starting bonus
    
    def things_to_explain(self):
        return [
            ("structure", "vault"),
            ("custom", "special.filling_vaults", constants.Int("vault.base_time"), 
                L_BONUS, LW_BONUS, LWF_BONUS,
                O_PERCENT, O_YEARS,
                TB_YEARS),
            ("custom", "special.sealing_vaults")
        ]
    
    def borrowed_techs(self):
        return {
            "baqar": ["freeze_resistant_bots", "mineral_seeding", "gravitic_tugs"],
            "silthid": ["integrated_manufacturing", "extreme_mini", "bioextraction"],
            "aphorian": ["brain_machine_interface", "geoharvesting", "hyperdrive"],
            "vattori": ["orbital_labs", "matter_transposition", "skill_download"],
        }

    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("menus.game_end.mission_failed"),
                "shown_elements": ["undo"]
            }

###############################################################
# Mission goals and scoring

class DMMEnoughSealed:
    def __init__(self):
        self._required = (constants.Int("den.required_genes"), constants.Int("den.required_culture"))

    def check_completion(self): 
        sealed = self.state()
        return sealed[0] >= self._required[0] and sealed[1] >= self._required[1]

    def state(self):
        sealed = [0, 0]
        for v in game.Nodes.WithType("structure.vault"):
            if v.Level >= 1:
                sealed[0] += v.CustomData.Get("genes")
                sealed[1] += v.CustomData.Get("culture")
        return sealed

    def description(self): return LS("mission.dendr.goal.enough_sealed", None, *self._required)
    def short(self):
        genes, culture = self.state()
        r_genes, r_culture = self._required
        return "%d/%d:Gen:\n%d/%d:C:" % (genes, r_genes, culture, r_culture)

class ScoringCultureSurplus(ScoringFiveRanks):
    def __init__(self, adds):
        base = constants.Int("den.required_culture")
        self._limits = [0] + [(base + a) for a in adds]
    def tags(self): return ["mission"]
    def id(self): return "scoring.dendr.culture_surplus"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return sum(v.CustomData.GetOr("culture", 0) for v in game.Nodes.WithType("structure.vault") if v.Level >= 1)
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":C:"
    def number_text(self, number, rank): return "%d:C:" % number

class ScoringGenesSurplus(ScoringFiveRanks):
    def __init__(self, adds):
        base = constants.Int("den.required_genes")
        self._limits = [0] + [(base + a) for a in adds]
    def tags(self): return ["mission"]
    def id(self): return "scoring.dendr.genes_surplus"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        return sum(v.CustomData.GetOr("genes", 0) for v in game.Nodes.WithType("structure.vault") if v.Level >= 1)
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":Gen:"
    def number_text(self, number, rank): return "%d:Gen:" % number

class ScoringBiggestVault(ScoringFiveRanks):
    def __init__(self, counts):
        adjustment = 0
        self._limits = [0] + [c + adjustment for c in counts]
    def tags(self): return ["mission"]
    def id(self): return "scoring.dendr.biggest_gene_vault"
    def base_number(self):
        if game.GameContext != GameContext.PlayingScenario: return 0
        try:
            return max(v.CustomData.Get("genes") for v in game.Nodes.WithType("structure.vault") if v.Level == 1)
        except:
            return 0
    def rank_limits(self): return self._limits
    def rank_count(self): return len(self._limits) - 1
    def post_rank_text(self): return ":Gen:"
    def number_text(self, number, rank): return "%d:Gen:" % number


class DendrMusic(MusicProgression):
    def _check_for_transition(self, prev):
        vaults, sealed = 0, 0
        for vlt in game.Nodes.WithType("structure.vault"):
            if vlt.Level >= 1: sealed += 1
            vaults += 1
        lv = 0
        if vaults >= 1: lv += 1
        if sealed >= 2: lv += 1
        if game.CustomData.GetOr("mission_complete", False): lv += 1
        if prev == lv - 1: return lv

###############################################################
# Vaults

def vault_allowed_to_build(kind):
    open_vault_exists = any(v.Level == 0 for v in game.Nodes.WithType("structure.vault"))
    if open_vault_exists:
        return Permission.No(LS("structure.vault.only_one_open"))
    return Permission.Yes()

VAULT_ORBIT = 1.4
VAULT_TYPES = set("planet.%s" % k for k in ["earthlike", "swamp", "arctic", "arid", "ocean", "jungle", "primordial"])

def vault_placement():
    return [
        PlaceNear(vault_node_eligible, f(VAULT_ORBIT + 0.05), LS("structure.trap.place_in_orbit"), "VPlaceNear"),
        ScriptedPlacement(SnapToNode(f(VAULT_ORBIT + 0.05), vault_node_eligible, offset=Vector2(0, 0)))
    ]

class SnapToNode:
    def __init__(self, range, filter, offset = None):
        self._range = range
        self._filter = filter
        self._offset = offset or Vector2.zero

    def adjust_position(self, pos, ps):
        node = game.Nodes.ClosestWith(pos, self._range, self._filter)
        if not node: return pos
        return node.Position + self._offset

def vault_node_eligible(node):
    return node.NodeType in VAULT_TYPES and node.Level < 0

def vault_placed(vault):
    planet = game.Nodes.ClosestWith(vault.Position, f(VAULT_ORBIT + 0.5), vault_node_eligible)
    update = ConsUpdateNodeData()
    update.add(vault, "genes", 0)
    update.add(vault, "time_required", constants.Int("vault.base_time"))
    update.add(vault, "time_spent", 0)
    update.add(vault, "planet", planet)
    update.append_to_list(vault, "dependent_nodes", planet)
    update.add(planet, "vault", vault)
    update.append_to_list(planet, "dependent_nodes", vault)
    update.issue()
    ConsEstablishIndustry(planet, IndustryKind.All["protected"]).issue()

def vault_tooltip(vault, original):
    if vault.Level == 1:
        genes, culture = vault.CustomData.Get("genes"), vault.CustomData.Get("culture")
        return [original, LS("structure.vault.tooltip.sealed", None, genes, culture)]
    elif vault.CustomData.Get("planet").ImportCount == 0:
        return [original, LS("structure.vault.tooltip.deliver")]
    else:
        time = vault_time_remaining(vault)
        genes = vault.CustomData.Get("genes")
        culture = game.Nodes.TotalProduction(Resource.All["C"])
        return [original, LS("structure.vault.tooltip.in_progress", None, time, genes, culture)]

def prot_tooltip(planet, original):
    vault = planet.CustomData.Get("vault")
    vt = vault_tooltip(vault, original)
    return [original, LS("planet.protected.tooltip")] + vt[1:]

def vault_info_on_upgrades(vault):
    if vault.Level == 1: 
        genes, culture = vault.CustomData.Get("genes"), vault.CustomData.Get("culture")
        return InfoBlock(LS("structure.vault.sealed"), [
            LS("structure.vault.tooltip.sealed", None, genes, culture)
        ])
    else:
        header = LS("structure.lab.upgrade_header")
        info = [
            LS("structure.vault.deliver_lwf"),
            LS("structure.vault.deliver_o", None, O_PERCENT, O_YEARS),
            LS("structure.vault.deliver_tb", None, TB_YEARS)
        ]
        return InfoBlock(header, info)

def vault_obstructed_by(vault, other):
    if not isinstance(other, Node): return True
    return not vault_node_eligible(other)

def vault_genes(vault):
    planet = vault.CustomData.Get("planet")
    l, w, f, o, t, b = [planet.AmountReceived(Resource.All[id]) for id in "LWFOTB"]
    smallest, middle, biggest = min(l, w, f), mid(l, w, f), max(l, w, f)
    genes = biggest * L_BONUS + middle * (LW_BONUS - L_BONUS) + smallest * (LWF_BONUS - LW_BONUS)
    genes += t + b
    multiplier = 1.0 + (O_PERCENT * 0.01) * o
    genes = int(math.ceil(genes * multiplier))
    return genes

def vault_time_required(vault):
    planet = vault.CustomData.Get("planet")
    o, t, b = [planet.AmountReceived(Resource.All[id]) for id in "OTB"]
    time = constants.Int("vault.base_time") + o * O_YEARS - (t+b) * TB_YEARS
    return time

def vault_time_remaining(vault):
    return vault.CustomData.Get("time_required") - vault.CustomData.Get("time_spent")

def prot_want_normal(need, resource):
    vault = need.Consumer.CustomData.Get("vault")
    if vault.Level >= 1: return False
    if resource.ID not in "LWOFTB": return False

def prot_node_tag(prot, blocks):
    text = blocks.OnlySuppliedNeeds()
    vault = prot.CustomData.Get("vault")
    if vault.Level >= 1:
        text = ""
    return text

def prot_upgrade(prot, industry, level):
    if level == 1: return Permission.Yes()
    return Permission.NoWithNoReason()

def prot_accepts_special(node, resource):
    return False

def vault_chrome(vault):
    time = vault_time_remaining(vault)
    genes = vault.CustomData.Get("genes")
    planet = vault.CustomData.Get("planet")
    if planet.ImportCount > 0 or genes > 0:
        if vault.Level == 0:
            text = "%d:Gen:\n%s" % (genes, Localization.Plural(time, "unit.year"))
        else:
            culture = vault.CustomData.Get("culture")
            text = "%d:Gen: %d:C:" % (genes, culture)
        return [{"type": NodeChrome.Text, "text": text, "bg_color": Color.black}]

def vault_upgrade(vault, industry, level):
    if level == 1 and vault_time_remaining(vault) <= 0:
        vault.CustomData.Set("culture", game.Nodes.TotalProduction(Resource.All["C"]))
        conditions.Get("VaultProgress()").PythonObject.post_vault_sealed_message(vault)
        return Permission.Yes()
    return Permission.NoWithNoReason()

def vault_after_trade(vault):
    if vault.Level > 0: return
    genes = vault_genes(vault)
    time = vault_time_required(vault)
    old_genes = vault.CustomData.Get("genes")
    old_time = vault.CustomData.Get("time_required")
    if old_genes != genes or old_time != time:
        u = ConsUpdateNodeData()
        u.add(vault, "genes", genes)
        u.add(vault, "time_required", time)
        u.issue()

def vault_connectivity(vault, other):
    return NodeConnectivity.Ignores()

class VaultProgress(GlobalCondition):
    def activate(self):
        self.react_to(Trigger.NewTurn, self.advance_vaults)
    
    def advance_vaults(self, data):
        vaults = list(game.Nodes.WithType("structure.vault"))
        for v in vaults:
            if v.Level > 0: continue # sealed
            genes = v.CustomData.Get("genes")
            if genes > 0:
                ConsUpdateNodeData(trigger_changes=True).inc(v, "time_spent").issue()
        ConsRefreshNode(*vaults).issue()
    
    def post_vault_sealed_message(self, vault):
        vaults = list(game.Nodes.WithType("structure.vault"))
        index = vaults.index(vault)
        self.post_message(self._msg_vault_sealed, index)
    
    def _msg_vault_sealed(self, vault_index):            
        vaults = list(game.Nodes.WithType("structure.vault"))
        vault = vaults[vault_index]
        msg = MessageContent()        
        # text
        msg.ShortText = LS("structure.vault.msg_sealed")
        msg.Picture = "situation"
        # reactions
        def jump():
            game.Camera.JumpTo(vault)
            return MessageAction.Dismiss
        msg.WhenClicked = jump
        msg.WhenDismissed = lambda: MessageAction.Dismiss        
        msg.ExpiresIn = 6
        return msg

class QualityVaultUpkeep:
    def name(self): return LS("quality.vault_upkeep")
    def desc(self): return LS("quality.vault_upkeep.desc", None, constants.Int("vault.upkeep"))

    def effects(self, vault):
        if vault.Level > 0: return 
        upkeep = constants.Int("vault.upkeep")       
        return [ResourceFlow.Cash(-upkeep, FlowCategory.StructureUpkeep)]
