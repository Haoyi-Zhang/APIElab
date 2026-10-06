# Uniform Elaboration Across Evolving APIs — artifact

APIElab-code accompanies **“Uniform Elaboration Across Evolving APIs: Principal Regions, Obstructions, and Complexity.”** It contains a standard-library Python reference implementation, independent finite checkers/oracles, exact generated and authored inputs, retained raw results, tests, ordinary mathematical arguments, and source provenance.

The repository is complete for the declared bounded evidence. It is not a proof-assistant development, Android detector, source-to-source repair system, solver scalability study, or real-app/device benchmark. The asymptotic theorems are ordinary proofs in `proofs/arguments.md`; finite execution checks only the stated families.

## Reproduce from a clean extraction

Use Python 3.10 or newer. The full finite campaign was rerun on Windows 11 AMD64 with CPython 3.12.14. Linux uses `resource` for CPU/address-space limits and peak RSS. Windows obtains the current process's real peak working set through `GetProcessMemoryInfo`; it records CPU/address-space limits as unavailable. No third-party package, network access, GPU, solver, model API, paper directory, or external service is required.

The complete bounded driver (seven owned commands, at most 180 wall seconds each) is:

```sh
python -B -m compatibility.scientific_checks --output FRESH-OUTPUT
```

It retains raw stdout/stderr, actual command results, environment metadata, test fixtures and fresh campaign output. Set `PYTHONUTF8=1` and `PYTHONDONTWRITEBYTECODE=1`. The supplied Linux workflow uses Python 3.12, a 30-minute job bound, a fresh `RUNNER_TEMP` directory, and pinned actions; it is prepared for execution, not evidence of a completed CI run.

```sh
python -m unittest discover -s tests -v
python -m compatibility.reproduce --output /tmp/epc-semantic-reproduction
python -m compatibility.reproduce_succinct --output /tmp/epc-circuit-reproduction
```

The two output directories must not already exist. The public commands exercise CLI wrappers, which call the campaign functions in the same Python process. Unit tests also call those functions directly and separately check CLI argument parsing. Exclusive creation prevents stale output from being reused. An existing path is never modified; if a fresh run fails after creation, its fresh path and any partial diagnostic output are retained rather than silently removed.

Expected completion conditions:

- **65 tests** run; the Windows-limit test is skipped on non-Windows systems;
- semantic reproduction reports **14/14 exact file matches**, reexecutes the example and boundary fixtures, and confirms the boundary counts;
- succinct reproduction reports **7/7 exact file matches** and rechecks all **6,280** structure certificates.

Timing and maximum resident memory are recorded but intentionally excluded from byte equality.

JSON/JSONL files use fixed LF line endings on every platform; CSV retains its explicit dialect. The measured Windows campaign records and raw test log are in `results/windows-20261006/`. Historical Unix measurements are retained separately and are not attributed to this run. Peak memory is a process-lifetime observation, not an aggregate over child processes.

Useful direct checks:

```sh
python -m compatibility.cli check inputs/example.json results/example_certificate.json
python -m compatibility.cli check inputs/boundary_case.json results/boundary_certificate.json
python -m compatibility.structure_check --directory results/succinct
```

## Model

The base language has Boolean values and loop-free terms: return, calls with explicit or omitted arguments, lexical `let`, Boolean branches, presence guards, and version-threshold guards. Every declaration supplies exact rows for the two Boolean inputs, optional fixed-default behavior, and an allowed effect-label set. Outcomes are errors or a Boolean result paired with an ordered word over two modeled event labels. Missing declarations/defaults are explicit errors.

The reference state must succeed on all admitted inputs. A version is fixed-client compatible exactly when every input produces the same successful result and event word as the fixed reference. Candidate-side `missing_api` and `missing_default` outcomes are incompatibility witnesses and retain prior event prefixes; malformed inputs, reference faults, and cap violations yield no conclusion. Uniform elaboration separately supplies a finite choice relation and an observation partition; versions in one partition block must share a choice. The compact extension represents compatibility predicates as acyclic total Boolean circuits and keeps the quantifier order `exists common choice, for all runtime inputs`.

