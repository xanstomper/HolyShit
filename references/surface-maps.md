# HOLYSHIT — Surface Maps (asset class × recon action × canon × handoff)

The finder's checklist generator (`surface --domain D`) is driven by these tables.
Every confirmed box hands off — the family consumes everything the finder proves.

| Asset class | Enumerate (read-only) | Action class | Canon | Handoff to |
|---|---|---|---|---|
| **web** | subdomains, live hosts, stacks, bundles | CT sweep → passive enum → fingerprint → bundle mine | vector-matrix.md · case files (era-stack) | undercroft (logic seams) · 3am (sweep targets) |
| **api** | dev portals, OpenAPI/GraphQL history, authz ids | schema mining → authz matrix plan → legacy route sweep | arsenal/recipe canon (IDOR/coercion) | undercroft (value-flow seams) |
| **mail** | SPF/DKIM/DMARC records, oauth mail grants | record audit → grant surface → relay canon | case lore (spoofing/relay) | 3am (header/parser classes) |
| **dns** | zones, NS/registrar, DNSSEC | passive DNS → AXFR attempt → hygiene check | detection-evasion-modules.md (resolution discipline) | holyshit recon (feeds everything) |
| **cloud** | bucket names, IAM/OIDC footprint, snapshots | naming sweep → provider footprint → exposure checks | vector-matrix (family 13) | kairo (config/keys = synthesis material) |
| **repos** | org/repo inventory, commits, CI | identity leak scan → secret-class scan → workflow surface | case canon (source-plane) | kairo (SRC vectors) · shukaku (SRC crown) |
| **identity** | OIDC well-known, SSO chains, breach OSINT | IdP discovery → token-chain map → breach context | arsenal-04 (auth/identity) | 3am (AUTHBYPASS sweep) |
| **social** | handles, staff, oauth grants, helpdesk | staff mapping → grant audit → trust-flow recon | operational-playbooks.md | holyshit handoff (more recon) |
| **devices** | firmware portals, OTA channels, panels, certs | portal mining → OTA discovery → fingerprint → CA chain | case files (hardware families) | kairo (the metal domain) |

## The pivot table (confirmed seam → canon → next)

`pivot --target T` reads the family states (undercroft CONFIRMED seams, 3AM
chains) and matches them against the case canon by keyword score:

- CONFIRMED undercroft surface → which case file has this seam class → crown-class
  guess (PII/FIN/CRED/BACKUP/SRC/SASS) → `shukaku ingest`.
- CONFIRMED undercroft logic → value-flow recipes → `kairo compile` → 3AM promote.
- 3AM chains → takeover batteries → shukaku prices what the chain reaches.

## Handoff formats (what the finder emits)

- `--to undercroft` — findings registered as PROBED logic seams (the descent's map).
- `--to 3am` — (flaw 11, seam A) observable-oracle rows: finder-confirmed leads
  the sweep verifies.
- `--to shukaku` — findings ingested into the harvest register WITH crown-class
  suggestions, derived from the family's CONFIRMED states when `--findings` is
  omitted. The harvester reasons/hunts from there.
