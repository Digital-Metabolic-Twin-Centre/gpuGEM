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
      reproducibility claim in `.zenodo.json`. Harvey and Harvetta are
      published VMH models and the BiGG models carry BiGG's terms; PMM1 to PMM6 are
      internal to the Digital Metabolic Twin Centre. See
      `benchmarks/model_cache/PROVENANCE.md`. A licence for PMM1 to PMM6 is still to be chosen.
- [ ] `pytest -q` passes: expect **206 passed, 10 skipped** on a CPU-only
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

1. [x] Uploaded v0.1.2 to TestPyPI (2026-10-14) and installed from it in a clean virtualenv:
       `twine upload -r testpypi <dir>/*`
2. [x] `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gpugem`
       then `python -c "import gpugem"` -- works with no GPU present. On an RTX A4500 the TestPyPI
       build passed the test suite and solved 7 models (see
       `specs/016-missing-dependency-errors/gpu-verification.md`).
3. [x] Uploaded to PyPI (2026-10-14): <https://pypi.org/project/gpugem/0.1.2/>. The two files'
       SHA-256 digests on PyPI match the tested files.
4. [x] `pip install gpugem` confirmed from a clean environment on a CPU-only machine (import works,
       `solve` raises `DependencyError` kind `no_gpu`) and on the GPU machine (smoke test, e_coli_core,
       iML1515 all Optimal, objectives within 2e-8 of the Gurobi reference).

### Automated publishing (from the next release)

`.github/workflows/publish.yml` uploads to PyPI when a GitHub release is **published**.
It checks that the tag matches the version in `pyproject.toml`, `gpugem/__init__.py`,
`CITATION.cff` and `.zenodo.json`, runs lint and the tests, builds and checks the files,
and then **waits for a reviewer to approve** before uploading. Pre-releases never publish.
There is no API token: PyPI trusts the workflow itself (Trusted Publishing).

One-time setup (nothing publishes until both are done):

1. [ ] PyPI: open <https://pypi.org/manage/project/gpugem/settings/publishing/> and add a
       GitHub trusted publisher: owner `Digital-Metabolic-Twin-Centre`, repository `gpuGEM`,
       workflow `publish.yml`, environment `pypi`.
2. [ ] GitHub: repo Settings -> Environments -> New environment `pypi` -> tick
       "Required reviewers" and add the reviewers.

Per release:

1. Bump the version in all four files (the workflow refuses a mismatch), commit and push.
2. Wait for CI to pass, then create the tag and publish the GitHub release (this also
   triggers Zenodo).
3. In the Actions tab, open the "Publish to PyPI" run, check the files and checksums in
   its summary, and click "Review deployments" -> "Approve and deploy".

A version can be uploaded to PyPI once only. If the upload fails after approval, fix the
problem and release a new version number.

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
