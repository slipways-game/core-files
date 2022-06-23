#################################################

class ConsNoop:
    """Used if something expects a consequence object, but you don't want to do anything."""
    def apply(self):
        pass
    def revert(self):
        pass

#################################################

class ConsGrantResources:
    """Gives resources to the player immediately, optionally popping up a notification over the node that caused this."""
    def __init__(self, amount, resource, node = None):
        self.amount, self.resource, self.node = amount, resource, node

    def apply(self):
        empire.Stock.Receive(self.resource, self.amount)
        if self.node is not None:
            HVPoppingInfo.Spawn(self.node).Show(self.amount, self.resource)

    def revert(self):
        empire.Stock.Return(self.resource, self.amount)

    def issue(self):
        commands.IssueScriptedConsequence(self)

#################################################

class ConsAttachQualityOnce:
    """Attaches a quality to a node reversibly."""
    def __init__(self, node, flag, quality):
        self._node, self._quality, self._flag = node, quality, flag

    def apply(self):
        node = self._node
        node.CustomData.Inc(self._flag)
        game.Qualities.Attach(self._quality, node)
        return [self._node]
    
    def revert(self):
        node = self._node
        connections = node.CustomData.Dec(self._flag)
        if connections == 0:
            game.Qualities.Detach(self._quality, node)
        return [self._node]

    def issue(self): commands.IssueScriptedConsequence(self)

class ConsDetachQuality:
    def __init__(self, node, flag, quality):
        self._node, self._quality, self._flag = node, quality, flag

    def apply(self):
        node = self._node
        self._previous = node.CustomData.Get(self._flag)
        node.CustomData.Clear(self._flag)
        game.Qualities.Detach(self._quality, node)
    
    def revert(self):
        node = self._node
        node.CustomData.Set(self._flag, self._previous)
        game.Qualities.Attach(self._quality, node)

#################################################

class ConsUpdateNodeData:
    """Used to reversibly update CustomData on multiple objects. Despite the 'Node' in the name,
    it works with other things as well."""
    def __init__(self, trigger_changes = False):
        self._trigger_changes = trigger_changes
        self._updates = []
        self._nodes = []
        self._others = []
        self._callbacks = []
        self._change_callbacks = []

    def add(self, node, key, value):
        self._updates.append({
            "node": node, "key": key, "value": value
        })
        return self

    def inc(self, node, key, amount = 1):
        return self.add(node, key, lambda x: (x or 0) + amount)

    def dec(self, node, key, amount = 1):
        return self.add(node, key, lambda x: (x or 0) - amount)

    def append_to_list(self, node, key, new_element):
        return self.add(node, key, lambda x: (x or []) + [new_element])
    
    def remove_from_list(self, node, key, element):
        def remover(lst):
            lst = lst or []
            lst.remove(element)
            return lst
        return self.add(node, key, remover)

    def store_in_dict(self, node, prop, key, value):
        def storer(dct):
            dct = dct or {}
            dct[key] = value
            return dct
        return self.add(node, key, storer)

    def when_done(self, callback):
        self._callbacks.append(callback)
        return self

    def when_done_or_reverted(self, callback):
        self._change_callbacks.append(callback)
        return self

    def issue(self):
        commands.IssueScriptedConsequence(self)

    def apply(self):
        self._previous = []
        touched_objects = set()
        for update in self._updates:
            node, key, value = update["node"], update["key"], update["value"]
            previous_value = node.CustomData.GetOr(key, None)
            touched_objects.add(node)
            self._previous.append({"node": node, "key": key, "value": previous_value})
            if callable(value):
                value = value(previous_value)
            node.CustomData.Set(key, value)            
        self._nodes = list(n for n in touched_objects if isinstance(n, Node))
        self._others = list(o for o in touched_objects if not o in self._nodes)
        if self._trigger_changes:
            for model in self._others:
                model.TriggerChange()
        for callback in self._callbacks:
            callback()
        for callback in self._change_callbacks:
            callback()
        return self._nodes

    def revert(self):
        for prev in self._previous:
            node, key, previous_value = prev["node"], prev["key"], prev["value"]
            if previous_value is not None:
                node.CustomData.Set(key, previous_value)
            else:
                node.CustomData.Clear(key)
        if self._trigger_changes:
            for model in self._others:
                model.TriggerChange()
        for callback in self._change_callbacks:
            callback()
        return self._nodes

class ConsSetProp:
    """Sets a property on an object in a reversible fashion.
       Intended for use when you don't want this to be saved, otherwise
       you should use ConsUpdateNodeData with persistent CustomData."""
    def __init__(self, obj, prop_name, value):
        self._obj, self._prop, self._new_value = obj, prop_name, value

    def apply(self):
        self._existed = hasattr(self._obj, self._prop)
        if self._existed:
            self._old_value = getattr(self._obj, self._prop)
        setattr(self._obj, self._prop, self._new_value)
        return []

    def revert(self):
        if not self._existed:
            delattr(self._obj, self._prop)
        else:
            setattr(self._obj, self._prop, self._old_value)
        return []

    def issue(self):
        commands.IssueScriptedConsequence(self)

class ConsRefreshNode:
    def __init__(self, *nodes):
        self._nodes = list(nodes)

    def apply(self): return self._nodes
    def revert(self): return self._nodes
    def issue(self):
        commands.IssueScriptedConsequence(self)

class ConsEstablishIndustry:
    def __init__(self, node, kind):
        self._node, self._kind = node, kind
    
    def apply(self): 
        self._node.EstablishIndustry(self._kind)
        return [self._node]
    def revert(self): 
        self._node.AbandonIndustry()
        return [self._node]
    def issue(self):
        commands.IssueScriptedConsequence(self)
