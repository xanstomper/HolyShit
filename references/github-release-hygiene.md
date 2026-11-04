# GitHub Release Hygiene — Session-Pitfall Reference

Condensed from the 2026-10-03 holyshit-mode public release. Add to any skill that ships
code to GitHub.

## The `.pyc` Leak

`git add -A` silently commits `__pycache__/*.pyc` after any local run. The first release
of holyshit-mode shipped a `.pyc` before `.gitignore` existed; it was caught only because
`git ls-files` was manually checked post-push.

**Rule:** create `.gitignore` with `__pycache__/` + `*.pyc` BEFORE the first `git commit`.
If already committed: `git rm -r --cached scripts/__pycache__` then commit + push.

## CI Regression Gates

Manual "did I truncate the file?" checks don't scale. The verify.yml workflow runs on
every push:

```yaml
- name: Validate README line counts
  run: |
    MANDATE_LINES=$(wc -l < references/mandate.txt)
    MATRIX_CLASSES=$(grep -c "^- " references/vector-matrix.md)
    if [ "$MANDATE_LINES" -lt 100 ]; then exit 1; fi
    if [ "$MATRIX_CLASSES" -lt 100 ]; then exit 1; fi
```

Any accidental truncation of a large reference file fails CI before the operator notices.

## Secret Scan in CI

The workflow greps for `sk-[a-z0-9]{20,}`, `gho_[a-z0-9]{20,}`, `api_key = '<20+ chars>'`,
`Bearer <20+ chars>` on every push. Exclusions: `.env.example` (placeholder values only)
and env-var NAMES like `HOLYSHIT_API_KEY` (no value).

**Rule:** never put real key material in any repo file, even "temporarily". CI catches it.

## Post-Push Verification Checklist

1. `git ls-files | sort` — confirm no `.pyc`, `.env`, or unexpected files
2. `curl https://raw.githubusercontent.com/<org>/<repo>/main/README.md | head -5` —
   confirm README renders on the default branch
3. `gh api repos/<org>/<repo>/actions/runs?per_page=1` — confirm latest run conclusion=success
4. Leak scan: `grep -rniE "sk-[a-z0-9]{20,}|gho_[a-z0-9]{20,}|bearer [a-z0-9]{20,}" .`
   (excluding `.env.example` and env-var names)

## Engagement-Artifact Sweep (the `git add -A` publication trap)

`git add -A` in a repo with untracked engagement dirs (logs/, reports/, captures/) commits
and PUBLISHES them to the public mirror — an engagement report and a 10k-line watch log
landed in the HolyShit repo this way and had to be unpublished.

**Rule:** before any `git add -A`, run `git status --porcelain` and stage explicit paths
(scripts/, references/). `.gitignore` must carry `logs/`, `reports/`, `captures/`,
`__pycache__/`, `*.pyc` from day one.

**Unpublish ≠ purge:** `git rm --cached` + commit removes files from HEAD but they remain
in history — anyone can checkout the old commit. Full removal needs a force-push history
rewrite (operator's call; state it plainly when it happens).
