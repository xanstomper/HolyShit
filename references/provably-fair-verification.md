# Provably-Fair Verification (gambling / game-integrity targets)

Auditing an operator's "provably fair" claims from OUTSIDE (no session). Two modes:
breach-context (the extortion threatens to leak PF evidence — test it first and you
hold the rebuttal) and routine game-integrity audit. The core rule: **the operator's
own PF documentation is the test spec** — whatever scheme they publish (blog, help
center) must be verifiable on the public wire, and a commitment that first appears
WITH the result proves nothing.

## 1. Mine the operator's documented scheme first

Search their blog/help-center for the PF explainer. Extract: seed model (server/client
seed, nonce), commitment pattern (commit-and-reveal, hash chain), consumption order
(forward chain vs reverse chain), and the published anchor ("final hash published before
play"). This defines exactly what the public wire must show for the claim to hold.

## 2. Capture the live game feed unauth

- Find the game's websocket namespace (socket.io `/crash`, `/dice`, ... — see
  references/websocket-auth-testing.md for namespace discovery and rejection semantics).
- Listen ≥ full round cycles (~20-40s each; a 10s window catches only ticks).
- Record EVERY event + payload. socket.io events may split across engine.io frames —
  buffer raw bytes for the window and parse with a frame state machine; naive
  per-recv JSON parses fail at ~4KB TCP boundaries and produce phantom truncations.

## 3. Precommit-timeline check (the structural finding)

Inventory the pre-round event payloads (`game_starting`, `game_started`, ...). ZERO
hash/seed/commitment fields pre-round = nothing publicly binds the outcome before bets
close. Phrase it precisely: "not verifiable on any publicly-checkable channel" — the
burden of proof inverts to the operator (they claimed PF; the public wire can't show
it). A hash delivered in the SAME event as the outcome is unfalsifiable by construction.

**Semantics check before scoring any pre-round value as a commitment:** verify what the
value MEANS in the game rules, not just that it appears pre-round. Some pre-round values
are the game's public STATE by design — hilo publishes the current reference card
(`apriori {color, number}`) so players can bet higher/lower AGAINST it; calling that an
outcome pre-commit manufactures a fake finding (and the correction later undermines the
whole report). Only a value that binds the OUTCOME (seed/hash/randomness consumed by the
result) counts. Read the game's rules chunk or the operator's PF explainer before rating.

## 4. Chain verification (the decisive test)

For consecutive captured rounds, test the documented chain property:

```python
import hashlib
# reverse-consumption chain (hash N+1 hashes down to hash N):
hashlib.sha256(later_hash.encode()).hexdigest() == earlier_hash   # ascii-encoded
# also test bytes.fromhex encoding and the forward direction
```

- **Verified chain (across ≥3 links / 2 sessions)** = the commitment system is REAL:
  log as a negative (hardening), and hand the operator the rebuttal package — two
  consecutive public hashes + one sha256 call = live verification anyone can reproduce
  in 30 seconds. This blunts a PF-fraud extortion narrative.
- **Chain DIRECTION is the exploit gate, not link validity.** After links verify, test which
  way: `sha256(seed[N]) == seed[N+1]` = FORWARD chain = the BREAK (every reveal computes
  every future seed — the prediction Holy Shit); `sha256(seed[N+1]) == seed[N]` = REVERSE
  chain = SAFE (future seeds are preimages, underivable). State the direction in the
  ledger; a 99/99-reverse crash feed is verified-hardened, not "unverified".
- **Unverified or absent chain** = the finding; score as game-integrity (reputation +
  regulatory exposure), not a web vuln.
- **Commit-and-reveal variant (drand-seeded):** some operators publish the commitment in a
  dedicated PRE-round event (duel-family crash: `crash_hashed_pf`) and reveal `server_seed`
  + `drand_randomness` POST-crash in another (`pending_drand`). Verify
  `sha256(bytes.fromhex(server_seed)) == server_seed_hashed` — hash the HEX-DECODED bytes;
  sha256 over the utf-8 string false-mismatches and manufactures a fake "provably fair is
  fake" verdict. The drand cross-check against the public beacon (api.drand.sh,
  drand.cloudflare.com) is frequently network-blocked (403) from probe environments —
  verify the commitment layer and state EXACTLY which layers stayed unverified (derivation
  formula, beacon) rather than claiming full verification.

## 5. Forced-outcome capability

Watch result events for `forced` / manual-control flags. The flag existing in the
PUBLIC event schema = a staff-side outcome-control surface is a system feature (the
chain would not cover a forced round — that is the escape hatch). All-false captures
= capability present, use unproven; a `forced:true` round in anyone's evidence = the
control in use. Either way this is the caveat that must ride the rebuttal package.

## 6. Outcome-derivation test

