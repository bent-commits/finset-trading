---
name: houdini-lokalsondering
description: Bruk når Claude skal sondere butikklokaler i Oslo for Houdini Sportswear for Bent Finset, enten den daglige sonderingen kl. 15 eller fredagsmailen kl. 08 til bent@odeon.no. Dekker kriterier, kilder (FINN, næringsmeglere, gårdeiere), kreativ sondering i Bogstadveien, Hegdehaugsveien og sidegatene, loggføring i Google-arket og formatet på fredagsmailen.
---

# Houdini lokalsondering, Oslo

Oppdraget: finne relevante butikklokaler i Oslo for Houdini Sportswear, slik at Bent Finset kan sende CEO Knut Are Høgberg direkte forslag og vinne oppdraget foran andre næringsmeglere. Forslagene må være relevante og bygge på fakta. Kreativitet teller høyt.

## Kunden

- Houdini Sportswear: svensk premium friluftsmerke. Sirkulært konsept med kjøp, leie, reparasjon og brukt (Houdini Hub Kungsgatan 30 i Stockholm, tegnet av White Arkitekter 2022).
- Ingen egen butikk i Norge i dag. Hadde Houdini Hub på 70 m² i Hegdehaugsveien 34 (Snøhetta) fra 2017 til ca. 2022.
- Prisnivå: om lag 35 % over Bergans og ca. 10 % under Norrøna og Arc'teryx.
- Signal fra CEO (samtale 26.10.2026): ser etter lokaler i Bogstadveien og Hegdehaugsveien på grunn av husleienivået. Åpne for «typete» høye 1. etasjer, også i sidegatene. Størrelse opp til 200 m². Andre muligheter er ikke utelukket.
- Referansecase: Amundsen Sports gikk inn i en typete høy 1. etasje ved Bogstadveien for profilen og følelsen av konseptet. Detaljer står i `references/marked.md`.

## Kriterier

- Areal: opp til ca. 200 m² (ta med 200 til 250 m² hvis lokalet er spesielt godt).
- Gateplan, gjerne høy takhøyde, karakter (gamle bankhaller, verksteder, kafeer, hjørner, bakgårder med gateadkomst).
- Område først: Bogstadveien, Hegdehaugsveien og alle sidegater (se `references/marked.md`). Deretter Majorstuen, Uranienborg, Homansbyen, Frogner, Fagerborg og sentrum som sekundært.
- Ingenting er utelukket: kjøpesenter i området, lokaler som ikke er ledige, drift som legger ned, konkurser.
- Score 1 til 5: 5 = riktig gate, størrelse og karakter; 3 = interessant med svakheter; 1 = bare for oversikt.

## Kilder hver kjøring

1. FINN næringseiendom: faste søk i fanen «Søkeoppsett» i arket.
2. Næringsmeglernes egne oppføringssider: listen i fanen «Meglere og gårdeiere» og i `references/meglere.md`.
3. Gårdeiere og forvaltere som leier ut selv.
4. Nyheter: «legger ned», «konkurs», «flytter» + Bogstadveien, Hegdehaugsveien og sidegatene; Brønnøysund (konkurser i området).
5. Kreativ sondering: gå gjennom én eller to sidegater per dag og noter lokaler som kan passe, også om de ikke er ledige.

Direkte henting av nettsider blir ofte blokkert av proxyen. Prøv WebFetch, deretter WebFetch på `https://r.jina.ai/<url>`, deretter søkeutdrag. Skriv i loggen hva som ikke kunne leses.

## Faktakrav

- Hvert lokale: adresse, kilde-URL og dato. Areal, leie og takhøyde bare når det står i en kilde, ellers «ukjent».
- Kontaktperson for hvert lokale: navn, firma, telefon, e-post fra kilden. Finnes den ikke, skriv den konkrete ruten til eieren: gårdeier via seeiendom.no eller Kartverket, forvalter, eierselskapet til driften i Brreg eller Proff, næringsforeningen.
- Ikke finn på navn, telefonnumre, e-poster, arealer eller priser.
- Skriv «antatt» der noe er antatt.

## Daglig kjøring (kl. 15)

1. Åpne arket «Houdini Oslo lokaler, sondering» (ID `1SoD3bBCNppP9HySSTWvo-zTTC8-oQ8RyhYEstNwJZjk`). Les fanene «Muligheter», «Søkeoppsett» og «Meglere og gårdeiere».
2. Kjør alle kildene over. Sammenlign med eksisterende rader (adresse) for å unngå dubletter.
3. Nye lokaler: legg til rad i «Muligheter» med neste ID (H-001, H-002 ...), «Først sett» = dagens dato.
4. Kjente lokaler: oppdater «Sist sjekket», status og endringer (for eksempel utleid eller ny pris).
5. Legg til én rad i «Logg»: dato, kilder sjekket, nye ID-er, endringer, hva som var blokkert.
6. Ikke send e-post i den daglige kjøringen.

## Fredagsmail (kl. 08)

Til: bent@odeon.no, og bare denne adressen. Send med Gmail. Hvis sending ikke er mulig, lag utkast til bent@odeon.no og si det i første linje.

Emne: «Houdini lokaler uke NN: X nye, Y aktuelle»

Innhold (HTML, ryddig, bokmål, ingen tankestrek, ingen «bør»):
1. Kort status: antall nye siden forrige fredag, antall aktive totalt, hva som er endret.
2. Topp 5 denne uka, sortert på score: adresse, hvorfor Houdini, areal og etasje, status, kontaktperson med telefon og e-post (eller konkret kontaktrute), kilde-lenke.
3. Kreative forslag (ikke ledige): 3 til 5 lokaler med begrunnelse og hvem som eier dem.
4. Alle øvrige aktive muligheter i en kort tabell.
5. Nytt fra markedet: nedleggelser, konkurser, nyåpninger i området.
6. Forslag til hvilke tre lokaler som kan sendes til CEO, med én setning hver. Bare lokaler med score 4 eller 5.
7. Metode: kilder sjekket, hva som var blokkert, lenke til arket.

Marker radene som er tatt med i kolonnen «Sendt i fredagsmail» med datoen.

## Tone

Fakta, kort, ryddig. Bent bestemmer hva som sendes videre til CEO. Ikke skriv til Houdini eller meglere.
