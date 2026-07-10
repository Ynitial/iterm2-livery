# livery — Claude-modus — Design

**Datum:** 2026-07-10
**Status:** Ontwerp goedgekeurd, klaar voor implementatieplan

## Doel

Wanneer je `claude` start, krijgt de iTerm2-tab een herkenbare "AI-look" die
losstaat van het projectprofiel: een Claude-oranje venster met een 🦀-marker in
de titel. Zodra je claude afsluit, valt de tab terug op de normale livery-look
van de map waar je op dat moment bent.

De look is **per-invocation**, niet per-map: in dezelfde map draai je niet
altijd claude, dus de oranje look mag nooit in het projectprofiel gebakken
worden. `cd` → projectkleuren; `claude` → oranje; claude afsluiten →
projectkleuren terug.

Het mechanisme is **per-commando instelbaar**: andere commando's kunnen later
hun eigen emoji/achtergrondkleur krijgen zonder codewijziging.

## Scope & non-doelen

- **Alleen iTerm2** (net als de rest van livery; buiten iTerm2 doet de wrapper
  niets bijzonders en draait het commando gewoon door).
- **Geen code-snippet-achtergrond.** Claude Code heeft geen theme-token voor de
  achtergrond achter markdown code-blokken; dit is geverifieerd onmogelijk en
  valt buiten scope. Code rendert op het oranje met Claude Code's eigen
  syntax-kleuren.
- **Geen per-map claude-look.** De oranje toestand is een tijdelijke overlay,
  geen projectprofiel-variant.
- **Geen live status in de titel.** Claude Code publiceert z'n status niet naar
  de OSC-tabtitel; alleen de 🦀-marker wordt vóór de bestaande titel geplakt.

## Achtergrond: wat wel/niet kan (geverifieerd via docs-research)

- **Vensterachtergrond** wordt door de terminal (iTerm2) bepaald, niet door
  Claude Code. De oranje achtergrond is dus livery/iTerm2-werk.
- **Claude Code custom themes** bestaan: JSON in `~/.claude/themes/*.json` met
  een `base` + `overrides` van kleur-tokens (hex/rgb/ansi), geactiveerd via
  `settings.json` → `"theme": "custom:<slug>"`. Er is geen launch-flag of
  env-var om een thema te kiezen.
- **Gevulde berichtachtergronden** (waaronder `userMessageBackground`) werken
  **alleen in fullscreen-rendermodus**. Er is geen token voor code-blok- of
  algemene assistant-achtergronden, en syntax-highlight-kleuren zijn niet
  instelbaar.
- **Claude Code raakt de OSC-tabtitel niet aan** (het heeft alleen een in-app
  statusline). Een titel die de wrapper vóór de start zet, blijft dus staan
  gedurende de sessie.

> Twee dingen worden tijdens de bouw nog empirisch geverifieerd: (1) de exacte
> manier om fullscreen aan te zetten bij launch (env-var `CLAUDE_CODE_NO_FLICKER`
> of settings-sleutel), en (2) dat Claude Code de tabtitel inderdaad niet
> overschrijft.

## Architectuur — twee gescheiden delen

**Deel A — iTerm2-toestand (per-invocation, door de wrapper).** Zet de oranje
look aan bij start van het commando en herstelt de normale livery-look bij
afsluiten.

**Deel B — Claude Code thema (eenmalige setup).** Leesbare tekst en
lichter-oranje berichten *binnen* Claude Code. Mag globaal aan staan, want het
manifesteert zich alleen tijdens een claude-sessie.

## Deel A — de `livery-claude`-toestand

- Eén gedeeld dynamisch profiel `livery-claude.json` in de DynamicProfiles-map:
  - achtergrond `#D97757` (`rgb(217,119,87)`),
  - een afgestemd 16-kleuren **ANSI-palet** zodat kale terminal-tekst leesbaar
    blijft op oranje (exacte waarden worden tijdens de bouw getuned met een
    contrast-check),
  - géén custom icoon (erft verder van Default).
- De wrapper emit bij start:
  1. `SetProfile=livery-claude`,
  2. **tabkleur = de projectkleur** (behouden, zodat je bij meerdere claude-tabs
     ziet wélk project het is; het oranje venster signaleert al de AI-modus),
  3. titel = **🦀 ** vóór de bestaande projecttitel voor `$PWD` (livery kent de
     projectnaam en een eventuele `rename` al).
- Bij afsluiten emit livery de normale look voor `$PWD` opnieuw (de bestaande
  `_livery_run`): projectprofiel, projectkleur, titel zonder 🦀. Werkt ook als
  je tijdens de sessie ge-`cd`'d bent.

## Deel B — het Claude Code thema

- livery schrijft `~/.claude/themes/livery-claude.json` met `base: light`
  (donkere tekst leest het best op dit oranje) en o.a.:
  - tekst-tokens afgestemd op oranje (leesbaar),
  - `userMessageBackground` = een **lichter oranje** (jouw verzonden berichten),
  - overige achtergrond-tokens waar zinvol (exacte tinten getuned tijdens bouw).
- Activeren via een **`livery claude-setup`**-commando dat
  `~/.claude/settings.json` bijwerkt met `"theme": "custom:livery-claude"` —
  **mergend**, niet overschrijvend (bestaande sleutels blijven staan).
- De wrapper start claude in **fullscreen** (nodig voor de gevulde
  berichtachtergrond). De README vermeldt deze fullscreen-eis expliciet.

## Per-commando config (extensibiliteit)

Een klein configbestand `~/.config/livery/commands.json`:

```json
{
  "claude": { "emoji": "🦀", "bg": [217, 119, 87], "fullscreen": true }
}
```

`livery.zsh` leest dit bij het laden en definieert voor elke sleutel een
wrapper-functie met die naam. Nu is dat dus `claude`. Een extra commando
(bijv. `codex`) is een regel erbij — geen codewijziging. Het Claude Code thema
(Deel B) is de enige claude-specifieke extra; generieke commando's krijgen
alleen achtergrond + emoji-titel.

## Wrapper-structuur (zsh)

Elke wrapper omhult het echte commando via `command <naam> …` zodat de
PATH-versie draait, met herstel gegarandeerd — óók bij Ctrl-C:

```
claude() {
  <look aan: SetProfile livery-claude + projectkleur + 🦀-titel>
  {
    command claude "$@"
  } always {
    _livery_run   # herstelt de normale look voor $PWD
  }
}
```

## Bestanden

- **Nieuw:** de generatie van `livery-claude.json` (Deel A profiel) en
  `~/.claude/themes/livery-claude.json` (Deel B thema).
- **Nieuw:** `commands.json`-lezer + wrapper-generatie in `livery.zsh`.
- **Nieuw:** subcommando's `livery claude-setup` (thema activeren) en de
  emit-logica voor "commando-look aan".
- **Gewijzigd:** `livery.zsh` (wrappers definiëren), `__main__.py` (nieuwe
  subcommando's), README.

## README

De README wordt bijgewerkt met een **korte, duidelijke** sectie over de
Claude-modus: wat het doet (oranje look + 🦀-titel bij `claude`), de eenmalige
`livery claude-setup`, en de notitie dat claude in **fullscreen** draait (nodig
voor de gekleurde berichtachtergrond). Bewust beknopt houden.

## Wat er níét in zit (bewust)

- Code-snippet-achtergronden donkerder oranje — niet mogelijk (geen token).
- De claude-look in een projectprofiel bakken — nee, blijft per-invocation.
- Live claude-status in de tabtitel — Claude Code publiceert die niet.
