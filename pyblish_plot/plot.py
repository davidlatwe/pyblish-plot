
from pyblish import api
from . import dictoper


def plot(families, plugins=None, targets=None):
    plugins = api.discover() if plugins is None else plugins
    plugins = api.plugins_by_families(plugins, families)

    dictoper.parse("filename",
                   objects=["context", "instance"],
                   attrs=["data"])
