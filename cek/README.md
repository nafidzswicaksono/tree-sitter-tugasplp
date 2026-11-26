# cek.py: pemeriksa file Python berbasis tree-sitter (Tugas 6)

CLI kecil yang memindai semua file `*.py` di sebuah folder (rekursif) dan melaporkan tiga hal:

| Label | Arti | Cara kerja |
| --- | --- | --- |
| `[TODO]` | Komentar yang mengandung `TODO` atau `FIXME` | Query `((comment) @c (#match? @c "TODO\|FIXME"))` |
| `[FUNGSI PANJANG]` | Fungsi dengan lebih dari 30 baris | Query `function_definition`, lalu `end_point - start_point + 1` |
| `[SINTAKS]` | File yang pohonnya mengandung `ERROR` / `MISSING` | `root_node.has_error`, lalu DFS mencari node error pertama |

Karena memakai pohon sintaks, kata `TODO` di dalam *string* tidak ikut dilaporkan (hanya komentar sungguhan).

## Memasang dependensi

Butuh Python 3.10+.

```bash
python -m pip install tree-sitter tree-sitter-python
```

(Diuji dengan `tree-sitter` 0.27 dan `tree-sitter-python` 0.25, memakai API `Parser(LANG)`, `Query`, `QueryCursor`.)

## Menjalankan

```bash
python cek.py <folder>
```

Contoh pada folder uji buatan sendiri:

```bash
python cek.py uji/
```

```
uji/ada_todo.py:1: [TODO] # TODO: tambahkan validasi input
uji/ada_todo.py:3: [TODO] # FIXME: belum menangani pembagian dengan nol
uji/fungsi_panjang.py:1: [FUNGSI PANJANG] fungsi_panjang() 36 baris (batas 30)
uji/rusak.py:1: [SINTAKS] ERROR di kolom 0

4 file diperiksa, 4 temuan.
```

Format tiap baris: `file:baris: [JENIS] keterangan`. Folder `venv`, `.venv`, `.git`, `node_modules`, dan `__pycache__` dilewati.

Contoh pada repo nyata ([psf/requests](https://github.com/psf/requests)): lihat `hasil-requests.txt`.

## Catatan

- **Semua fungsi dihitung**, termasuk method di dalam kelas dan fungsi bersarang, sehingga satu blok kode bisa muncul dua kali (fungsi luar dan fungsi dalam).
- Baris awal fungsi adalah baris `def` atau baris dekorator pertama (`@...`), karena dekorator bagian dari node `function_definition`.
- Lokasi `[SINTAKS]` adalah node `ERROR`/`MISSING` pertama yang ditemukan parser. Untuk kode yang rusak, tree-sitter bisa menandai area yang lebih luas dari titik kesalahan sebenarnya.
- File dibaca sebagai bytes dan teks di-decode dengan `errors="replace"`, jadi file dengan encoding lain tidak membuat program berhenti.
- Kode keluar (exit code): `0` jika berjalan normal, `2` jika argumen salah.

## Struktur

```
cek/
├── cek.py
├── README.md
├── hasil-requests.txt   # output pada repo nyata
└── uji/                 # file uji buatan sendiri
    ├── ada_todo.py      # komentar TODO/FIXME (+ kata TODO di dalam string, tidak dilaporkan)
    ├── fungsi_panjang.py
    ├── rusak.py         # sintaks rusak
    └── bersih.py        # tidak boleh menghasilkan temuan
```
