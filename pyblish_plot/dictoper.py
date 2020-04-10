import sys
import ast


PY38 = sys.version_info[:2] == (3, 8)


def parse(filename, objects, attrs):
    """
    """
    with open(filename, "rb") as file:
        source = file.read().decode(encoding="utf8")

    root = ast.parse(source, filename=filename)
    VisitAddParent().visit(root)

    visitor = VisitDictAttrs(source, objects, attrs)
    visitor.visit(root)

    return visitor.op_stack()


class VisitAddParent(ast.NodeVisitor):

    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node
        ast.NodeVisitor.generic_visit(self, node)


class VisitDictAttrs(ast.NodeVisitor):
    """
    Only intrested in any change in `context.data` or `instance.data`
    * set
    * get
    * update
    * del
    * pop
    """

    OP_GET = "get"
    OP_SET = "set"
    OP_DEL = "del"
    OP_TRY = "try"

    def __init__(self, source, objects, attrs):
        self._src = source
        self._lines = source.split("\n")
        self._objects = objects
        self._attrs = attrs
        self._op_stack = list()
        ast.NodeVisitor.__init__(self)

    def op_stack(self):
        return self._op_stack

    def visit_Attribute(self, node):
        if node.attr in self._attrs:
            name = next((c for c in ast.iter_child_nodes(node)
                         if isinstance(c, ast.Name)), None)

            if name and name.id in self._objects:
                operation, entries = self.parse_data_op(node)
                op = DictOp(node, name.id, node.attr, operation, entries)
                self._op_stack.append(op)

        else:
            self.generic_visit(node)

    def parse_data_op(self, node, parent_entry=None):
        """
        """
        entries = None
        operation = None
        OP = node.parent

        if isinstance(OP, ast.Attribute):

            if not isinstance(OP.parent, ast.Call):
                # Assume `data` is being changed via `dict` operation,
                # so the grandparent node must be `ast.Call` type.
                raise Exception("Undefined operation.")

            elif OP.attr == "update":
                operation = self.OP_SET
                entries = self.parse_dict_update(OP.parent)

            elif OP.attr == "get":
                arg = OP.parent.args[0]
                if isinstance(arg, ast.Str):
                    entry = arg.s
                else:
                    entry = self.get_source_in_call(*OP.parent.args)

                operation = self.OP_TRY
                entries = [entry]

            elif OP.attr == "pop":
                arg = OP.parent.args[0]
                if isinstance(arg, ast.Str):
                    entry = arg.s
                else:
                    entry = self.get_source_in_call(arg)

                operation = self.OP_DEL
                entries = [entry]

            elif OP.attr == "clear":
                operation = self.OP_DEL
                entries = _ALL

        elif isinstance(OP, ast.Subscript):
            slicer = OP.slice.value

            if isinstance(slicer, ast.Str):
                entry = slicer.s
            else:
                entry = self.get_source_in_slice(slicer)

            operation, entries, _ = self.parse_data_op(OP, parent_entry=entry)
            entries = [entry] if entries is None else entries

        elif isinstance(OP, ast.Compare) and parent_entry is None:
            # Handling for case like `"foo" in instance.data`
            if isinstance(OP.left, ast.Str):
                entry = OP.left.s
            else:
                entry = self.get_source_in_compare(OP.left,
                                                   OP.ops[0],
                                                   OP.comparators[0])
            operation = self.OP_TRY
            entries = [entry]

        elif isinstance(OP, ast.Assign):

            if OP.value is node:
                operation = self.OP_GET

            elif node in OP.targets:
                operation = self.OP_SET

        elif isinstance(OP, ast.Delete):
            operation = self.OP_DEL

        # done

        if operation is None:
            operation = self.OP_GET

        if parent_entry is not None and entries is not None:
            entries = ["%s.%s" % (parent_entry, e) for e in entries]
            # (TODO) keep Code type entry

        return operation, entries

    def parse_dict_update(self, node):
        """
        """
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
                # Assume mapping type class init
                entries = self.parse_dict_update(arg)

            else:
                raise Exception("Undefined operation.")

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
        sep = {ast.Eq: "==",
               ast.NotEq: "!=",
               ast.Lt: "<",
               ast.LtE: "<=",
               ast.Gt: ">",
               ast.GtE: ">=",
               ast.Is: "is",
               ast.IsNot: "is ",
               ast.In: "in",
               ast.NotIn: "not "}[type(op)]

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

    VisitDictAttrs.get_source_in_dict = get_source_segment
    VisitDictAttrs.get_source_in_compare = get_source_segment
    VisitDictAttrs.get_source_in_call = get_source_segment
    VisitDictAttrs.get_source_in_slice = get_source_segment


_ALL = object()


class Code(str):
    pass


class DictOp(object):

    def __init__(self, node, obj, attr, operation, entries):
        self.obj = obj
        self.attr = attr
        self.lineno = node.lineno
        self.column = node.col_offset
        self.op = operation
        self.entries = entries

    def __repr__(self):
        return ("DictOp(%s.%s, L%d col %d, %s [%s]"
                % (self.obj,
                   self.attr,
                   self.lineno,
                   self.column,
                   self.op,
                   ", ".join(self.entries)))
