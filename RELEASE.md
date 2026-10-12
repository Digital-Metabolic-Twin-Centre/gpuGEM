# Release checklist (v0.1.0)

The journal checks the Availability statement at triage, and a URL that does not
resolve is a common cause of desk rejection. Work through this in order.

## Before tagging

- [x] **Make the repository public.** Done: the URL returns HTTP 200 to an anonymous
      request (checked 2026-10-12; it returned 404 on 2026-09-10).
- [ ] *(Recommended, not required)* **Add the four ORCIDs** to `CITATION.cff`
      and `.zenodo.json`; both currently have placeholders. ORCIDs are optional
      Zenodo metadata, and the deposit will mint a DOI without them. They are
      worth adding because they link the record to author profiles, but they do
      not block the release: on Zenodo the *files* of a published record are
      immutable, while the *metadata* stays editable with the DOI unchanged, so
      ORCIDs can be filled in afterwards without cutting a new version.

      The journal is a separate matter and is not handled in these files.
      Oxford University Press requires the submitting/corresponding author to
      supply an ORCID iD at submission, and encourages but does not require it
      for co-authors. That is entered in the submission system, not here.
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

The name `gpugem` was unregistered as of 2026-10-12 (`pypi.org/pypi/gpugem/json` returned 404), so it is available.

1. [ ] Upload to TestPyPI first and install from it in a clean virtualenv:
       `twine upload -r testpypi dist/*`
2. [ ] `pip install -i https://test.pypi.org/simple/ gpugem` then
       `python -c "import gpugem"` — this must work with no GPU present.
3. [ ] `twine upload dist/*`
4. [ ] Confirm `pip install gpugem` works from a clean environment.

Note that the wheel ships `gpugem` only. The candidate-gene application
(`gpugem_app`) and its 8.4 MB of model data are **not** on PyPI; they come from
the repository or the Zenodo archive. The Availability statement must say so, or
a reviewer who runs `pip install gpugem` will look for the application and not
find it.

## After both DOIs exist

- [ ] Replace the two placeholders in the manuscript's Availability section with
      the public GitHub URL and the Zenodo concept DOI.
- [ ] State the two-year maintenance commitment (already in README.md).
- [ ] Re-export the PDFs.
