# Mathematical arguments and evidence boundary

These are ordinary mathematical proofs. They are not proof-assistant derivations. The executable checkers validate finite instances and complete finite evaluation tables; they do not certify the asymptotic proofs in this document. The same development process drafted the proofs, producer, and separately implemented checking code. The research lock is proportional: standard synthesis, MUS/MSS, product-program, effect-system, and maximum-score components are credited to prior work; no priority claim is made. The retained claim is the stated quantifier separation and exact compact-complexity classification with its one-call/two-maxima embedding.

## 1. Fixed semantics, not metadata

Let V be a nonempty finite totally ordered set of platform states, X a nonempty finite totally ordered input domain, and r in V a reference. A fixed, deterministic, terminating client has outcome E(v,x), either success(b,w) with a typed value b and finite event word w, or an error with its event prefix. Require that E(r,x) succeeds for every x. Define C(v,x) iff E(v,x) succeeds and equals E(r,x), including its event word. Define P={v: for every x, C(v,x)}.

**Proposition 1 (semantic principality).** A region S is safe iff S is a subset of P. Consequently P is the unique greatest safe region.

**Proof.** Safety of S means that each of its members satisfies every input obligation, which is exactly membership in P. Thus every safe S is contained in P, and P itself is safe. Any two greatest safe regions must contain one another. No assumption concerning purity is used in this argument. Effects change C, not the elementary implication. End.

**Proposition 2 (metadata insufficiency).** Signatures, availability, default values, and effect-label sets do not in general determine exact behavioral compatibility.

**Proof.** Take two versions, one Boolean API, no events or defaults, and the client that returns the API result. The reference always returns zero. In history H the candidate returns zero on both inputs; in H' it returns one on both. All named metadata are identical. The candidate belongs to P in H and not in H'. An algorithm receiving only that metadata has the same input on both histories and therefore cannot return the exact actual-behavior answer on both. This does not prohibit conservative analyses or exact answers relative to a supplied behavioral specification. End.

## 2. Executable finite client semantics

The implemented base type is B={0,1}. Expressions are constants, variables, and Boolean negation. Terms are return e; let y=f(e) in c; let y=f() in c; if e then c else d; if-present f then c else d; and if-version-at-least k then c else d. Bindings are fresh and lexical. The initial environment maps x to the supplied input. At each version, each present API f has two exact rows B -> B x {a,b}*, an optional fixed default in B x {a,b}*, and an effect-label set containing every label in these rows and the default.

Returns produce an empty trace. Pure expressions produce Boolean values without events. Branches choose exactly one child; presence and threshold branches are evaluated at the current version. A missing API produces an error. An omitted argument requires a default, otherwise it produces an error. A fixed default contributes its value and trace; an explicit argument bypasses it. Lookup of the selected API row produces a Boolean result and body trace. The continuation receives that result. Default events precede body events, which precede the continuation's events. An error in the continuation retains all preceding events.

The mathematical finite-table semantics is unbounded in finite trace length. The executable instance admission imposes a finite trace cap; a run that would exceed it yields no conclusion. It is not truncated and classified as compatible or incompatible.

**Lemma 3 (termination and preservation of success).** A well-formed finite term in a well-formed declaration history has exactly one mathematical outcome; if successful, its return value is Boolean and every emitted label is authorized by the declaration that emitted it.

**Proof.** By structural induction on expressions, an expression with a Boolean environment evaluates to exactly one Boolean: constants and variables are immediate, and negation maps B to B. For terms, return is immediate. Every branch evaluates a total pure condition or finite declaration/ordering test and selects exactly one strict subterm, to which the induction hypothesis applies. For a call, missing declaration/default produces a specified error. Otherwise the explicit expression or fixed default yields one Boolean argument; the total two-row table yields one Boolean result and finite word. Extending a fresh binding with that result preserves a Boolean environment, and the strict continuation has one outcome by induction. Concatenation is unique, finite, and preserves each event's provenance. Rows/defaults were checked against the declaration's label set. There are no loops, recursive calls, dynamic code, or unspecified transitions. End.

This is not progress for a rich source language: modeled missing-API/default errors are possible for well-formed terms. An accepted compatibility region additionally excludes those errors for every declared input.

**Theorem 4 (enumeration and least failures).** Exhaustive evaluation of V x X computes P exactly. For every v outside P, the minimum x with not C(v,x) exists. Sorting versions and inputs gives the lexicographically least failing pair outside P; when P=V, there is no such pair.

