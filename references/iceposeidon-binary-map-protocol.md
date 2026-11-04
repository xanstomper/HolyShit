# iceposeidon.com public-map-ws binary protocol (reversed 2026-10-21)

Source: minified decoder in `cx-client.zJQN-0cw.js` (functions `Gr` header parse, `Wd` kind-8, kind-1/3 branch in the main dispatch). Minified names change per build — re-locate by grepping `getFloat64` / `Invalid binary frame length` / `Invalid zombie flags` error strings, which are stable.

## Shared 36-byte header (all kinds)
| off | type | field |
|-----|------|-------|
| 0 | u8 | kind (1..8) |
| 1 | u8 | version = 1 |
| 2 | u16 LE | flags: 1=full, 1|2=clear, 4=sparse |
| 4 | u32 | generation (>0) |
| 8 | u32 | sequence (>0) |
| 12 | f64 | eventRevision |
| 20 | f64 | sampledAt (epoch ms, must be multiple of 100) |
| 28 | u16 | partIndex |
| 30 | u16 | partCount (1..256) |
| 32 | u16 | recordCount |
| 34 | u16 | reserved (must be 0) |

Sparse/clear semantics: sparse = patch upserts (recordCount>0), clear = empty replacement (recordCount=0, len==36).

## Global constants
`bt=36` header size; `$r=1e7` generic coord grid; `Re=1e5` contestant-fix coord scale; coord validation `X(v,isLat,scale)` = v/scale, abs<=90 lat / 180 lng. Health status enum `Yi = [disabled, paused, inside, outside, unavailable, eliminated]`.

## Kind 1 — contestant location fixes (record size 11)
Layout after header (offsets are absolute, `o=36`, `l=recordCount`):
- `o+0` u32 definitionSequence (>0)
- `o+4` f64 ageBaseMs (epoch ms, grid of 100)
- `o+12` i32 latBase (scale 1e5, i.e. value/1e5 = degrees)
- `o+16` i32 lngBase (scale 1e5)
- `o+20` per-record i16 latDelta  (lat = (latBase + delta)/1e5)
- `o+20+l*2` per-record i16 lngDelta
- `o+20+l*4` per-record u16 slot
- `o+20+l*6` per-record u8 flags (bit1 = mock, bit2 = has age)
- `o+20+l*8` per-record u16 accuracyM (divide by 10 → meters)
- `o+20+l*10` per-record u16 ageSecondsAgo (at = ageBaseMs − v*100)

Example decode: header `01 01 01 00 ...`, latBase=3025493 lngBase=-9773031 → contestants slots 21/27/67 at lat 30.25479–30.25508, lng -97.73009…-97.73053.

## Kind 3 — object positions (record size 20)
`o+0` u32 definitionSequence; `o+4` i32 latBase, `o+8` i32 lngBase (scale 1e5); then `o+12` l× i16 latDelta, then l× i16 lngDelta, then l× 16-byte UUID (lowercased id).

## Kind 2 — contestant status (record size 28, `qi=12, Sd=28`)
- `o+0` u32 definitionSequence, `o+4` f64 timeBase (ms grid 100)
- Per record: `M=o+12`: u16 slot (z*2), u8 statusFlags (z at M+l*2; bit6+ reserved, `Id`=self bit etc.), u8 status badges (bitfield over `yd`), u8 healthStatus (index into Yi), u8 hp, u8 maxHp (max `Gi`), then optional i32 fields gated by statusFlags bits — offsets `M+l*8, l*12, l*16, l*20, l*24` (z*4 stride): poison started/ends, droneLandsAt, outsideSince, nextDamageAt — each `timeBase + v*100` ms.

## Kind 4 — variable-length records (`en`-byte records, type table `Zd`)
`recordCount` from header; each record: first byte indexes table `Zd`, followed by typed fields via `Zd[r.getUint8(...)]` descriptor. (Not fully enumerated — event was quiet.)

## Kind 7 — zombies (record size 37: `Ki=16` UUID, `Nd=37`)
- `o+0` u32 rosterSequence, `o+4` u32 slotsSequence, `o+8` f64 timeBase
- Per record: 16-byte UUID id, u16 ownerSlot, i32 expiresAtDelta (timeBase + v*100, gated by flag bit `$d`), f32 speedMps (gated `Wi`), u8 flags (top 3 bits reserved must be 0; `Ld`=guard), f32 leechIntervalSeconds, f32 leechRadiusM, u16 leechAmount.
- Roster ids must be strictly sorted (`Qu(a,b)<0`).

## Kind 8 — zombie leech schedule (`Pd=20, Dd=9, Ud=6`)
- `o+0` u32 rosterSequence, `o+4` f64 timeBase, `o+12` i32 latBase, `o+16` i32 lngBase (scale 1e5)
- l× u8 count + l× u16 index; per zombie: u16 slot, i16 latDelta, i16 lngDelta, u16 targetSlot, then count× {u16 leechSlot, i32 nextHitAtDelta*100ms}.

## Practical notes
- Quiet event = one full snapshot per kind at connect, then heartbeat + JSON patches only. Don't conclude "no fixes stream" from a short idle window.
- Text frames (op=1) JSON types: heartbeat, event, map_objects, map_objects_patch, contestants, game_items, tracked_devices.
- Handshake (stdlib, no deps): GET /public-map-ws with Origin + Sec-WebSocket-Key/Version; read frames manually (2-byte hdr; op=1 text, op=2 binary; extended lengths 126/127).
