
from pyblish import api, logic
from . import dictail


def plot(families, plugins=None, targets=None, subjects=None):
    subjects = subjects or ["context.data", "instance.data"]

    plugins = api.discover() if plugins is None else plugins
    plugins = logic.plugins_by_families(plugins, families)

    traces = list()

    for plugin in plugins:
        trace = dictail.parse(plugin.__module__, subjects=subjects)
        traces.append((plugin, trace))

    return traces
