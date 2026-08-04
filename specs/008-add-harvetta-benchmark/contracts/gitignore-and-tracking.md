# Contract: `.gitignore` change and file tracking

## Before

```gitignore
.claude/settings.local.json
__pycache__/
*.pyc
benchmarks/model_cache/*.mat
```

## After

```gitignore
.claude/settings.local.json
__pycache__/
*.pyc
benchmarks/model_cache/*_lifted.mat
```

## Files newly committed by this feature

```
benchmarks/model_cache/Harvetta_1_03d.mat     (13.9 MB)
benchmarks/model_cache/mWBM_S9_male.mat       (72.4 MB)
benchmarks/model_cache/mWBM_S15_male.mat      (70.6 MB)
benchmarks/model_cache/mWBM_S23_male.mat      (65.4 MB)
benchmarks/model_cache/mWBM_S83_male.mat      (76.7 MB)
```

Total: ≈ 299 MB added to repository history. This is a one-way operation for anyone who has
already cloned before this change lands (their next `git pull`/`fetch` downloads this history);
removing it later cleanly requires a history rewrite (`git filter-repo`/BFG), not a plain revert.

## Files that remain untracked (research R3)

```
benchmarks/model_cache/mWBM_S9_male_lifted.mat    (89.2 MB)
benchmarks/model_cache/mWBM_S15_male_lifted.mat   (87.1 MB)
benchmarks/model_cache/mWBM_S23_male_lifted.mat   (80.9 MB)
benchmarks/model_cache/mWBM_S83_male_lifted.mat   (94.6 MB)
```

Not referenced by any `REGISTRY` entry; excluded by the narrowed `*_lifted.mat` pattern rather than
committed. If a future feature registers a lifted-variant model, that feature updates
`.gitignore` (or adds an explicit exception) at the same time it adds the `REGISTRY` entry —
consistent with this feature's own invariant (data-model.md: every file `REGISTRY` references is
tracked).

## Verification

```bash
git check-ignore benchmarks/model_cache/mWBM_S9_male_lifted.mat   # still ignored -> exits 0
git check-ignore benchmarks/model_cache/mWBM_S9_male.mat          # no longer ignored -> exits 1
git ls-files benchmarks/model_cache/ | wc -l                      # 7 -> 2 XML + 5 plain .mat
```
