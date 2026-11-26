"""cek.py - pemeriksa sederhana untuk file Python berbasis tree-sitter.

Tiga pemeriksaan:
  1. Komentar TODO / FIXME
  2. Fungsi yang lebih dari 30 baris
  3. File yang pohon sintaksnya mengandung error

Pemakaian: python cek.py <folder>
"""
import sys
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor

PY = Language(tspython.language())
parser = Parser(PY)

BATAS_BARIS = 30
FOLDER_DILEWATI = {"venv", ".venv", ".git", "node_modules", "__pycache__"}

# Query dibuat sekali di luar fungsi agar tidak dikompilasi ulang per file.
Q_TODO = Query(PY, '((comment) @c (#match? @c "TODO|FIXME"))')
Q_FUNGSI = Query(PY, "(function_definition name: (identifier) @nama) @fungsi")


def teks(node):
    return node.text.decode(errors="replace")


def cari_error_pertama(node):
    """Telusuri pohon (DFS, urut sumber) dan kembalikan node ERROR/MISSING pertama."""
    if node.is_error or node.is_missing:
        return node
    if not node.has_error:  # subtree ini bersih, tidak perlu ditelusuri
        return None
    for child in node.children:
        ditemukan = cari_error_pertama(child)
        if ditemukan is not None:
            return ditemukan
    return None


def cek_file(path):
    """Memeriksa satu file, mengembalikan jumlah temuan."""
    tree = parser.parse(path.read_bytes())
    temuan = 0

    # Fitur 1: komentar TODO/FIXME
    for node in QueryCursor(Q_TODO).captures(tree.root_node).get("c", []):
        print(f"{path}:{node.start_point[0] + 1}: [TODO] {teks(node).strip()}")
        temuan += 1

    # Fitur 2: fungsi yang lebih dari 30 baris
    for _, cap in QueryCursor(Q_FUNGSI).matches(tree.root_node):
        fungsi = cap["fungsi"][0]
        nama = teks(cap["nama"][0])
        jumlah = fungsi.end_point[0] - fungsi.start_point[0] + 1
        if jumlah > BATAS_BARIS:
            print(f"{path}:{fungsi.start_point[0] + 1}: [FUNGSI PANJANG] "
                  f"{nama}() {jumlah} baris (batas {BATAS_BARIS})")
            temuan += 1

    # Fitur 3: file dengan error sintaks
    if tree.root_node.has_error:
        err = cari_error_pertama(tree.root_node)
        jenis = "MISSING " + err.type if err.is_missing else "ERROR"
        print(f"{path}:{err.start_point[0] + 1}: [SINTAKS] {jenis} "
              f"di kolom {err.start_point[1]}")
        temuan += 1

    return temuan


def main():
    if len(sys.argv) != 2:
        print("Pemakaian: python cek.py <folder>")
        return 2
    akar = Path(sys.argv[1])
    if not akar.is_dir():
        print(f"Bukan folder: {akar}")
        return 2

    jumlah_file = jumlah_temuan = 0
    for path in sorted(akar.rglob("*.py")):
        if FOLDER_DILEWATI.intersection(path.parts):
            continue
        jumlah_file += 1
        jumlah_temuan += cek_file(path)

    print(f"\n{jumlah_file} file diperiksa, {jumlah_temuan} temuan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
