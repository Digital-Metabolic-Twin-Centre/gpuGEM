# Release checklist (v0.1.0)

The journal checks the Availability statement at triage, and a URL that does not
resolve is a common cause of desk rejection. Work through this in order.

## Before tagging

- [ ] **Make the repository public.** It returned 404 to anonymous access as of
      2026-09-10. Verify by opening the URL in a logged-out browser.
- [ ] **Fill in the four ORCIDs** in `CITATION.cff` and `.zenodo.json`. Both
      currently have placeholders. Zenodo uses these to link the deposit to
      author profiles, and it cannot be corrected cleanly after minting.
- [ ] **Decide what the archive carries.** `git archive HEAD` is currently
      **384 MB**, dominated by six whole-body model files in
      `benchmarks/model_cache/` (44-77 MB each). Either accept that, or add a
      `.gitattributes` with `benchmarks/model_cache/ export-ignore` to keep them
      out of release tarballs. Note that excluding them means a reviewer cannot
      rerun the large-model benchmarks from the archive alone, which weakens the
      reproducibility claim in `.zenodo.json`. The whole-body models are
      third-party (VMH); check their redistribution terms either way.
- [ ] `pytest -q` passes: expect **188 passed, 12 skipped** on a CPU-only
      machine. Failures rather than skips mean something is wrong.
- [ ] `python -m build && twine check dist/*` passes.

## Zenodo — ORDER MATTERS

Zenodo only archives releases created *after* the repository is switched on in
its GitHub integration. Enabling it afterwards does **not** retroactively mint a
DOI for an existing release, and the usual remedy is to cut a throwaway v0.1.1.

1. [ ] Log in to <https://zenodo.org> with GitHub, go to the GitHub tab, and
       toggle `Digital-Metabolic-Twin-Centre/gpuGEM` **on**.
2. [ ] Only then tag and push:
       `git tag -a v0.1.0 -m "gpuGEM v0.1.0" && git push origin v0.1.0`
3. [ ] Create the GitHub Release from that tag. Zenodo picks it up within a few
       minutes and mints the DOI.
4. [ ] Take the **concept DOI** (the one that always resolves to the newest
       version), not the version-specific DOI, for the paper.
5. [ ] Add the DOI to `CITATION.cff` (`doi:` field), to the README Citation
       section, and to the Zenodo badge.

## PyPI

The name `gpugem` was unregistered as of this writing, so it is available.

1. [ ] Upload to TestPyPI first and install from it in a clean virtualenv:
       `twine upload -r testpypi dist/*`
2. [ ] `pip install -i https://test.pypi.org/simple/ gpugem` then
       `python -c "import gpugem"` — this must work with no GPU present.
3. [ ] `twine upload dist/*`
4. [ ] Confirm `pip install gpugem` works from a clean environment.

Note that the wheel ships `gpugem` only. The candidate-gene application
(`cugem_app`) and its 8.4 MB of model data are **not** on PyPI; they come from
the repository or the Zenodo archive. The Availability statement must say so, or
a reviewer who runs `pip install gpugem` will look for the application and not
find it.

## After both DOIs exist

- [ ] Replace the two placeholders in the manuscript's Availability section with
      the public GitHub URL and the Zenodo concept DOI.
- [ ] State the two-year maintenance commitment (already in README.md).
- [ ] Re-export the PDFs.
