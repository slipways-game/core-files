"""
These are common functions that are used in every Slipways game.
"""

# This was a hack to work around a Unity bug which is no longer there.
# The function name is kept for compatibility.
def ih(some_iterable):
    return some_iterable

# Can be used anywhere a boolean-returning rule is expected, to get true/false unconditionally.
def yes(*args): return True
def no(*args): return False

##########################################################
## Slipway building costs

def slipway_cost_between_points(a, b, distance):
    global constants
    base_cost = constants.Float("slipway.base_cost")
    base_len = constants.Distance("slipway.base_distance")    
    cost_factor = (distance / base_len) ** 1.5
    cost_factor = max(0.5, cost_factor)
    return cost_factor * base_cost
