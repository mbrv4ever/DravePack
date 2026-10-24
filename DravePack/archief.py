# -*- coding: utf-8 -*-
"""DravePack - archief-motor (in-/uitpakken, lijsten) voor zip, tar(.gz/.bz2/.xz),
7z, iso en rar (rar = alleen uitpakken). Puur functioneel, geen GUI; zo apart
testbaar. 7z en rar worden 'lui' geimporteerd: ontbreekt de bibliotheek, dan
geeft de functie een nette fout in plaats van te crashen."""
import os
import io
import zipfile
import tarfile


class ArchiefFout(Exception):
    pass


# Formaten die we kunnen MAKEN (volgorde voor de keuzelijst)
MAAK_FORMATEN = ["zip", "7z", "tar", "tar.gz", "tar.bz2", "tar.xz", "iso"]
# Bestandsextensie per maak-formaat
EXT = {
    "zip": ".zip", "7z": ".7z", "tar": ".tar", "tar.gz": ".tar.gz",
    "tar.bz2": ".tar.bz2", "tar.xz": ".tar.xz", "iso": ".iso",
}


def detecteer_formaat(pad):
    p = pad.lower()
    if p.endswith((".tar.gz", ".tgz")):
        return "tar.gz"
    if p.endswith((".tar.bz2", ".tbz2", ".tbz")):
        return "tar.bz2"
    if p.endswith((".tar.xz", ".txz")):
        return "tar.xz"
    if p.endswith(".tar"):
        return "tar"
    if p.endswith(".zip"):
        return "zip"
    if p.endswith(".7z"):
        return "7z"
    if p.endswith(".iso"):
        return "iso"
    if p.endswith(".rar"):
        return "rar"
    return ""


def _verzamel(bronnen):
    """Maak een lijst (absoluut_pad, naam_in_archief) van bestanden uit een lijst
    van bronnen (bestanden en/of mappen). Mappen behouden hun structuur onder hun
    eigen naam; meerdere bronnen worden zo samengevoegd in een archief."""
    bestanden = []
    mappen = set()
    for bron in bronnen:
        bron = os.path.abspath(bron)
        if os.path.isfile(bron):
            bestanden.append((bron, os.path.basename(bron)))
        elif os.path.isdir(bron):
            basis = os.path.basename(bron.rstrip(os.sep))
            mappen.add(basis)
            for root, dirs, files in os.walk(bron):
                rel_root = os.path.relpath(root, bron)
                arc_root = basis if rel_root == "." else os.path.join(basis, rel_root)
                for d in dirs:
                    mappen.add(os.path.join(arc_root, d).replace(os.sep, "/"))
                for f in files:
                    bestanden.append((os.path.join(root, f),
                                      os.path.join(arc_root, f).replace(os.sep, "/")))
    return bestanden, sorted(mappen)


# ---------------------------------------------------------------------------
# MAKEN
# ---------------------------------------------------------------------------
def maak_archief(formaat, doel, bronnen, wachtwoord="", niveau=5, voortgang=None):
    bestanden, mappen = _verzamel(bronnen)
    if not bestanden and not mappen:
        raise ArchiefFout("geen bestanden")
    tmp = doel + ".tmp"
    try:
        if formaat == "zip":
            _maak_zip(tmp, bestanden, wachtwoord, niveau, voortgang)
        elif formaat in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
            _maak_tar(tmp, formaat, bronnen, voortgang)
        elif formaat == "7z":
            _maak_7z(tmp, bestanden, wachtwoord, voortgang)
        elif formaat == "iso":
            _maak_iso(tmp, bestanden, mappen, voortgang)
        else:
            raise ArchiefFout("onbekend formaat: %s" % formaat)
        os.replace(tmp, doel)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _maak_zip(doel, bestanden, wachtwoord, niveau, voortgang):
    n = len(bestanden)
    if wachtwoord:
        import pyzipper
        with pyzipper.AESZipFile(doel, "w", compression=pyzipper.ZIP_DEFLATED,
                                 encryption=pyzipper.WZ_AES) as z:
            z.setpassword(wachtwoord.encode("utf-8"))
            for i, (ap, arc) in enumerate(bestanden):
                z.write(ap, arc)
                if voortgang:
                    voortgang(i + 1, n)
    else:
        comp = zipfile.ZIP_DEFLATED if niveau > 0 else zipfile.ZIP_STORED
        with zipfile.ZipFile(doel, "w", comp, compresslevel=niveau or None) as z:
            for i, (ap, arc) in enumerate(bestanden):
                z.write(ap, arc)
                if voortgang:
                    voortgang(i + 1, n)


