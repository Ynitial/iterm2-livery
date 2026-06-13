# livery

Geeft elke **iTerm2**-tab automatisch de identiteit van het project waarin je
staat: het favicon-**icoon**, een subtiel gemute **merkkleur**-tint op de tab +
terminal-achtergrond, en een **titel**. Net als een livery — de kleuren en het
embleem waaraan je ziet bij wie iets hoort.

Bron van waarheid is een `site.webmanifest` (favicon + naam) of een `.env`
(naam). Eenmaal afgeleid wordt alles per project-root opgeslagen, zodat elke
`cd` razendsnel blijft.

## Installatie

1. iTerm2 vereist: `brew install --cask iterm2`
2. Voeg aan `~/.zshrc` toe:
   ```sh
   source ~/projects/livery/livery.zsh
   ```
3. Open een nieuwe iTerm2-tab.

## Hoe het werkt

Bij elke `cd` (en bij het openen van een tab):

1. Alleen actief in iTerm2 (anders gebeurt er niets).
2. De project-root wordt bepaald (omhoog tot `.git`, anders de map zelf).
3. Bestaat er al een store-entry voor die root? → meteen icoon + kleur + titel
   emitten (geen scan). Zo niet → eenmalig afleiden en opslaan.
4. Afleiden: `site.webmanifest` zoeken → eerste PNG-icoon → dominante kleur (via
   `sips`) → naam.

### Manifest zoeken (snel & veilig)

Eerst conventionele plekken: de root zelf en `public/`, `static/`, `www/` —
losse stat-checks, dus altijd instant. Niets gevonden én er is een `.git`? Dan
pas een begrensde recursieve `find` binnen de repo (`node_modules`/`dist`/… 
overgeslagen, diepte `LIVERY_MAXDEPTH`). **Mappen zonder `.git` (zoals `~` of
`/tmp`) worden nooit afgestruind** — dat houdt elke `cd` snel en voorkomt dat
een willekeurig genest project je tab kaapt.

Een root wordt "themed" als er een `site.webmanifest` **of** een `.env` is:

- **Manifest met PNG** → icoon + gemute tint + titel.
- **Alleen `.env`** → titel (geen custom icoon/kleur).
- **Geen van beide** → niets; de tab houdt iTerm's eigen default-titel.

> **Tip:** livery zet de tabtitel. Gebruik je oh-my-zsh, zet dan
> `DISABLE_AUTO_TITLE="true"` in je `.zshrc` (vóór `source oh-my-zsh.sh`),
> anders overschrijft oh-my-zsh livery's titel bij elke prompt.

### Naam (tab-titel)

livery gebruikt twee iTerm2-titelcomponenten:

- **Profile Name = mapnaam van de project-root** (bv. `vanderkrabben`). Livery's
  profiel heet naar de map, dus dit toont automatisch het project.
- **Session Name = `livery rename <naam>`** — **per tab** (gekoppeld aan
  `$ITERM_SESSION_ID`). Twee tabs in dezelfde map kunnen dus elk een eigen naam
  hebben.

Zet in iTerm2 de **Title** op **Profile & Session Name** (Settings → Profiles →
General → Title). De tab toont dan `vanderkrabben` (geen rename) of
`vanderkrabben — dev` (na `livery rename dev`). Niet-getheme­de map → geen titel.

### Kleur

De dominante kleur van het icoon (bijna-wit/zwart pixels eruit gefilterd) kleurt
de **tab** — standaard de volle merkkleur. De terminal-achtergrond wordt niet
getint (blijft je thema). Wil je de tabkleur zachter, zet `LIVERY_TAB_STRENGTH`
lager (blendt dan richting je thema-achtergrond).

## Commando's

| Commando | Effect |
|----------|--------|
| `livery scan` | Opnieuw afleiden uit `site.webmanifest` (na een logo/naam-wijziging) |
| `livery set-icon <pad>` | Handmatig icoon-pad instellen (werkt ook zonder manifest) |
| `livery rename <naam>` | Zet de **sessienaam** van deze tab (per tab); zonder argument wist het 'm |
| `livery clean` | Verweesde profielen/store-entries opruimen |

## Configuratie (env-vars)

| Var | Default | Effect |
|-----|---------|--------|
| `LIVERY_TAB_STRENGTH` | `1.0` | Tabkleur-sterkte (1 = volle merkkleur, 0 = thema-kleur) |
| `LIVERY_MAXDEPTH` | `6` | Max zoekdiepte bij de recursieve `find` binnen een git-repo |
| `LIVERY_PROFILE_DELAY` | `0.3` | Pauze (s) ná het schrijven van een nieuw profiel, zodat iTerm2 het inlaadt vóór de switch (alleen bij 1e bezoek). Hoger zetten als 't icoon dán nog mist; 0 om uit te zetten |
| `LIVERY_LOG` | (uit) | `1` = foutregels naar `~/.config/livery/log` |

## Opslag

- Per-root config: `~/.config/livery/dirs/<hash>.json`
- iTerm2 Dynamic Profiles: `~/Library/Application Support/iTerm2/DynamicProfiles/`

## Ontwikkeling

```sh
python3 -m pytest        # volledige suite
```

Pure-Python (stdlib) + de macOS-tools `sips` en `defaults`. Geen externe
dependencies.
