# livery — Design

**Datum:** 2026-06-12
**Status:** Ontwerp goedgekeurd, klaar voor implementatieplan

## Doel

Een lichte "schil" rond iTerm2 die elke tab automatisch een eigen look geeft op
basis van het project waarin je staat. Bij het wisselen van map (`cd`) zoekt de
tool de favicon van het project op en gebruikt die voor:

1. **Tab-icoon** — de PNG-favicon verschijnt als icoon in de tabbalk.
2. **Gemute kleur-tint** — de dominante kleur van die favicon, subtiel
   ingeblend met het systeem-thema, kleurt de tab én de terminal-achtergrond.

Het effect: je tabs vertellen je voortdurend in welk project je zit, in de
herkenbare merkkleur, zonder schreeuwerig te zijn.

## Scope & non-doelen

- **Alleen iTerm2.** Apple Terminal.app en andere terminals worden gedetecteerd
  en overgeslagen (geen escape-rommel).
- **Geen SVG-rasterisatie.** De bron is een `site.webmanifest` die al naar
  PNG's verwijst; we gebruiken die PNG direct.
- **Geen daemon / Python-API.** Bewust gekozen voor de lichtste vorm: een
  zsh-hook + een Python-helper die wordt aangeroepen en weer afsluit.
- Geen ondersteuning voor meerdere favicons per project, geen GUI. Gedrag wordt
  gestuurd via env-vars; de per-map-keuzes leven in een centrale store (zie
  "Per-map store").

## Achtergrond: wat iTerm2 wel/niet kan (geverifieerd)

- Een willekeurig plaatje als tab-icoon kan **niet** via een escape-code (noch
  SVG noch PNG), en ook **niet** via de Python-API.
- Een custom icoon kan **wel** per *profiel* worden ingesteld; dat icoon
  verschijnt in de tabbalk en de venstertitel.
- Profielen kunnen runtime gewisseld worden via de `SetProfile`-escape-code.
- iTerm2 leest **Dynamic Profiles** automatisch in vanuit
  `~/Library/Application Support/iTerm2/DynamicProfiles/` (JSON).
- Tab-kleur kan ook via escape-code: `OSC 6 ; 1 ; bg ; <kanaal> ; brightness ; N ST`.

Daarom de **profiel-route**: per project genereren we een Dynamic Profile met de
favicon als custom icoon plus de gemute kleuren, en we switchen ernaartoe.

Bronnen:
- https://iterm2.com/documentation-dynamic-profiles.html
- https://iterm2.com/documentation-escape-codes.html
- https://iterm2.com/documentation-session-title.html

## Architectuur

Twee lagen:

### 1. zsh-laag (`livery.zsh`)
Een dun bestand dat vanuit `~/.zshrc` wordt ge-`source`d. Het:
- registreert een `chpwd`-hook (draait bij elke `cd`);
- draait één keer bij shell-startup (op de startmap);
- roept de Python-helper aan en `eval`t de teruggegeven escape-sequences;
- **faalt altijd stil** — een fout in de helper mag de shell nooit vertragen of
  breken (helper-aanroep met timeout-bewustzijn, fouten naar /dev/null tenzij
  logging aanstaat).

### 2. Python-helper (`livery.py`)
Het testbare hart. Stdlib + de macOS-ingebouwde `sips`. Verantwoordelijk voor:
manifest zoeken, parsen, PNG→kleur, profiel schrijven, escape-sequences printen.

Aanroep-contract (zodat tests geïsoleerd draaien):
```
livery.py emit     --cwd <dir> --profiles-dir <dir> --store-dir <dir>
livery.py scan   --cwd <dir> --profiles-dir <dir> --store-dir <dir>
livery.py set-icon <pad> --cwd <dir> --profiles-dir <dir> --store-dir <dir>
livery.py rename   [custom] --cwd <dir> --profiles-dir <dir> --store-dir <dir>
livery.py clean    --profiles-dir <dir> --store-dir <dir>
```
- `emit` — leest de store voor de huidige project-root; bij een treffer emit het
  meteen (snel pad). Bij geen treffer: auto-detecteren, store vullen, emitten.
- `scan` — forceert opnieuw afleiden uit de `site.webmanifest` en overschrijft
  de store-entry voor deze root (behoudt de `rename`-suffix).
