# Benchmark model provenance

The ten models in this directory are the inputs to the solver benchmarks
reported in the gpuGEM manuscript. They are cached here so that the benchmarks
can be rerun offline and so that the Zenodo deposit is self-contained; see
`benchmarks/README.md` for the mapping between these filenames and the model
labels used in the paper.

`SHA256SUMS` records the checksum of each file. Verify with:

```bash
cd benchmarks/model_cache && sha256sum -c SHA256SUMS
```

## Sources

| file | model | origin |
|---|---|---|
| `e_coli_core.xml` | E. coli core | BiGG Models, <http://bigg.ucsd.edu/models/e_coli_core> |
| `iML1515.xml` | iML1515 | BiGG Models, <http://bigg.ucsd.edu/models/iML1515> |
| `Harvey_1_03c_reduced.mat` | Harvey (male whole-body) | Virtual Metabolic Human, <https://www.vmh.life/> |
| `Harvetta_1_03d.mat` | Harvetta (female whole-body) | Virtual Metabolic Human, <https://www.vmh.life/> |
| `mWBM_S84_male.mat` | PMM1 | Digital Metabolic Twin Centre |
| `mWBM_S85_male.mat` | PMM2 | Digital Metabolic Twin Centre |
| `mWBM_S23_male.mat` | PMM3 | Digital Metabolic Twin Centre |
| `mWBM_S15_male.mat` | PMM4 | Digital Metabolic Twin Centre |
| `mWBM_S9_male.mat` | PMM5 | Digital Metabolic Twin Centre |
| `mWBM_S83_male.mat` | PMM6 | Digital Metabolic Twin Centre |

The BiGG models are downloaded automatically by `benchmarks/models.py` when
absent; the cached copies here exist so the suite also runs without network
access. The whole-body and personalised microbiome models are not downloadable
from a public endpoint by the benchmark code and must be present in this
directory.

## Licensing

The gpuGEM source code is MIT licensed (see `LICENSE` at the repository root).
**The MIT licence does not extend to the model files in this directory.** They
are covered by the terms of their respective origins:

- **Harvey and Harvetta** are published models distributed by the Virtual
  Metabolic Human resource (Thiele *et al.*, *Mol Syst Biol* 2020) and remain
  subject to its terms: <https://www.vmh.life/>.
- **E. coli core and iML1515** are BiGG models and carry BiGG's own terms:
  <http://bigg.ucsd.edu/>.
- **PMM1 to PMM6**: Digital Metabolic Twin Centre. All rights reserved. These models may be used to reproduce the results of the gpuGEM manuscript. For any other use, please contact the Digital Metabolic Twin Centre.

If you intend to redistribute any of these files, or to use them commercially,
check the terms of the relevant source first.

This mirrors the note in `application/data/PROVENANCE.md`, which covers the
model data used by the candidate-gene application.