**Proof.** The product is finite and each evaluation terminates by Lemma 3. Membership is the conjunction of precisely the defining obligations of Proposition 1. A version excluded from P has a nonempty finite failure-input set, hence a minimum. If any version fails, the nonempty finite set of failing versions has a minimum; its minimum failing input is lexicographically no greater than any other failing pair. End.

**Theorem 5 (finite certificate checking).** For admitted cases whose entire enumerated executions fit the operational caps and whose reference succeeds, the canonical complete evaluation certificate is accepted. Any accepted certificate has exactly the correct region, full state/input coverage, execution outcomes and call logs, minimum per-version witnesses, and least global witness.

**Proof.** The certificate schema fixes a canonical order: ascending version and input. Its row domain is all V x X, not a producer-chosen subset. A separate checker re-admits the trusted input (including its reference field) and re-evaluates each pair using an iterative syntax cursor and environment. Its loop invariant is that the cursor/environment denote the same residual computation as the recursive semantics; the accumulated event prefix and ordered log equal exactly the calls already traversed. Return produces the final Boolean. Every conditional chooses the same child. A successful call appends the same default/body prefixes, extends the same fresh binding, and advances to the stored body; a candidate error ends with the prefix already accumulated. Thus induction on the finite traversal gives identical outcomes/logs. After all rows, it recomputes the defining conjunctions and ordered failures of Theorem 4. Canonical, type-sensitive comparison rejects extra/missing/reordered rows, changed values, booleans substituted for integer indices, altered conclusions or witnesses. Conversely the correctly enumerated canonical certificate agrees at every comparison. This proof describes the checker specification and invariant; tests do not constitute a verified Python implementation proof. End.

## 3. Expressible guards

Let G be a finite family of subsets of V, containing the empty set. For a semantic safe set S, the sound expressible guards are G_S={g in G:g subset S}.

**Theorem 6 (union criterion).** Every S subset V has a greatest member of G_S iff G is closed under finite unions.

**Proof.** If G is union-closed, take the union of the finite family G_S. It belongs to G, is contained in S, and contains every member of G_S. Conversely take g,h in G and S=g union h. A greatest element of G_S must contain g and h, hence S; it is also contained in S, hence equals S. Therefore g union h belongs to G. Binary union closure plus the included empty set gives finite union closure. End.

If all singleton sets belong to G, a particular S has a greatest sound expressible guard iff S itself belongs to G. A greatest guard must include each singleton of S and therefore S; the converse is immediate. For at most k intervals of a finite total order, every singleton is expressible. A set with k+1 separated components has no greatest sound k-interval guard. On n ordered points the largest possible number of components is ceil(n/2), attained by alternating included and excluded points. Thus the representation failure disappears exactly when k reaches that bound. This is an expressiveness fact, not the nonexistence of the semantic safe set.

## 4. Observation-uniform choices

Let A be a nonempty finite choice set and Pi a partition of V. The compatibility relation is fixed before choosing the policy. For an API interpretation, freeze the reference observation on each input independently of the selected policy. The matrix model itself need not contain a distinguished reference. Adding a new always-compatible reference r with W(r)=A does not change greatest-region existence: any realizing policy can include it, and any region in the extended model projects to a region of the old model. Hence all extended maximal regions are exactly old maximal regions with r added. For each v, let W(v) subset A be the choices satisfying every fixed input obligation. A policy maps every observation block to one choice in A. A region S is realizable when some policy is safe on every version in S.

**Theorem 7 (uniform feasibility).** S is realizable iff, for every block B in Pi, the intersection of W(v) over v in S intersect B is nonempty; the intersection of an empty family is A.

**Proof.** A realizing policy's choice for B lies in each W(v) demanded in that block. Conversely choose one member of each nonempty intersection. There are finitely many blocks, so these choices define a policy. It satisfies every demanded version. End.

Let U={v:W(v) is nonempty}.

**Theorem 8 (greatest uniform region).** A greatest realizable region exists iff U is realizable. If it exists it is U.

**Proof.** Every singleton {v} with v in U is realizable: choose a member of W(v) on its block and arbitrary choices on other blocks. Every realizable region is contained in U. Hence any greatest one must contain all these singletons and be contained in U, so equals U. The converse follows because realizable U contains every realizable region. This includes U empty, realized by any policy. End.

**Pure counterexample.** Two indistinguishable candidate versions with W(v0)={0} and W(v1)={1} have realizable singleton regions but no greatest region. A complete API history can include a third, always-compatible reference: on the chosen default bit a, the reference returns 0, candidate v0 returns a, and candidate v1 returns 1-a. The same pure constant is used at all three states. Exact evaluation then gives fixed-choice regions {r,v0} and {r,v1}. This witnesses a two-candidate conflict, not a two-state full history with an implicit always-compatible reference. The supplied reference-choice fixture evaluates both clients, keeps their reference observation identical, derives W(r)={0,1}, and checks the two-candidate obstruction. Conversely, fixed effectful default semantics still satisfies Proposition 1. An effect boundary and a uniformity boundary are different propositions.

