# Claude Code – jukseark

Verifisert mot dokumentasjonen 2026-11-05 (Claude Code 2.1.x).

## Snarveier

| Tast | Gjør |
|---|---|
| `Shift+Tab` | Bytt modus (auto, default, acceptEdits, plan) |
| `Esc` | Stopp pågående svar |
| `Esc Esc` | Tom prompt: åpne rewind. Med tekst: slett utkast |
| `Ctrl+B` | Kjør pågående kommando/agent i bakgrunnen |
| `Ctrl+T` | Vis/skjul oppgaveliste |
| `Ctrl+O` | Vis/skjul transkript |
| `Ctrl+R` | Søk i historikk |
| `Ctrl+V` | Lim inn bilde (`Cmd+V` i iTerm2, `Alt+V` på Windows) |
| `Ctrl+X Ctrl+K` | Stopp alle bakgrunnsagenter (trykk to ganger) |
| `@fil` | Henvis til fil eller mappe |
| `!kommando` | Kjør shell-kommando direkte |

## Daglig bruk

| Kommando | Gjør |
|---|---|
| `/btw` | Sidespørsmål uten å avbryte arbeidet |
| `/recap` | Enlinjes sammendrag av sesjonen |
| `/usage` (`/cost`, `/stats`) | Forbruk og grenser |
| `/status` | Versjon, modell, konto, tilkobling |
| `/doctor` | Sjekk oppsettet |
| `/tasks` | Bakgrunnsjobber og subagenter |
| `/mcp` | MCP-servere |
| `/plugin` | Plugins |
| `/help` | Alle kommandoer |

## Arbeidsflyt

| Kommando | Gjør |
|---|---|
| `/code-review` (`/review`) | Gjennomgå diff, PR eller gren |
| `/security-review` | Sikkerhetsgjennomgang av grenen |
| `/simplify` | Rydd og forenkle endret kode |
| `/loop 5m <prompt>` | Gjenta en prompt med intervall |
| `/schedule` | Planlagte oppgaver i skyen |
| `/batch` | Del en stor endring i flere PR-er |
| `/autofix-pr` | Overvåk PR og push rettelser |
| `/verify`, `/run` | Kjør appen og bekreft en endring |

## Bruk med omhu

- `"ultracode"` i prompten starter multi-agent-arbeid og kan koste mye.
- `/ultrareview` (`/code-review ultra`) går på usage credits etter 3 gratis kjøringer.
- `/ultraplan` er fjernet. Bruk plan mode (`Shift+Tab`).
- `Option+T` (tenking) har ingen effekt på Claude 5-modellene.
