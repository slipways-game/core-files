#########################################################
# Main mission class

class BridgeMainMission(MainMission):
    def __init__(self):
        MainMission.__init__(self, "bridge", [BMMBuildBridge()])

    @staticmethod
    def get():
        return game.Conditions.Get("BridgeMainMission()").PythonObject

    def scenario_id(self): return "m-bridge"
    def scoring_rules(self): return []
    def conditions(self): return [
        (WinMissionOnTime, "BridgeMainMission()", 25),
    ]

    def perks_available(self):
        return ["novelty_traders", "reciprocity", "miners", "explorers", "social_capital", "growth", "experimental_tech", "joint_factories", "researchers", "curiosity"]

    def things_to_explain(self):
        return [
        ]
    
    def check_win_condition(self):
        if not self.finished():
            return {
                "outcome": "loss", "defeat": True,
                "heading": LS("menus.game_end.mission_failed.header"),
                "comment": LS("mission.id.failed"),
                "shown_elements": ["undo"]
            }

class BMMBuildBridge:
    def state(self): 
        return None
    def check_completion(self):
        return False
    def description(self): return LS("mission.br.goal.build")

#########################################################
# Mapgen

class BridgeMapSettings:
    CENTERS_DISTANCE = 9
    CENTERS_COUNT = 4
    POINT_COUNTS = [[22, 60], [20,55]]
    PLANET_COUNTS = [[15, 30], [13, 27]]
    LINK_VALUES = [[6.6, 6], [6, 5.4]]

    def __init__(self):
        self._rng = Randomness.SeededRNG(game.GameSeed)

    def generate_center_points(self):
        distance_total = 0.0
        maximum_distance = (self.CENTERS_COUNT - 1) * self.CENTERS_DISTANCE
        points = None
        for i in range(100):
            points = [Vector2.zero]
            current = Vector2.zero
            angle = Randomness.Float(self._rng, -1, 1)
            while len(points) < self.CENTERS_COUNT:
                direction = Vector2(math.cos(angle), math.sin(angle))
                next_point = current + direction * self.CENTERS_DISTANCE
                points.append(next_point)
                angle += Randomness.Float(self._rng, -1, 1)
                current = next_point
            distance = (points[0] - points[-1]).magnitude
            ratio = distance / maximum_distance
            if ratio >= 0.86 and ratio <= 0.92: 
                log("Distance ratio: %f after %d runs" % (ratio, i))
                break
        return points

    def create_zones(self):
        centers = self.generate_center_points()
        zone_infos = []
        for index, ctr in enumerate(centers):
            zone_type = 1 if (index == 0 or index == len(centers) - 1) else 0
            ctr_zones = Zones.circle(ctr, 3.1, 6.2, self.POINT_COUNTS[zone_type])
            zone_info = [{"zone": z, "pc": self.PLANET_COUNTS[zone_type][i], "lv": self.LINK_VALUES[zone_type][i]} for i,z in enumerate(ctr_zones)]
            zone_infos += zone_info
        zone_infos.sort(key=lambda zi: zi["pc"])
        zones = [zi["zone"] for zi in zone_infos]
        planet_counts = [zi["pc"] for zi in zone_infos]
        link_values = [zi["lv"] for zi in zone_infos]
        return {
            "zones": zones,
            "centers": [centers[0], centers[-1]],
            "planet_counts": planet_counts,
            "link_values": link_values
        }
