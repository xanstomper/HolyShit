# Breach-History & Regulator-Leak OSINT for Operator Targets

The class: study a target's past breaches, leaks, and vulns from public sources alongside
live probing. Prior breaches name the crown jewels and the control layer that failed — the
fastest route to knowing where the real vulnerability lives, and sometimes the finding
itself (operator dossiers leaked via regulators).

## Breach-history research chain (in order)

1. `web_search "<target> hack OR breach OR vulnerability OR exploit"` — the first hit names
   the incident class (hot-wallet key compromise vs smart-contract vs platform/web).
2. Follow the cascade: the wire (CoinDesk, news.bitcoin.com) -> aggregators/loss trackers ->
   forensic blogs. The forensic blogs carry the second-by-second timelines the wire drops:
   drain duration ("hot wallet emptied in 132 seconds" = signing automation, not manual),
   attacker addresses, consolidation addresses, mixer flows, chaser dust (a competitor
   attacker watching the same wallets = the target is under ACTIVE multi-party pressure).
3. Record root-cause status explicitly. "Suspected private-key compromise, no post-mortem
   published" weeks later = the root cause may still be live, and a hastily rebuilt stack
   ("2.0", relaunch in days) = a fresh, unaudited surface. That combination is the highest-
   priority live-engagement brief.
4. Corporate-blog contradictions are findings: "no breach since <year>" claims vs the record;
   license/footer pages naming TWO different legal entities or license numbers on one site =
   ops-hygiene signals and OSINT leads.
5. Repeat for every sibling brand in the fleet — shared infra means one breach = fleet-wide
   exposure, and the smaller brand's incident write-ups often name the shared backend.

## Regulator-leak archives (operator dossiers, public)

- Curaçao: the Casino Secrets leak (a researcher breached the CGA licensing system;
  filings published as public-interest journalism). Per-operator files at
  `curacaofiles.com/casinos/<license-number>-<entity>` — the license number on the target's
  own site footer is the file key (e.g. OGL/2024/1507/0838 -> file 1507).
- A file page lists applications, domains, related entities, and DOCUMENTS behind a
  download API (`/api/documents/<id>?key=...&name=...`). Pair the listing order with the
  hrefs to map names -> files, then download the priority classes.
- **Document priority order:** P&L/financial statements -> org chart (densest: dozens of
  real names + roles = the personnel map) -> group-structure charts -> M&A / share-purchase
  agreements (the ownership chain) -> signed personnel history disclosures -> AML/data-
  protection policies -> passport scans / bank references (last; PII-minimal handling).
- Extract with `pdftotext <file> -`. Scanned/image PDFs have no text layer = OCR ceiling —
  note "scanned, not read" rather than claiming content. Person-name extraction: regex
  capitalized name pairs, then filter against a corporate-word blacklist (Share, Director,
  Class, Meeting, ...) before calling anything a person.
- Check sibling-license files too: renames/amendments ("X thans Y") link the old and new
  entities = the fleet's corporate history.

## Handling

- Regulator-leak data is published journalism / public interest — accessing it is
  legitimate OSINT. The SCOPE GATE for live probing is unchanged by it: history informs,
  it does not authorize.
- PII minimality: pull the minimum documents needed for the finding; report the CLASSES
  exposed (passports, financials, personnel rosters) with counts, not the personal data
  itself. Keep downloaded PDFs in /tmp scratch, not the workspace or reports.

## Litigation dockets as a code-origin oracle (no-breach case)

When a target has NO breach record, run its corporate entities (from the site footer:
foreign parents + US LLCs + any additional vehicles like payments companies) through
CourtListener RECAP (`storage.courtlistener.com/recap/...` PDFs), Justia Dockets, and
govinfo USCOURTS PDFs. Complaints are technical documents:

- IP/code-misappropriation complaints name the PREDECESSOR codebase and the engineers
  ("used software code belonging to the Partnership to develop <target> for <casino>")
  — that codebase's public audits and brand lineage answer architecture questions the
  live site won't answer unauth (RNG/seed policy, ownership chain, who built what).
- The judge's order rules on which claims survive dismissal — surviving fiduciary /
  misappropriation claims carry the best-supported factual allegations: dev timelines
  ("first assets imported <date> from the predecessor Figma"), domains seized, code
  origin, deposit volumes in user-facing filings.
- Harvest the entity map (extra corporate vehicles), financial scale (deposit figures
  named in complaints), licensing status ("operates without a license"), and adjacent
  litigation (the target named as defendant in laundering/impersonation suits) — all
  public, all report-class.
- `web_search "<entity> lawsuit OR complaint OR docket"` to find the cases, then pull
  the PDFs directly from the PACER mirrors above (free, no account).