If the synthesized choice may inspect the exact version, Pi is discrete. Every nonempty W(v) can be handled independently, and U is realizable. Thus a language allowing unrestricted version guards in the synthesized policy cannot use this counterexample to claim a loss of principality. The restricted observation applies to the choice policy, not to all branches of every fixed client.

**Lemma 9 (sharp conflict size).** If the uniform feasibility test fails, some failing observation block has an inclusion-minimal nonempty conflict C with empty intersection of W(v). Such a C has at most |A| members, and this bound is attained for every |A|>=2 even when every member is individually viable.

**Proof.** Start from a finite failing block and delete a member while emptiness persists. The process terminates in an inclusion-minimal C. For each c in C choose a_c in the nonempty intersection of the sets for C without c. This element cannot belong to W(c), since then it would be in their full intersection. If c!=d and a_c=a_d, the witness a_d is in W(c), contradicting a_c not in W(c). Thus c maps injectively to a_c in A. For sharpness let A={1,...,m}, C={1,...,m}, W(i)=A without i. Their intersection is empty, and deleting i leaves i in all remaining sets. End.

A deletion certificate consists of the conflict, one rejecting member for each choice, and a satisfying choice after each single-member deletion. These respectively establish emptiness and inclusion-minimality. They do not establish minimum cardinality or earliest ordering among all possible conflicts. The independent matrix checker enumerates policies and checks these facts; its input-matrix admission is a stated precondition.

**Lemma 10 (observation refinement).** Refining Pi cannot remove a realizable region. If U is realizable before refinement it remains the greatest region after refinement.

**Proof.** Restrict an old block's choice to each new subblock. The same policy values realize the old region. U depends only on W, not Pi; apply Theorem 8. End.

## 5. Succinct circuits and oracle classes

For a list of Boolean circuits C_i(a,x), with common fixed-width bit tuples a and x, define W_i={a: for all x, C_i(a,x)=1}. A region S is realizable iff some a lies in every W_i for i in S. The choice precedes all runtime inputs. The circuit list and widths are the input; widths and list length are unbounded finite parameters for the following asymptotic theorems. Fixed experimental ceilings do not carry these hardness claims.

SAT is the problem whether a Boolean circuit has a satisfying assignment. QSAT2 is whether a Boolean circuit phi(y,x) satisfies exists y forall x phi. Write P_parallel^SAT and P_parallel^QSAT2 for deterministic polynomial-time computation with a polynomial-length batch of nonadaptive queries to the corresponding oracle, followed by polynomial-time Boolean postprocessing. These are commonly denoted Theta_2^P and Theta_3^P. The proof below uses the explicitly defined oracle classes, not a separate equivalence with logarithmically many adaptive queries.

An oracle-batch acceptance instance consists of a list of queries Q_1,...,Q_q and a Boolean circuit g on their answer bits. Deciding g(b)=1, where b is the truth vector of the queries, is complete for the corresponding nonadaptive-oracle class: membership asks the list and computes g; any computation in the class produces its nonadaptive list and compiles the polynomial-time postprocessing into a polynomial-size Boolean circuit. We may assume q>=1 by adding an unused always-false query when necessary. Individual query variables are renamed apart, so their witnesses are independent.

**Lemma 11 (upper bound by two counts).** Greatest-region existence for the circuit model belongs to P_parallel^QSAT2. Without x it belongs to P_parallel^SAT.

**Proof.** Let u be the number of individually viable versions and s the maximum number simultaneously safe under one choice. Every simultaneously safe version is individually viable, so s<=u. Theorem 8 says principality holds exactly when s=u. For k=1,...,n ask two queries. To express u>=k use the formula exists z,a_1,...,a_n forall x: |z|>=k and conjunction_i(z_i implies C_i(a_i,x)). To express s>=k use exists a,z forall x: |z|>=k and conjunction_i(z_i implies C_i(a,x)). Each is an existential-universal Boolean circuit of polynomial size. The selection vector and witnesses are fixed before the universal input; it is not enough to accept a different k-element set on each input. For C_1=x and C_2=not x, the two rows are (0,1) and (1,0), so u=s=0. All 2n queries can be formed without any oracle answers. Their answer prefixes determine the two counts, which are compared in polynomial time. With no x every query is SAT. End.

