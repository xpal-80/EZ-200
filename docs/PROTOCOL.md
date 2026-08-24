# Protocole KODAK EZ200

Source : `libgphoto2/camlibs/kodak/ez200/ez200.c`.

## USB descriptor

```
VID 040a PID 0300 USB 1.10 Vendor Specific
Config 1 : 500mA
  If 1 (photo) : Bulk IN 0x82 (64) / OUT 0x03
```

`ACTIVE 0xe0` commute.

## Mode photo (bulk)

```
WRITE ACTIVE 0xe0 wValue 0 wIndex 1 → enter → poll STATUS 0x06 jusqu'à 0x00 (retry 3× + dev.reset() si timeout)
READ  PICTURE 0x08 wValue 0 wIndex 0 len1 → N (0..20, 4 Mo max, 64/128 selon qualité)
READ  PICTURE 0x08 wValue n wIndex 1 len3 → LE24 size (n = 0 .. N-1, 0-based)
READ  PICTURE 0x08 wValue n wIndex 1 len3 (re-trigger) + BULK 0x82 size (chunks 0x1000)
READ  PICTURE_HEAD 0x0b wValue 3 wIndex 3 len 623 (589 JPEG header + 34)
JPEG = header (623) + data[512:]
WRITE ACTIVE 0xe0 wValue 0 wIndex 0 → leave → poll
WRITE ERASE 0x09 wValue 0 wIndex 1 → efface tout (après récupération, en 1 session get-all+delete)
```

- `hdr 623` identique pour les 20 images ; `data[:512]` varie par image (qval 42→200) mais non utilisé pour le brut.

---

# KODAK EZ200 Protocol

Source: `libgphoto2/camlibs/kodak/ez200/ez200.c`.

## USB descriptor

```
VID 040a PID 0300 USB 1.10 Vendor Specific
Config 1 : 500mA
  If 1 (photo): Bulk IN 0x82 (64) / OUT 0x03
```

`ACTIVE 0xe0` switches.

## Photo mode (bulk)

```
WRITE ACTIVE 0xe0 wValue 0 wIndex 1 → enter → poll STATUS 0x06 until 0x00 (3× retry + dev.reset() on timeout)
READ  PICTURE 0x08 wValue 0 wIndex 0 len1 → N (0..20, 4 MB max, 64/128 depending on quality)
READ  PICTURE 0x08 wValue n wIndex 1 len3 → LE24 size (n = 0 .. N-1, 0-based)
READ  PICTURE 0x08 wValue n wIndex 1 len3 (re-trigger) + BULK 0x82 size (chunks 0x1000)
READ  PICTURE_HEAD 0x0b wValue 3 wIndex 3 len 623 (589 JPEG header + 34)
JPEG = header (623) + data[512:]
WRITE ACTIVE 0xe0 wValue 0 wIndex 0 → leave → poll
WRITE ERASE 0x09 wValue 0 wIndex 1 → erase all (after retrieval, in 1 session get-all+delete)
```

- `hdr 623` identical for all 20 images; `data[:512]` varies per image (qval 42→200) but not used for raw.
