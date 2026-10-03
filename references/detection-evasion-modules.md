# Detection-Evasion Modules — Purple-Team Stealth Validation

For authorized engagements where the objective includes validating detection coverage.
Every module pairs a stealth technique with its likely detection surface so the operator
can confirm whether their tooling catches it. Use only under written scope that explicitly
includes stealth validation.

---

## MODULE 1 — PROCESS & MEMORY TRADECRAFT

**Objective**: validate EDR/AV detection of in-memory techniques.

**Techniques**:
- **In-memory payload delivery**: reflective DLL injection, process hollowing, APCLoad
  on operator lab hosts. Validate: does EDR flag memory anomalies (RWX pages, unbacked
  regions) or only file-system IOCs?
- **Syscall direct invocation**: bypass userland hooks via direct syscalls (Hell's Gate
  class) on Windows lab; `syscall` inline on Linux lab. Validate: does ETW catch the
  syscall pattern or only the API call?
- **AMSI/ETW patching**: patch AMSI or ETW in a lab process, execute known-bad payload.
  Validate: does the EDR still catch the payload via kernel callback or behavioral chain?
- **Process herpaderping**: write payload, map, modify on-disk, execute — validate
  hash-mismatch detection.

**Detection surface to report**: EDR memory scanning, ETW-TI (threat intelligence) events,
kernel callbacks, behavioral chains, AMSI integration.

---

## MODULE 2 — NETWORK TRADECRAFT

**Objective**: validate network detection of C2 and exfiltration channels.

**Techniques**:
- **Domain fronting**: route C2 through CDN with front domain (aws.amazon.com class) and
  custom domain. Validate: does the proxy inspect the Host header or only the SNI?
- **DNS tunneling**: encode data in TXT/NULL queries with low-and-slow timing (1 query/30s).
  Validate: does DNS analytics flag entropy/volume or only known-bad domains?
- **HTTPS beacon jitter**: vary sleep 30–90s, randomize URI paths, mimic browser JA3.
  Validate: does the NDR flag periodicity, JA3 anomalies, or URI entropy?
- **ICMP/SMB exfil**: tunnel data through ICMP echo or SMB named pipes on isolated segments.
  Validate: does the IDS inspect non-HTTP protocols or only port 80/443?
- **Dead-drop resolvers**: store C2 instructions in public paste/gist, poll infrequently.
  Validate: does egress filtering flag paste sites or only known C2 domains?

**Detection surface to report**: NDR flow analytics, JA3/JA3S fingerprinting, DNS analytics,
egress allow-listing, TLS inspection coverage, protocol anomaly detection.

---

## MODULE 3 — LOG & TELEMETRY EVASION

**Objective**: validate SIEM/UEBA detection of anti-forensic techniques.

**Techniques**:
- **Log tampering**: clear Windows event log (wevtutil), truncate Linux auth.log, delete
  SIEM forwarder logs. Validate: does the SIEM alert on log-source silence or only on
  event content?
- **Timestomping**: modify MAC times on payload files to blend with system files.
  Validate: does file-integrity monitoring flag timestamp changes or only content?
- **Artifact wiping**: secure-delete tools, USN journal deletion, prefetch wiping.
  Validate: does the EDR/SIEM correlate deletion events with prior process telemetry?
- **Parent-PID spoofing**: spawn payload under a trusted parent (explorer.exe, svchost).
  Validate: does the EDR validate PPID chains or only the executable hash?

**Detection surface to report**: SIEM log-source heartbeat, file-integrity monitoring,
USN journal analysis, process-tree analytics, UEBA anomaly baselines.

---

## MODULE 4 — CREDENTIAL & IDENTITY TRADECRAFT

**Objective**: validate identity-threat detection of credential attacks.

**Techniques**:
- **Password spraying**: 1 password × N users (not 1 user × N passwords) from a single
  source IP, low-and-slow (1 attempt/min). Validate: does the IdP flag spray patterns or
  only per-user lockouts?
- **Token impersonation**: steal a session token from a lab browser profile, replay from
  different IP/UA. Validate: does the IdP flag token reuse or only credential mismatches?
- **Kerberoasting**: request RC4-encrypted service tickets for SPN accounts, crack offline.
  Validate: does the DC flag encryption-downgrade or only abnormal TGS volume?
- **Pass-the-hash/ticket**: reuse NTLM hash or Kerberos ticket on lab hosts. Validate:
  does the EDR flag hash-reuse patterns or only logon type anomalies?

**Detection surface to report**: IdP risk analytics, DC anomaly detection, Kerberos
encryption policy, token-binding enforcement, UEBA credential-behavior baselines.

---

## MODULE 5 — CLOUD & CONTAINER TRADECRAFT

**Objective**: validate cloud-native detection of lateral movement and privilege escalation.

**Techniques**:
- **Instance-metadata credential theft**: query IMDSv1 on a lab instance, use creds from
  external IP. Validate: does CloudTrail flag credential-use from external IPs or only
  internal API calls?
- **Container escape**: privileged container → host mount → root. Validate: does the
  container runtime flag mount escapes or only process anomalies?
- **Serverless persistence**: modify Lambda env vars, insert CloudWatch event rules.
  Validate: does CloudTrail flag config changes or only API calls?
- **Cross-account role assumption**: assume role in lab account B from account A without
  external ID. Validate: does CloudTrail flag cross-account assumptions or only same-account?
- **Kubernetes lateral movement**: exploit over-permissive RBAC to list secrets in all
  namespaces. Validate: does the K8s audit log flag bulk secret access or only pod exec?

**Detection surface to report**: CloudTrail event selectors, GuardDuty/Security Hub
findings, K8s audit-log analysis, container runtime security, IAM anomaly detection.

---

## MODULE 6 — AI-SPECIFIC EVASION

**Objective**: validate detection of AI-targeted attacks.

**Techniques**:
- **Prompt-injection obfuscation**: encode payloads in base64/rot13/unicode, split across
  turns, embed in markdown images. Validate: does the guardrail inspect decoded content or
  only surface strings?
- **Token-smuggling**: use homoglyphs, zero-width chars, or split tokens to evade keyword
  filters. Validate: does the filter normalize unicode or only ASCII?
- **Model-extraction pacing**: vary query timing and phrasing to avoid rate-limit-based
  extraction detection. Validate: does the API flag semantic similarity across queries or
  only volume?
- **Embedding inversion pacing**: query embeddings with noise, reconstruct via nearest-
  neighbor. Validate: does the system flag embedding-anomaly patterns or only direct text?

**Detection surface to report**: Guardrail/normalization coverage, semantic-similarity
analytics, API-abuse detection, embedding-anomaly baselines.

---

## USAGE RULES

- Every module requires explicit stealth-validation scope in the authorization document.
- Each technique is run once, logged with timestamp, and reverted immediately after
  validation.
- The output is a detection-gap report: technique → expected detection → observed
  detection → proposed analytic (Sigma/KNQL/CloudWatch rule).
- No module is used against production users or data — lab tenants, test accounts, and
  scoped resources only.
