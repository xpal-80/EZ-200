#!/usr/bin/env python3
"""
Kodak EZ200 (040a:0300) — driver photo officiel
Protocole : libgphoto2 camlibs/kodak/ez200/ez200.c (ACTIVE 0xe0, STATUS 0x06,
  PICTURE 0x08, PICTURE_HEAD 0x0b) + bulk 0x82.
Docs : docs/PROTOCOL.md
"""
import sys
import time
import argparse
import pathlib
from typing import Optional

VID, PID = 0x040a, 0x0300
IFACE = 1
EP_IN = 0x82

ACTIVE = 0xe0
STATUS = 0x06
PICTURE = 0x08
ERASE = 0x09
PICTURE_HEAD = 0x0b

HEADER_SIZE = 0x26F      # 623
DATA_HEADER_SIZE = 0x200 # 512
JPG_HEADER_SIZE = 0x24D  # 589


def _require_usb():
    try:
        import usb.core, usb.util  # type: ignore
        return usb.core, usb.util
    except ImportError:
        print("pyusb requis : pip install pyusb", file=sys.stderr)
        sys.exit(2)


def open_dev():
    usb_core, usb_util = _require_usb()
    dev = usb_core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print(f"EZ200 non trouvé ({VID:04x}:{PID:04x})", file=sys.stderr)
        sys.exit(1)
    # détache kernel gspca_spca500 sur IFACE 0 si besoin
    for iface in (0, 1):
        if dev.is_kernel_driver_active(iface):
            try:
                dev.detach_kernel_driver(iface)
            except Exception:
                pass
    try:
        dev.set_configuration()
    except Exception:
        pass
    # claim iface 1 (photo)
    try:
        usb_util.claim_interface(dev, IFACE)
    except Exception:
        pass
    return dev


def poll_status(dev, timeout=2.0) -> None:
    """Poll 0x06 jusqu'à 0"""
    t0 = time.time()
    while True:
        try:
            c = dev.ctrl_transfer(0xC0, STATUS, 0, 0, 1, timeout=1000)
            if c and c[0] == 0:
                return
        except Exception:
            pass
        if time.time() - t0 > timeout:
            raise TimeoutError("poll STATUS timeout")
        time.sleep(0.05)


def enter_photo_mode(dev) -> None:
    # Robust enter: ensure webcam mode first, then photo, with retries + USB reset for chaining
    import time
    for attempt in range(3):
        try:
            dev.ctrl_transfer(0x40, ACTIVE, 0, 0, b"", timeout=1000)
            time.sleep(0.4)
            poll_status(dev, timeout=1.0)
        except Exception:
            pass
        time.sleep(0.3)
        try:
            dev.ctrl_transfer(0x40, ACTIVE, 0, 1, b"", timeout=1000)
            poll_status(dev, timeout=4.0)
            return
        except TimeoutError:
            if attempt < 2:
                time.sleep(0.8)
                # try soft USB reset on last attempt
                if attempt == 1:
                    try:
                        dev.reset()
                        time.sleep(1.0)
                    except Exception:
                        pass
                continue
            raise


def exit_photo_mode(dev) -> None:
    try:
        dev.ctrl_transfer(0x40, ACTIVE, 0, 0, b"", timeout=1000)
        poll_status(dev, timeout=4.0)
    except Exception:
        pass
    time.sleep(0.5)


def get_num_pics(dev) -> int:
    c = dev.ctrl_transfer(0xC0, PICTURE, 0, 0, 1, timeout=1000)
    return int(c[0])


def get_picture_size(dev, n: int) -> int:
    c = dev.ctrl_transfer(0xC0, PICTURE, n, 1, 3, timeout=1000)
    size = c[0] | (c[1] << 8) | (c[2] << 16)
    if size >= 0xFFFFF:
        raise ValueError(f"taille invalide {size:#x} pour n={n}")
    return size


