# Complete local execution

`campaign.json` records the actual eight-command Windows/Python 3.12.14 run,
including raw command outcomes, environment and current processor metadata.
All commands completed without timeout. The unit command ran 87 tests with
no skip. CPU model comes from the Windows registry, logical processor count
from the OS; physical core count and affinity remain unknown when not obtained.

The semantic command regenerated and matched 14 deterministic files and
re-executed the example/boundary fixtures. The succinct command regenerated and
matched seven files, including complete structure replay of all 6,280 cases.
The group command emitted the six named controls and checked 16 label-subset
choice projections; these do not change the 1,230/6,280 campaign denominators.
Full group circuits, clauses and projection records are in the sibling
`group-encoding/` collection, which has the same unchanged six core sources.

Raw stdout/stderr for each of the eight commands is retained under `logs/`.
Current measured resource JSON is separate from the original scientific
measurements; neither timing nor peak memory is expected to match byte for byte.
These are finite implementation checks, not a general-proof mechanization,
native API deployment or publication-priority finding. Remote CI is verified
against its own current commit and runtime.
