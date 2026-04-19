# LLM Judge (GPT-5) Held-Out Retrieval Report

- Queries judged: **20**
- Judgments total: **200** (top-10 per query)

## Rubric

- **2 (DIRECT)**: paraphrase / template / close analogue of ground-truth comment.
- **1 (PARTIAL)**: same file/module or related concern, but not the same advice.
- **0 (NONE)**: different issue, not directly useful.

## Hit@K (LLM-judged)

| K | Strict (any label = 2) | Lenient (any label >= 1) |
|---:|:---|:---|
| 1 | 0/20 = **0%** | 5/20 = **25%** |
| 3 | 1/20 = **5%** | 13/20 = **65%** |
| 5 | 2/20 = **10%** | 14/20 = **70%** |
| 10 | 2/20 = **10%** | 16/20 = **80%** |

## Per-judgment label distribution (across all 200 hits)

| Label | Count | Share |
|---:|---:|---:|
| 0 | 166 | 83% |
| 1 | 31 | 16% |
| 2 | 3 | 2% |

## Per-query best label (out of top-10)

| Best label achieved | # queries |
|---:|---:|
| 2 | 2 |
| 1 | 14 |
| 0 | 4 |

## LLM label vs. lexical-F1 bucket

| Lex F1 bucket | label=0 | label=1 | label=2 |
|:---|---:|---:|---:|
| high_lex (n=11) | 8 | 2 | 1 |
| low_lex (n=189) | 158 | 29 | 2 |

## LLM label vs. same-file flag

| Same-file? | label=0 | label=1 | label=2 |
|:---|---:|---:|---:|
| same_file (n=32) | 26 | 6 | 0 |
| diff_file (n=168) | 140 | 25 | 3 |

## Similarity score vs. LLM label

| Label | n | mean cosine sim | median |
|---:|---:|---:|---:|
| 0 | 166 | 0.750 | 0.750 |
| 1 | 31 | 0.770 | 0.758 |
| 2 | 3 | 0.763 | 0.753 |

---

## Per-query summary table

| # | PR | File | top-10 labels | best | any 2? |
|---:|---:|:---|:---|---:|:---:|
| 1 | 36906 | `Style.lean` | 0,0,0,0,1,0,0,0,0,1 | **1** |  |
| 2 | 37689 | `Basic.lean` | 0,1,0,0,0,0,0,0,0,0 | **1** |  |
| 3 | 31560 | `Sion.lean` | 0,0,0,0,0,0,0,0,0,0 | **0** |  |
| 4 | 36462 | `InnerProductSpace.lean` | 0,0,0,0,0,0,1,0,0,0 | **1** |  |
| 5 | 36243 | `Order.lean` | 0,0,1,0,0,0,1,0,0,0 | **1** |  |
| 6 | 37009 | `Basic.lean` | 1,0,0,0,2,0,1,2,0,0 | **2** | YES |
| 7 | 37610 | `Subgraph.lean` | 0,1,0,0,0,0,0,0,0,0 | **1** |  |
| 8 | 35939 | `HomologySequence.lean` | 0,0,0,0,0,0,0,0,0,0 | **0** |  |
| 9 | 36109 | `Luroth.lean` | 0,0,0,0,0,0,0,0,0,0 | **0** |  |
| 10 | 36532 | `Basic.lean` | 1,1,0,0,0,1,0,0,0,0 | **1** |  |
| 11 | 36908 | `Range.lean` | 0,0,1,0,1,0,0,0,1,0 | **1** |  |
| 12 | 36007 | `LieGroup.lean` | 0,0,2,0,0,1,0,0,0,0 | **2** | YES |
| 13 | 35670 | `Completeness.lean` | 1,0,1,0,0,0,0,0,0,0 | **1** |  |
| 14 | 37060 | `Indicator.lean` | 0,0,0,0,0,0,0,1,0,0 | **1** |  |
| 15 | 35586 | `Radical.lean` | 1,0,1,0,0,1,0,1,0,0 | **1** |  |
| 16 | 37009 | `StrictPositivity.lean` | 0,0,1,0,0,0,0,0,0,1 | **1** |  |
| 17 | 36996 | `FinitelyPresentedGroup.lean` | 0,0,1,0,0,0,0,0,0,0 | **1** |  |
| 18 | 37325 | `Hermitian.lean` | 1,0,0,1,0,1,0,0,0,0 | **1** |  |
| 19 | 33082 | `Simple.lean` | 0,1,0,0,0,0,1,0,0,0 | **1** |  |
| 20 | 36127 | `Basic.lean` | 0,0,0,0,0,0,0,0,0,0 | **0** |  |

---

## Example: queries with at least one DIRECT (label=2) hit


### PR #37009 — `Mathlib/Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean`
**Ground-truth reviewer comment:**
> Untested, but I have to imagine that this works.
```suggestion
lemma sqrt_of_not_nonneg {a : A} (ha : ¬0 ≤ a) : sqrt a = 0 := 
  cfc_apply_of_not_predicate _ ha
```

**Query hunk (excerpt):**
```
@@ -638,6 +647,10 @@ lemma sqrt_eq_cfc {a : A} : sqrt a = cfc NNReal.sqrt a := by
   unfold sqrt
   rw [cfcₙ_eq_cfc]
 
+lemma sqrt_of_not_nonneg {a : A} (ha : ¬0 ≤ a) : sqrt a = 0 := by
+  rw [sqrt_eq_cfc]
+  exact cfc_apply_of_not_predicate _ ha
```

