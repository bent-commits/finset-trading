# Finset Trading 📊

**Kongress vs. Indeks** — et selvoppdaterende dashbord som svarer på ett spørsmål, ærlig:

> **Hva lønner seg mest — å følge amerikanske kongresspolitikeres aksjekjøp, eller bare å kjøpe et indeksfond?**
> Begge strategier starter med **1 500 000 kr**, og alt måles i norske kroner.

Dashbordet oppdateres **automatisk hver morgen kl. 08:00 norsk tid** via GitHub Actions, helt uten at en PC trenger å stå på.

---

## Hva du ser

Fire strategier sammenlignes side om side:

| Strategi | Hva det er |
|---|---|
| **Congress (Hus + Senat)** | Speiler hva kongresspolitikerne (begge kamre) netto kjøper mest av |
| **Stjernetrader** | Følger hver måned den ene politikeren med best resultat frem til da (punkt-i-tid) |
| **S&P 500 (USA)** | Det amerikanske markedet (SPY) |
| **Globalt indeksfond** | Verdensindeksen MSCI World (URTH) — typen KLP/DNB Global Indeks |
| **Oslo Børs** | Hovedindeksen OSEBX |

For hver strategi og tidshorisont (live siden lansering, siden 2019, 5 / 3 / 1 år) vises sluttverdi i kr, avkastning, årlig avkastning, svingning (volatilitet), største verdifall (drawdown) og Sharpe-tall.

## Metoden (slik et seriøst meglerhus ville gjort det)

- **Innsynsforsinkelse er bakt inn (det viktigste).** Politikere må rapportere handler opptil 45 dager etter at de er gjort. Vi legger derfor inn handler på **publiseringsdato** (`disclosure_date`), aldri på politikerens hemmelige handelsdato. Det er det som gjør tallene ærlige — mange «politikerne slår markedet»-analyser jukser ved å late som man kunne handlet samme dag.
- **Porteføljekonstruksjon.** Hver måned holdes de **20 aksjene** med størst netto kjøp (kjøp minus salg, i dollar) blant House-politikerne siste 12 måneder, vektet etter kjøpsstørrelse, **maks 10 % per aksje**. Aksjer som selges tungt faller ut og lukkes.
- **Valuta.** Amerikanske aksjer prises i USD og veksles til NOK til daglig kurs, slik at valutarisikoen en norsk investor faktisk har, er med.
- **Kostnader.** Kurtasje/spread (0,20 %) og valutapåslag (0,50 %) ved hver rebalansering, samt amerikansk kildeskatt på utbytte. Indeksfondene belastes årlig forvaltningshonorar (TER). Avkastning er total (utbytte reinvestert).
- **Risiko, ikke bare avkastning.** Vi rapporterer svingning, største fall og Sharpe — ikke bare prosent opp.

## Foreløpig funn (per juni 2026)

- **Siden 2019** (lang sikt) har Congress-porteføljen gitt klart mest (~+375 % mot ~+265 % for S&P 500) — men med **betydelig høyere risiko** (større svingninger og verre fall).
- **Siste 3–5 år** har vanlige indeksfond **matchet eller slått** Congress-porteføljen, med lavere risiko.
- Med andre ord: «følg politikerne»-fordelen var sterk i 2019–2021 (kurven var full av mega-tech), men har ikke vedvart. Dataene får tale.

## Kjøre lokalt

Krever bare Python 3.12+ (ingen pip-avhengigheter — alt er standardbibliotek).

```bash
python run.py
```

Det henter ferske data, kjører backtesten og bygger `docs/index.html`. Åpne den filen i nettleseren.

## Hvordan automatikken virker

`.github/workflows/daily.yml` kjører `run.py` hver morgen, committer oppdaterte data + dashbord, og GitHub Pages serverer `docs/`. Ingen server, ingen PC som må stå på.

## Datakilder

- **Handler (Representantenes hus):** [house-stock-watcher-data](https://github.com/TattooedHead/house-stock-watcher-data), utledet fra de offisielle PTR-innleveringene hos House Clerk.
- **Handler (Senatet):** den offisielle [Senate eFD](https://efdsearch.senate.gov), hentet via `curl_cffi` (etterligner ekte nettleser-TLS for å komme forbi WAF-en). Parsede transaksjoner committes som et «seed» og oppdateres inkrementelt.
- **Priser og valuta:** Yahoo Finance.

## Begrensninger (ærlig liste)

- Dekker **både Representantenes hus og Senatet** (kun aksjer — opsjoner, fond, krypto m.m. utelates).
- Aksjer som er kjøpt opp / avnotert (uten priser) utelates — kan gi en liten skjevhet.
- Beløp rapporteres i intervaller; vi bruker midtpunktet.
- Dette er en **simulert papirportefølje**, ikke ekte handel.

---

> **Viktig:** Dette er en analyse, ikke investeringsrådgivning, og ingen anbefaling om å plassere ekte penger. Historisk avkastning er ingen garanti for fremtidig avkastning. Ingen kjøp eller salg utføres.
