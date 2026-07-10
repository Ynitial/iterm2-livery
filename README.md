# livery

Geeft elke **iTerm2**-tab automatisch de identiteit van het project waarin je staat:
het favicon als **tab-icoon**, de **merkkleur** op de tab, en de **mapnaam** als titel.

Net als een livery — de kleuren en het embleem waaraan je ziet bij wie iets hoort.

## Installeren

1. iTerm2: `brew install --cask iterm2`
2. Zet in je `~/.zshrc`:
   ```sh
   source ~/projects/iterm2-livery/livery.zsh
   ```
3. Zet in iTerm2 de tab-titel goed: **Settings → Profiles → General → Title → Profile & Session Name**.
4. Gebruik je **oh-my-zsh**? Zet dan ook `DISABLE_AUTO_TITLE="true"` in je `.zshrc` (vóór `source oh-my-zsh.sh`), anders overschrijft oh-my-zsh de tabtitel.
5. Open een nieuwe tab.

Geen externe dependencies — puur zsh + Python (stdlib) + de macOS-tools `sips` en `defaults`.

## Hoe het werkt

Eén regel in je `.zshrc` laadt een dun zsh-script. Dat draait een klein Python-helpertje
bij **elke `cd`** (en bij het openen van een tab). De helper bepaalt het project, leest de
favicon + kleur, en stuurt iTerm2 een paar escape-codes (icoon/kleur/titel). Geen app, geen
daemon — het start, doet z'n ding, en sluit weer af. Resultaten worden gecached, dus elke `cd`
blijft snel.

## Wat het scant (en hoe het weet wat te tonen)

1. **Project-root bepalen:** vanaf je huidige map omhoog tot de eerste map met een `.git`.
   Geen `.git` gevonden? Dan is het **geen project** en doet livery niks (de tab houdt iTerm's
   eigen titel). Zo blijft bv. `~/Sites` leeg.
2. **Manifest zoeken** (alleen in een git-project): eerst op vaste plekken — de root zelf en
   `public/`, `static/`, `www/`. Niets daar? Dan een begrensde recursieve zoektocht binnen de
   repo (`node_modules`/`dist`/… overgeslagen). **Container-mappen zonder `.git` worden nooit
   afgestruind** — dat houdt het snel en voorkomt dat een willekeurig genest project je tab kaapt.
3. **Uit het manifest:** de eerste PNG → **icoon** + de dominante (merk)kleur → **tabkleur**.
   De mapnaam → **titel**.

Een map wordt dus "themed" als er een `.git` + `site.webmanifest` is. Heeft een project alleen
een `.env` (geen favicon), dan krijgt 't wel de mapnaam als titel, maar geen icoon/kleur.

De **achtergrond** wordt niet getint: livery's profiel erft je eigen licht/donker-thema van je
Default-profiel, dus de terminal volgt gewoon dark/light mode.

## Commando's

| Commando | Wat het doet |
|----------|--------------|
| `livery rename <naam>` · `livery rn <naam>` | Geeft **deze tab** een eigen naam (per tab). Twee tabs in dezelfde map kunnen elk een andere naam hebben. |
| `livery rename -p <naam>` | Hernoemt het **hele project** (de profielnaam; geldt voor alle tabs in de map). `--project` mag ook. |
| `livery icon <pad>` | Stel handmatig een icoon-PNG in (werkt ook zonder manifest). |
| `livery scan` | Leest de favicon/naam opnieuw in (na een logo- of naamswijziging). |
| `livery clean` | Ruimt profielen/cache op van projecten die niet meer bestaan. |

Een leeg argument wist de naam. De tab toont **projectnaam — tabnaam** (iTerm's "Profile &
Session Name"): standaard de mapnaam, of bv. `Krabben` (project-rename) of `Krabben — dev`
(project + tab-rename).

## Claude-modus

Start je `claude`, dan krijgt de tab tijdelijk een **Claude-oranje** look met een 🦀 vóór de titel — los van je projectprofiel. Sluit je claude af, dan komt de normale projectlook terug. De projecttabkleur blijft zichtbaar, zodat je bij meerdere claude-tabs ziet welk project het is.

Eenmalig instellen (schrijft een Claude Code-thema en activeert het):

    livery claude-setup

Claude draait in **fullscreen** (nodig voor de gekleurde achtergrond achter je eigen berichten). Andere commando's een eigen look geven? Voeg een regel toe aan `~/.config/livery/commands.json`:

    { "claude": { "emoji": "🦀", "bg": [217, 119, 87], "fullscreen": true } }

## Configuratie (optioneel, via env-vars)

| Var | Default | Effect |
|-----|---------|--------|
| `LIVERY_TAB_STRENGTH` | `1.0` | Tabkleur-sterkte (1 = volle merkkleur, lager = zachter richting je thema) |
| `LIVERY_MAXDEPTH` | `6` | Max zoekdiepte bij de recursieve zoektocht binnen een repo |
| `LIVERY_PROFILE_DELAY` | `0.3` | Pauze (s) zodat iTerm2 een nieuw profiel inlaadt; hoger als 't icoon bij 't 1e bezoek mist |
| `LIVERY_LOG` | (uit) | `1` = foutregels naar `~/.config/livery/log` |

## Waar het z'n data bewaart

- `~/.config/livery/dirs/` — per project: icoon-pad + kleur (cache).
- `~/.config/livery/sessions/` — per tab: je `rename`-naam.
- `~/Library/Application Support/iTerm2/DynamicProfiles/livery-*.json` — de gegenereerde profielen.

## Ontwikkeling

```sh
python3 -m pytest
```