def _maak_tar(doel, formaat, bronnen, voortgang):
    modus = {"tar": "w", "tar.gz": "w:gz", "tar.bz2": "w:bz2", "tar.xz": "w:xz"}[formaat]
    bestanden, _ = _verzamel(bronnen)
    n = len(bestanden)
    with tarfile.open(doel, modus) as t:
        for i, (ap, arc) in enumerate(bestanden):
            t.add(ap, arcname=arc, recursive=False)
            if voortgang:
                voortgang(i + 1, n)


def _maak_7z(doel, bestanden, wachtwoord, voortgang):
    import py7zr
    n = len(bestanden)
    # Wel de inhoud versleutelen, maar NIET de namenlijst (header): zo kun je de
    # inhoud bekijken zonder wachtwoord, en is het wachtwoord pas nodig bij uitpakken
    # (zelfde gedrag als zip; vriendelijker in de schil).
    kwargs = {"password": wachtwoord} if wachtwoord else {}
    with py7zr.SevenZipFile(doel, "w", **kwargs) as z:
        for i, (ap, arc) in enumerate(bestanden):
            z.write(ap, arc)
            if voortgang:
                voortgang(i + 1, n)


def _maak_iso(doel, bestanden, mappen, voortgang):
    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, interchange_level=3)
    iso_dir_van_real = {"": "/"}
    dir_teller = [0]

    def zorg_iso_dir(real_rel):
        real_rel = real_rel.strip("/")
        if real_rel in iso_dir_van_real:
            return iso_dir_van_real[real_rel]
        ouder = os.path.dirname(real_rel)
        ouder_iso = zorg_iso_dir(ouder)
        dir_teller[0] += 1
        naam = "DIR%05d" % dir_teller[0]
        iso_path = (ouder_iso.rstrip("/") + "/" + naam) or "/" + naam
        joliet_path = "/" + real_rel
        iso.add_directory(iso_path, joliet_path=joliet_path)
        iso_dir_van_real[real_rel] = iso_path
        return iso_path

    for m in mappen:
        zorg_iso_dir(m)

    n = len(bestanden)
    for i, (ap, arc) in enumerate(bestanden):
        arc = arc.replace(os.sep, "/").lstrip("/")
        d = os.path.dirname(arc)
        ouder_iso = zorg_iso_dir(d) if d else "/"
        ext = os.path.splitext(arc)[1].lstrip(".").upper()
        ext = "".join(c for c in ext if c.isalnum())[:3] or "DAT"
        iso_naam = "F%07d.%s;1" % (i + 1, ext)
        iso_path = (ouder_iso.rstrip("/") + "/" + iso_naam)
        joliet_path = "/" + arc
        with open(ap, "rb") as f:
            data = f.read()
        iso.add_fp(io.BytesIO(data), len(data), iso_path, joliet_path=joliet_path)
        if voortgang:
            voortgang(i + 1, n)
    iso.write(doel)
    iso.close()


# ---------------------------------------------------------------------------
# LIJSTEN
# ---------------------------------------------------------------------------
def lijst_inhoud(pad, wachtwoord=""):
    """Geef een lijst (naam, grootte_in_bytes) van de bestanden in het archief."""
    fmt = detecteer_formaat(pad)
    items = []
    if fmt == "zip":
        import pyzipper
        try:
            z = pyzipper.AESZipFile(pad)
        except Exception:
            z = zipfile.ZipFile(pad)
        with z:
            for info in z.infolist():
                if not info.is_dir():
                    items.append((info.filename, info.file_size))
    elif fmt in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
        with tarfile.open(pad) as t:
            for m in t.getmembers():
                if m.isfile():
                    items.append((m.name, m.size))
    elif fmt == "7z":
        import py7zr
        with py7zr.SevenZipFile(pad, "r", password=wachtwoord or None) as z:
            for info in z.list():
                if not info.is_directory:
                    items.append((info.filename, info.uncompressed))
    elif fmt == "iso":
        import pycdlib
        iso = pycdlib.PyCdlib()
        iso.open(pad)
        try:
            for dirname, _dirs, files in iso.walk(joliet_path="/"):
                for f in files:
                    pad_in = (dirname.rstrip("/") + "/" + f)
                    rec = iso.get_record(joliet_path=pad_in)
                    items.append((pad_in.lstrip("/"), getattr(rec, "data_length", 0)))
        finally:
            iso.close()
    elif fmt == "rar":
        import rarfile
        with rarfile.RarFile(pad) as r:
            for info in r.infolist():
                if not info.isdir():
                    items.append((info.filename, info.file_size))
    else:
        raise ArchiefFout("onbekend of niet-ondersteund formaat")
    return items


