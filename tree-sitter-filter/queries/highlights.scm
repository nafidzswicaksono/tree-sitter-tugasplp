; Kata kunci logika dan operator teks
["and" "or" "not" "in" "contains"] @keyword

; Operator perbandingan
["=" "!=" ">" "<" ">=" "<="] @operator

; Nilai literal
(string) @string
(number) @number
; boolean memakai @type.builtin agar warnanya berbeda dari @number
; pada tema default CLI (keduanya akan sama jika memakai @constant.builtin).
(boolean) @type.builtin

; Nama field di semua jenis ekspresi
(comparison field: (identifier) @property)
(in_expression field: (identifier) @property)
(contains_expression field: (identifier) @property)
