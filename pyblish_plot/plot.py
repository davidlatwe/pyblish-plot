
from pyblish import api, logic
from . import dictail
import inspect


def plot(families, plugins=None, targets=None, subjects=None):
    subjects = subjects or ["context.data", "instance.data"]

    plugins = api.discover() if plugins is None else plugins
    plugins = logic.plugins_by_families(plugins, families)

    traces = list()

    for plugin in plugins:

        cls = next(c for c in plugin.mro() if c.__module__ != "pyblish.plugin")
        source, lineno = inspect.getsourcelines(cls)
        source = "".join(source).strip()  # Strip to avoid unexpected indent
        lineno -= 1
        filename = plugin.__module__

        trace = dictail.parse(source, filename, subjects, offset=lineno)
        traces.append((plugin, trace))

    return traces