**Top-10 LLM labels:** [1, 0, 0, 0, 2, 0, 1, 2, 0, 0]

  - **Rank 5 (label=2, sim=0.795):**
    - File: `Mathlib/Data/Real/Sqrt.lean` (PR #25856)
    - Rationale: Both comments suggest simplifying proofs by relying on the definitional equality of sqrt (i.e., unfolding sqrt) rather than extra rewriting/steps. The historical comment advises `unfold sqrt`, which is directly analogous to the new reviewer's suggestion to drop the `rw [sqrt_eq_cfc]` and use the definition directly.
    - Candidate comment: > ```suggestion
  unfold sqrt
```
Similarly here.

  - **Rank 8 (label=2, sim=0.753):**
    - File: `Mathlib/Data/Real/Sqrt.lean` (PR #25856)
    - Rationale: Both comments advise relying on the definition of sqrt directly (unfolding/using definitional equality) instead of extra rewrites/lemmas. The historical suggestion to `unfold sqrt` mirrors the new PR’s suggestion to drop `rw [sqrt_eq_cfc]` and use the definition directly, enabling a shorter proof.
    - Candidate comment: > ```suggestion
  unfold sqrt
```
I would like to be more declarative about what is happening here ... assuming this works.

### PR #36007 — `Mathlib/Geometry/Manifold/Algebra/LieGroup.lean`
**Ground-truth reviewer comment:**
> ```suggestion
    CMDiff n fun x ↦ f x / g x := by simp_rw [div_eq_mul_inv]; exact hf.mul hg.inv
```

**Query hunk (excerpt):**
```
@@ -138,41 +139,41 @@ end
 
 @[to_additive]
 theorem ContMDiffWithinAt.inv {f : M → G} {s : Set M} {x₀ : M}
-    (hf : ContMDiffWithinAt I' I n f s x₀) : ContMDiffWithinAt I' I n (fun x => (f x)⁻¹) s x₀ :=
+    (hf : CMDiffAt[s] n f x₀) : CMDiffAt[s] n (fun x => (f x)⁻¹) x₀ :=
   (contMDiff_inv I n).contMDiffAt.contMDiffWithinAt.comp x₀ hf <| Set.mapsTo_univ _ _
 
 @[to_additive]
-theorem ContMDif
```

**Top-10 LLM labels:** [0, 0, 2, 0, 0, 1, 0, 0, 0, 0]

  - **Rank 3 (label=2, sim=0.742):**
    - File: `Mathlib/Geometry/Manifold/Algebra/Monoid.lean` (PR #29459)
    - Rationale: Both comments address the same style issue: prefer using the ↦ (\mapsto) notation instead of `fun x =>`. The candidate explicitly requests \mapsto, matching the ground-truth suggestion that uses ↦ in the replacement.
    - Candidate comment: > Please use \mapsto, thanks!


## Example: hard queries (best label = 0)


### PR #31560 — `Mathlib/Topology/Sion.lean`
**Ground-truth reviewer comment:** > ```suggestion
  have hs' (x) (hx : x ∈ X) : ∃ y ∈ Subtype.val '' (s : Set Y), t < f x y := by
```
**Top-3 rationales:**
  - rank 1 (sim 0.729): Different issues. Ground-truth suggests formulating an existential over an image via Subtype.val; candidate tweaks the statement shape of an isSaddlePointOn_iff lemma with iInf/iSup equalities. No substantive overlap beyond general topic.
  - rank 2 (sim 0.725): Ground-truth suggests a precise Lean fix (explicit arguments, Subtype.val image for a set), while the candidate is a vague style/readability comment. No substantive overlap in the review point.
  - rank 3 (sim 0.671): Different concerns. Ground-truth suggests rewriting an existential with membership in Subtype.val '' (s : Set Y). Candidate suggests using an isClosed_iff lemma via IsInducing.subtypeVal, about closedness of subsets in subtypes. No substantive overla

### PR #35939 — `Mathlib/Algebra/Homology/DerivedCategory/HomologySequence.lean`
**Ground-truth reviewer comment:** > I think we at least prefer `erw` to track the defeq abuse as technical debt
**Top-3 rationales:**
  - rank 1 (sim 0.810): Ground-truth requests using `erw` to document defeq abuse; candidate suggests adding/adjusting `[simp]` and `@[reassoc]` attributes. Different concerns; no actionable overlap.
  - rank 2 (sim 0.807): Different issues: the ground-truth asks to use `erw` to make definitional-equality abuse explicit, while the candidate suggests adding `@[reassoc]`/`@[simp]` attributes to a lemma. No substantive overlap.
  - rank 3 (sim 0.803): Ground-truth is about tactic/style (use `erw` to track definal equality abuse), whereas candidate is about changing hypotheses (`NeZero n`) for an iso. Different issues; no actionable overlap.

### PR #36109 — `Mathlib/FieldTheory/RatFunc/Luroth.lean`
**Ground-truth reviewer comment:** > ```suggestion
  · exact C_ne_zero.mpr (div_ne_zero (algebraMap_ne_zero (generator E).denom_ne_zero) (c_ne_zero h))
```
**Top-3 rationales:**
  - rank 1 (sim 0.832): Ground-truth suggests a specific proof simplification using C_ne_zero.mpr and div_ne_zero; candidate is about extracting an irreducibility proof into a standalone lemma. Different issues (proof step vs code organization), no direct overlap.
  - rank 2 (sim 0.830): Different issue. The ground-truth suggests a specific proof refactor for a nonzeroness goal using C_ne_zero.mpr/div_ne_zero, while the candidate asks about extracting an instance. Same broader topic (Lüroth), but no overlapping advice.
  - rank 3 (sim 0.733): Ground-truth addresses proving non-zeroness via C_ne_zero/div_ne_zero/algebraMap_ne_zero; candidate is a meta remark about a rewrite not causing instance issues. Different concerns.