import tree_sitter_python as tspython
from tree_sitter import Language, Parser

parser = Parser(Language(tspython.language()))

fungsi = b"def sapa(nama):\n    return nama\n"
if_else = b"if x > 0:\n    print('positif')\nelse:\n    print('non-positif')\n"
kelas = b"class Hewan:\n    def suara(self):\n        return 'halo'\n"

tree = parser.parse(fungsi)
print(tree.root_node)