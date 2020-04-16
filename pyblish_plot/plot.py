
from pyblish import api, logic
from . import dictail
import inspect


def plot_publish(families, targets=None, identifiers=None, keys=None):
    """Parse and plot all plugins by families and targets

    Args:
        families (list): List of interested instance family names
        targets (list, optional): List of target names
        identifiers (list, optional): List of interested dict names, take
            ["context.data", "instance.data"] if not provided.
        keys (list, optional): List of interested key names, return all dict
            keys if not provided.

    """
    if not targets:
        targets = ["default"] + api.registered_targets()

    plugins = api.discover()
    plugins = logic.plugins_by_families(plugins, families)
    plugins = logic.plugins_by_targets(plugins, targets)

    reports = list()

    for plugin in plugins:
        report = plot_plugin(plugin, identifiers, keys)
        if report:
            reports.append(report)

    return reports


def plot_plugin(plugin, identifiers=None, keys=None):
    """Parse plugin from source and plot dict operations

    Args:
        plugin (pyblish.api.Plugin): A plugin class object to plot
        identifiers (list, optional): List of interested dict names, take
            ["context.data", "instance.data"] if not provided.
        keys (list, optional): List of interested key names, return all dict
            keys if not provided.

    """
    identifiers = identifiers or ["context.data", "instance.data"]

    cls = next(c for c in plugin.mro() if c.__module__ != "pyblish.plugin")
    source, lineno = inspect.getsourcelines(cls)
    source = "".join(source).strip()  # Strip to avoid unexpected indent
    lineno -= 1
    filename = plugin.__module__

    trace = dictail.parse(source, filename, identifiers, offset=lineno)
    report = TraceReport()

    if keys:
        filtered_trace = list()
        for op in trace:
            matched = [k for k in keys if k in op.entries]
            if matched:
                new_op = op.copy()
                new_op.entries = matched
                filtered_trace.append(new_op)

        trace = filtered_trace

    report.parse(plugin, trace)

    return report


class TraceReport(object):

    def __init__(self):
        # Plugin
        self.module = None
        self.name = None
        self.context = None
        self.order = None
        self.hosts = []
        self.families = []
        self.targets = []
        # Keys Operations
        self.trace = []

    def __bool__(self):
        return bool(self.trace)

    def __repr__(self):
        type = "api.ContextPlugin" if self.context else "api.InstancePlugin"
        traces = "        ".join(
            "{op} {id}: [ {keys} ]  ...... L{no}\n".format(
                no=op.lineno,
                id=op.name,
                op=op.op,
                keys=", ".join(op.entries))
            for op in self.trace
        )

        return """
class {name}({type}):  {module}

    order = {order}
    hosts = {hosts}
    families = {families}
    targets = {targets}

    Operations:
        {traces}
        """.format(
            name=self.name,
            type=type,
            module=self.module,
            order=self.order,
            hosts=self.hosts,
            families=self.families,
            targets=self.targets,
            traces=traces,
        )

    def parse(self, plugin, trace):
        # Plugin
        self.module = next(c.__module__ for c in plugin.mro()
                           if c.__module__ != "pyblish.plugin")
        self.name = plugin.__name__
        self.context = issubclass(plugin, api.ContextPlugin)
        self.order = plugin.order
        self.hosts = plugin.hosts
        self.families = plugin.families
        self.targets = plugin.targets
        # Keys Operations
        self.trace = trace
