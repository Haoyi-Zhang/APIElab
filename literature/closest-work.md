# Closest-work adversarial comparison

This note records the research lock rather than a citation inventory. The full 12+5+5 calibration matrix is in `calibration.csv`. The comparison below asks whether the paper's strongest claim is already a standard instance of an existing theorem.

## 1. Fixed clients and principal regions

For a fixed deterministic terminating client, the exact safe set is the set of versions satisfying all input obligations. This is definitional and is not claimed as novel. Behavioral subtyping, Hoare logic, relational logics, abstract interpretation, semantic differencing, and lifecycle analyses all provide richer or more practical settings. The paper uses the fixed case only as the reference against which three distinct losses are measured: missing behavioral information, restricted guard representation, and a choice shared across versions.

## 2. Uniform choices and satisfiable-subset geometry

For one observation block, each version induces a finite set of choices that satisfy all of its obligations. Realizable regions are therefore the satisfiable subsets of a monotone constraint family. The criterion “a greatest region exists iff every individually viable constraint is jointly satisfiable” is elementary. Minimal obstructions are ordinary minimal unsatisfiable subsets, and maximal regions are ordinary maximal satisfiable subsets. MARCO-style MUS/MSS enumeration, model-based diagnosis, QuickXplain, MaxSAT, and monotone dualization own this general geometry. The paper does **not** claim a new MUS/MSS algorithm, diagnosis framework, or conflict-minimization method.

The retained language-level contribution is narrower: (i) the exact quantifier separation between a fixed API elaboration and an observation-uniform elaboration, (ii) a certificate format that cannot misreport an individually viable state as intrinsically impossible, and (iii) an embedding showing that the decision about a greatest region remains parallel-oracle complete for one pure API call even when negative instances have only two maximal regions and a two-state obstruction.

## 3. Synthesis

Syntax-guided and oracle-guided synthesis already treat an implementation choice existentially against semantic examples or universally quantified inputs. The uniform default is a finite synthesis variable. Its novelty cannot be “using synthesis for compatibility.” What is specific here is the output question: not whether a total implementation exists, but whether the union of all individually satisfiable version obligations is realizable by a single implementation under the observation partition. The paper states this as a decision problem and classifies its succinct Boolean representation.

## 4. Relational verification and composition

Product programs and relational program logics already carry paired intermediate states, align control flow, and prove equivalence or refinement. The paper's counterexample to region-only composition is a negative result about a deliberately coarse summary. The exact repair—paired-state relational composition—is standard and is credited as such. No new relational program logic is claimed.

## 5. Variability and guards

Variational programming and software-product-line analysis share representations across configurations while preserving alternatives. This project instead indexes externally supplied API states and constrains which choice may vary with an observation partition. The finite union criterion for a guard family is elementary; interval and k-interval results are representation facts, not new abstract-interpretation theory.

## 6. API evolution

CiD already models non-contiguous Android API lifecycles and guarded bytecode use. Taming Android Fragmentation, later empirical studies, repair systems, SemDiff, and silently evolved methods cover practical detection, migration, or prevalence questions. This project supplies exact finite behavior rather than inferring it from Android code or metadata. Its 30 scholarly cases are hand-authored projections used to exercise semantic categories; they are not replications, extracted benchmarks, or evidence of prevalence.

## 7. Research-lock decision

The project is locked on the following proportional claim:

> In a finite version-indexed client calculus, fixed semantic compatibility, guard expressibility, and observation-uniform elaboration have different principal objects and different witnesses. For succinct Boolean behavior, deciding whether the uniform family has a greatest region is complete for nonadaptive parallel SAT queries, or for nonadaptive parallel existential-universal SAT queries with runtime inputs; the lower bound embeds in one pure call and still has at most two maximal regions.

The paper does not claim that maximum-score encodings, parity extraction, monotone constraint families, product programs, effect systems, or finite replay certificates are new in general. The proof obligation is the correctness of the stated reductions and embedding. The empirical obligation is implementation consistency within the frozen finite families, not practical Android effectiveness.
