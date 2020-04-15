## pyblish-plot

A tool for visualize dict `data` flow in Pyblish plugins from abstract syntax trees.


### Example

Say you have these plugins that can be `pyblish.api.discover`

```python
import pyblish.api


class A(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.1
    families = ["test"]

    def process(self, instance):
        instance.data["foo"] = True


class B(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder

    def process(self, context):
        for instance in context:
            if instance.data["foo"]:
                instance.data.update({"bar": 5})

        if "age" in context.data:
            context.data.pop("age")


# Clean register
pyblish.deregister_all_paths()
pyblish.deregister_all_plugins()
pyblish.api.register_plugin(A)
pyblish.api.register_plugin(B)
```

Plot !

```python
import pyblish_plot


families = ["test"]
for report in pyblish_plot.plot_publish(families):
    print(report)
```

And you get this kind of report

```
class B(api.ContextPlugin):  __main__

    order = 0
    hosts = ['*']
    families = ['*']
    targets = ['default']

    Operations:
        ! instance.data: [ foo ]  ...... L36
        + instance.data: [ bar ]  ...... L37
        ? context.data: [ age ]  ...... L39
        - context.data: [ age ]  ...... L40

        

class A(api.InstancePlugin):  __main__

    order = 0.1
    hosts = ['*']
    families = ['test']
    targets = ['default']

    Operations:
        + instance.data: [ foo ]  ...... L28
```