- `set-icon <pad>` — slaat een handmatig icoon-pad op in de store-entry
  (overschrijft auto-detectie); kleur wordt uit die PNG afgeleid.
- `rename [custom]` — zet een eigen achtervoegsel achter de afgeleide naam:
  titel wordt `<Naam> | <custom>`. Zonder argument wist het de suffix.
- `clean` — ruimt verweesde store-entries en profielen op.

`emit` print de escape-sequences naar stdout; de zsh-laag echoot die door naar de
tab. `--profiles-dir`/`--store-dir` defaulten naar de echte iTerm2/store-paden
maar zijn override-baar in tests.

## Data-flow per `cd` (emit)

1. **iTerm2-guard:** is `$TERM_PROGRAM` ongelijk aan `iTerm.app` (bv. SSH,
   Terminal.app)? → niets doen.
2. **Project-root bepalen:** vanaf `$PWD` omhoog lopen tot de eerste map met
   `.git` (of de filesystem-wortel als er geen `.git` is). Dit is zowel het
   zoekgebied als de store-sleutel — zo werkt het ook vanuit een submap zoals
   `src/`.
3. **Store-lookup:** is er een store-entry voor deze root
   (`~/.config/livery/dirs/<hash(root)>.json`)?
   - **Treffer (snelpad):** lees icoon-pad + ruwe dominante kleur uit de store,
     bereken de gemute tints voor het huidige thema (zie stap 7), zorg dat het
     profiel up-to-date is, en emit. **Geen manifest-scan, geen `sips`.**
   - **Geen treffer:** ga door naar auto-detectie (stappen 4–6), schrijf het
     resultaat naar de store, en emit. Dit gebeurt dus maar één keer per project.
4. **Auto-detectie — zoeken:** vanaf de root recursief omlaag zoeken naar
   `site.webmanifest` met een diepte-limiet (default 6) en pruning van
   `node_modules`, `.git`, `dist`, `build`, `vendor`. Eerste match wint.
5. **Manifest parsen:** JSON laden → `icons`-array → eerste entry met een
   `.png`-`src`. Het `src`-pad resolven t.o.v. de map van het manifest
   (web-absoluut `/foo.png` → manifest-map + `foo.png`).
6. **Kleur berekenen (dominant):**
   - `sips` schaalt de PNG naar 16×16 PNG.
   - Een mini pure-Python PNG-decoder (zlib is stdlib) leest de pixels.
   - Transparante pixels (alpha < drempel) en bijna-wit/bijna-zwart pixels
     worden weggefilterd.
   - De resterende pixels worden gequantiseerd (4 bits/kanaal), geteld; de
     meest voorkomende bucket wint → dominante kleur.
   - **Fallback:** als (bijna) alles weggefilterd is, val terug op het pure
     gemiddelde (sips 1×1).
7. **Gemute tint berekenen:**
   - Systeem-thema via `defaults read -g AppleInterfaceStyle`
     ("Dark" → bg = zwart; fout/afwezig → bg = wit).
   - `tint = kleur × sterkte + bg × (1 − sterkte)`.
   - Twee sterktes: tab (`LIVERY_TAB_STRENGTH`, default 0.15) en
     achtergrond (`LIVERY_BG_STRENGTH`, default 0.07).
8. **Store-entry schrijven** (alleen bij auto-detectie of `set-icon`/`scan`):
   sla in `dirs/<hash(root)>.json` op: `root`-pad, `icon_path`, ruwe
   `dominant_color` (RGB), en de bron (`manifest` of `manual`). De gemute tint
   wordt **niet** opgeslagen — die hangt van het thema af en wordt bij elke
   `emit` opnieuw berekend.
