# -*- coding: utf-8 -*-
"""DravePack - in- en uitpakken van archieven (Dravenlock).

Maakt en pakt uit: ZIP (+wachtwoord), 7z (+wachtwoord), TAR/GZ/BZ2/XZ en ISO.
Pakt ook RAR uit (als er een unrar/7-Zip op de pc staat). Meerdere bronnen
samenvoegen in een archief. Volledig lokaal en offline.
"""
import os
import sys
import json
import traceback

import archief

APP_NAAM = "DravePack"
APP_VERSIE = "0.3.2"
DONATIE_URL = "https://paypal.me/roger076"
CONTACT = "service@dravenlock.nl"

if getattr(sys, "frozen", False):
    BASIS = os.path.dirname(sys.executable)
else:
    BASIS = os.path.dirname(os.path.abspath(__file__))
FOUT_BESTAND = os.path.join(BASIS, "app-fout.txt")
DATA_MAP = os.path.join(BASIS, "DravePack-data")
CONFIG_BESTAND = os.path.join(DATA_MAP, "instellingen.json")

BG = "#0e0e11"; PANEL = "#16161b"; PANEL2 = "#1c1c22"; TEXT = "#d4d4d4"
MUTED = "#8a8a94"; ACCENT = "#6fa3d6"; LINE = "#23232b"; WARN = "#d68a6f"
GOED = "#7fb069"


def zorg_voor_mappen():
    try:
        os.makedirs(DATA_MAP, exist_ok=True)
    except OSError:
        pass


def _excepthook(soort, waarde, tb):
    try:
        with open(FOUT_BESTAND, "w", encoding="utf-8") as f:
            f.write("DravePack startfout\n\n")
            f.write("".join(traceback.format_exception(soort, waarde, tb)))
    except Exception:
        pass
    sys.__excepthook__(soort, waarde, tb)


sys.excepthook = _excepthook

STANDAARD_CONFIG = {"taal": "auto", "niveau": 5, "laatste_map": "", "toon_welkom": True}


def laad_config():
    cfg = dict(STANDAARD_CONFIG)
    try:
        with open(CONFIG_BESTAND, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            cfg.update(d)
    except Exception:
        pass
    return cfg


def bewaar_config(cfg):
    try:
        tmp = CONFIG_BESTAND + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_BESTAND)
    except Exception:
        pass


def log_fout(actie, pad, fout):
    """Schrijf de echte fout (met traceback) naar DravePack-data, voor diagnose."""
    try:
        zorg_voor_mappen()
        with open(os.path.join(DATA_MAP, "fout-log.txt"), "a", encoding="utf-8") as f:
            import datetime
            f.write("\n=== %s | %s ===\n" % (datetime.datetime.now().isoformat(timespec="seconds"), actie))
            f.write("archief: %s\n" % pad)
            f.write("".join(traceback.format_exception(type(fout), fout, fout.__traceback__)))
    except Exception:
        pass


def mooie_grootte(n):
    for eenheid in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or eenheid == "TB":
            return ("%.0f %s" % (n, eenheid)) if eenheid == "B" else ("%.1f %s" % (n, eenheid))
        n /= 1024.0


# ---------------------------------------------------------------------------
# Windows-shell-integratie (rechtsklikmenu), per gebruiker -> geen admin nodig.
# Archief-bestanden krijgen 'Uitpakken met DravePack', mappen 'Inpakken met DravePack'.
# ---------------------------------------------------------------------------
CTX_EXTS = (".zip", ".7z", ".rar", ".iso", ".tar", ".gz", ".tgz",
            ".bz2", ".tbz2", ".xz", ".txz")
CTX_VERB_UIT = "DravePack.Uitpakken"
CTX_VERB_IN = "DravePack.Inpakken"


def _app_script():
    try:
        return os.path.abspath(__file__)
    except NameError:
        return os.path.join(BASIS, "app.py")


def _commando_basis():
    """Het deel van het commando dat de app start, klaar om er argumenten aan
    te plakken. Werkt zowel voor de losse .exe als voor het draaien vanuit Python."""
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    return '"%s" "%s"' % (pyw, _app_script())


def _icoon_voor_menu():
    if getattr(sys, "frozen", False):
        return sys.executable
    p = _bundel("app.ico")
    return p if os.path.exists(p) else sys.executable


def _zet_verb(winreg, basis_pad, verb_id, label, argument, icoon):
    sleutel = basis_pad + "\\" + verb_id
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sleutel) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, label)
        if icoon:
            winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icoon)
    cmd = _commando_basis() + " " + argument + ' "%1"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sleutel + "\\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)


def _weg_verb(winreg, basis_pad, verb_id):
    for sub in ("\\command", ""):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, basis_pad + "\\" + verb_id + sub)
        except OSError:
            pass


def registreer_contextmenu():
    """Zet de rechtsklik-items in het register (HKCU). Geeft (ok, fouttekst)."""
    if os.name != "nt":
        return False, "alleen-windows"
    try:
        import winreg
        icoon = _icoon_voor_menu()
        lbl_uit = "Uitpakken met DravePack" if _TAAL == "nl" else "Extract with DravePack"
        lbl_in = "Inpakken met DravePack" if _TAAL == "nl" else "Pack with DravePack"
        # mappen
        _zet_verb(winreg, r"Software\Classes\Directory\shell",
                  CTX_VERB_IN, lbl_in, "--inpakken", icoon)
        # archief-extensies
        for ext in CTX_EXTS:
            basis = r"Software\Classes\SystemFileAssociations\%s\shell" % ext
            _zet_verb(winreg, basis, CTX_VERB_UIT, lbl_uit, "--uitpakken", icoon)
        return True, ""
    except Exception as e:
        return False, str(e)


