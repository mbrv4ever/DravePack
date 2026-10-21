DravePack - bestanden in- en uitpakken
======================================

Dravenlock - lokaal en offline.

STARTEN
-------
Dubbelklik run.bat. De eerste keer installeert die zichzelf (Python 3.10 t/m
3.13 nodig). Werkt iets niet, gebruik start-debug.bat: die toont de fouten.

INPAKKEN
--------
Voeg bestanden en/of mappen toe (meerdere bronnen worden samengevoegd in een
archief). Kies een formaat: zip, 7z, tar, tar.gz, tar.bz2, tar.xz of iso. Voor
zip en 7z kun je een wachtwoord instellen. Kies "Opslaan als" en klik Inpakken.

UITPAKKEN
---------
Open een archief (zip, 7z, tar*, iso of rar). Je ziet de inhoud. Kies een map en
klik "Alles uitpakken", of selecteer bestanden en klik "Selectie uitpakken".
Heeft het archief een wachtwoord, vul dat dan eerst in.

OVER RAR
--------
Een rar-archief MAKEN kan geen enkele app (gesloten formaat). UITPAKKEN kan wel,
maar daarvoor moet er 7-Zip, WinRAR of UnRAR op de pc staan; die vindt DravePack
dan vanzelf.

OVER 7Z
-------
7z-ondersteuning komt via een los pakket dat run.bat probeert te installeren.
Lukt dat niet, dan werkt de app gewoon door voor zip/tar/iso; kies dan een ander
formaat.

RECHTSKLIKMENU (WINDOWS)
------------------------
Ga naar Bestand > Instellingen en klik "In rechtsklikmenu zetten". Daarna kun
je in Verkenner rechtsklikken op een archief ("Uitpakken met DravePack") of op
een map ("Inpakken met DravePack"); de app opent dan met dat item erin. Op
Windows 11 staat het onder "Meer opties weergeven". Tip: zet het pas in het
menu vanuit de uiteindelijke .exe (of vaste maplocatie); het menu verwijst naar
waar DravePack dan staat. Geen beheerdersrechten nodig (per gebruiker).

WAAR STAAN MIJN INSTELLINGEN
----------------------------
In de map DravePack-data naast de app.

LOSSE .EXE MAKEN (optioneel)
----------------------------
Dubbelklik bouw-exe.bat. De .exe komt in de map dist (onefile).

SNELGIDS: druk op F1.
DONATIE (vrijwillig): https://paypal.me/roger076
CONTACT: service@dravenlock.nl