# ---------------------------------------------------------------------------
# UITPAKKEN
# ---------------------------------------------------------------------------
def pak_uit(pad, doelmap, wachtwoord="", alleen=None, voortgang=None):
    """Pak het archief uit naar doelmap. 'alleen' = optionele set namen om alleen
    die te pakken (anders alles)."""
    fmt = detecteer_formaat(pad)
    os.makedirs(doelmap, exist_ok=True)
    if fmt == "zip":
        _uit_zip(pad, doelmap, wachtwoord, alleen, voortgang)
    elif fmt in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
        _uit_tar(pad, doelmap, alleen, voortgang)
    elif fmt == "7z":
        _uit_7z(pad, doelmap, wachtwoord, alleen, voortgang)
    elif fmt == "iso":
        _uit_iso(pad, doelmap, alleen, voortgang)
    elif fmt == "rar":
        _uit_rar(pad, doelmap, wachtwoord, alleen, voortgang)
    else:
        raise ArchiefFout("onbekend of niet-ondersteund formaat")


def _veilig_pad(doelmap, naam):
    doel = os.path.abspath(os.path.join(doelmap, naam))
    if not doel.startswith(os.path.abspath(doelmap) + os.sep) and \
            doel != os.path.abspath(doelmap):
        raise ArchiefFout("onveilig pad in archief: %s" % naam)
    return doel


def _uit_zip(pad, doelmap, wachtwoord, alleen, voortgang):
    import pyzipper
    if wachtwoord:
        pw_varianten = []
        for enc in ("utf-8", "cp437", "latin-1"):
            try:
                b = wachtwoord.encode(enc)
                if b not in pw_varianten:
                    pw_varianten.append(b)
            except Exception:
                pass
    else:
        pw_varianten = [None]
    laatste = None
    ww_fout = None
    # Probeer AES (pyzipper) en daarna gewoon/ZipCrypto (stdlib), elk met de
    # verschillende wachtwoord-coderingen. De eerste combinatie die werkt, wint.
    for opener in (pyzipper.AESZipFile, zipfile.ZipFile):
        for pw in pw_varianten:
            try:
                with opener(pad) as z:
                    namen = [n for n in z.namelist() if not n.endswith("/")]
                    doelnamen = [n for n in namen if (not alleen or n in alleen)]
                    n = len(doelnamen)
                    for i, naam in enumerate(doelnamen):
                        _veilig_pad(doelmap, naam)
                        z.extract(naam, doelmap, pwd=pw)
                        if voortgang:
                            voortgang(i + 1, n)
                return
            except Exception as e:
                laatste = e
                low = str(e).lower()
                if ww_fout is None and any(k in low for k in
                                           ("password", "pass", "encrypt", "crc", "corrupt")):
                    ww_fout = e
                continue
    if ww_fout or laatste:
        raise ww_fout or laatste


def _uit_tar(pad, doelmap, alleen, voortgang):
    with tarfile.open(pad) as t:
        leden = [m for m in t.getmembers() if m.isfile()]
        if alleen:
            leden = [m for m in leden if m.name in alleen]
        n = len(leden)
        for i, m in enumerate(leden):
            _veilig_pad(doelmap, m.name)
            t.extract(m, doelmap)
            if voortgang:
                voortgang(i + 1, n)


def _uit_7z(pad, doelmap, wachtwoord, alleen, voortgang):
    import py7zr
    with py7zr.SevenZipFile(pad, "r", password=wachtwoord or None) as z:
        if alleen:
            z.extract(path=doelmap, targets=list(alleen))
        else:
            z.extractall(path=doelmap)
    if voortgang:
        voortgang(1, 1)


def _uit_iso(pad, doelmap, alleen, voortgang):
    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.open(pad)
    try:
        alle = []
        for dirname, _dirs, files in iso.walk(joliet_path="/"):
            for f in files:
                alle.append(dirname.rstrip("/") + "/" + f)
        if alleen:
            alle = [p for p in alle if p.lstrip("/") in alleen]
        n = len(alle)
        for i, pad_in in enumerate(alle):
            rel = pad_in.lstrip("/")
            doel = _veilig_pad(doelmap, rel)
            os.makedirs(os.path.dirname(doel), exist_ok=True)
            with open(doel, "wb") as out:
                iso.get_file_from_iso_fp(out, joliet_path=pad_in)
            if voortgang:
                voortgang(i + 1, n)
    finally:
        iso.close()


def _uit_rar(pad, doelmap, wachtwoord, alleen, voortgang):
    import rarfile
    with rarfile.RarFile(pad) as r:
        if wachtwoord:
            r.setpassword(wachtwoord)
        namen = [i.filename for i in r.infolist() if not i.isdir()]
        if alleen:
            namen = [x for x in namen if x in alleen]
        n = len(namen)
        for i, naam in enumerate(namen):
            _veilig_pad(doelmap, naam)
            r.extract(naam, doelmap)
            if voortgang:
                voortgang(i + 1, n)


def rar_backend_beschikbaar():
    """True als rar uitgepakt kan worden (er is een unrar/7z/bsdtar gevonden)."""
    try:
        import rarfile
        rarfile.tool_setup()
        return True
    except Exception:
        return False
