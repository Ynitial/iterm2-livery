# iterm-favicon — Design

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
- Geen ondersteuning voor meerdere favicons per project, geen GUI, geen
  config-bestand (alles via env-vars).

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

### 1. zsh-laag (`iterm-favicon.zsh`)
Een dun bestand dat vanuit `~/.zshrc` wordt ge-`source`d. Het:
- registreert een `chpwd`-hook (draait bij elke `cd`);
- draait één keer bij shell-startup (op de startmap);
- roept de Python-helper aan en `eval`t de teruggegeven escape-sequences;
- **faalt altijd stil** — een fout in de helper mag de shell nooit vertragen of
  breken (helper-aanroep met timeout-bewustzijn, fouten naar /dev/null tenzij
  logging aanstaat).

### 2. Python-helper (`iterm_favicon.py`)
Het testbare hart. Stdlib + de macOS-ingebouwde `sips`. Verantwoordelijk voor:
manifest zoeken, parsen, PNG→kleur, profiel schrijven, escape-sequences printen.

Aanroep-contract (zodat tests geïsoleerd draaien):
```
iterm_favicon.py emit  --cwd <dir> --profiles-dir <dir> --cache-dir <dir>
iterm_favicon.py clean --profiles-dir <dir> --cache-dir <dir>
```
`emit` print de escape-sequences naar stdout; de zsh-laag echoot die door naar
de tab. `--profiles-dir`/`--cache-dir` defaulten naar de echte iTerm2/cache-paden
maar zijn override-baar in tests.

## Data-flow per `cd`

1. **iTerm2-guard:** is `$TERM_PROGRAM` ongelijk aan `iTerm.app` (bv. SSH,
   Terminal.app)? → niets doen.
2. **Project-root bepalen:** vanaf `$PWD` omhoog lopen tot de eerste map met
   `.git` (of de filesystem-wortel). Dit is zowel het zoekgebied als de
   cache-sleutel — zo werkt het ook vanuit een submap zoals `src/`.
3. **Cache-check:** kijk in `~/.cache/iterm-favicon/` op sleutel
   `hash(root) + manifest-mtime`. Hit → meteen de gecachte kleur +
   `SetProfile` emitten. Klaar.
4. **Cache-miss:** vanaf de root recursief omlaag zoeken naar `site.webmanifest`
   met een diepte-limiet (default 6) en pruning van `node_modules`, `.git`,
   `dist`, `build`, `vendor`. Eerste match wint.
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
   - Twee sterktes: tab (`ITERM_FAVICON_TAB_STRENGTH`, default 0.15) en
     achtergrond (`ITERM_FAVICON_BG_STRENGTH`, default 0.07).
8. **Profiel genereren/updaten:** schrijf/overschrijf een Dynamic-Profile-JSON
   `iterm-favicon/<hash>.json` met:
   - stabiele `Guid` afgeleid van het root-pad (her-bezoek hergebruikt 't profiel);
   - `Name` (bv. `favicon: <projectnaam>`);
   - `Custom Icon Path` → absoluut PNG-pad, `Icon` → custom-modus;
   - `Tab Color` + `Use Tab Color`, `Background Color` → de gemute tints;
   - `Dynamic Profile Parent Name: "Default"` zodat al het overige geërfd wordt.
9. **Emitten:** `OSC 1337 ; SetProfile=<Name> ST` (icoon + profiel) plus de
   `OSC 6 ; 1 ; bg ; …` kleur-codes voor direct effect. Cache wegschrijven.
10. **Geen manifest gevonden of fout:** switch terug naar het **Default**-profiel
    en reset de tab-kleur (`OSC 6 ; 1 ; bg ; * ; default ST`). De normale look
    herstelt zo zodra je een project verlaat.

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

Alles fail-silent; optioneel een logregel naar `~/.cache/iterm-favicon/log` als
`ITERM_FAVICON_LOG=1`. Concrete gevallen:
- Kapotte/ongeldige JSON → skip, reset naar Default.
- `icons` leeg of geen PNG → skip, reset naar Default.
- Gerefereerde PNG ontbreekt op schijf → skip icoon, reset naar Default.
- `sips` of decode faalt → kleur-fallback, anders skip.
- Niet in iTerm2 → volledig no-op (geen output).

## Profiel-opruiming

Commando `iterm-favicon clean`: verwijdert gegenereerde Dynamic-Profile-bestanden
waarvan het bron-pad/manifest niet meer bestaat (en hun cache-entries). Handmatig,
niet automatisch.

## Configuratie (env-vars)

| Var | Default | Effect |
|-----|---------|--------|
| `ITERM_FAVICON_TAB_STRENGTH` | `0.15` | Blend-sterkte tab-kleur |
| `ITERM_FAVICON_BG_STRENGTH` | `0.07` | Blend-sterkte terminal-achtergrond |
| `ITERM_FAVICON_MAXDEPTH` | `6` | Max zoekdiepte vanaf project-root |
| `ITERM_FAVICON_LOG` | (uit) | `1` = logregels naar cache-log |

## Testen (TDD)

De Python-helper is het testbare hart; cwd + profiles-dir + cache-dir zijn
parameters zodat tests geïsoleerd in tmp-mappen draaien.

Fixture-scenario's:
- **Geldig:** map met `site.webmanifest` + PNG → asserten: juiste PNG gekozen,
  pad correct geresolved, plausibele dominante kleur, geldige profiel-JSON
  geschreven, verwachte escape-sequences geprint.
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
~/projects/iterm-favicon/
├── iterm-favicon.zsh        # zsh-hook (source vanuit .zshrc)
├── iterm_favicon.py         # Python-helper (emit/clean)
├── tests/                   # pytest + fixture-mappen
│   └── fixtures/
├── docs/superpowers/specs/  # deze spec
└── README.md                # installatie (1 source-regel in .zshrc) + config
```

Installatie voor de gebruiker: één regel in `~/.zshrc`:
```sh
source ~/projects/iterm-favicon/iterm-favicon.zsh
```