Admission caps are 32 states, 64 declarations, 24 call sites, 256 syntax nodes, depth 40, trace length 20, and 6,000 certificate nodes. Cap violations yield no compatibility conclusion.

## Frozen campaign

| Family | Exact scope | Result |
|---|---|---|
| Truth-table histories | 4×5×5×6 cases; six named clients, no numerical version guard, at most two calls | zero oracle mismatches |
| Default/effect histories | 4×5×5×6 cases; six named clients, at most two calls | zero oracle mismatches |
| Scholarly projections | 30 hand-authored source-mapped Boolean illustrations; may contain three calls | zero oracle mismatches; not source reproductions |
| Regression controls | 16 authored controls outside the 1,230 denominator | all expected outcomes |
| Uniform choice | 3,102 matrices/partitions; 31,538 policies | 2,548 positive, 554 negative; zero mismatches |
| Guard representation | 378 subset/k-interval queries | 306 greatest, 72 absent; zero mismatches |
| Composition | 256 Boolean quadruples | 80 universal whole-client agreements; initial-zero local rule: 16 false acceptances on `{0}`, 32 on `{0,1}` |
| Compact reduction | 6,280 circuit histories | 3,140 positive, 3,140 negative; zero mismatches |

The principal campaign is exactly **1,200 generated histories + 30 scholarly projections = 1,230**. The 16 regression controls are executed but not counted in that denominator. No random seed exists because every family is deterministically enumerated.

Mutation testing rejects 13,705 selected semantic-certificate mutations, 1,108 uniform-certificate mutations, and 18,840 compact-certificate mutations. These totals count only applicable selected faults; they are not universal mutation scores.

## Producer/checker separation

- `compatibility/model.py` and `infer.py` implement the recursive finite semantics and producer.
- `compatibility/replay.py` independently replays complete semantic certificates with an iterative syntax cursor and environment.
- `compatibility/uniform.py` produces policies/conflicts; `uniform_check.py` independently validates complete policy supports and deletion witnesses.
- `compatibility/succinct_campaign.py` uses scalar circuit evaluation; `succinct_check.py` checks complete policies with packed truth vectors.
- `compatibility/cases.py`, `scholarly.py`, and independent closed-form/direct oracles construct expected answers without invoking the client producer.
- `compatibility/guards.py` enumerates endpoint-interval unions without calling the separate component-count oracle.
- `reproduce.py` and `reproduce_succinct.py` regenerate and compare declared deterministic files.

“Independent” here means separate code paths, not independent people or organizations. The same development process produced the code and prose, so correlated conceptual errors remain possible.

## Repository map

- `compatibility/`: semantics, producers, checkers, oracles, campaigns, reproduction drivers
- `tests/`: 65 unit and finite regression tests
- `inputs/`: exact generated/authored inputs, source mapping, fixtures
- `results/`: retained raw results, certificates, summaries, scoped measurements, reproduction records
- `proofs/arguments.md`: complete ordinary mathematical arguments and evidence boundary
- `literature/calibration.csv`: 22 related-work comparisons (11 TOPLAS, one PLDI framework, five foundational/synthesis, five API-compatibility)
- `literature/closest-work.md`: adversarial research-lock decision
- `claim_evidence_ledger.csv`: material claim-to-proof/result mapping
- `external_resources.csv`: scholarly/official provenance and integration mode
- `resource_accounting.csv`: scoped measured runs; not a reconstructed conversation total
- `THIRD_PARTY.md`, `LICENSE`: licensing boundaries

## Evidence labels and non-claims

- **Proved:** ordinary mathematical argument is present.
- **Finite-checked:** every member of a declared finite family was checked against the stated oracle.
- **Measured:** a scoped run recorded CPU/wall/RSS observations.
- **Source-mapped:** a scholarly pattern was projected into the toy calculus with a stated fidelity limit.

The artifact does not claim proof-assistant assurance, industrial scalability, Android prevalence, detector precision/recall, repair success, human validation, independent peer review, or acceptance. Scholarly projections preserve only a source-motivated pattern.
