# Halloween Skin for QGIS 🎃

[![Tests](https://github.com/envirosolutionspl/qgis-halloween/actions/workflows/tests.yml/badge.svg)](https://github.com/envirosolutionspl/qgis-halloween/actions/workflows/tests.yml)
[![Qt5 and Qt6 compatibility](https://github.com/envirosolutionspl/qgis-halloween/actions/workflows/qt5-qt6-compat.yml/badge.svg)](https://github.com/envirosolutionspl/qgis-halloween/actions/workflows/qt5-qt6-compat.yml)
[![Security and quality](https://github.com/envirosolutionspl/qgis-halloween/actions/workflows/security_and_quality.yml/badge.svg)](https://github.com/envirosolutionspl/qgis-halloween/actions/workflows/security_and_quality.yml)
[![Release](https://img.shields.io/github/v/release/envirosolutionspl/qgis-halloween)](https://github.com/envirosolutionspl/qgis-halloween/releases/latest)

> **The first plugin that brings an animated skin to QGIS**, from QGIS 3.40 up to
> QGIS 4.x: bats flap, ghosts float and pumpkins glow on the QGIS menu bar.

**Halloween Skin gives the standard QGIS interface a Halloween look**: pumpkin
orange, violet and a dark menu bar decorated with animated pumpkins, bats and ghosts.
It is the Halloween skin of EnviroSolutions' MAIP application, brought to QGIS. The
layout of QGIS is not changed, and the skin is switched off with one click.

[Polska wersja poniżej](#halloween-skin-dla-qgis-)

## Features

- Two themes: *Halloween Light* (white and pale violet surfaces) and
  *Halloween Dark* (deep violet surfaces), both with a pumpkin-orange accent.
- Dark menu bar decorated with pumpkins, bats and ghosts, animated as in MAIP.
  Three animation modes: *Flying across the menu bar* (default: bats and ghosts fly
  on wavy courses while the pumpkins stay at the right), *In place, as in MAIP*
  (bats flap their wings, ghosts float, pumpkins pulse and their faces flicker)
  and *Off*.
- The [Nosifer](https://fonts.google.com/specimen/Nosifer) face on the menu bar,
  pane titles and welcome-page headings.
- A spider web over the icons of EnviroSolutions plugins on hover.
- Halloween cursors for the map tools and a spider easter egg (details below).
- Arrows, check boxes, radio buttons and tree branches drawn for each theme.
- Works alongside [ArcSkin](https://github.com/envirosolutionspl/arcskin): the
  Halloween colours go on top of the ribbon, the pumpkins, bats and ghosts move to
  the ribbon's title row and the easter egg also answers in ArcSkin's coordinate box.
- English interface, Polish translation.

## Halloween cursors

The map tools get Halloween cursors. Their icons on the toolbars stay as they are;
only the cursor over the map changes:

| Tool            | Cursor         |
| --------------- | -------------- |
| Pan             | white ghost    |
| Select Features | witch's broom  |
| Zoom In         | large pumpkin  |
| Zoom Out        | small pumpkin  |
| Identify        | bat            |

A tool gets its cursor when you choose it and keeps it for the rest of the session.
When the skin is switched off, every tool gets the standard QGIS cursor back.

## Easter egg 🕷️

Type `halloween` into the coordinate box on the status bar (at the bottom of the
QGIS window) and press Enter. Four black spiders come down from the top of the map
view on their threads, each at its own speed. They hang for a while, swaying and
moving their legs, then climb back up and disappear.

The spiders do not get in the way: you can pan the map and click on it as usual the
whole time. The easter egg answers to the word `halloween` only; anything else
typed into the coordinate box works as normal in QGIS.

## Requirements

- QGIS 3.40 or newer (Qt 5)
- QGIS 4.x (Qt 6)

## Installation

1. Download `halloween_skin-<version>.zip` from the
   [releases](https://github.com/envirosolutionspl/qgis-halloween/releases)
   (or build it, see [Development](#development)).
2. In QGIS open *Plugins → Manage and Install Plugins… → Install from ZIP*,
   choose the file and click *Install Plugin*.

The skin is applied as soon as the plugin is installed. Before installing a newer
version, uninstall the old one first: QGIS keeps the loaded modules in memory.

## Turning the skin on and off

| What you want                    | How                                                                              |
| -------------------------------- | -------------------------------------------------------------------------------- |
| Switch the skin off or on        | **Plugins → Halloween Skin → Halloween look**                                    |
| Choose the light or dark variant | **Plugins → Halloween Skin → Theme**                                             |
| Change or stop the animation     | **Plugins → Halloween Skin → Animation**                                         |
| Keep plain QGIS after restarting | **Plugins → Manage and Install Plugins… → Installed**, untick **Halloween Skin** |
| Remove the plugin                | Same dialog, select **Halloween Skin**, **Uninstall Plugin**                     |

The on/off switch, the theme and the animation setting are remembered.
Switching the skin off puts back the style sheet and palette QGIS had before.
Nothing is written into the QGIS profile and your projects are not changed.

## How it works

- **Style sheet and palette.** Each theme in `halloween_skin/themes/<name>/` has a
  Qt style sheet (`style.qss`, colours written out in full, `@theme_path` standing
  for the theme folder) and a palette (`palette.txt`, lines
  `<QPalette::ColorRole number>:<colour>`). The palette is needed because the style
  sheet does not reach every QGIS dialog. The style sheet is appended to the
  application's as a marked block, so the rules of another plugin that styles QGIS
  (ArcSkin) stay; switching off removes that block only and puts the palette back.
  If another plugin replaces the whole sheet, the `StyleChange` event on the main
  window brings the block back (or removes a stale copy while the skin is off).
- **Menu-bar decoration** (`animation.py`). Qt does not run CSS or SMIL animations
  in SVG, so the MAIP drawings are painted with `QPainter` on a transparent overlay
  that lets the mouse through, refreshed 25 times a second. While ArcSkin hides the
  menu bar, the overlay sits on the ribbon's title row.
- **Cursors** (`cursors.py`). The map tools are recognised through their actions
  when they become the canvas's current tool (`QgsMapCanvas.mapToolSet`).
- **Spider web** (`icons.py`). Tool buttons of plugins whose metadata names
  EnviroSolutions as the author get an event filter that swaps the icon on hover.
- **Easter egg** (`spiders.py`). An event filter on the status bar's coordinate box
  (and on ArcSkin's, when present) catches the word `halloween` followed by Enter
  and runs the spiders on an overlay over the map canvas.
- **ArcSkin** (`arcskin.py`). The object names of ArcSkin's title row and coordinate
  box; nothing from ArcSkin is imported.

Every part has a `remove()` method and is taken off when the skin is switched off
or the plugin is unloaded.

## Development

```
halloween_skin/          the plugin (what goes into the ZIP)
  plugin.py              menu, switching on and off, themes, font
  animation.py           menu-bar decoration and animation modes
  cursors.py             map tool cursors
  icons.py               spider web over EnviroSolutions plugin icons
  spiders.py             spider easter egg
  themes/                Halloween Light and Halloween Dark
  fonts/                 Nosifer (SIL Open Font License 1.1)
  icons/                 plugin icon, cursor pictures, spider web
scripts/
  package.py             builds dist/halloween_skin-<version>.zip
  build_icons.py         generates icons/tool_*.svg and icons/web.svg
  build_stars.py         generates themes/*/stars.svg
tests/                   offscreen tests with a stand-in qgis package
```

The tests run without QGIS, on PyQt5 or PyQt6:

```bash
pip install PyQt5 flake8 flake8-docstrings pep8-naming
flake8
sh tests/run_all.sh
python scripts/package.py
```

The same checks run on GitHub for every push and pull request: the tests in
the `qgis/qgis` Docker images (3.40, LTR, stable and latest), the
[pyqgis4-checker](https://github.com/qgis/pyqgis4-checker) for Qt 5 / Qt 6
compatibility, and flake8, Bandit and detect-secrets. Pushing a tag `v<version>`
that matches `metadata.txt` builds the ZIP and publishes a GitHub release.

The tests write previews of the menu bar, the spider web and the spiders to
`tests/out/`. They do not replace a check in QGIS itself: install the ZIP in
QGIS 3.40 and in QGIS 4.x after every larger change (Python errors show in
*View → Panels → Log Messages*).

The SVG pictures use only the part of SVG Tiny that Qt renders (no masks, filters,
CSS or animation). Generated pictures are changed in the scripts, not by hand; the
tests check that the files match the scripts.

To release a new version, raise `version` in `halloween_skin/metadata.txt`, add an
entry at the top of `changelog`, update this README and push the tag `v<version>`.

## Licence

Halloween Skin is licensed under the GPL-2.0-or-later, see [LICENSE](LICENSE).
The Nosifer font is licensed under the SIL Open Font License 1.1, see
[OFL-Nosifer.txt](halloween_skin/fonts/OFL-Nosifer.txt).
Made by [EnviroSolutions](https://github.com/envirosolutionspl).

---

# Halloween Skin dla QGIS 🎃

> **Pierwsza wtyczka, która wprowadza do QGIS animowaną skórkę**, od QGIS 3.40 po
> QGIS 4.x: na pasku menu QGIS trzepoczą nietoperze, unoszą się duszki i świecą dynie.

**Halloween Skin nadaje standardowemu interfejsowi QGIS wygląd Halloween**:
dyniowy pomarańcz, fiolet i ciemny pasek menu z animowanymi dyniami, nietoperzami
i duszkami. To skórka Halloween aplikacji MAIP firmy EnviroSolutions przeniesiona
do QGIS. Układ okna QGIS się nie zmienia, a skórkę wyłącza się jednym kliknięciem.

## Funkcje

- Dwa motywy: *Halloween – jasny* (białe i bladofioletowe powierzchnie) oraz
  *Halloween – ciemny* (głęboki fiolet), oba z dyniowym akcentem.
- Ciemny pasek menu z dyniami, nietoperzami i duszkami animowanymi jak w MAIP.
  Trzy tryby animacji: *Przelot przez pasek menu* (domyślny: nietoperze i duszki
  przelatują falistym torem, dynie zostają po prawej), *W miejscu, jak w MAIP*
  (nietoperze machają skrzydłami, duszki się unoszą, dynie pulsują i migoczą)
  oraz *Wyłączona*.
- Krój [Nosifer](https://fonts.google.com/specimen/Nosifer) na pasku menu,
  w tytułach paneli i nagłówkach strony powitalnej.
- Pajęczyna nad ikonami wtyczek EnviroSolutions po najechaniu myszą.
- Współpraca z wtyczką [ArcSkin](https://github.com/envirosolutionspl/arcskin):
  kolory Halloween nakładają się na wstążkę, dynie, nietoperze i duszki przenoszą
  się na jej wiersz tytułowy, a niespodzianka działa także w polu współrzędnych
  ArcSkin.
- Halloweenowe kursory narzędzi mapy i ukryta niespodzianka z pająkami.
- Strzałki, pola wyboru, przełączniki i gałęzie drzew rysowane dla każdego motywu.
- Interfejs angielski i polski.

## Kursory

Ikony narzędzi na paskach zostają bez zmian; zmienia się tylko kursor nad mapą:

| Narzędzie             | Kursor       |
| --------------------- | ------------ |
| Przesuń widok         | biały duszek |
| Zaznacz obiekty       | miotła       |
| Powiększ              | duża dynia   |
| Pomniejsz             | mała dynia   |
| Informacje o obiekcie | nietoperz    |

Po wyłączeniu skórki wszystkie narzędzia wracają do standardowych kursorów QGIS.

## Niespodzianka 🕷️

Wpisz `halloween` w pole współrzędnych na pasku stanu (na dole okna QGIS)
i naciśnij Enter. Z góry widoku mapy na nitkach zjadą cztery czarne pająki,
pokołyszą się chwilę i wspinają z powrotem. Mapa przez cały czas działa normalnie.
Inny tekst wpisany w pole współrzędnych działa w QGIS jak zwykle.

## Wymagania i instalacja

QGIS 3.40 lub nowszy (Qt 5) albo QGIS 4.x (Qt 6).

1. Pobierz `halloween_skin-<wersja>.zip` z
   [wydań](https://github.com/envirosolutionspl/qgis-halloween/releases).
2. W QGIS wybierz *Wtyczki → Zarządzaj wtyczkami… → Zainstaluj z pliku ZIP*,
   wskaż plik i kliknij *Zainstaluj wtyczkę*.

Skórka włącza się od razu po instalacji. Przed instalacją nowszej wersji
odinstaluj starą – QGIS trzyma załadowane moduły w pamięci.

## Włączanie i wyłączanie

| Co chcesz zrobić                  | Jak                                                                      |
| --------------------------------- | ------------------------------------------------------------------------ |
| Wyłączyć lub włączyć skórkę       | **Wtyczki → Halloween Skin → Wygląd Halloween**                          |
| Wybrać wariant jasny lub ciemny   | **Wtyczki → Halloween Skin → Motyw**                                     |
| Zmienić lub zatrzymać animację    | **Wtyczki → Halloween Skin → Animacja**                                  |
| Zwykły QGIS po ponownym starcie   | **Wtyczki → Zarządzaj wtyczkami… → Zainstalowane**, odznacz wtyczkę      |
| Usunąć wtyczkę                    | To samo okno, zaznacz **Halloween Skin**, **Odinstaluj wtyczkę**         |

Ustawienia są zapamiętywane. Wyłączenie skórki zdejmuje tylko jej część arkusza
stylów i przywraca paletę QGIS; style innych wtyczek (np. ArcSkin) zostają. Nic nie
jest zapisywane w profilu QGIS, a projekty się nie zmieniają.

## Licencja

GPL-2.0-or-later, zob. [LICENSE](LICENSE). Krój Nosifer: SIL Open Font
License 1.1. Autor: [EnviroSolutions](https://github.com/envirosolutionspl).