9. **Profiel genereren/updaten:** schrijf/overschrijf een Dynamic-Profile-JSON
   `livery/<hash(root)>.json` met:
   - stabiele `Guid` afgeleid van het root-pad (her-bezoek hergebruikt 't profiel);
   - `Name` (bv. `livery: <projectnaam>`);
   - `Custom Icon Path` → absoluut PNG-pad, `Icon` → custom-modus;
   - `Tab Color` + `Use Tab Color`, `Background Color` → de gemute tints
     (berekend voor het huidige thema).
   - `Dynamic Profile Parent Name: "Default"` zodat al het overige geërfd wordt.

   Om onnodige profiel-rewrites (en iTerm2-reloads) te vermijden: schrijf alleen
   als het profiel nog niet bestaat of als het thema sinds de vorige `emit` is
   gewisseld (laatst gebruikte thema wordt in de store-entry bijgehouden).
10. **Emitten:** `OSC 1337 ; SetProfile=<Name> ST` (icoon + profiel) plus de
    `OSC 6 ; 1 ; bg ; …` kleur-codes voor direct effect.
11. **Geen manifest gevonden of fout (en geen store-entry):** switch terug naar
    het **Default**-profiel en reset de tab-kleur (`OSC 6 ; 1 ; bg ; * ; default
    ST`). De normale look herstelt zo zodra je een project zonder favicon
    binnenloopt.

## Tab-titel

Naast icoon + kleur krijgt elke themed tab een titel via `OSC 0` (`ESC]0;<titel>BEL`).

- **Naam-bron (volgorde):** manifest `name` → manifest `short_name` → `.env`
  (eerste niet-lege van `APP_NAME`, `PROJECT_NAME`, `NAME`, `VITE_APP_NAME`,
  `NEXT_PUBLIC_APP_NAME`) → basisnaam van de project-root.
- **"Themed":** een root wordt behandeld als er een `site.webmanifest` **of** een
  `.env` aanwezig is. Manifest-met-PNG → icoon + kleur + titel. Alleen `.env`
  (geen favicon) → titel + Default-profiel (geen icoon/kleur). Geen van beide →
  volledige reset.
- **`rename`:** zet `custom_name`; de getoonde titel wordt `"<name> | <custom_name>"`.
  `scan`/`set-icon` behouden de `custom_name`.
- **Reset:** bij een niet-themed map wordt de titel gewist (`ESC]0;BEL`) naast de
  profiel/kleur-reset. (Titel-persistentie t.o.v. een prompt die de titel
  herschrijft wordt in de E2E geverifieerd.)

## Per-map store

De store is de **bron van waarheid** (geen wegwerp-cache met mtime-invalidatie).
Eenmaal gevuld leest `emit` 'm direct en doet géén manifest-scan meer.

- **Locatie:** `~/.config/livery/dirs/<hash(root)>.json`, gekoppeld aan
  het absolute project-root-pad. Onzichtbaar in je repo's, werkt ook voor
  niet-git-mappen.
- **Niveau:** per project-root (omhoog tot `.git`; anders de letterlijke map).
- **Inhoud per entry:**
  ```json
  {
    "root": "/abs/pad/naar/project",
    "icon_path": "/abs/pad/naar/icon.png",  // null bij .env-only project
    "dominant_color": [82, 113, 255],        // null als er geen icoon is
    "name": "Slowboard",                      // afgeleide naam (titel-basis)
    "custom_name": null,                      // rename-suffix; titel = "<name> | <custom_name>"
    "source": "manifest",                     // "manifest" | "manual" | "env" | "name"
    "last_theme": "dark"                      // voor het vermijden van profiel-rewrites
  }
  ```
- **Wanneer geschreven:** alleen bij eerste auto-detectie, `scan` of
  `set-icon`. Een gewone `cd` schrijft nooit (behalve `last_theme` bij een
  thema-wissel).
- **Levenscyclus:** `scan` herberekent uit het manifest; `set-icon` zet
  `source: "manual"` met een eigen pad; `clean` verwijdert entries waarvan
  `root` niet meer bestaat (plus hun profiel-bestand).

## iTerm2-sleutels — verificatiestap (geen gok)

De exacte Dynamic-Profile-sleutels voor een custom icoon staan niet in de docs;
het officiële advies is "copy from a known-good reference". Daarom een vaste
stap in het implementatieplan:

1. Installeer iTerm2 (`brew install --cask iterm2`).
2. Maak handmatig een profiel met een custom icoon (Preferences → Profiles →
   General → Icon → Custom).
3. Exporteer/lees het profiel (Preferences → Profiles → other actions → Save
   Profile as JSON, of lees `~/Library/Preferences/com.googlecode.iterm2.plist`).
4. Bevestig de echte sleutelnamen + waarden.

Verwachte waarden (te bevestigen):
- `"Icon"`: integer, `2` = custom.
- `"Custom Icon Path"`: absoluut pad-string.
- `"Tab Color"` / `"Background Color"`: dict met `Red/Green/Blue/Alpha Component`
  (0–1 floats) + `Color Space: "sRGB"`.
- `"Use Tab Color"`: bool.

## Error handling

Alles fail-silent; optioneel een logregel naar `~/.config/livery/log` als
`LIVERY_LOG=1`. Concrete gevallen:
- Kapotte/ongeldige JSON → skip, reset naar Default.
- `icons` leeg of geen PNG → skip, reset naar Default.
- Gerefereerde PNG ontbreekt op schijf → skip icoon, reset naar Default.
- `sips` of decode faalt → kleur-fallback, anders skip.
- Niet in iTerm2 → volledig no-op (geen output).

## Profiel-opruiming

Commando `livery clean`: verwijdert store-entries waarvan het `root`-pad
niet meer bestaat, plus de bijbehorende gegenereerde Dynamic-Profile-bestanden.
Handmatig, niet automatisch.

## Configuratie (env-vars)

| Var | Default | Effect |
|-----|---------|--------|
| `LIVERY_TAB_STRENGTH` | `0.15` | Blend-sterkte tab-kleur |
| `LIVERY_BG_STRENGTH` | `0.07` | Blend-sterkte terminal-achtergrond |
| `LIVERY_MAXDEPTH` | `6` | Max zoekdiepte vanaf project-root |
| `LIVERY_LOG` | (uit) | `1` = logregels naar `~/.config/livery/log` |

## Testen (TDD)

De Python-helper is het testbare hart; cwd + profiles-dir + store-dir zijn
parameters zodat tests geïsoleerd in tmp-mappen draaien.

Fixture-scenario's:
- **Geldig (eerste keer):** map met `site.webmanifest` + PNG → asserten: juiste
  PNG gekozen, pad correct geresolved, plausibele dominante kleur, **store-entry
  geschreven**, geldige profiel-JSON geschreven, verwachte escape-sequences.
- **Store-treffer (snelpad):** tweede `emit` met bestaande store-entry →
  asserten dat er **geen** manifest-scan/`sips` draait (bv. manifest verwijderd
  maar entry intact → emit werkt nog steeds uit de store).
- **`scan`:** wijzig manifest/PNG, draai `scan` → store-entry + kleur
  bijgewerkt.
- **`set-icon <pad>`:** zet handmatig pad → store-entry krijgt `source: manual`,
  kleur afgeleid uit die PNG, `scan`/`emit` respecteren de handmatige bron tot
  een volgende `set-icon`/`scan`.
- **Thema-wissel:** zelfde entry, ander `AppleInterfaceStyle` → profiel
  herschreven met nieuwe tints; gelijk thema → profiel **niet** herschreven.
- **`clean`:** entry met niet-bestaand `root` → entry + profiel verwijderd;
  bestaande root blijft staan.
- **Submap:** `cd` in `src/` met manifest in `public/` → vindt 't via root-walk.
- **Kapotte JSON** → reset-naar-Default-pad, geen crash.
- **Geen PNG in `icons`** → reset-pad.
- **Ontbrekende PNG-file** → reset-pad.
- **Geen manifest** → reset-pad.
- **Kleur-fallback:** icoon dat na filtering leeg is → gemiddelde-fallback.
- **Tint-berekening:** bekende kleur + thema → exacte verwachte gemute RGB.
- **Niet-iTerm2 guard:** `TERM_PROGRAM` anders → lege output.

De zsh-laag blijft een dunne wrapper; smoke-test (source + `cd` in fixture,
controleer dat er output komt en de shell intact blijft).

## Projectstructuur

```
~/projects/livery/
├── livery.zsh        # zsh-hook (source vanuit .zshrc)
├── livery.py         # Python-helper (emit/clean)
├── tests/                   # pytest + fixture-mappen
│   └── fixtures/
├── docs/superpowers/specs/  # deze spec
└── README.md                # installatie (1 source-regel in .zshrc) + config
```

Installatie voor de gebruiker: één regel in `~/.zshrc`:
```sh
source ~/projects/livery/livery.zsh
```