**Lemma 12 (encoding a batch answer in a maximum score).** Let Q_i=exists y_i forall x_i phi_i and b_i be its answer. Introduce selection z and independent y_i. Define Valid(z,y,x) as the conjunction of (z_i implies phi_i(y_i,x_i)). Define F(z)=2|z|+1-g(z). A selection z has witnesses making Valid true for all x iff z subset b. The maximum achievable score K is 2|b|+1-g(b), hence K is even iff g(b)=1.

**Proof.** If selected query i is false, no choice y_i makes it true on every x_i, so a tuple x falsifying that selected conjunct exists for every tuple y. Conversely if all selected queries are true, choose their independent witnesses y_i; arbitrary witnesses suffice for unselected queries. The conjunction then holds for every tuple x. Thus feasible masks are precisely submasks of b. Mask b has |b| bits. Every proper submask has at most |b|-1 bits and score at most 2|b|-1, whereas F(b)>=2|b|. Therefore b is the unique maximum-cardinality feasible mask and strictly dominates every proper submask in score. The displayed equality and parity follow. With no universal variables the argument is unchanged. End.

The coefficient two is essential for strict priority. With one query having answer one and g(z)=z, the weight-one scores of z=0 and z=1 both equal one. Maximum-score parity would incorrectly reject g(b)=1.

**Lemma 13 (threshold circuits).** For j=1,...,N+1, where N=2q+1, let T_j(z,y,x)=Valid(z,y,x) and [F(z)>=j]. Then exists z,y forall x T_j iff j<=K. All thresholds have a polynomial-size joint Boolean DAG, and T_(N+1) is false.

**Proof.** The equivalence is the definition of maximum achievable score. To bound size, Valid contains one renamed copy of each input query and q implications. The circuit for g is one copied subcircuit. A polynomial-size cardinality circuit counts z. For even j=2h the threshold is |z|>=h. For odd j=2h+1 it is (|z|>=h+1) or (|z|>=h and not g(z)). Reusing these subcircuits produces polynomial total size for the O(q) thresholds. F(z)<=2q+1, so the final threshold is false. This construction does not require computing K or b. End.

**Lemma 14 (principality gadget).** Use one common choice a=(t,z,y). Add an always-true reference circuit R and an anchor D_0=(not t). For j=1,...,N let

    D_j = T_j and (T_(j+1) or [t = (j mod 2)]).

The support of individually viable versions is {R,D_0,D_1,...,D_K}. This support is jointly viable iff K is even.

**Proof.** The reference and anchor are viable. D_j implies T_j, so viability entails j<=K. Conversely when j<=K, choose witnesses for T_j and t equal to j's parity; the disjunction is then true on every runtime input. This establishes the support. If K is even, choose witnesses achieving maximum score K and t=0. For every j<K, both T_j and T_(j+1) are true for all inputs. For j=K, T_K is true and the parity disjunct is true. The same witnesses work for the entire prefix: thresholds share the selected mask and original-query witnesses. The anchor and reference also hold. If K is odd, any common choice satisfying the anchor has t=0. To satisfy D_K on all inputs with that tag it must make T_(K+1) true on all inputs, contradicting maximality of K. For K=0 only the reference and anchor are viable, and t=0 realizes them. End.

**Theorem 15 (classification).** Greatest uniform region existence is P_parallel^SAT-complete for pure Boolean circuits without runtime inputs, and P_parallel^QSAT2-complete when the runtime inputs are universally quantified. Reductions are polynomial-time many-one reductions.

**Proof.** Membership is Lemma 11. Given any batch-acceptance instance, build Valid, F, thresholds, and the circuits of Lemma 14. Lemma 13 proves that this transformation is polynomial and does not query the source oracle. By Lemma 12, g(b)=1 iff K is even. By Lemma 14 and Theorem 8, this is equivalent to greatest-region existence in the output. This is a many-one reduction from the complete batch-acceptance problem, proving hardness. Removing universal inputs gives the same reduction for SAT. End.

**API embedding.** At every version declare one total pure API of the same type (X x A)->B. It returns zero when that version's compatibility circuit is true and one otherwise. The reference returns zero unconditionally. A typed client returns the result of this one call on its runtime input and one synthesized constant tuple a in an omitted default slot. There are no guards, effects, reflection, missing declarations, state mutation, or code loading. Compatibility with the reference is exactly C_i(a,x). This embeds the lower bounds into a one-call evolution model. It is not an Android front end or a claim about a language's standard default-binding convention.

