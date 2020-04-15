
from pyblish import api, logic
from . import dictail
import inspect


def plot_publish(families, targets=None, identifiers=None, keys=None):

    if not targets:
        targets = ["default"] + api.registered_targets()

    plugins = api.discover()
    plugins = logic.plugins_by_families(plugins, families)
    plugins = logic.plugins_by_targets(plugins, targets)

    traces = list()

    for plugin in plugins:
        trace = plot_plugin(plugin, identifiers, keys)
        if trace:
            traces.append((plugin, trace))

    return traces


def plot_plugin(plugin, identifiers=None, keys=None):
    identifiers = identifiers or ["context.data", "instance.data"]

    cls = next(c for c in plugin.mro() if c.__module__ != "pyblish.plugin")
    source, lineno = inspect.getsourcelines(cls)
    source = "".join(source).strip()  # Strip to avoid unexpected indent
    lineno -= 1
    filename = plugin.__module__

    trace = dictail.parse(source, filename, identifiers, offset=lineno)

    if keys:
        filtered_trace = list()
        for op in trace:
            matched = [k for k in keys if k in op.entries]
            if matched:
                new_op = op.copy()
                new_op.entries = matched
                filtered_trace.append(new_op)

        return filtered_trace
    else:
        return trace
