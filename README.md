# Kodak EZ200 (040a:0300) — Récupération photos

Outil pour **Kodak EZ200 (040a:0300)** sur Linux (Raspberry Pi) — mode photo.

## Protocole (ez200.c)

```
ACTIVE 0xe0 idx 1 → enter photo mode → poll STATUS 0x06 jusqu'à 0x00
PICTURE 0x08 n,1 → 3 bytes LE size (n = 0 .. N-1, 0-based)
  → PICTURE 0x08 n,1 (3o) + bulk IN 0x82 size → données
PICTURE_HEAD 0x0b 3,3 → 623 bytes header (589o JPEG header + 34o)
JPEG final = header (623) + data[512:]
ACTIVE 0xe0 idx 0 → leave photo mode
ERASE 0x09 → efface tout
```

- N = `PICTURE 0x08 0,0` (1 byte)
- Tailles : 11K → 51K, 20 photos max selon qualité (64/128)
- Qualité changeable entre prises (header 623 identique, 512o data header varie)

## Usage

```bash
sudo python3 src/ez200.py --list
sudo python3 src/ez200.py --get-all -o ./photos
sudo python3 src/ez200.py --get-all -o ./photos --delete-all  # en 1 session
sudo python3 src/ez200.py --get 1 -o ./photos
```

- `enter` : `ACTIVE 0` → wait → `ACTIVE 1` avec retry 3× + `dev.reset()` si timeout
- `0..n-1` obligatoire

## Fichiers

```
src/ez200.py          # driver photo (ACTIVE/STATUS/PICTURE/ERASE)
photos/               # sortie
```

Licence GPL-2.0.

---

# Kodak EZ200 (040a:0300) — Photo Retrieval

Tool for **Kodak EZ200 (040a:0300)** on Linux (Raspberry Pi) — photo mode.

## Protocol (ez200.c)

```
ACTIVE 0xe0 idx 1 → enter photo mode → poll STATUS 0x06 until 0x00
PICTURE 0x08 n,1 → 3 bytes LE size (n = 0 .. N-1, 0-based)
  → PICTURE 0x08 n,1 (3o) + bulk IN 0x82 size → data
PICTURE_HEAD 0x0b 3,3 → 623 bytes header (589o JPEG header + 34o)
Final JPEG = header (623) + data[512:]
ACTIVE 0xe0 idx 0 → leave photo mode
ERASE 0x09 → erase all
```

- N = `PICTURE 0x08 0,0` (1 byte)
- Sizes: 11K → 51K, 20 photos max depending on quality (64/128)
- Quality changeable between shots (header 623 identical, 512o data header varies)

## Usage

```bash
sudo python3 src/ez200.py --list
sudo python3 src/ez200.py --get-all -o ./photos
sudo python3 src/ez200.py --get-all -o ./photos --delete-all  # in 1 session
sudo python3 src/ez200.py --get 1 -o ./photos
```

- `enter`: `ACTIVE 0` → wait → `ACTIVE 1` with 3× retry + `dev.reset()` on timeout
- `0..n-1` required

## Files

```
src/ez200.py          # photo driver (ACTIVE/STATUS/PICTURE/ERASE)
photos/               # output
```

License GPL-2.0.
