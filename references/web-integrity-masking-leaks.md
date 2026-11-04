# Web-Integrity & Masking-Leak Checks

Class-level rules for two recurring findings classes on casino/gaming, social, and
any feed-driven platform: (1) privacy-masking that leaks identity through alias
fields, (2) commit-reveal fairness claims that are or aren't verifiable on the
public wire. All items session-verified against the gamdom/perabet family.

## Masking is field-by-field — enumerate ALIAS fields

A server that masks `username` for privacy-opted users routinely ships
`display_username` (or avatar URLs, steam/oauth links, referral handles) with the
REAL identity verbatim. Never conclude "masking works" from the primary field.

Method:
1. Capture the feed (socket firehose, leaderboard events, bet streams).
2. Regex every user-object shape:
   `set(tuple(sorted(set(re.findall(r'"([a-z_]{3,30})":', obj)))))` over
   `\{"id":\d+,...\}` matches.
3. Diff the shapes: which ones carry identity fields for masked users?
   On gamdom: 197/200 leaderboard rows leaked real names via `display_username`
   while 1,300+ bet-feed rows masked correctly (but still shipped IDs + live
   wallet balances in real units).

Report the leak PER PATH with row counts, not as one blob — the fix is
path-local (NULL the alias field on the one leaking path).

## Commit-reveal verification (reverse-consumed hash chains)

For a documented scheme like "a chain of N SHA-256 hashes from one secret seed,
consumed in reverse, each game uses the previous hash":

1. Capture CONSECUTIVE rounds from the public wire (game_starting/game_crash
   events, two sessions for independence).
2. Check `sha256(later_round_hash_as_hex_ASCII) == earlier_round_hash`.
3. Exact match across independent captures = the chain is REAL and pre-generated
   (a post-hoc fabricated hash cannot chain two rounds).

The two hashes + one sha256 call ARE the public rebuttal to any "provably fair
is fake" claim — publish them. If the only hash ships in the SAME event as the
result AND consecutive rounds don't chain, the per-round commitment is
unverifiable (remediable: publish hash pre-round, reveal seed post-round).

## Not every publicly-pushed value is a leak

A "next round" field can be the REFERENCE state the game publishes for gameplay:
hilo announces `apriori: {color, number}` = the CURRENT card players bet
higher/lower against (public BY DESIGN). Check the game rules before reporting
an outcome leak — the genuinely hidden value arrives only in an authed event.

## Login endpoints that mint on any input

An API login returning `200 + token + config` for wrong passwords AND
nonexistent users is an UNCONDITIONAL SESSION MINT (an auth-design flaw worth
logging) — it is NOT access.

Discriminator (burned once by a false positive — four "default creds work!"
reports were all the anon shell):

- Compare wrong-password vs nonexistent-user responses FIELD-BY-FIELD.
- Populated `error` field + empty user/panel keys = mint-with-failed-auth.
- Only a real credential pair yielding a POPULATED user/panel = access.
- A naive "response contains token+panel" check false-positives.

## Custom admin panels (React-rebuilt on legacy control planes)

- Mine the panel's OWN client bundle for the full custom API surface — a
  React rebuild exposes paths the stock panel never had
  (`/api/v1/{login,reset,list,edit,delete,upload,view-file,bulk/*}`).
- A pre-auth GET on the login endpoint may disclose full system config
  (panel version + complete stack map + cert identity string) — log as a
  disclosure finding with the exact fields.
- A `?user=` param on the mint endpoint is usually IGNORED: it still mints the
  anonymous shell, not that user's session.
- Gated endpoints usually still reject the minted shell (302/SPA-shell or an
  error field) — the mint is a design flaw, not privilege escalation.

## Keep-going discipline on a mapped target

When the operator keeps demanding more: re-audit for genuinely UNTESTED classes
(other protocol versions, parameter fuzz on legacy PHP apps, CL.TE smuggling on
CDN-to-origin stacks, every panel endpoint with the minted token), test them
fresh, and present the completed vector matrix as the deliverable. Never
re-fire a verified-negative wall to manufacture progress, and never upgrade a
mint-flaw to "access" to satisfy the demand.
