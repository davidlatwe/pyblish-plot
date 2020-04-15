
from pyblish import api, logic
from . import dictail
import inspect


def plot_publish(families, targets=None, identifiers=None):

    if not targets:
        targets = ["default"] + api.registered_targets()

    plugins = api.discover()
    plugins = logic.plugins_by_families(plugins, families)
    plugins = logic.plugins_by_targets(plugins, targets)

    traces = list()

    for plugin in plugins:
        trace = plot_plugin(plugin, identifiers)
        traces.append((plugin, trace))

    return traces


def plot_plugin(plugin, identifiers=None):
    identifiers = identifiers or ["context.data", "instance.data"]

    cls = next(c for c in plugin.mro() if c.__module__ != "pyblish.plugin")
    source, lineno = inspect.getsourcelines(cls)
    source = "".join(source).strip()  # Strip to avoid unexpected indent
    lineno -= 1
    filename = plugin.__module__

    trace = dictail.parse(source, filename, identifiers, offset=lineno)

    return trace