**Corollary 16 (two maximal regions and a two-state obstruction).** The hard instances above have either one or two maximal realizable regions. In the negative case they have exactly two, and a conflict of two individually viable versions suffices.

**Proof.** When K is even the support itself is realized, so it is the only maximal region. Suppose K is odd. Let U denote the individually viable support. Maximum-score witnesses with t=1 realize U without D_0; the same witnesses with t=0 realize U without D_K. These are incomparable. Any policy with t=1 omits D_0, so its support is contained in the first region. Any policy with t=0 cannot realize D_K, since that would imply the unrealizable threshold K+1, so its support is contained in the second. Thus these two are exactly the maximal regions. The pair {D_0,D_K} is not jointly realizable, while each singleton is; it is an inclusion-minimal two-state obstruction. End.

**Corollary 17 (conditional certificate-size barrier).** Unless NP=coNP, there is no sound and complete polynomial-time verifier with polynomial-size certificates for every positive instance of greatest-region existence in the unrestricted succinct no-input model.

**Proof.** In the batch reduction take one SAT query for arbitrary circuit phi and let g negate its answer. The output is a positive principality instance exactly when phi is unsatisfiable. If every positive output had a polynomial-size certificate accepted by a polynomial-time sound verifier, guessing that certificate would decide circuit unsatisfiability in NP. As circuit satisfiability is NP-complete, unsatisfiability is coNP-complete; coNP would be contained in NP, and taking complements gives equality. The finite complete tables in the artifact do not contradict this statement: their size can be exponential in succinct input width, and the implementation has fixed admission bounds. End.

## 6. Composition and unbounded computation

**Proposition 18 (region bitsets cannot compose exactly).** No rule depending only on the individual universal-input safe-version regions of two calls can always compute the safe region of their composition.

**Proof.** Use two versions, two Boolean APIs, and both inputs. At the reference both APIs are identity. In H, both candidate APIs are negation; neither individual API agrees universally with its reference, but their composition is identity. In H', the first candidate is negation and the second is constant zero. The individual safe-version sets are identical to those in H: only the reference for both APIs. Their composition is constant zero and fails on input one. A function of only the two region sets receives identical arguments and would need distinct results. End.

Universal-domain equality of each component is a sufficient compositional rule, by substitution and associativity of trace concatenation, but is not necessary as the first example shows. Checking only an initial input domain need not be sufficient. With initial input set {0}, take f_0=f_1=constant one, g_0=identity, g_1=constant zero. Each local comparison on {0} passes. The composed programs return one and zero, respectively. The continuation obligation must cover the reached intermediate values, not merely the initial input domain.

A full paired-state transformer is an exact, but standard, repair: it carries both intermediate values and both event prefixes, updates the paired state with both calls, and compares only complete observations. Determinism gives ordinary relational composition. This does not establish a new relational program logic.

**Proposition 19 (finite versions do not ensure decidability).** In an extension admitting arbitrary unbounded computation in a default or API, no total algorithm can always decide exact successful-termination compatibility, even with two versions and a singleton input domain.

**Proof.** The reference returns zero. The candidate first simulates an arbitrary machine M on its fixed input, then returns zero if the simulation terminates. It is compatible exactly when M terminates. A total exact compatibility decider would decide the halting problem. Its semantic safe set still exists as a mathematical subset; it is its effective computation that fails. This argument requires unbounded computation, not merely the syntactic presence of a feature called reflection. End.

## 7. What the finite evidence establishes

The principal semantic campaign checks exactly 1,230 cases: 600 exhaustive instances of the first Boolean truth-table grammar, 600 exhaustive default/effect instances of a second frozen grammar, and 30 hand-authored source-mapped scholarly projections. Sixteen additional regression controls are executed outside that denominator. The projections test representation paths only; they do not reproduce source apps, tools, devices, or prevalence. Uniform matrices, composition quadruples, and guards have their own explicitly stated finite families. The succinct campaign checks every common choice and input for 6,280 generated circuit histories and compares scalar generation, packed-vector checking, and a direct source-query oracle. Its 3,140 positive and 3,140 negative answers follow the balanced enumeration of postprocessing truth tables, not a prevalence estimate. The additional structure replay checks Corollary 16 on every retained circuit after rechecking its complete support certificate. Fifty-seven unit tests and clean reproduction compare 14 semantic and seven compact deterministic files byte for byte. The compact controls also check q=1 and q=2 at K=0 and K=2q+1, including the always-false T_(2q+2) sentinel. The proofs above, rather than these finite counts, justify the mathematical statements. No generalized source-language verifier, industrial scalability result, proof-assistant assurance, deployed-app claim, or independent human validation is asserted.
