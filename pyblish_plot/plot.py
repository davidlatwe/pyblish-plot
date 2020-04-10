
from pyblish import api
from . import dictail


def plot(families, plugins=None, targets=None):
    plugins = api.discover() if plugins is None else plugins
    plugins = api.plugins_by_families(plugins, families)

    dictail.parse("filename",
                  objects=["context", "instance"],
                  attrs=["data"])