def verwijder_contextmenu():
    if os.name != "nt":
        return False, "alleen-windows"
    try:
        import winreg
        _weg_verb(winreg, r"Software\Classes\Directory\shell", CTX_VERB_IN)
        for ext in CTX_EXTS:
            basis = r"Software\Classes\SystemFileAssociations\%s\shell" % ext
            _weg_verb(winreg, basis, CTX_VERB_UIT)
        return True, ""
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QStatusBar, QListWidget, QListWidgetItem, QFileDialog,
    QProgressBar, QCheckBox, QAbstractItemView, QTabWidget, QTextBrowser,
)
from PyQt6.QtGui import QAction, QIcon, QDesktopServices, QGuiApplication, QPixmap
from PyQt6.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal


def _bundel(naam):
    return os.path.join(getattr(sys, "_MEIPASS", BASIS), naam)


def app_icoon():
    for naam in ("app.ico", "logo.png"):
        p = _bundel(naam)
        if os.path.isfile(p):
            ic = QIcon(p)
            if not ic.isNull():
                return ic
    return QIcon()


def STIJL():
    return """
    QWidget { background: %(bg)s; color: %(text)s; font-size: 15px; }
    QLabel#titel { font-size: 24px; font-weight: bold; }
    QLabel#sub { color: %(muted)s; }
    QLineEdit, QComboBox, QSpinBox {
        background: %(panel2)s; color: %(text)s; border: 1px solid %(line)s;
        border-radius: 8px; padding: 7px; }
    QLineEdit:focus, QComboBox:focus { border: 1px solid %(accent)s; }
    QListWidget { background: %(panel)s; color: %(text)s; border: 1px solid %(line)s;
        border-radius: 8px; padding: 4px; }
    QListWidget::item:selected { background: %(accent)s; color: #0b0b0e; }
    QPushButton { background: %(panel2)s; color: %(text)s; border: 1px solid %(line)s;
        border-radius: 9px; padding: 8px 12px; }
    QPushButton:hover { border: 1px solid %(accent)s; }
    QPushButton#primair { background: %(accent)s; color: #0b0b0e; border: none; font-weight: bold; }
    QPushButton#primair:hover { background: #84b4e0; }
    QPushButton#gevaar { border: 1px solid %(warn)s; color: %(warn)s; }
    QTabWidget::pane { border: 1px solid %(line)s; border-radius: 8px; }
    QTabBar::tab { background: %(panel)s; color: %(muted)s; padding: 9px 16px;
        border: 1px solid %(line)s; border-bottom: none;
        border-top-left-radius: 8px; border-top-right-radius: 8px; }
    QTabBar::tab:selected { background: %(panel2)s; color: %(text)s; }
    QProgressBar { background: %(panel2)s; border: 1px solid %(line)s; border-radius: 8px;
        text-align: center; color: %(text)s; }
    QProgressBar::chunk { background: %(accent)s; border-radius: 7px; }
    QMenuBar { background: %(bg)s; color: %(text)s; }
    QMenuBar::item:selected { background: %(panel2)s; }
    QMenu { background: %(panel)s; color: %(text)s; border: 1px solid %(line)s; }
    QMenu::item:selected { background: %(accent)s; color: #0b0b0e; }
    QStatusBar { background: %(bg)s; color: %(muted)s; }
    QCheckBox { color: %(text)s; spacing: 10px; } /* vinkje-0.3.2 */
    QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid %(muted)s;
        border-radius: 5px; background: %(panel2)s; }
    QCheckBox::indicator:checked { background: %(accent)s; border-color: %(text)s; }
    """ % {"bg": BG, "panel": PANEL, "panel2": PANEL2, "text": TEXT,
           "muted": MUTED, "accent": ACCENT, "line": LINE, "warn": WARN}


