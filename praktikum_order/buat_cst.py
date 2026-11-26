import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

with open("simple_order_management.py", "rb") as f:
    source_code = f.read()

tree = parser.parse(source_code)
cst_text = str(tree.root_node)

with open("hasil_cst.txt", "w", encoding="utf-8") as out:
    out.write(cst_text)

print("Sukses! CST lengkap tersimpan di file 'hasil_cst.txt'.")
print("\n--- Cuplikan CST ---")
print(cst_text[:600])