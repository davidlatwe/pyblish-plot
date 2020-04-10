import sys
import ast


PY38 = sys.version_info[:2] == (3, 8)


def parse(filename, subjects):
    """
    """
    with open(filename, "rb") as file:
        source = file.read().decode(encoding="utf8")

    root = ast.parse(source, filename=filename)
    AddParent().visit(root)

    visitor = VisitDict(source, subjects)
    visitor.visit(root)

    return visitor.result()


class AddParent(ast.NodeVisitor):

    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node
        ast.NodeVisitor.generic_visit(self, node)


class VisitDict(ast.NodeVisitor):
    """
    dict[k]
    dict[k][K]
    dict[k] = v
    K In|NotIn dict|dict[k]
    dict.update(d)
    dict.get(k)
    dict.pop(k)
    dict.clear()
    dict.copy()
    dict.items()
    del dict[k]
    deepcopy(dict)
    """

    OP_GET = "get"
    OP_SET = "set"
    OP_DEL = "del"
    OP_TRY = "try"

    def __init__(self, source, subjects):
        self._src = source
        self._lines = source.split("\n")
        self._op_trace = list()
        self._subjects = subjects

        ast.NodeVisitor.__init__(self)

    def result(self):
        return self._op_trace

    def visit_Name(self, node):
        """Parse operation if the `Name` node identifier matches
        """
        name = node.id
        if name in self._subjects:
            operation, entries = self.parse_dict_op(node)
            if operation is not None:
                op = DictOp(node, name, operation, entries)
                self._op_trace.append(op)
        else:
            self.generic_visit(node)

    def visit_Attribute(self, node):
        """
        """
        all_children = list(ast.walk(node))
        name = next((c for c in all_children if isinstance(c, ast.Name)), None)
        if name is None:
            return

        attr = ".".join(reversed([
            c.attr for c in all_children if isinstance(c, ast.Attribute)
        ] + [name.id]))

        if attr in self._subjects:
            operation, entries = self.parse_dict_op(node)
            if operation is not None:
                op = DictOp(node, attr, operation, entries)
                self._op_trace.append(op)
        else:
            self.generic_visit(node)

    def parse_dict_op(self, node, parent_entry=None):
        """
        """
        entries = None
        operation = None
        OP = node.parent

        if isinstance(OP, ast.Subscript):
            # `dict` subscription operation

            slicer = OP.slice.value
            if isinstance(slicer, ast.Str):
                entry = slicer.s
            else:
                entry = self.get_source_in_slice(slicer)

            operation, entries = self.parse_dict_op(OP, parent_entry=entry)
            entries = [entry] if entries is None else entries
            operation = operation or self.OP_GET

        # Operations on `dict` subscription

        elif (isinstance(OP, ast.Compare)
                and isinstance(OP.ops[0], (ast.In, ast.NotIn))):
            # key In or NotIn `dict`

            if isinstance(OP.left, ast.Str):
                entry = OP.left.s
            else:
                entry = self.get_source_in_compare(OP.left,
                                                   OP.ops[0],
                                                   OP.comparators[0])
            entries = [entry]
            operation = self.OP_TRY

        elif isinstance(OP, ast.Assign):

            if OP.value is node:
                operation = self.OP_GET

            elif node in OP.targets:
                if parent_entry is None:  # Object/attribute re-assigned
                    entries = _ALL
                operation = self.OP_SET

        elif isinstance(OP, ast.Delete):
            if parent_entry is None:
                entries = _ALL
            operation = self.OP_DEL

        # Functions of `dict`

        elif isinstance(OP, ast.Attribute) and isinstance(OP.parent, ast.Call):
            # `OP` node should be a `dict` function and is being called

            if OP.attr == "update":
                entries = self.parse_dict_update(OP.parent)
                operation = self.OP_SET

            elif OP.attr in ("copy", "items"):
                entries = _ALL
                operation = self.OP_GET

            elif OP.attr == "get":
                arg = OP.parent.args[0]
                if isinstance(arg, ast.Str):
                    entry = arg.s
                else:
                    entry = self.get_source_in_call(*OP.parent.args)
                entries = [entry]
                operation = self.OP_TRY

            elif OP.attr == "pop":
                arg = OP.parent.args[0]
                if isinstance(arg, ast.Str):
                    entry = arg.s
                else:
                    entry = self.get_source_in_call(arg)
                entries = [entry]
                operation = self.OP_DEL

            elif OP.attr == "clear":
                entries = _ALL
                operation = self.OP_DEL

        elif isinstance(OP, ast.Call):
            if ((isinstance(OP.func, ast.Name)
                 and OP.func.id in ("copy", "deepcopy"))
                or (isinstance(OP.func, ast.Attribute)
                    and OP.func.attr in ("copy", "deepcopy"))):
                entries = _ALL
                operation = self.OP_GET

        # done

        if parent_entry is not None and entries is not None:
            entries = ["%s.%s" % (parent_entry, e) for e in entries]
            # (TODO) keep Code type entry

        return operation, entries

    def parse_dict_update(self, node):
        """
        """
        entries = None

        if node.keywords:
            entries = [k.arg for k in node.keywords]

        elif node.args:
            arg = node.args[0]

            if isinstance(arg, ast.Dict):
                entries = list()
                for k, v in zip(arg.keys, arg.values):
                    if isinstance(k, ast.Str):
                        entries.append(k.s)
                    else:
                        entries.append(self.get_source_in_dict(k, v))

            elif isinstance(arg, ast.Call):

                if ((isinstance(arg.func, ast.Name)
                     and arg.func.id in ("dict", "OrderedDict"))
                    or (isinstance(arg.func, ast.Attribute)
                        and arg.func.attr == "OrderedDict")):
                    # Assume mapping type class init
                    entries = self.parse_dict_update(arg)

        if entries is None:
            entries = [self.get_source_in_call(arg)]

        return entries

    def get_source_in_dict(self, key, value):
        """"""
        lines = self._lines[key.lineno - 1: value.lineno]
        lines[-1] = lines[-1][:value.col_offset - 1]
        lines[0] = lines[0][key.col_offset:]
        line = "\n".join(lines).rsplit(":", 1)[0].strip()

        return Code(line)

    def get_source_in_compare(self, left, op, comparator):
        """"""
        sep = {ast.In: "in", ast.NotIn: "not "}[type(op)]

        lines = self._lines[left.lineno - 1: comparator.lineno]
        lines[-1] = lines[-1][:comparator.col_offset - 1]
        lines[0] = lines[0][left.col_offset:]
        line = "\n".join(lines).rsplit(sep, 1)[0].strip()

        if line.endswith(")") and line.count("(") < line.count(")"):
            line = line[:-1]

        return Code(line)

    def get_source_in_call(self, *args):
        arg = args[0]

        if len(args) > 1:
            sep = ","
            nxarg = args[1]

            lines = self._lines[arg.lineno - 1: nxarg.lineno]
            lines[-1] = lines[-1][:nxarg.col_offset - 1]
            lines[0] = lines[0][arg.col_offset:]
            line = "\n".join(lines).rsplit(sep, 1)[0].strip()

        else:
            sep = ")"

            lines = self._lines[arg.lineno - 1:]
            lines[0] = lines[0][arg.col_offset:]

            # Counting `()` pairs
            start = 1
            end = 0
            for i, line in enumerate(lines):
                start += line.count("(")
                end += line.count(")")
                if start == end:
                    lines = lines[:i + 1]
                    break

            line = "\n".join(lines).rsplit(sep, 1)[0].strip()

        return Code(line)

    def get_source_in_slice(self, slicer):
        """"""
        sep = "]"

        lines = self._lines[slicer.lineno - 1:]
        lines[0] = lines[0][slicer.col_offset:]

        # Counting `[]` pairs
        start = 1
        end = 0
        for i, line in enumerate(lines):
            start += line.count("[")
            end += line.count("]")
            if start == end:
                lines = lines[:i + 1]
                break

        line = "\n".join(lines).rsplit(sep, 1)[0].strip()

        return Code(line)


if PY38:
    def get_source_segment(self, *args):
        return Code(ast.get_source_segment(self._src, args[0]))

    VisitDict.get_source_in_dict = get_source_segment
    VisitDict.get_source_in_compare = get_source_segment
    VisitDict.get_source_in_call = get_source_segment
    VisitDict.get_source_in_slice = get_source_segment


_ALL = ["*"]


class Code(str):
    pass


class DictOp(object):

    def __init__(self, node, name, operation, entries):
        self.name = name
        self.lineno = node.lineno
        self.column = node.col_offset
        self.op = operation
        self.entries = entries

    def __repr__(self):
        return ("DictOp(%s, L%d col %d, %s [%s]"
                % (self.name,
                   self.lineno,
                   self.column,
                   self.op,
                   ", ".join(self.entries)))
