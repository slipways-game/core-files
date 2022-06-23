class ModeMenu:
    def pages(self):
        seeds, message = None, None
        if FeatureFlags.Beta:
            seeds = BETA_SEEDS
            message = LS("beta.standard_locked_down")
        return [
            PageCommonSelectSector("standard", seeds=seeds, message=message),
            PageReloadGameDataForSeedVersion(),
            PageActivateEarlyMutatorEffects(),
            PageSetDescription("{difficulty}"),
            PageAddPackage('modes/standard-scenario'),
            PageAlterFlowIfRequested(),
            PagePickPotentialTechs('012344'),
            PagePickPotentialPerks(2),
            PageSelectRacesAndPerks(),
            PageUnlockPotentialTechs(),
            PageTechsForceUnlock('slipstream_relay'),
            PageStartScenario()
        ]

class MainSceneDefaults:
    def pages(self):
        return [
            PageRandomSector(),
            PageSetDifficulty('challenging'),
            PageSetDescription("{difficulty}"),
            PageRacesAutoAssign(3),
            PageTechsForceUnlock('slipstream_relay'),
            PageTechsAutoAssign('012344','012344','012344'),
        ]

class QuickStartFirstGame:
    def pages(self):
        preset_seeds = None
        if FeatureFlags.Beta:
            preset_seeds = BETA_SEEDS
        return [
            PageAddPackage('modes/standard-scenario'),
            PageRandomSector(preset_seeds = preset_seeds),
            PageSetDifficulty('reasonable'),
            PageSetDescription("{difficulty}"),
            PageRacesAutoAssign(3),
            PageTechsForceUnlock('slipstream_relay'),
            PageTechsAutoAssign('012344','012344','012344'),
            PageStartScenario()
        ]