def read_picture_data(dev, n: int, size: int) -> bytes:
    # annonce (même requête que get_size)
    dev.ctrl_transfer(0xC0, PICTURE, n, 1, 3, timeout=1000)
    # bulk IN
    data = bytearray()
    remaining = size
    # libgphoto2 lit par blocs 0x1000 via gp_port_read
    while remaining > 0:
        chunk = dev.read(EP_IN, min(0x1000, remaining), timeout=3000)
        data.extend(chunk)
        remaining -= len(chunk)
        if len(chunk) == 0:
            break
    if len(data) != size:
        raise IOError(f"bulk incomplet : {len(data)}/{size}")
    return bytes(data)


def read_picture_header(dev) -> bytes:
    hdr = dev.ctrl_transfer(0xC0, PICTURE_HEAD, 3, 3, HEADER_SIZE, timeout=1000)
    if len(hdr) != HEADER_SIZE:
        raise IOError(f"header incomplet {len(hdr)} != {HEADER_SIZE}")
    return bytes(hdr)


def get_picture(dev, n: int) -> bytes:
    size = get_picture_size(dev, n)
    data = read_picture_data(dev, n, size)
    hdr = read_picture_header(dev)
    # reassemblage libgphoto2 : data_start = data + (HEADER - DATA_HEADER)
    # fichier = hdr (623o) + data[0x200:]
    return hdr + data[DATA_HEADER_SIZE:]


def delete_all(dev) -> None:
    dev.ctrl_transfer(0x40, ERASE, 0, 1, b"", timeout=1000)
    poll_status(dev, timeout=5.0)


def main():
    p = argparse.ArgumentParser(description="Kodak EZ200 driver (040a:0300)")
    p.add_argument("--list", action="store_true", help="liste le nombre de photos")
    p.add_argument("--info", action="store_true", help="infos + nombre")
    p.add_argument("--get", type=int, metavar="N", help="extrait photo N (1-indexé)")
    p.add_argument("--get-all", action="store_true", help="extrait toutes les photos")
    p.add_argument("--delete-all", action="store_true", help="efface toutes les photos (ERASE)")
    p.add_argument("-o", "--output", type=str, default=None, help="fichier ou dossier de sortie")
    args = p.parse_args()

    if not any([args.list, args.info, args.get, args.get_all, args.delete_all]):
        p.print_help()
        sys.exit(0)

    dev = open_dev()
    try:
        enter_photo_mode(dev)
        n_pics = get_num_pics(dev)

        if args.info or args.list:
            print(f"photos: {n_pics}")
            if args.list:
                for n in range(n_pics):
                    try:
                        sz = get_picture_size(dev, n)
                        print(f"  {n:03d} : {sz} octets")
                    except Exception as e:
                        print(f"  {n:03d} : erreur {e}")

        if args.get is not None:
            n = args.get
            # user gives 1-indexed, device is 0-indexed
            dev_n = n - 1 if n >= 1 else n
            if n < 1 or n > n_pics:
                print(f"N hors bornes 1..{n_pics}", file=sys.stderr)
                sys.exit(1)
            buf = get_picture(dev, dev_n)
            out = pathlib.Path(args.output) if args.output else pathlib.Path(f"ez200_pic{n:03d}.jpg")
            if out.is_dir():
                out = out / f"ez200_pic{n:03d}.jpg"
            out.write_bytes(buf)
            print(f"photo {n} -> {out} ({len(buf)} octets)")

        if args.get_all:
            outdir = pathlib.Path(args.output) if args.output else pathlib.Path("photos")
            outdir.mkdir(parents=True, exist_ok=True)
            if n_pics == 0:
                print("aucune photo")
            for n in range(1, n_pics + 1):
                buf = get_picture(dev, n-1)
                out = outdir / f"ez200_pic{n:03d}.jpg"
                out.write_bytes(buf)
                print(f"photo {n} -> {out} ({len(buf)} octets)")

        if args.delete_all:
            if n_pics == 0:
                print("rien à effacer")
            else:
                print(f"effacement de {n_pics} photos...")
                delete_all(dev)
                print("effacé")

    finally:
        try:
            exit_photo_mode(dev)
        except Exception:
            pass
        # release
        try:
            import usb.util  # type: ignore
            usb.util.release_interface(dev, IFACE)
        except Exception:
            pass


if __name__ == "__main__":
    main()
