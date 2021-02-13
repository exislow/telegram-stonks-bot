from collections import defaultdict


def factory_defaultdict():
    return defaultdict(factory_defaultdict)
