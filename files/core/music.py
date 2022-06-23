class MusicProgression(GlobalCondition):
    """Extend from this class to provide music progression in your campaign missions."""
    def activate(self):
        self.react_to(Trigger.ActionTaken, self.after_action)

    def after_action(self, _):
        lv = self._check_for_transition(music.Level)
        if lv is not None:
            self.transition_to(lv)
    
    def _check_for_transition(self, previous_lv):
        raise Exception("_check_for_transition() should be overriden.")

    def transition_to(self, lv):
        if music.MusicID != "MusicMain": return
        if not lv > music.Level: return
        music.TransitionToLevel(lv)
