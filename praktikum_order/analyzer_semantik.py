import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

with open("simple_order_management.py", "rb") as f:
    CODE = f.read()

tree = parser.parse(CODE)


def get_text(node):
    return CODE[node.start_byte:node.end_byte].decode("utf-8")


class SemanticAnalyzer:
    def __init__(self):
        self.classes = {}
        self.functions = {}
        self.scopes = [{}]
        self.errors = []
        self.current_class = None
        self.current_func = None

    def current_scope(self):
        return self.scopes[-1]

    def lookup_var(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def add_error(self, line, category, message):
        self.errors.append(f"[Baris {line}] {category}: {message}")

    def infer_type(self, node):
        if node is None:
            return "None"
        t = node.type
        if t == "integer":
            return "int"
        if t == "float":
            return "float"
        if t == "string":
            return "str"
        if t == "list":
            return "list"
        if t == "dictionary":
            return "dict"
        if t == "none":
            return "None"
        if t == "identifier":
            name = get_text(node)
            if name in ("True", "False"):
                return "bool"
            if name in self.classes or name in self.functions:
                return name
            var_type = self.lookup_var(name)
            if var_type is None:
                self.add_error(
                    node.start_point[0] + 1,
                    "Scope/Name Error",
                    f"Variabel '{name}' digunakan sebelum dideklarasikan pada scope aktif."
                )
                return "unknown"
            return var_type
        if t == "attribute":
            obj_node = node.child_by_field_name("object")
            attr_node = node.child_by_field_name("attribute")
            obj_type = self.infer_type(obj_node)
            attr_name = get_text(attr_node)

            if obj_type in self.classes:
                class_info = self.classes[obj_type]
                if attr_name not in class_info["attributes"] and attr_name not in class_info["methods"]:
                    self.add_error(
                        node.start_point[0] + 1,
                        "Attribute Error",
                        f"Kelas '{obj_type}' tidak memiliki atribut atau metode '{attr_name}'."
                    )
                    return "unknown"
                return class_info["attributes"].get(attr_name, "method")
            elif obj_type == "dict":
                self.add_error(
                    node.start_point[0] + 1,
                    "Attribute Error",
                    f"Objek bertipe 'dict' tidak memiliki atribut '.{attr_name}' (seharusnya akses key ['{attr_name}'])."
                )
                return "unknown"
            return "unknown"
        if t == "binary_operator":
            left = self.infer_type(node.child_by_field_name("left"))
            right = self.infer_type(node.child_by_field_name("right"))
            op = get_text(node.child_by_field_name("operator"))
            if op == "+" and ("str" in (left, right)) and left != right and "unknown" not in (left, right):
                self.add_error(
                    node.start_point[0] + 1,
                    "Type Error (Binary Operator)",
                    f"Operasi '{op}' tidak valid antara tipe '{left}' dan '{right}'."
                )
                return "error"
            if left == "str" and right == "str":
                return "str"
            if "float" in (left, right):
                return "float"
            if left == "int" and right == "int":
                return "int"
            return "unknown"
        if t == "call":
            return self.check_call(node)
        return "unknown"

    def check_call(self, node):
        func_node = node.child_by_field_name("function")
        args_node = node.child_by_field_name("arguments")
        arg_nodes = [c for c in args_node.named_children] if args_node else []

        if func_node.type == "identifier":
            func_name = get_text(func_node)
            if func_name in self.classes:
                init_sig = self.classes[func_name]["methods"].get("__init__")
                if init_sig:
                    self.validate_arguments(node.start_point[0] + 1, f"{func_name}.__init__", init_sig["params"], arg_nodes)
                return func_name
            elif func_name in self.functions:
                sig = self.functions[func_name]
                self.validate_arguments(node.start_point[0] + 1, func_name, sig["params"], arg_nodes)
                return sig["return"]

        elif func_node.type == "attribute":
            obj_node = func_node.child_by_field_name("object")
            method_node = func_node.child_by_field_name("attribute")
            obj_type = self.infer_type(obj_node)
            method_name = get_text(method_node)

            if obj_type in self.classes:
                methods = self.classes[obj_type]["methods"]
                if method_name in methods:
                    sig = methods[method_name]
                    self.validate_arguments(node.start_point[0] + 1, f"{obj_type}.{method_name}", sig["params"], arg_nodes)
                    return sig["return"]
                else:
                    self.add_error(
                        node.start_point[0] + 1,
                        "Attribute Error",
                        f"Metode '{method_name}' tidak ditemukan pada kelas '{obj_type}'."
                    )
        return "unknown"

    def validate_arguments(self, line, target_name, expected_params, arg_nodes):
        param_items = list(expected_params.items())
        for idx, arg_node in enumerate(arg_nodes):
            actual_type = self.infer_type(arg_node)
            if idx < len(param_items):
                param_name, expected_type = param_items[idx]
                if expected_type != "any" and actual_type != "unknown":
                    if expected_type != actual_type:
                        self.add_error(
                            line,
                            "Type Mismatch (Argument)",
                            f"Pemanggilan '{target_name}' pada parameter '{param_name}' mengharapkan '{expected_type}', tetapi menerima '{actual_type}'."
                        )

    def collect_signatures(self, root):
        for node in root.named_children:
            if node.type == "class_definition":
                cname = get_text(node.child_by_field_name("name"))
                self.classes[cname] = {"attributes": {}, "methods": {}}
                body = node.child_by_field_name("body")
                for stmt in body.named_children:
                    if stmt.type == "function_definition":
                        mname, params, ret_type = self.parse_func_signature(stmt, is_method=True)
                        self.classes[cname]["methods"][mname] = {"params": params, "return": ret_type}
                        if mname == "__init__":
                            self.collect_self_attributes(stmt.child_by_field_name("body"), cname)
            elif node.type == "function_definition":
                fname, params, ret_type = self.parse_func_signature(node, is_method=False)
                self.functions[fname] = {"params": params, "return": ret_type}

    def parse_func_signature(self, func_node, is_method=False):
        name = get_text(func_node.child_by_field_name("name"))
        params_node = func_node.child_by_field_name("parameters")
        params = {}
        for p in params_node.named_children:
            if p.type == "identifier":
                pname = get_text(p)
                if is_method and pname == "self":
                    continue
                params[pname] = "any"
            elif p.type == "typed_parameter":
                pname = get_text(p.named_children[0])
                ptype = get_text(p.child_by_field_name("type"))
                if is_method and pname == "self":
                    continue
                params[pname] = ptype
        ret_node = func_node.child_by_field_name("return_type")
        ret_type = get_text(ret_node) if ret_node else "any"
        return name, params, ret_type

    def collect_self_attributes(self, body_node, cname):
        for stmt in body_node.named_children:
            if stmt.type == "expression_statement":
                expr = stmt.named_children[0]
                if expr.type == "assignment":
                    left = expr.child_by_field_name("left")
                    right = expr.child_by_field_name("right")
                    if left.type == "attribute" and get_text(left.child_by_field_name("object")) == "self":
                        attr_name = get_text(left.child_by_field_name("attribute"))
                        self.classes[cname]["attributes"][attr_name] = self.infer_type(right)

    def analyze(self, root):
        self.collect_signatures(root)
        for c in self.classes:
            self.scopes[0][c] = c
        for f in self.functions:
            self.scopes[0][f] = f
        self.scopes[0]["print"] = "builtin"
        self.scopes[0]["ValueError"] = "builtin"
        self.scopes[0]["__name__"] = "str"

        for node in root.named_children:
            if node.type == "class_definition":
                cname = get_text(node.child_by_field_name("name"))
                self.current_class = cname
                body = node.child_by_field_name("body")
                for stmt in body.named_children:
                    if stmt.type == "function_definition":
                        self.analyze_function(stmt, cname)
                self.current_class = None
            elif node.type == "function_definition":
                self.analyze_function(node, None)

    def analyze_function(self, func_node, cname):
        fname, params, ret_type = self.parse_func_signature(func_node, is_method=(cname is not None))
        self.current_func = (fname, ret_type)
        local_scope = dict(params)
        if cname:
            local_scope["self"] = cname
        self.scopes.append(local_scope)
        self.visit_block(func_node.child_by_field_name("body"))
        self.scopes.pop()
        self.current_func = None

    def visit_block(self, node):
        if node is None:
            return
        for child in node.named_children:
            t = child.type
            if t == "expression_statement":
                expr = child.named_children[0]
                if expr.type == "assignment":
                    left = expr.child_by_field_name("left")
                    right = expr.child_by_field_name("right")
                    inferred = self.infer_type(right)
                    if left.type == "identifier":
                        self.current_scope()[get_text(left)] = inferred
                    elif left.type == "attribute":
                        self.infer_type(left)
                elif expr.type == "augmented_assignment":
                    self.infer_type(expr.child_by_field_name("left"))
                    self.infer_type(expr.child_by_field_name("right"))
                else:
                    self.infer_type(expr)
            elif t == "if_statement":
                self.infer_type(child.child_by_field_name("condition"))
                self.visit_block(child.child_by_field_name("consequence"))
                alt = child.child_by_field_name("alternative")
                if alt:
                    self.visit_block(alt)
            elif t == "else_clause":
                self.visit_block(child.child_by_field_name("body"))
            elif t == "for_statement":
                left = child.child_by_field_name("left")
                right = child.child_by_field_name("right")
                iter_type = self.infer_type(right)
                elem_type = "Order" if get_text(right) == "self.orders" else ("dict" if iter_type == "list" else "unknown")
                if left.type == "identifier":
                    self.current_scope()[get_text(left)] = elem_type
                self.visit_block(child.child_by_field_name("body"))
            elif t == "return_statement":
                if child.named_children:
                    ret_val_type = self.infer_type(child.named_children[0])
                    fname, expected_ret = self.current_func
                    if expected_ret != "any" and ret_val_type not in ("unknown", "error") and ret_val_type != expected_ret:
                        self.add_error(
                            child.start_point[0] + 1,
                            "Type Mismatch (Return Type)",
                            f"Fungsi '{fname}' mendeklarasikan return '{expected_ret}', tetapi mengembalikan '{ret_val_type}'."
                        )


analyzer = SemanticAnalyzer()
analyzer.analyze(tree.root_node)

print("=== DAFTAR ERROR SEMANTIK TERDETEKSI ===")
for idx, err in enumerate(analyzer.errors, 1):
    print(f"{idx}. {err}")