def centreer(d, ouder=None):
    try:
        s = (ouder.screen() if ouder else None) or QGuiApplication.primaryScreen()
        g = s.availableGeometry()
        d.move(g.center().x() - d.width() // 2, g.center().y() - d.height() // 2)
    except Exception:
        pass


def taal_detecteren():
    try:
        from PyQt6.QtCore import QLocale
        return "nl" if QLocale.system().name().lower().startswith("nl") else "en"
    except Exception:
        return "en"


TEKST = {
    "nl": {
        "ondertitel": "Bestanden in- en uitpakken - zip, 7z, tar, iso (en rar uitpakken)",
        "menu_bestand": "Bestand", "menu_help": "Help", "instellingen": "Instellingen",
        "afsluiten": "Afsluiten", "snelgids": "Snelgids", "over": "Over DravePack",
        "donatie": "Donatie", "sluiten": "Sluiten", "opslaan": "Opslaan",
        "annuleren": "Annuleren", "bladeren": "Bladeren...",
        "tab_in": "Inpakken", "tab_uit": "Uitpakken",
        "tab_welkom": "Welkom",
        "welkom_intro": "Pak bestanden in en uit - zip, 7z, tar en iso, en pak rar uit. "
                        "Voeg meerdere bestanden en mappen samen in een archief, met een "
                        "wachtwoord als je wilt. Alles lokaal en offline.",
        "welkom_in": "Bestanden inpakken", "welkom_uit": "Archief uitpakken",
        "welkom_toon": "Dit welkomscherm tonen bij opstarten",
        # inpakken
        "bronnen": "Toe te voegen bestanden en mappen:",
        "best_toevoegen": "Bestanden toevoegen...", "map_toevoegen": "Map toevoegen...",
        "verwijderen": "Verwijderen", "wissen": "Lijst wissen",
        "formaat": "Formaat", "wachtwoord": "Wachtwoord (alleen zip/7z)",
        "tonen": "Tonen", "niveau": "Compressie (0-9, alleen zip)",
        "doel": "Opslaan als", "inpakken": "Inpakken", "bezig_in": "Bezig met inpakken...",
        "klaar_in": "Klaar: {pad}", "geen_bronnen": "Voeg eerst bestanden of mappen toe.",
        "geen_doel": "Kies eerst waar het archief moet komen (Opslaan als).",
        # uitpakken
        "archief": "Archief", "open_archief": "Archief openen...",
        "inhoud": "Inhoud (selecteer voor 'selectie uitpakken'):",
        "doelmap": "Uitpakken naar", "uit_alles": "Alles uitpakken",
        "uit_selectie": "Selectie uitpakken", "bezig_uit": "Bezig met uitpakken...",
        "klaar_uit": "Klaar in: {map}", "geen_archief": "Open eerst een archief.",
        "geen_doelmap": "Kies eerst een map om naar uit te pakken.",
        "lezen_mislukt": "Kon het archief niet lezen. Klopt het wachtwoord? ({fout})",
        "ww_enter": "wachtwoord + Enter",
        "ww_nodig": "Dit archief heeft een wachtwoord. Vul het in en druk op Enter.",
        "ww_fout": "Lezen mislukt - klopt het wachtwoord? ({fout})",
        "ww_uitpak_fout": "Uitpakken mislukt: het wachtwoord ontbreekt of klopt niet.",
        "fout_log": "Details staan in DravePack-data\\fout-log.txt.",
        "items_n": "{n} bestanden, samen {grootte}",
        # algemeen
        "fout": "Er ging iets mis: {fout}",
        "mist_7z": "7z-ondersteuning is niet geinstalleerd. Voer run.bat opnieuw uit, of "
                   "kies een ander formaat (zip werkt altijd).",
        "mist_rar": "Voor rar uitpakken is 7-Zip of WinRAR (of UnRAR) op de pc nodig. "
                    "Installeer een daarvan en probeer opnieuw.",
        "inst_taal": "Taal", "inst_taal_auto": "Automatisch (computertaal)",
        "herstart_taal": "Herstart de app om de taal volledig toe te passen.",
        "ctx_kop": "Windows-rechtsklikmenu",
        "ctx_note": "Voeg 'Uitpakken met DravePack' (op archieven) en 'Inpakken met "
                    "DravePack' (op mappen) toe aan het rechtsklikmenu. Op Windows 11 "
                    "staat het onder 'Meer opties weergeven'.",
        "ctx_zet": "In rechtsklikmenu zetten", "ctx_haal": "Uit rechtsklikmenu halen",
        "ctx_gezet": "Toegevoegd aan het rechtsklikmenu.",
        "ctx_gehaald": "Verwijderd uit het rechtsklikmenu.",
        "over_tekst": "DravePack v{versie}\n\nBestanden in- en uitpakken (zip, 7z, tar, "
                      "iso; rar uitpakken). Lokaal en offline.\n\nContact: {contact}\n"
                      "Donatie: {donatie}",
    },
    "en": {
        "ondertitel": "Pack and unpack files - zip, 7z, tar, iso (and extract rar)",
        "menu_bestand": "File", "menu_help": "Help", "instellingen": "Settings",
        "afsluiten": "Quit", "snelgids": "Quick guide", "over": "About DravePack",
        "donatie": "Donate", "sluiten": "Close", "opslaan": "Save",
        "annuleren": "Cancel", "bladeren": "Browse...",
        "tab_in": "Pack", "tab_uit": "Unpack",
        "tab_welkom": "Welcome",
        "welkom_intro": "Pack and unpack files - zip, 7z, tar and iso, and extract rar. "
                        "Merge multiple files and folders into one archive, with a "
                        "password if you like. Everything local and offline.",
        "welkom_in": "Pack files", "welkom_uit": "Unpack archive",
        "welkom_toon": "Show this welcome screen at startup",
        "bronnen": "Files and folders to add:",
        "best_toevoegen": "Add files...", "map_toevoegen": "Add folder...",
        "verwijderen": "Remove", "wissen": "Clear list",
        "formaat": "Format", "wachtwoord": "Password (zip/7z only)",
        "tonen": "Show", "niveau": "Compression (0-9, zip only)",
        "doel": "Save as", "inpakken": "Pack", "bezig_in": "Packing...",
        "klaar_in": "Done: {pad}", "geen_bronnen": "Add files or folders first.",
        "geen_doel": "Choose where to save the archive (Save as) first.",
        "archief": "Archive", "open_archief": "Open archive...",
        "inhoud": "Contents (select for 'unpack selection'):",
        "doelmap": "Unpack to", "uit_alles": "Unpack all",
        "uit_selectie": "Unpack selection", "bezig_uit": "Unpacking...",
        "klaar_uit": "Done in: {map}", "geen_archief": "Open an archive first.",
        "geen_doelmap": "Choose a folder to unpack to first.",
        "lezen_mislukt": "Could not read the archive. Is the password correct? ({fout})",
        "ww_enter": "password + Enter",
        "ww_nodig": "This archive has a password. Enter it and press Enter.",
        "ww_fout": "Reading failed - is the password correct? ({fout})",
        "ww_uitpak_fout": "Unpacking failed: the password is missing or incorrect.",
        "fout_log": "Details are in DravePack-data\\fout-log.txt.",
        "items_n": "{n} files, {grootte} total",
        "fout": "Something went wrong: {fout}",
        "mist_7z": "7z support is not installed. Run run.bat again, or choose another "
                   "format (zip always works).",
        "mist_rar": "Extracting rar needs 7-Zip or WinRAR (or UnRAR) on the pc. Install "
                    "one of those and try again.",
        "inst_taal": "Language", "inst_taal_auto": "Automatic (system language)",
        "herstart_taal": "Restart the app to fully apply the language.",
        "ctx_kop": "Windows right-click menu",
        "ctx_note": "Add 'Extract with DravePack' (on archives) and 'Pack with "
                    "DravePack' (on folders) to the right-click menu. On Windows 11 it "
                    "appears under 'Show more options'.",
        "ctx_zet": "Add to right-click menu", "ctx_haal": "Remove from right-click menu",
        "ctx_gezet": "Added to the right-click menu.",
        "ctx_gehaald": "Removed from the right-click menu.",
        "over_tekst": "DravePack v{versie}\n\nPack and unpack files (zip, 7z, tar, iso; "
                      "extract rar). Local and offline.\n\nContact: {contact}\n"
                      "Donate: {donatie}",
    },
}
_TAAL = "nl"


def T(s):
    return TEKST.get(_TAAL, TEKST["nl"]).get(s, s)


# ---------------------------------------------------------------------------
# Werk-threads
# ---------------------------------------------------------------------------
class MaakThread(QThread):
    voortgang = pyqtSignal(int, int)
    klaar = pyqtSignal(bool, str)

    def __init__(self, formaat, doel, bronnen, wachtwoord, niveau):
        super().__init__()
        self.formaat = formaat; self.doel = doel; self.bronnen = bronnen
        self.wachtwoord = wachtwoord; self.niveau = niveau

    def run(self):
        try:
            archief.maak_archief(self.formaat, self.doel, self.bronnen,
                                 wachtwoord=self.wachtwoord, niveau=self.niveau,
                                 voortgang=lambda a, b: self.voortgang.emit(a, b))
            self.klaar.emit(True, self.doel)
        except ImportError:
            self.klaar.emit(False, "MIST_7Z")
        except Exception as e:
            log_fout("inpakken", self.doel, e)
            self.klaar.emit(False, str(e))


class UitpakThread(QThread):
    voortgang = pyqtSignal(int, int)
    klaar = pyqtSignal(bool, str)

    def __init__(self, pad, doelmap, wachtwoord, alleen):
        super().__init__()
        self.pad = pad; self.doelmap = doelmap
        self.wachtwoord = wachtwoord; self.alleen = alleen

    def run(self):
        try:
            archief.pak_uit(self.pad, self.doelmap, wachtwoord=self.wachtwoord,
                            alleen=self.alleen,
                            voortgang=lambda a, b: self.voortgang.emit(a, b))
            self.klaar.emit(True, self.doelmap)
        except ImportError:
            fmt = archief.detecteer_formaat(self.pad)
            self.klaar.emit(False, "MIST_RAR" if fmt == "rar" else "MIST_7Z")
        except Exception as e:
            log_fout("uitpakken", self.pad, e)
            self.klaar.emit(False, str(e))


# ---------------------------------------------------------------------------
class InstellingenDialoog(QDialog):
    def __init__(self, ouder, cfg):
        super().__init__(ouder)
        self.cfg = cfg
        self.setWindowTitle(T("instellingen")); self.setWindowIcon(app_icoon())
        self.resize(560, 320); self.setStyleSheet(STIJL())
        lay = QVBoxLayout(self); form = QFormLayout()
        self.taal = QComboBox()
        self.taal.addItem(T("inst_taal_auto"), "auto")
        self.taal.addItem("Nederlands", "nl"); self.taal.addItem("English", "en")
        self.taal.setCurrentIndex(max(0, self.taal.findData(cfg.get("taal", "auto"))))
        form.addRow(T("inst_taal"), self.taal)
        lay.addLayout(form)

        if os.name == "nt":
            from PyQt6.QtWidgets import QFrame
            lijn = QFrame(); lijn.setFrameShape(QFrame.Shape.HLine)
            lijn.setStyleSheet("color:%s;" % LINE); lay.addWidget(lijn)
            kop = QLabel(T("ctx_kop")); kop.setStyleSheet("font-weight:bold;")
            lay.addWidget(kop)
            note = QLabel(T("ctx_note")); note.setObjectName("sub"); note.setWordWrap(True)
            lay.addWidget(note)
            crij = QHBoxLayout()
            bzet = QPushButton(T("ctx_zet")); bzet.clicked.connect(self._ctx_zet)
            bhaal = QPushButton(T("ctx_haal")); bhaal.clicked.connect(self._ctx_haal)
            crij.addWidget(bzet); crij.addWidget(bhaal); crij.addStretch(1)
            lay.addLayout(crij)

        lay.addStretch(1)
        knr = QHBoxLayout(); knr.addStretch(1)
        ann = QPushButton(T("annuleren")); ann.clicked.connect(self.reject); knr.addWidget(ann)
        ok = QPushButton(T("opslaan")); ok.setObjectName("primair")
        ok.clicked.connect(self._ok); knr.addWidget(ok)
        lay.addLayout(knr)
        QTimer.singleShot(0, lambda: centreer(self, ouder))

    def _ctx_zet(self):
        ok, fout = registreer_contextmenu()
        if ok:
            QMessageBox.information(self, APP_NAAM, T("ctx_gezet"))
        else:
            QMessageBox.warning(self, APP_NAAM, T("fout").format(fout=fout))

    def _ctx_haal(self):
        ok, fout = verwijder_contextmenu()
        if ok:
            QMessageBox.information(self, APP_NAAM, T("ctx_gehaald"))
        else:
            QMessageBox.warning(self, APP_NAAM, T("fout").format(fout=fout))

    def _ok(self):
        self.cfg["taal"] = self.taal.currentData()
        self.accept()


SNELGIDS_NL = """
<h2>DravePack - Snelgids</h2>
<p>In- en uitpakken van archieven. Volledig lokaal en offline.</p>
<h3>Inpakken</h3>
<p>Voeg <b>bestanden</b> en/of <b>mappen</b> toe (meerdere bronnen worden samengevoegd
in een archief). Kies een <b>formaat</b> (zip, 7z, tar, tar.gz, tar.bz2, tar.xz of iso).
Voor <b>zip</b> en <b>7z</b> kun je een <b>wachtwoord</b> instellen. Kies <b>Opslaan
als</b> en klik <b>Inpakken</b>.</p>
<h3>Uitpakken</h3>
<p><b>Open</b> een archief (zip, 7z, tar*, iso of rar). Je ziet de inhoud; kies een
<b>map</b> en klik <b>Alles uitpakken</b>, of selecteer bestanden en klik <b>Selectie
uitpakken</b>. Heeft het een wachtwoord, vul dat dan eerst in (typ het en druk op <b>Enter</b> om de inhoud te tonen). Let op: een <b>versleuteld</b> archief open je in DravePack, 7-Zip of WinRAR - de Windows-verkenner kan versleutelde zip/7z niet openen.</p>
<h3>Rechtsklikmenu (Windows)</h3>
<p>Via <b>Bestand &rarr; Instellingen</b> kun je DravePack in het Windows-rechtsklikmenu zetten. Rechtsklik daarna op een <b>archief</b> voor <b>Uitpakken met DravePack</b>, of op een <b>map</b> voor <b>Inpakken met DravePack</b>. Op Windows&nbsp;11 staat dit onder <b>"Meer opties weergeven"</b>.</p>
<p>Let op: <b>rar maken</b> kan niet (gesloten formaat); rar <b>uitpakken</b> kan als er
7-Zip/WinRAR/UnRAR op de pc staat. Donatie (vrijwillig): <b>paypal.me/roger076</b>
&middot; service@dravenlock.nl</p>
"""
SNELGIDS_EN = """
<h2>DravePack - Quick guide</h2>
<p>Pack and unpack archives. Fully local and offline.</p>
<h3>Pack</h3>
<p>Add <b>files</b> and/or <b>folders</b> (multiple sources are merged into one archive).
Pick a <b>format</b> (zip, 7z, tar, tar.gz, tar.bz2, tar.xz or iso). For <b>zip</b> and
<b>7z</b> you can set a <b>password</b>. Choose <b>Save as</b> and click <b>Pack</b>.</p>
<h3>Unpack</h3>
<p><b>Open</b> an archive (zip, 7z, tar*, iso or rar). You'll see the contents; choose a
<b>folder</b> and click <b>Unpack all</b>, or select files and click <b>Unpack
selection</b>. If it has a password, fill it in first (type it and press <b>Enter</b> to show the contents). Note: open an <b>encrypted</b> archive in DravePack, 7-Zip or WinRAR - Windows Explorer cannot open encrypted zip/7z.</p>
<h3>Right-click menu (Windows)</h3>
<p>Via <b>File &rarr; Settings</b> you can add DravePack to the Windows right-click menu. Then right-click an <b>archive</b> for <b>Extract with DravePack</b>, or a <b>folder</b> for <b>Pack with DravePack</b>. On Windows&nbsp;11 it appears under <b>"Show more options"</b>.</p>
<p>Note: <b>creating rar</b> is not possible (closed format); <b>extracting</b> rar works
if 7-Zip/WinRAR/UnRAR is on the pc. Donate (voluntary): <b>paypal.me/roger076</b>
&middot; service@dravenlock.nl</p>
"""


class SnelgidsDialoog(QDialog):
    def __init__(self, ouder):
        super().__init__(ouder)
        self.setWindowTitle(T("snelgids")); self.setWindowIcon(app_icoon())
        self.resize(680, 560); self.setStyleSheet(STIJL())
        lay = QVBoxLayout(self)
        b = QTextBrowser(); b.setOpenExternalLinks(True)
        b.setHtml(SNELGIDS_NL if _TAAL == "nl" else SNELGIDS_EN)
        lay.addWidget(b)
        k = QPushButton(T("sluiten")); k.clicked.connect(self.accept); lay.addWidget(k)
        QTimer.singleShot(0, lambda: centreer(self, ouder))


# ---------------------------------------------------------------------------
class Hoofdvenster(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._maak = None
        self._uitpak = None
        self._archief_pad = ""
        self.setWindowTitle("%s  v%s" % (APP_NAAM, APP_VERSIE))
        self.setWindowIcon(app_icoon())
        self.resize(1060, 720); self.setStyleSheet(STIJL())
        self._menu()
        self._bouw()
        sb = QStatusBar(); self.setStatusBar(sb)
        self.btn_donatie = QPushButton(" \u2665 " + T("donatie"))
        self.btn_donatie.setObjectName("primair")
        self.btn_donatie.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(DONATIE_URL)))
        sb.addPermanentWidget(self.btn_donatie)

    def _menu(self):
        balk = self.menuBar()
        m = balk.addMenu(T("menu_bestand"))
        a = QAction(T("instellingen"), self); a.triggered.connect(self._instellingen); m.addAction(a)
        m.addSeparator()
        a = QAction(T("afsluiten"), self); a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close); m.addAction(a)
        h = balk.addMenu(T("menu_help"))
        a = QAction(T("snelgids"), self); a.setShortcut("F1")
        a.triggered.connect(lambda: SnelgidsDialoog(self).exec()); h.addAction(a)
        a = QAction(T("over"), self); a.triggered.connect(self._over); h.addAction(a)
        a = QAction(T("donatie"), self)
        a.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(DONATIE_URL))); h.addAction(a)

    def _bouw(self):
        centraal = QWidget(); self.setCentralWidget(centraal)
        lay = QVBoxLayout(centraal)
        kop = QLabel(APP_NAAM); kop.setObjectName("titel"); lay.addWidget(kop)
        sub = QLabel(T("ondertitel")); sub.setObjectName("sub"); lay.addWidget(sub)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_welkom(), T("tab_welkom"))   # 0
        self.tabs.addTab(self._tab_in(), T("tab_in"))           # 1
        self.tabs.addTab(self._tab_uit(), T("tab_uit"))         # 2
        lay.addWidget(self.tabs, 1)
        # Begin op het welkomscherm tenzij uitgezet
        self.tabs.setCurrentIndex(0 if self.cfg.get("toon_welkom", True) else 1)

    def _tab_welkom(self):
        w = QWidget(); buiten = QVBoxLayout(w)
        buiten.addStretch(1)
        midden = QVBoxLayout(); midden.setSpacing(14)
        midden.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        # logo
        logo = QLabel(); logo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        p = _bundel("logo.png")
        if os.path.isfile(p):
            pix = QPixmap(p)
            if not pix.isNull():
                logo.setPixmap(pix.scaledToHeight(
                    150, Qt.TransformationMode.SmoothTransformation))
        midden.addWidget(logo)
        titel = QLabel("%s  v%s" % (APP_NAAM, APP_VERSIE))
        titel.setObjectName("titel"); titel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        midden.addWidget(titel)
        intro = QLabel(T("welkom_intro")); intro.setObjectName("sub")
        intro.setWordWrap(True); intro.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        intro.setFixedWidth(620)  # hele zin zichtbaar (was afgekapt)
        midden.addWidget(intro, 0, Qt.AlignmentFlag.AlignHCenter)
        # twee grote knoppen
        knr = QHBoxLayout(); knr.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        bin_ = QPushButton(T("welkom_in")); bin_.setObjectName("primair")
        bin_.setMinimumWidth(230); bin_.setMinimumHeight(56)
        bin_.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        buit = QPushButton(T("welkom_uit")); buit.setObjectName("primair")
        buit.setMinimumWidth(230); buit.setMinimumHeight(56)
        buit.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        knr.addWidget(bin_); knr.addWidget(buit)
        midden.addLayout(knr)
        # snelgids-link
        gids = QPushButton(T("snelgids"))
        gids.clicked.connect(lambda: SnelgidsDialoog(self).exec())
        midden.addWidget(gids, 0, Qt.AlignmentFlag.AlignHCenter)
        # toon-bij-opstarten
        self.chk_welkom = QCheckBox(T("welkom_toon"))
        self.chk_welkom.setChecked(self.cfg.get("toon_welkom", True))
        self.chk_welkom.toggled.connect(self._welkom_toggle)
        midden.addWidget(self.chk_welkom, 0, Qt.AlignmentFlag.AlignHCenter)
        buiten.addLayout(midden)
        buiten.addStretch(1)
        return w

    def _welkom_toggle(self, aan):
        self.cfg["toon_welkom"] = bool(aan)
        bewaar_config(self.cfg)

    # ---- inpakken ----
    def _tab_in(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lay.addWidget(QLabel(T("bronnen")))
        self.bronnen = QListWidget()
        self.bronnen.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        lay.addWidget(self.bronnen, 1)
        rij = QHBoxLayout()
        b1 = QPushButton(T("best_toevoegen")); b1.clicked.connect(self._add_bestanden)
        b2 = QPushButton(T("map_toevoegen")); b2.clicked.connect(self._add_map)
        b3 = QPushButton(T("verwijderen")); b3.clicked.connect(self._verwijder_bron)
        b4 = QPushButton(T("wissen")); b4.clicked.connect(lambda: self.bronnen.clear())
        for b in (b1, b2, b3, b4):
            rij.addWidget(b)
        rij.addStretch(1)
        lay.addLayout(rij)

        opties = QHBoxLayout()
        opties.addWidget(QLabel(T("formaat")))
        self.formaat = QComboBox()
        for f in archief.MAAK_FORMATEN:
            self.formaat.addItem(f, f)
        self.formaat.currentTextChanged.connect(self._formaat_gewijzigd)
        opties.addWidget(self.formaat)
        opties.addWidget(QLabel(T("niveau")))
        self.niveau = QSpinBox(); self.niveau.setRange(0, 9); self.niveau.setValue(int(self.cfg.get("niveau", 5)))
        opties.addWidget(self.niveau)
        opties.addWidget(QLabel(T("wachtwoord")))
        self.ww_in = QLineEdit(); self.ww_in.setEchoMode(QLineEdit.EchoMode.Password)
        opties.addWidget(self.ww_in, 1)
        self.toon_in = QCheckBox(T("tonen"))
        self.toon_in.toggled.connect(lambda c: self.ww_in.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        opties.addWidget(self.toon_in)
        lay.addLayout(opties)

        drij = QHBoxLayout()
        drij.addWidget(QLabel(T("doel")))
        self.doel_in = QLineEdit(); drij.addWidget(self.doel_in, 1)
        bb = QPushButton(T("bladeren")); bb.clicked.connect(self._kies_doel)
        drij.addWidget(bb)
        self.knop_in = QPushButton(T("inpakken")); self.knop_in.setObjectName("primair")
        self.knop_in.clicked.connect(self._start_inpakken)
        drij.addWidget(self.knop_in)
        lay.addLayout(drij)

        self.balk_in = QProgressBar(); self.balk_in.setVisible(False)
        lay.addWidget(self.balk_in)
        self.status_in = QLabel(""); self.status_in.setObjectName("sub")
        lay.addWidget(self.status_in)
        return w

    def _add_bestanden(self):
        paden, _ = QFileDialog.getOpenFileNames(self, T("best_toevoegen"),
                                                self.cfg.get("laatste_map", BASIS))
        for p in paden:
            self._voeg_bron(p)

    def _add_map(self):
        p = QFileDialog.getExistingDirectory(self, T("map_toevoegen"),
                                             self.cfg.get("laatste_map", BASIS))
        if p:
            self._voeg_bron(p)

    def _voeg_bron(self, pad):
        for i in range(self.bronnen.count()):
            if self.bronnen.item(i).data(Qt.ItemDataRole.UserRole) == pad:
                return
        it = QListWidgetItem(("[map] " if os.path.isdir(pad) else "") + pad)
        it.setData(Qt.ItemDataRole.UserRole, pad)
        self.bronnen.addItem(it)
        self.cfg["laatste_map"] = os.path.dirname(pad)

    def _verwijder_bron(self):
        for it in self.bronnen.selectedItems():
            self.bronnen.takeItem(self.bronnen.row(it))

    def _formaat_gewijzigd(self, fmt):
        # wachtwoord alleen zinvol bij zip/7z; niveau alleen bij zip
        self.ww_in.setEnabled(fmt in ("zip", "7z"))
        self.niveau.setEnabled(fmt == "zip")
        # doel-extensie bijwerken
        pad = self.doel_in.text().strip()
        if pad:
            stam = pad
            for e in sorted(archief.EXT.values(), key=len, reverse=True):
                if stam.lower().endswith(e):
                    stam = stam[:-len(e)]; break
            self.doel_in.setText(stam + archief.EXT.get(fmt, ""))

    def _kies_doel(self):
        fmt = self.formaat.currentData()
        start = self.doel_in.text() or os.path.join(
            self.cfg.get("laatste_map", BASIS), "archief" + archief.EXT.get(fmt, ".zip"))
        p, _ = QFileDialog.getSaveFileName(self, T("doel"), start,
                                           "*" + archief.EXT.get(fmt, ""))
        if p:
            if not any(p.lower().endswith(e) for e in archief.EXT.values()):
                p += archief.EXT.get(fmt, "")
            self.doel_in.setText(p)

    def _start_inpakken(self):
        bronnen = [self.bronnen.item(i).data(Qt.ItemDataRole.UserRole)
                   for i in range(self.bronnen.count())]
        if not bronnen:
            QMessageBox.information(self, APP_NAAM, T("geen_bronnen")); return
        doel = self.doel_in.text().strip()
        if not doel:
            QMessageBox.information(self, APP_NAAM, T("geen_doel")); return
        self.cfg["niveau"] = self.niveau.value(); bewaar_config(self.cfg)
        self.knop_in.setEnabled(False); self.balk_in.setVisible(True)
        self.balk_in.setRange(0, 0); self.status_in.setText(T("bezig_in"))
        self._maak = MaakThread(self.formaat.currentData(), doel, bronnen,
                                self.ww_in.text(), self.niveau.value())
        self._maak.voortgang.connect(self._voortgang_in)
        self._maak.klaar.connect(self._klaar_in)
        self._maak.start()

    def _voortgang_in(self, a, b):
        self.balk_in.setRange(0, b); self.balk_in.setValue(a)

    def _klaar_in(self, ok, info):
        self.knop_in.setEnabled(True); self.balk_in.setVisible(False)
        if ok:
            self.status_in.setText(T("klaar_in").format(pad=info))
            self.status_in.setStyleSheet("color: %s;" % GOED)
            QMessageBox.information(self, APP_NAAM, T("klaar_in").format(pad=info))
        else:
            self.status_in.setStyleSheet("color: %s;" % WARN)
            if info == "MIST_7Z":
                self.status_in.setText(T("mist_7z"))
                QMessageBox.warning(self, APP_NAAM, T("mist_7z"))
            else:
                self.status_in.setText(T("fout").format(fout=info))
                QMessageBox.warning(self, APP_NAAM, T("fout").format(fout=info))

    # ---- uitpakken ----
    def _tab_uit(self):
        w = QWidget(); lay = QVBoxLayout(w)
        arij = QHBoxLayout()
        arij.addWidget(QLabel(T("archief")))
        self.arch_pad = QLineEdit(); self.arch_pad.setReadOnly(True); arij.addWidget(self.arch_pad, 1)
        bo = QPushButton(T("open_archief")); bo.setObjectName("primair")
        bo.clicked.connect(self._open_archief); arij.addWidget(bo)
        arij.addWidget(QLabel(T("wachtwoord")))
        self.ww_uit = QLineEdit(); self.ww_uit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ww_uit.setMaximumWidth(180)
        self.ww_uit.setPlaceholderText(T("ww_enter"))
        self.ww_uit.returnPressed.connect(self._herlees_inhoud)
        arij.addWidget(self.ww_uit)
        self.toon_uit = QCheckBox(T("tonen"))
        self.toon_uit.toggled.connect(lambda c: self.ww_uit.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        arij.addWidget(self.toon_uit)
        lay.addLayout(arij)

        lay.addWidget(QLabel(T("inhoud")))
        self.inhoud = QListWidget()
        self.inhoud.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        lay.addWidget(self.inhoud, 1)
        self.inhoud_info = QLabel(""); self.inhoud_info.setObjectName("sub")
        lay.addWidget(self.inhoud_info)

        drij = QHBoxLayout()
        drij.addWidget(QLabel(T("doelmap")))
        self.doelmap = QLineEdit(); drij.addWidget(self.doelmap, 1)
        bb = QPushButton(T("bladeren")); bb.clicked.connect(self._kies_doelmap)
        drij.addWidget(bb)
        self.knop_alles = QPushButton(T("uit_alles")); self.knop_alles.setObjectName("primair")
        self.knop_alles.clicked.connect(lambda: self._start_uitpakken(False))
        drij.addWidget(self.knop_alles)
        self.knop_sel = QPushButton(T("uit_selectie"))
        self.knop_sel.clicked.connect(lambda: self._start_uitpakken(True))
        drij.addWidget(self.knop_sel)
        lay.addLayout(drij)

        self.balk_uit = QProgressBar(); self.balk_uit.setVisible(False)
        lay.addWidget(self.balk_uit)
        self.status_uit = QLabel(""); self.status_uit.setObjectName("sub")
        lay.addWidget(self.status_uit)
        return w

    def _open_archief(self):
        p, _ = QFileDialog.getOpenFileName(
            self, T("open_archief"), self.cfg.get("laatste_map", BASIS),
            "Archieven (*.zip *.7z *.tar *.gz *.tgz *.bz2 *.xz *.iso *.rar);;Alle (*.*)")
        if not p:
            return
        self._archief_pad = p
        self.arch_pad.setText(p)
        self.cfg["laatste_map"] = os.path.dirname(p)
        if not self.doelmap.text().strip():
            self.doelmap.setText(os.path.splitext(p)[0] + "_uitgepakt")
        self._lees_inhoud()

    def _herlees_inhoud(self):
        if self._archief_pad:
            self._lees_inhoud()

    def _lees_inhoud(self):
        if not self._archief_pad:
            return
        self.inhoud.clear()
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            items = archief.lijst_inhoud(self._archief_pad, self.ww_uit.text())
        except ImportError:
            fmt = archief.detecteer_formaat(self._archief_pad)
            QMessageBox.warning(self, APP_NAAM, T("mist_rar") if fmt == "rar" else T("mist_7z"))
            return
        except Exception as e:
            # Waarschijnlijk een wachtwoord nodig: geen schrik-popup, maar een hint.
            self.inhoud_info.setStyleSheet("color: %s;" % WARN)
            if not self.ww_uit.text():
                self.inhoud_info.setText(T("ww_nodig"))
                self.ww_uit.setFocus()
            else:
                self.inhoud_info.setText(T("ww_fout").format(fout=e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        totaal = 0
        for naam, grootte in items:
            it = QListWidgetItem("%s   (%s)" % (naam, mooie_grootte(grootte)))
            it.setData(Qt.ItemDataRole.UserRole, naam)
            self.inhoud.addItem(it); totaal += grootte
        self.inhoud_info.setStyleSheet("color: %s;" % MUTED)
        self.inhoud_info.setText(T("items_n").format(n=len(items), grootte=mooie_grootte(totaal)))

    def _kies_doelmap(self):
        p = QFileDialog.getExistingDirectory(self, T("doelmap"),
                                             self.doelmap.text() or self.cfg.get("laatste_map", BASIS))
        if p:
            self.doelmap.setText(p)

    def _start_uitpakken(self, selectie):
        if not self._archief_pad:
            QMessageBox.information(self, APP_NAAM, T("geen_archief")); return
        doelmap = self.doelmap.text().strip()
        if not doelmap:
            QMessageBox.information(self, APP_NAAM, T("geen_doelmap")); return
        alleen = None
        if selectie:
            alleen = set(it.data(Qt.ItemDataRole.UserRole)
                         for it in self.inhoud.selectedItems())
            if not alleen:
                QMessageBox.information(self, APP_NAAM, T("geen_archief")); return
        self.knop_alles.setEnabled(False); self.knop_sel.setEnabled(False)
        self.balk_uit.setVisible(True); self.balk_uit.setRange(0, 0)
        self.status_uit.setText(T("bezig_uit"))
        self._uitpak = UitpakThread(self._archief_pad, doelmap, self.ww_uit.text(), alleen)
        self._uitpak.voortgang.connect(self._voortgang_uit)
        self._uitpak.klaar.connect(self._klaar_uit)
        self._uitpak.start()

    def _voortgang_uit(self, a, b):
        self.balk_uit.setRange(0, b); self.balk_uit.setValue(a)

    def _klaar_uit(self, ok, info):
        self.knop_alles.setEnabled(True); self.knop_sel.setEnabled(True)
        self.balk_uit.setVisible(False)
        if ok:
            self.status_uit.setText(T("klaar_uit").format(map=info))
            self.status_uit.setStyleSheet("color: %s;" % GOED)
            QMessageBox.information(self, APP_NAAM, T("klaar_uit").format(map=info))
        else:
            self.status_uit.setStyleSheet("color: %s;" % WARN)
            if info in ("MIST_7Z", "MIST_RAR"):
                tekst = T("mist_rar") if info == "MIST_RAR" else T("mist_7z")
                self.status_uit.setText(tekst); QMessageBox.warning(self, APP_NAAM, tekst)
            else:
                low = info.lower()
                ww_woorden = ("password", "wachtwoord", "encrypted", "passwordrequired",
                              "bad pass")
                corrupt_woorden = ("corrupt", "crc", "checksum", "data error")
                is_ww = (any(w in low for w in ww_woorden) or
                         (self.ww_uit.text() and any(w in low for w in corrupt_woorden)))
                if is_ww:
                    self.status_uit.setText(T("ww_uitpak_fout"))
                    QMessageBox.warning(self, APP_NAAM, T("ww_uitpak_fout") + "\n\n" + T("fout_log"))
                else:
                    self.status_uit.setText(T("fout").format(fout=info))
                    QMessageBox.warning(self, APP_NAAM,
                                        T("fout").format(fout=info) + "\n\n" + T("fout_log"))

    # ---- menu ----
    def _instellingen(self):
        global _TAAL
        d = InstellingenDialoog(self, self.cfg)
        if d.exec():
            bewaar_config(self.cfg)
            nieuw = self.cfg.get("taal", "auto")
            _TAAL = taal_detecteren() if nieuw == "auto" else nieuw
            QMessageBox.information(self, APP_NAAM, T("herstart_taal"))

    def _over(self):
        QMessageBox.information(self, T("over"), T("over_tekst").format(
            versie=APP_VERSIE, contact=CONTACT, donatie=DONATIE_URL))

    def laad_opdracht(self, modus, pad):
        """Wordt aangeroepen als de app via het rechtsklikmenu (of de opdrachtregel)
        met een pad is gestart: open dat in de juiste tab."""
        try:
            pad = os.path.abspath(pad)
        except Exception:
            return
        if modus is None:
            fmt = archief.detecteer_formaat(pad)
            modus = "uitpakken" if (fmt and os.path.isfile(pad)) else "inpakken"
        if modus == "uitpakken" and os.path.isfile(pad):
            self.tabs.setCurrentIndex(2)
            self._archief_pad = pad
            self.arch_pad.setText(pad)
            self.cfg["laatste_map"] = os.path.dirname(pad)
            if not self.doelmap.text().strip():
                self.doelmap.setText(os.path.splitext(pad)[0] + "_uitgepakt")
            self._lees_inhoud()
        else:
            self.tabs.setCurrentIndex(1)
            self._voeg_bron(pad)


def main():
    global _TAAL
    zorg_voor_mappen()
    cfg = laad_config()
    taal = cfg.get("taal", "auto")
    _TAAL = taal_detecteren() if taal == "auto" else (taal if taal in ("nl", "en")
                                                      else taal_detecteren())
    argv = sys.argv[1:]
    # Stille register-acties (voor installer of de opdrachtregel)
    if "--register" in argv:
        ok, fout = registreer_contextmenu()
        print("DravePack: rechtsklikmenu toegevoegd" if ok else "fout: " + fout)
        return
    if "--unregister" in argv:
        ok, fout = verwijder_contextmenu()
        print("DravePack: rechtsklikmenu verwijderd" if ok else "fout: " + fout)
        return
    # Optioneel pad + modus (vanuit het rechtsklikmenu)
    modus = None
    doelpad = None
    for a in argv:
        if a == "--inpakken":
            modus = "inpakken"
        elif a == "--uitpakken":
            modus = "uitpakken"
        elif not a.startswith("-"):
            doelpad = a
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dravenlock.DravePack")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAAM)
    app.setWindowIcon(app_icoon())
    app.setStyleSheet(STIJL())
    venster = Hoofdvenster(cfg)
    venster.showMaximized()
    if doelpad:
        QTimer.singleShot(0, lambda: venster.laad_opdracht(modus, doelpad))
    try:  # Dravenlock: stille update-check (uit te zetten; Ctrl+Shift+U = met de hand)
        import drave_update
        drave_update.start(venster, 'DravePack', APP_VERSIE)
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
