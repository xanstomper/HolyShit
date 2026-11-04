# Operator-Infra Access Recovery — "find my host/VM" recipe (session-verified 2026-10-23)

Task class: operator lost/forgot how to reach their OWN server (LAN device, cloud VPS, VM)
and gives only a name ("the oracle vm named poop"). Never ask the operator for the IP first —
mine local artifacts, they almost always contain it.

## Ladder (worked end-to-end in one session)

1. **Orient on this box:** `hostname -I`, `ip route`, `systemd-detect-virt`, `free -h` —
   establish what the CURRENT machine is so the target isn't self.
2. **LAN sweep if the target is LAN-side:** `nmap -T4 --open -p <common ports> <subnet>/24`,
   then full `-p-` only on candidates. Triage hosts by fingerprinting ports (rokudev digest
   realm = Roku, AirTunes = AirPlay, noVNC/websockify = KVM console, minecraft = game box).
   Don't chase consumer appliances — they're not the target.
3. **Check the target isn't a VM ON the current host:** `ps aux | grep -E "qemu|kvm|virtualbox"`,
   `virsh list`, `lxc-ls`, `docker ps`, listening noVNC ports (5900/6080 websockify).
4. **Mine local credential/SSH artifacts (the high-yield step):**
   - `ls ~/.ssh/` — keys + `known_hosts`; also `ls ~/Downloads/*.key` (Oracle console-downloaded
     keys land there: `ssh-key-YYYY-MM-DD.key`), `chmod 600` before use.
   - `grep -rn "opc@\|ubuntu@\|ssh -i" ~/.hermes/skills/ ~/<deploy-dirs>/` — prior-session skill
     reference files and deploy scripts routinely contain the exact `ssh -i KEY user@IP` line.
     On 2026-10-23 the host+IP+key for the Oracle VPS came from
     `skills/software-development/zynema-maintenance/references/providers-adblock-plugins.md`.
   - Shell history, `~/.oci/config`, `~/.hermes/.env`.
5. **Verify by firing the found command once:** `ssh -i KEY -o BatchMode=yes user@IP 'hostname; free -h'`.
   Match the operator's hint (hostname "poop", 15Gi RAM) before declaring success.

## Pitfalls
- Oracle cloud images use `opc@`, not `ubuntu@` (ubuntu@ = Permission denied).
- A blanket `grep opc@ ~/ -r` is slow and noisy; scope to skills/, deploy scripts, and dotfiles
  first — they're dense and small.
- Don't full 65535-port sweep a whole /24; shortlist via common-port sweep, then deep-scan
  individual candidates only. Long scans risk the operator interrupting them.