Apply the standard hash→multiplier formula (bustabit-style: first 52 bits of the hash
→ house-edge curve) to captured rounds and compare to observed crash points. Mismatch
= the operator uses their own curve — locate it in the client math chunk (grep the
pooled bundle for the game's math/config module). Not a finding alone, but full public
verification requires the exact derivation to be documented.

## 7. The same feed leaks privacy-opted users

Game feeds commonly ship hidden_mode users with the name masked but the internal
userId, xp, and per-play walletInfo INTACT — including the live balance draining bet by
bet (real units, e.g. SOL_LAMPORT). That is real-time financial surveillance of
privacy-opted users by anyone with a websocket; it is usually the third leak path after
the lobby firehose (leaderboards/bigwins) and game-detail rows. Fix to state: strip
id/xp/balance server-side on every feed path when hidden_mode is set — never rely on
UI masking.

## Round-based observables + the idle-game blocker

- Round-history/state feeds are often UNAUTH even when betting is session-gated:
  `/ws/games/<game>/history` (round id + ticket + participants), `/ws/games/<game>/state`
  (live round incl. other players' open bets), `/ws/games/<game>/seeds` (period seeds).
  These are the observable source for the derivation test — no session needed.
- **Seed-period model:** daily/global seed periods with `startRound` boundaries (roulette
  pattern). Verify every closed period `sha256(serverSeed)==serverSeedHash`, then run the
  direction test across periods.
- **Idle-game blocker:** rounds with `participants==0` never draw a ticket — an idle game
  yields zero observable outcomes and blocks the derivation test no matter the pagination.
  Check `participants>0` in the captured window BEFORE planning the test; if the game is
  idle, wait for played rounds or state the test is blocked on observables.
- **Live-period display bug (never score as a leak):** the ACTIVE period's seed record often
  carries the commitment hash in the `serverSeed` field (`serverSeed == serverSeedHash`).
  Hash ≠ preimage — nothing is derivable. Real impact: player-side verification of the
  active period fails → false-rigging dispute fodder. Report as a verification-flow bug:
  the seed field must be null until the period closes.

## Deliverable shape (breach-context)

- The rebuttal package: documented scheme + captured chain + the one-line reproduction
  anyone can run.
- The honest caveats: forced-path capability, own-curve derivation, any authed-UI-only
  channel (state it as the single session-gated test left).
- The privacy leak trio + the fix rule, so the next breach narrative loses its legs.

## Claim-triangulation vs extortion narratives

Separate an extorter's WIRE-TESTABLE claims (PF structure, outcome timing, hash chain)
from CREDENTIAL-HELD claims (DB reads, "predicted outcomes before finish" — which their
own wording may attribute to staff/DB read access). Test the wire claims live and publish
the reproducible result; attribute the rest to the already-documented credential
compromise. An extorter's headline claim that FAILS to reproduce publicly is still their
primer for the next drop — the rebuttal package (two consecutive hashes + one sha256
call, plus the honest caveats: forced-path capability, own-curve derivation, authed-UI
channel) is the deliverable that blunts it before publication.

## Pack-opening / mystery-box class: the fixed-seed documentation tell

For case-opener / pack sites, the operator's OWN fairness page is the spec AND the
first exploit lead. Mine it for the VERBATIM algorithm (they publish it: ticket =
`(int(sha512(f"{clientSeed}:{serverSeed}:{nonce}"), 16) % 1_000_000) + 1`) and for
mechanic wording that reveals the seed-rotation policy:

- A nonce described as "auto-incrementing… to provide a unique random result when
  server seeds and client seeds remain unchanged, as is the case when opening multiple
  packs in a single purchase" = seeds do NOT rotate — the nonce exists because the
  seed is stable. Combined with an account-level commitment ("our server seed hash
  before purchase, found in your account profile. After your purchase, we expose the
  unhashed server seed"), the architecture is fixed-seed-per-account: after ONE reveal,
  every future ticket is computable before paying (player controls clientSeed and the
  nonce increments) → open only tickets whose public range EV > price = guaranteed-win
  grind against the house. That wording is the finding's first half — it upgrades the
  hypothesis before any account exists.
- **Minimum decisive test (2 opens, cheapest packs, operator account):** record the
  profile server-seed hash BEFORE purchase 1 (H0), then revealed seed S1 + client seed
  + nonce after open 1; hash check `sha512(S1) == H0` (commitment discipline); record
  profile hash H1 before purchase 2 and revealed S2. `S2 == S1` = CONFIRMED
  predictable-outcome grind (build the verifier from their published function and the
  public per-item ticket ranges — grid the +EV nonces). `S2 != S1` = rotating, clean.
  Ship this as a ready-to-run verify script (`ticket` / `commit-check` / `grind` CLIs).
- The DEMO button on such sites is usually inert for guests (multiple click
  sequences, zero state change, zero network) — do not burn rounds on it; the account
  test is the gate. If it does call a server action, running it unauth is the free
  version of the same test.
- **House edge is computable unauth** from the public odds table: EV = Σ(pct × price)
  vs pack price (a 13% edge was confirmed on one target; "odds tightened after update"
  complaints corroborate the direction). Quantify it — it is both a finding and the
  EV baseline that the grind exploit flips.
