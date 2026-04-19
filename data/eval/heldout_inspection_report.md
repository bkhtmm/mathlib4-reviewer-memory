# Held-out retrieval — hand-inspection report

Each query is a mathlib reviewer comment created on/after **2026-03-01** on a
CLOSED PR. The index at query time was filtered to **before 2026-03-01** and
`exclude_pr=query.pr_number` so retrieval must find cross-PR, temporally-earlier
material. Max 2 hits per PR (MMR-lite). Similarity is cosine.

Bucket legend:
- **A_lexical_hit**: at least one top-10 hit shares >=30% tokens with ground truth (obvious win)
- **B_same_file_topical_only**: top-10 pulls from the same `.lean` file but low lexical overlap
- **C_no_obvious_match**: neither (worst case to inspect)

## Bucket: A_lexical_hit  (8 samples)

### A_lexical_hit — sample 1

- **Query PR**: #36817 — [Merged by Bors] - feat(Data/ENat): more lemma about WithBot ENat
- **File**: `Mathlib/Data/ENat/Basic.lean`  (line 622.0)
- **Reviewer**: `vihdzp`  **Topics**: `t-algebra`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Should this be made simp? Can this be made simp without breaking too many other things?

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -619,6 +619,8 @@ end ENat
   
   namespace ENat.WithBot
   
  +lemma coe_eq_natCast (n : ℕ) : (n : ℕ∞) = (n : WithBot ℕ∞) := rfl
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.837 | 0.00 | #1892 | `Data/ENat/Basic.lean` ← same file | `joneugster` | otdated. Removed this instance as uneeded. See [Zulip](https://leanprover.zulipchat.com/#narrow/stream/287929-mathlib4/topic/NatCast). |
| 2 | 0.836 | 0.00 | #1892 | `Data/ENat/Basic.lean` ← same file | `joneugster` | I don't yet understand how the different kinds of coersions interplay, but it always takes some `NatCast` instance coming from one of the derived structures, and ended up with w... |
| 3 | 0.809 | 0.00 | #11499 | `Data/ENNReal/Basic.lean` | `eric-wieser` | ```suggestion theorem coe_natCast (n : ℕ) : ((n : ℝ≥0) : ℝ≥0∞) = n := rfl ``` or `ofNNReal_natCast` |
| 4 | 0.798 | 0.00 | #24781 | `Data/ENNReal/Basic.lean` | `b-mehta` | ```suggestion ``` |
| 5 | 0.790 | 0.00 | #2723 | `Data/Nat/WithBot.lean` | `jcommelin` | This theorem already exists: `Nat.cast_withBot`. |
| 6 | 0.785 | 0.25 | #28582 | `Data/ENat/Basic.lean` ← same file | `YaelDillies` | What do you think of making this a simp lemma? |
| 7 | 0.785 | 0.00 | #28582 | `Data/ENat/Basic.lean` ← same file | `YaelDillies` | ```suggestion lemma WithBot.add_natCast_cancel {a b : WithBot ℕ∞} {c : ℕ} : a + c = b + c ↔ a = b := ``` Same below |
| 8 | 0.784 | 0.17 | #28582 | `Data/ENat/Basic.lean` ← same file | `YaelDillies` | That's a weak argument to me. There are plenty of simp lemmas I use backwards from time to time |
| 9 | 0.784 | 0.33 | #28582 | `Data/ENat/Basic.lean` ← same file | `YaelDillies` | I would make it simp |
| 10 | 0.784 | 0.00 | #28582 | `Data/ENat/Basic.lean` ← same file | `YaelDillies` | `a + c = b + c ↔ a = b` here means `a + Nat.cast c = b + Nat.cast c ↔ a = b`. Can we also have `a + ofNat(c) = b + ofNat(c) ↔ a = b` under the hypothesis `[n.AtLeastTwo]`? |

---

### A_lexical_hit — sample 2

- **Query PR**: #37470 — [Merged by Bors] - feat(SetTheory/Ordinal): add `add_iSup`, `mul_iSup` and friends
- **File**: `Mathlib/SetTheory/Ordinal/Family.lean`  (line 929.0)
- **Reviewer**: `vihdzp`  **Topics**: `t-set-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > I think this is a more useful version of that lemma.
  > ```suggestion
  >     o + sSup s = sSup ((o + ·) '' s) :=
  > ```
  > It should follow immediately from [`Order.IsNormal.map_sSup`](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Order/IsNormal.html#Order.IsNormal.map_sSup) and shouldn't require all the API you added.

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -920,18 +920,48 @@ theorem apply_omega0_of_isNormal {f : Ordinal.{u} → Ordinal.{v}} (hf : IsNorma
   alias IsNormal.apply_omega0 := apply_omega0_of_isNormal
   
   @[simp]
  -theorem iSup_add_natCast (o : Ordinal) : ⨆ n :...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.914 | 0.00 | #15820 | `SetTheory/Ordinal/Arithmetic.lean` | `YaelDillies` | ```suggestion   (add_isNormal o).apply_omega ``` to fix the diff |
| 2 | 0.902 | 0.00 | #15820 | `SetTheory/Ordinal/Arithmetic.lean` | `YaelDillies` | Same here. Please fix the diff by restoring the old proof |
| 3 | 0.854 | 0.00 | #15820 | `SetTheory/Ordinal/Arithmetic.lean` | `YaelDillies` | Might make it easier to read ```suggestion     ⨆ n : ℕ, f n = f ω := by rw [← iSup_natCast, hf.map_iSup] ``` |
| 4 | 0.853 | 0.00 | #15820 | `SetTheory/Ordinal/Arithmetic.lean` | `YaelDillies` | ```suggestion     ⨆ i : ℕ, f i = f ω := by rw [← iSup_natCast, hf.iSup] ``` |
| 5 | 0.829 | 0.00 | #15820 | `SetTheory/Ordinal/Arithmetic.lean` | `YaelDillies` | Is this not a general theorem about `ConditionallyCompleteLinearOrder`? |
| 6 | 0.826 | 0.07 | #15820 | `SetTheory/Ordinal/Arithmetic.lean` | `YaelDillies` | From the name, I would expect this lemma to be concluding `IsNormal (\Sup i, f i)`. While you are changing the name, maybe fix it ```suggestion theorem IsNormal.map_iSup {f : Or... |
| 7 | 0.803 | 0.06 | #16866 | `SetTheory/Ordinal/Arithmetic.lean` | `vihdzp` | Something else that would be nice to do (in this PR or otherwise) is deprecate `IsNormal.le_set`. I think all it's doing is state `f (Sup s) = Sup (f '' s)` in a more roundabout... |
| 8 | 0.803 | 0.41 | #16866 | `SetTheory/Ordinal/Arithmetic.lean` | `vihdzp` | We already have [`small_of_injective`](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Logic/Small/Basic.html#small_of_injective). |
| 9 | 0.786 | 0.00 | #16866 | `SetTheory/Ordinal/Arithmetic.lean` | `vihdzp` | This already exists as `IsNormal.map_iSup`. I think it would be good to have two versions: - One taking in a `BddAbove` argument as this one. - One that infers it whenever the... |
| 10 | 0.772 | 0.00 | #16866 | `SetTheory/Ordinal/Arithmetic.lean` | `vihdzp` | ```suggestion     (g : ι → Ordinal.{max u v}) [Nonempty ι] : f (sup.{_, v} g) = sup.{_, w} (f ∘ g) :=   H.map_iSup g ``` |

---

### A_lexical_hit — sample 3

- **Query PR**: #35664 — [Merged by Bors] - feat(SimpleGraph): the adjacency matrix of empty and complete graphs
- **File**: `Mathlib/Combinatorics/SimpleGraph/AdjMatrix.lean`  (line 168.0)
- **Reviewer**: `YaelDillies`  **Topics**: `t-combinatorics`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     (⊤ : SimpleGraph V).adjMatrix α = .of (fun _ _ ↦ 1) - 1 := by
  > ```
  > or is
  > ```suggestion
  >     (⊤ : SimpleGraph V).adjMatrix α = .of (fun i j ↦ if i = j then 0 else 1) := by
  > ```
  > better?

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -158,6 +158,17 @@ theorem adjMatrix_apply (v w : V) [Zero α] [One α] :
       G.adjMatrix α v w = if G.Adj v w then 1 else 0 :=
     rfl
   
  +@[simp]
  +theorem adjMatrix_bot_eq [Zero α] [One α] :
  +    (⊥ : SimpleGraph V)....
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.807 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | I would guess this is a good simp lemma in one direction or the other, perhaps another reviewer has an opinion. |
| 2 | 0.784 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | Why redeclare `(V)`? This means something different to `variable (V)` on the line before. |
| 3 | 0.778 | 0.40 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | This might be better stated about `G.adjMatrix _ + H.adjMatrix _` where `IsCompl G H`? |
| 4 | 0.776 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `b-mehta` | The all-ones matrix shows up quite a lot in combi and graph theory, @eric-wieser what do you think about making it a def? |
| 5 | 0.775 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `b-mehta` | `of 1` is short but it appears often enough that I think it deserves a name, and even if not probably some API. But this is orthogonal to the PR |
| 6 | 0.775 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | ```suggestion     (completeGraph V).adjMatrix α = of 1 - 1 := by ``` might be enough. |
| 7 | 0.775 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | Is `of 1` not short enough? |
| 8 | 0.761 | 0.00 | #34119 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | ```suggestion     G.adjMatrix α ⊙ a.cast = 0 :=   adjMatrix_hadamard_diagonal _ _ ``` etc, to make it clear that these are all the same lemma. |
| 9 | 0.759 | 0.00 | #34601 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `b-mehta` | ```suggestion theorem adjMatrix_completeGraph_eq_of_one_sub_one (α V) [AddGroup α] [One α] [DecidableEq V] : ``` |
| 10 | 0.753 | 0.00 | #34119 | `Combinatorics/SimpleGraph/AdjMatrix.lean` ← same file | `eric-wieser` | ```suggestion     G.adjMatrix α ⊙ ofNat(a) = 0 := by ext; simp_all [ofNat_apply] ``` |

---

### A_lexical_hit — sample 4

- **Query PR**: #33634 — [Merged by Bors] - feat(ValuationSubring): eq_self_or_eq_top_of_le
- **File**: `Mathlib/RingTheory/Valuation/ValuationSubring.lean`  (line 414.0)
- **Reviewer**: `dagurtomas`  **Topics**: `t-algebra`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >   obtain h | h := IsLocalRing.Ring.KrullDimLE.eq_bot_or_eq_top
  >     ((primeSpectrumEquiv A).symm ⟨B, hle⟩) 
  >   all_goals
  >     replace h := congrArg (primeSpectrumEquiv A) h
  >     simp_all
  > ```
  > This is more readable

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -401,6 +403,27 @@ instance linearOrderOverring : LinearOrder {S // A ≤ S} where
     max_def a b := congr_fun₂ sup_eq_maxDefault a b
     toDecidableLE := _
   
  +section
  +
  +variable [Ring.KrullDimLE 1 A] {B : ValuationSu...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.784 | 0.00 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `ocfnash` | Is it worth adding the following for the 1-dimensional case: ```suggestion  instance [IsDomain R] [Ring.KrullDimLE 1 R] [Nontrivial (PrimeSpectrum R)] :     IsSimpleOrder (Prime... |
| 2 | 0.784 | 0.00 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `erdOne` | I think we seldom see `Nontrivial (PrimeSpectrum R)` so this instance wouldn't usually fire anyways. |
| 3 | 0.767 | 0.00 | #33797 | `RingTheory/Valuation/ValuationSubring.lean` ← same file | `vihdzp` | We really should have some sort of abbrev `IsTotalLE`. ```suggestion instance le_total_ideal : @Std.Total {S // A ≤ S} (· ≤ ·) := by ``` |
| 4 | 0.753 | 0.00 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `erdOne` | ```suggestion     (x : PrimeSpectrum R) : x = ⊥ ∨ x = ⊤ :=   Order.krullDim_le_one_iff_of_boundedOrder.mp Order.KrullDimLE.krullDim_le _ ``` |
| 5 | 0.742 | 0.33 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `erdOne` | Yes this is what I was thinking of. Thanks! Sorry I should have been more clear. |
| 6 | 0.741 | 0.00 | #23778 | `RingTheory/KrullDimension/Zero.lean` | `erdOne` | I wonder if this means that the `eq_maximalIdeal_of_isPrime` can be generalized to primary ideals. |
| 7 | 0.739 | 0.00 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `erdOne` | I meant something like ```lean example {α : Type*} [Preorder α] [Order.KrullDimLE 1 α] [BoundedOrder α] {x : α} :     x = ⊥ ∨ x = ⊤ := by   convert Order.krullDim_le_one_iff... |
| 8 | 0.739 | 0.00 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `erdOne` | This should be a theorem about `Order.krullDimLE_one` and `BoundedOrder` instead, and then specialized to this. |
| 9 | 0.731 | 0.00 | #19111 | `Order/KrullDimension.lean` | `YaelDillies` | ```suggestion ``` |
| 10 | 0.726 | 0.00 | #33607 | `RingTheory/Spectrum/Prime/Topology.lean` | `erdOne` | ```suggestion theorem Ring.KrullDimLE.eq_bot_or_eq_top [IsDomain R] [Ring.KrullDimLE 1 R] ``` |

---

### A_lexical_hit — sample 5

- **Query PR**: #37009 — [Merged by Bors] - feat(CStarAlgebra): `Ring.inverse` is convex and antitone on strictly positive operators
- **File**: `Mathlib/Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean`  (line 652.0)
- **Reviewer**: `j-loreaux`  **Topics**: `t-analysis`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Untested, but I have to imagine that this works.
  > ```suggestion
  > lemma sqrt_of_not_nonneg {a : A} (ha : ¬0 ≤ a) : sqrt a = 0 := 
  >   cfc_apply_of_not_predicate _ ha
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -638,6 +647,10 @@ lemma sqrt_eq_cfc {a : A} : sqrt a = cfc NNReal.sqrt a := by
     unfold sqrt
     rw [cfcₙ_eq_cfc]
   
  +lemma sqrt_of_not_nonneg {a : A} (ha : ¬0 ≤ a) : sqrt a = 0 := by
  +  rw [sqrt_eq_cfc]
  +  exact cf...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.877 | 0.00 | #24859 | `Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean` ← same file | `eric-wieser` | Doesn't that mean that this theorem can lose this `ha` assumption? |
| 2 | 0.877 | 0.00 | #24859 | `Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean` ← same file | `eric-wieser` | What's it equal to for negative `a`? |
| 3 | 0.807 | 0.00 | #29592 | `Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean` ← same file | `j-loreaux` | You're in the unital section, can you please move this to the non-unital section?  Also, how do you feel about this instead? Then you can have a bunch of `0 ≤ a ↔ _` lemmas, s... |
| 4 | 0.807 | 0.00 | #29896 | `Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean` ← same file | `j-loreaux` | The hypothesis `0 ≤ a` is unnecessary if `A` is nontrivial, because if `sqrt a = 1 ≠ 0` then by the definition of `cfcₙ`, it must be the case that `0 ≤ a`.  Can you add a varian... |
| 5 | 0.795 | 0.00 | #25856 | `Data/Real/Sqrt.lean` | `mattrobball` | ```suggestion   unfold sqrt ``` Similarly here. |
| 6 | 0.782 | 0.00 | #3825 | `Data/Nat/Sqrt.lean` | `digama0` | TBH I'm still not entirely sure about how to indent tuples when multiline formatting is needed. Possibilities include using 1 space indent like this: ```lean   ⟨fun h => Nat.e... |
| 7 | 0.781 | 0.00 | #3825 | `Data/Nat/Sqrt.lean` | `digama0` | hanging `by` in tuple |
| 8 | 0.753 | 0.25 | #25856 | `Data/Real/Sqrt.lean` | `mattrobball` | ```suggestion   unfold sqrt ``` I would like to be more declarative about what is happening here ... assuming this works. |
| 9 | 0.752 | 0.00 | #26497 | `Data/Real/Sqrt.lean` | `b-mehta` | Let's use `x` here like the surrounding lemmas |
| 10 | 0.750 | 0.40 | #26497 | `Data/Real/Sqrt.lean` | `b-mehta` | ```suggestion @[simp] lemma isSquare_iff : IsSquare x ↔ 0 ≤ x := ``` untested, but should work |

---

### A_lexical_hit — sample 6

- **Query PR**: #36838 — [Merged by Bors] - feat(RingTheory/Unramified/Dedekind): a domain finite and unramified over a Dedekind domain is a D...
- **File**: `Mathlib/RingTheory/Unramified/Dedekind.lean`  (line 60.0)
- **Reviewer**: `erdOne`  **Topics**: `t-algebra,t-ring-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > `IsReduced (A / p) <-> p.IsRadical` probably should be a separate lemma as well.

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,80 @@
  +/-
  +Copyright (c) 2026 Thomas Browning. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Thomas Browning
  +-/
  +module
  +
  +public import Mathlib.RingTh...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.720 | 0.00 | #15123 | `RingTheory/Unramified/Field.lean` | `riccardobrasca` | The name is strange, isn't it? There is no `field` assumption. |
| 2 | 0.719 | 0.17 | #15123 | `RingTheory/Unramified/Field.lean` | `riccardobrasca` | Well, not really. Let's merge this, we can always change the name later. |
| 3 | 0.700 | 0.11 | #20690 | `RingTheory/Unramified/LocalRing.lean` | `chrisflav` | Maybe split the lemma at this point and have `IsField (S ⧸ mR)` as an intermediate, possibly useful instance? Some references use the "S / mR is a separable field extension" def... |
| 4 | 0.696 | 0.00 | #20690 | `RingTheory/Unramified/LocalRing.lean` | `chrisflav` | Can some of these become global instances? e.g. `EssFiniteType R (S ⧸ I)`? |
| 5 | 0.683 | 0.00 | #29924 | `RingTheory/DedekindDomain/PID.lean` | `kckennylau` | The proof below can be simplified: ```lean /-- A Dedekind domain is a PID if its set of primes is finite. -/ theorem IsPrincipalIdealRing.of_finite_primes [IsDedekindDomain R]... |
| 6 | 0.680 | 0.00 | #31061 | `RingTheory/DedekindDomain/UFD.lean` | `riccardobrasca` | This can be an instance, right? |
| 7 | 0.680 | 0.25 | #21522 | `RingTheory/DedekindDomain/IntegralClosure.lean` | `erdOne` | Can these be instances as well? Or rather, are they not `infer_instance` yet? |
| 8 | 0.679 | 0.00 | #20690 | `RingTheory/Unramified/LocalRing.lean` | `chrisflav` | Should these all be global instances? |
| 9 | 0.678 | 0.00 | #34928 | `RingTheory/Unramified/LocalRing.lean` | `chrisflav` | This should probably go into `Ideal.GoingUp`. |
| 10 | 0.677 | 0.33 | #34222 | `RingTheory/Etale/Field.lean` | `chrisflav` | Should this be a separate declaration? |

---

### A_lexical_hit — sample 7

- **Query PR**: #37325 — [Merged by Bors] - feat(Analysis/InnerProductSpace): transfer lemmas about charpoly/eigenvalues from matrix to linear...
- **File**: `Mathlib/Analysis/Matrix/Hermitian.lean`  (line 65.0)
- **Reviewer**: `themathqueen`  **Topics**: `t-analysis`
- **Ground-truth comment** (what the reviewer actually wrote):

  > same proof, just stylistically shorter
  > ```suggestion
  >   refine ⟨fun h _ _ ↦ by rw [h.eq], fun h ↦ ?_⟩
  >   simpa using (LinearMap.ext fun x ↦ ext_inner_right _ (h x)).symm
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -51,6 +52,18 @@ lemma isHermitian_iff_isSymmetric [Fintype n] [DecidableEq n] :
       ext i j
       simpa [(Pi.single_star i 1).symm] using h (Pi.single i 1) (Pi.single j 1)
   
  +/-- A version of `Matrix.isHermitian_if...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.835 | 0.40 | #26459 | `LinearAlgebra/Matrix/Hermitian.lean` | `EtienneC30` | Here's how to fix this proof: ```lean   simp only [toEuclideanLin_toLp, Matrix.toLin'_apply, EuclideanSpace.inner_eq_star_dotProduct,     WithLp.ofLp_toLp, star_mulVec] ``` |
| 2 | 0.768 | 0.00 | #28097 | `LinearAlgebra/Matrix/Hermitian.lean` | `j-loreaux` | ```suggestion protected alias ⟨IsHermitian.isSelfAdjoint, _root_.IsSelfAdjoint.isHermitian⟩ := isHermitian_iff_isSelfAdjoint ``` |
| 3 | 0.756 | 0.00 | #9312 | `Analysis/InnerProductSpace/Symmetric.lean` | `dupuisf` | ```suggestion     T.IsSymmetric ↔ LinearMap.IsSelfAdjoint (R := 𝕜) (M := E) (starRingEnd 𝕜) sesqFormOfInner T := ``` |
| 4 | 0.753 | 0.00 | #33316 | `Analysis/InnerProductSpace/Adjoint.lean` | `mcdoll` | ```suggestion     IsAdjointPair (innerₛₗ 𝕜 (E := E)).flip       (innerₛₗ 𝕜 (E := F)).flip A A.adjoint := by ``` I wonder whether this should be replaced by `IsAdjointPair in... |
| 5 | 0.749 | 0.00 | #11363 | `LinearAlgebra/Matrix/Spectrum.lean` | `j-loreaux` | ```suggestion   simpa only [eigenvectorBasis, OrthonormalBasis.reindex_apply, toEuclideanLin_apply,     RCLike.real_smul_eq_coe_smul (K := 𝕜)] using       congr(⇑$((isHermitian_... |
| 6 | 0.748 | 0.00 | #11363 | `LinearAlgebra/Matrix/Spectrum.lean` | `j-loreaux` | You can use dot notation to shorten this a bit.  ```suggestion   simp only [mulVec_eigenvectorBasis, dotProduct_smul,← EuclideanSpace.inner_eq_star_dotProduct,     inner_self_eq... |
| 7 | 0.742 | 0.00 | #11363 | `LinearAlgebra/Matrix/Spectrum.lean` | `j-loreaux` | This should already be in Mathlib  ```suggestion ``` |
| 8 | 0.734 | 0.00 | #25958 | `Analysis/InnerProductSpace/Adjoint.lean` | `j-loreaux` | To go with the other suggestions ```suggestion ``` |
| 9 | 0.720 | 0.00 | #11363 | `LinearAlgebra/Matrix/Spectrum.lean` | `j-loreaux` | ```suggestion /-- Unitary matrix whose columns are `Matrix.IsHermitian.eigenvectorBasis`. -/ ``` |
| 10 | 0.716 | 0.00 | #11363 | `LinearAlgebra/Matrix/Spectrum.lean` | `j-loreaux` | Maybe the last `eigenvectorBasis` doesn't fit. I didn't check. Dot notation again. ```suggestion   ⟨(EuclideanSpace.basisFun n 𝕜).toBasis.toMatrix (hA.eigenvectorBasis).toBasis,... |

---

### A_lexical_hit — sample 8

- **Query PR**: #36462 — [Merged by Bors] - feat(Geometry/Euclidean): integration formula for μHE
- **File**: `Mathlib/MeasureTheory/Measure/Haar/InnerProductSpace.lean`  (line 238.0)
- **Reviewer**: `EtienneC30`  **Topics**: `t-euclidean-geometry,t-measure-probability`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Can't you prove this "by definition"? For instance going through [Module.Basis.addHaar_eq_iff](https://leanprover-community.github.io/mathlib4_docs/Mathlib/MeasureTheory/Measure/Haar/OfBasis.html#Module.Basis.addHaar_eq_iff) (there might be some missing API).

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -233,3 +233,23 @@ theorem WithLp.volume_preserving_toLp : MeasurePreserving (@toLp 2 (U × V)) :=
     (volume_preserving_symm_measurableEquiv_toLp_prod U V).symm
   
   end Prod
  +
  +/-- Volume on a 1-dimensional real vect...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.815 | 0.04 | #34859 | `MeasureTheory/Measure/Haar/InnerProductSpace.lean` ← same file | `copilot-pull-request-reviewer` | These two theorems are missing documentation comments. Following the pattern of similar theorems in this file (e.g., `PiLp.volume_preserving_ofLp` at line 155 and `PiLp.volume_p... |
| 2 | 0.779 | 0.00 | #31190 | `MeasureTheory/Measure/Haar/InnerProductSpace.lean` ← same file | `j-loreaux` | ```suggestion theorem EuclideanSpace.volume_preserving_symm_measurableEquiv_toLp : ``` |
| 3 | 0.776 | 0.06 | #34859 | `MeasureTheory/Measure/Haar/InnerProductSpace.lean` ← same file | `copilot-pull-request-reviewer` | The comment should use "equivalences" (plural) instead of "equivalence" (singular) since it refers to "a series of known measure-preserving equivalences". ```suggestion -- Decom... |
| 4 | 0.765 | 0.00 | #6907 | `MeasureTheory/Measure/Haar/InnerProductSpace.lean` ← same file | `eric-wieser` | Same here: please copy the standard hack + comment, and put it at the top of the file. |
| 5 | 0.758 | 0.00 | #34859 | `MeasureTheory/Measure/Haar/InnerProductSpace.lean` ← same file | `b-mehta` | or perhaps calc could work? |
| 6 | 0.758 | 0.00 | #34859 | `MeasureTheory/Measure/Haar/InnerProductSpace.lean` ← same file | `eric-wieser` | Rather than writing these intermediate states as comments, you might be able to enter tactic mode and use `trans`. |
| 7 | 0.756 | 0.00 | #8249 | `MeasureTheory/Constructions/Pi.lean` | `eric-wieser` | Maybe worth mentioning that the motivation was "for consistency with other lemmas" |
| 8 | 0.756 | 0.00 | #8249 | `MeasureTheory/Constructions/Pi.lean` | `eric-wieser` | I think this change to implicit arguments is worth at least one of: * A mention in the PR description * A library note * A change to core to make this not necessary in the fi... |
| 9 | 0.747 | 0.37 | #14185 | `MeasureTheory/Constructions/Pi.lean` | `sgouezel` | Can't you deduce the sigma-finiteness of `mu i` from the one of `nu i` instead of assuming it, thanks to [MeasureTheory.MeasurePreserving.sigmaFinite](https://leanprover-communi... |
| 10 | 0.744 | 0.00 | #6907 | `MeasureTheory/Measure/Lebesgue/Complex.lean` | `eric-wieser` | Can you copy the standard comment here, and put it at the top of the file? |

---

## Bucket: B_same_file_topical_only  (10 samples)

### B_same_file_topical_only — sample 1

- **Query PR**: #33188 — [Merged by Bors] - feat(RingTheory/MvPowerSeries): introduce `rename`
- **File**: `Mathlib/Order/Filter/Cofinite.lean`  (line 303.0)
- **Reviewer**: `Ruben-VandeVelde`  **Topics**: `t-ring-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     TendstoCofinite (g ∘ f) :=
  >   tendstoCofinite_iff_finite_preimage_singleton.mpr (fun r ↦ by
  >     simpa using h.finite_preimage (h'.finite_preimage (by simp)))
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -274,3 +274,32 @@ lemma Function.update_eventuallyEq [DecidableEq α] (f : α → β) (a : α) (b
   lemma Function.update_eventuallyEq_cofinite [DecidableEq α] (f : α → β) (a : α) (b : β) :
       Function.update f a b =ᶠ[c...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.894 | 0.00 | #24147 | `Order/Filter/Cofinite.lean` ← same file | `b-mehta` | ```suggestion     (hf : ∀ b, Finite (f ⁻¹' {b})) : Tendsto f cofinite cofinite :=    fun _ h => h.preimage' fun b _ ↦ hf b ``` optional, but consistent with the previous |
| 2 | 0.887 | 0.00 | #24147 | `Order/Filter/Cofinite.lean` ← same file | `b-mehta` | ```suggestion     (hf : ∀ b, Finite (f ⁻¹' {b})) : Tendsto f cofinite cofinite := by ``` and similarly below, the `Filter.` prefixes shouldn't be needed |
| 3 | 0.886 | 0.00 | #24147 | `Order/Filter/Cofinite.lean` ← same file | `b-mehta` | oops, sorry! |
| 4 | 0.753 | 0.00 | #31242 | `Order/Filter/Cofinite.lean` ← same file | `kckennylau` | ```suggestion theorem le_cofinite_iff_ker (f : Filter α) : f ≤ cofinite ↔ f.ker = ∅ := by   rw [le_cofinite_iff_compl_singleton_mem, ker_def, iInter₂_eq_empty_iff]   refine f... |
| 5 | 0.728 | 0.00 | #15158 | `Topology/Algebra/InfiniteSum/Group.lean` | `riccardobrasca` | Also, I guess `DiscreteTopology should appear in the name. |
| 6 | 0.728 | 0.00 | #15158 | `Topology/Algebra/InfiniteSum/Group.lean` | `riccardobrasca` | `to_additive` chooses the name `Summable.finite_support` that is probably not what you want. |
| 7 | 0.727 | 0.00 | #15158 | `Topology/Algebra/InfiniteSum/Group.lean` | `riccardobrasca` | I mean that in the multiplicative version there is `mul`, but there is no `add` in the additive version. |
| 8 | 0.723 | 0.00 | #15744 | `Order/Filter/Cofinite.lean` ← same file | `sgouezel` | Can you add a docstring to this theorem and the next one? |
| 9 | 0.711 | 0.00 | #31242 | `Order/Filter/Cofinite.lean` ← same file | `kckennylau` | I feel like maybe we can extract some lemmas from this? 1. `f = 𝓟 f.ker ⊔ (f ⊓ 𝓟 f.kerᶜ)` 2. `f ⊓ 𝓟 f.kerᶜ ≤ cofinite` |
| 10 | 0.710 | 0.00 | #7628 | `Topology/DiscreteSubset.lean` | `ocfnash` | Nitpick, let's add some whitespace: ```suggestion end cofinite_cocompact  section codiscrete_filter ``` |

---

### B_same_file_topical_only — sample 2

- **Query PR**: #35670 — [Merged by Bors] - feat(RingTheory/AdicCompletion): completeness of `AdicCompletion`
- **File**: `Mathlib/RingTheory/AdicCompletion/Completeness.lean`  (line 115.0)
- **Reviewer**: `Ruben-VandeVelde`  **Topics**: `t-ring-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  > theorem restrictScalars_range_ofPowSMul_eq_ker_eval {n : ℕ} :
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,185 @@
  +/-
  +Copyright (c) 2026 Bingyu Xia. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Bingyu Xia
  +-/
  +module
  +
  +public import Mathlib.Algebra.Lie.OfA...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.973 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | ```suggestion @[stacks 05GG "(2)"] theorem pow_smul_top_eq_eval_ker {n : ℕ} (h : I.FG) : I ^ n • ⊤ = (eval I M n).ker := by ``` |
| 2 | 0.951 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | This section shouldn't be here. |
| 3 | 0.949 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | `open Classical` is usually really bad. |
| 4 | 0.939 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | And there is `Submodule.subtype` that you can use instead. |
| 5 | 0.939 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | `DirectSum` is usually for dependent products. Here it might be better to use `Finsupp` instead, e.g. something like ```lean lemma Finsupp.span_single_eq_top {R M σ : Type*} [Co... |
| 6 | 0.938 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | Please give definitions proper signatures. |
| 7 | 0.915 | 0.00 | #34936 | `RingTheory/AdicCompletion/Completeness.lean` ← same file | `erdOne` | Here the equality should be swapped, since we prefer putting the more complex side on the left. And `⊤` should be generalized to arbitrary `N : Submodule R M`, saying  `((algebr... |
| 8 | 0.755 | 0.00 | #12516 | `RingTheory/AdicCompletion/Basic.lean` | `erdOne` | Can you split out the second half of this lemma into `eval_surjective`? |
| 9 | 0.754 | 0.00 | #12516 | `RingTheory/AdicCompletion/Basic.lean` | `erdOne` | Maybe we can define this to be `{ f // ∀ {m n} (hmn : m ≤ n), AdicCompletion.transitionMap I M hmn (f n) = f m }` and ditch `adicCompletion` entirely? Similarly for `adicCauchyS... |
| 10 | 0.754 | 0.00 | #12516 | `RingTheory/AdicCompletion/Basic.lean` | `erdOne` | I suppose the proof that pointwise add and smul works is exactly the same proof as showing `adicCompletion` is a submodule. But if you will need it elsewhere then I think your s... |

---

### B_same_file_topical_only — sample 3

- **Query PR**: #29550 — [Merged by Bors] - feat(RingTheory): Order of vanishing in a discrete valuation ring
- **File**: `Mathlib/Algebra/Order/GroupWithZero/Canonical.lean`  (line 397.0)
- **Reviewer**: `riccardobrasca`  **Topics**: `t-ring-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > This lemma has nothing to do with order, can you move it to the appropriate place?

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -394,6 +394,9 @@ theorem le_ofAdd_iff
       a ≤ ofAdd b ↔ toAdd (unzero ha) ≤ b :=
     ⟨toAdd_unzero_le_of_lt_ofAdd ha, le_ofAdd_of_toAdd_unzero_le ha⟩
   
  +lemma map_multiplicative_eq_map {α β : Type*} :
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.825 | 0.00 | #31739 | `Algebra/Order/Monoid/Unbundled/TypeTags.lean` | `eric-wieser` | I guess this should arguably be deprecated. |
| 2 | 0.808 | 0.00 | #27042 | `Algebra/Order/GroupWithZero/Canonical.lean` ← same file | `YaelDillies` | Why are all these lemmas using `toAdd`/`ofAdd`? ☹️ We have `WithZero.log`/`WithZero.exp` which are much better suited |
| 3 | 0.804 | 0.00 | #1816 | `Algebra/Order/Hom/Basic.lean` | `fpvandoorn` | Oh, these are two declarations with the same additive version? Yeah, that happens sometimes. |
| 4 | 0.797 | 0.00 | #3449 | `Algebra/Order/Hom/Basic.lean` | `eric-wieser` | Ah nevermind, I understand what's happening here now (and it's not what you described).  Because this is `to_additive existing`, there is a line in another file that is manual... |
| 5 | 0.797 | 0.00 | #3449 | `Algebra/Order/Hom/Basic.lean` | `Parcly-Taxel` | With that line uncommented I get this error message: `le_map_add_map_sub has already been aligned (to le_map_add_map_sub)` Since `to_additive` has been improved to the point w... |
| 6 | 0.797 | 0.00 | #3449 | `Algebra/Order/Hom/Basic.lean` | `eric-wieser` | Why was this removed? |
| 7 | 0.797 | 0.13 | #3449 | `Algebra/Order/Hom/Basic.lean` | `Parcly-Taxel` | Because the current mathport output for the file has that exact same line in the exact same place. |
| 8 | 0.797 | 0.00 | #3449 | `Algebra/Order/Hom/Basic.lean` | `eric-wieser` | I don't understand what you mean, can you elaborate? |
| 9 | 0.787 | 0.00 | #22420 | `Algebra/Order/GroupWithZero/Canonical.lean` ← same file | `YaelDillies` | This is still true, but your proof breaks: ```suggestion lemma map'_strictMono {β : Type*} [MulOneClass α] [MulOneClass β] [Preorder β] ``` |
| 10 | 0.780 | 0.00 | #27108 | `Algebra/Order/GroupWithZero/Canonical.lean` ← same file | `YaelDillies` | ```suggestion lemma le_exp_log (x : Gᵐ⁰) :     x ≤ exp (log x) := by ``` no? I would also advise making `x` implicit |

---

### B_same_file_topical_only — sample 4

- **Query PR**: #35818 — [Merged by Bors] - chore(Tactic): rewrite `finiteness` tactic docstring
- **File**: `Mathlib/Tactic/Finiteness.lean`  (line 62.0)
- **Reviewer**: `joneugster`  **Topics**: `t-meta`
- **Ground-truth comment** (what the reviewer actually wrote):

  > I think having two lists directly following each other runs into the danger on them being merged, either by the human reader or by any markdown renderer:
  > 
  > > this is a test
  > > * first list
  > > * first list2 (newline after this line)
  > > 
  > > * completely new list
  > > * completely new list2
  > 
  > Could you restructure the docstring somehow to avoid this? (one option is to add a non-empty line in betwe...

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -49,11 +49,24 @@ set_option linter.unusedTactic false in
   add_aesop_rules safe tactic (rule_sets := [finiteness]) (by positivity)
   
   /-- `finiteness` proves goals of the form `*** < ∞` and (equivalently) `*** ≠ ∞`...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.932 | 0.05 | #34039 | `Tactic/Finiteness.lean` ← same file | `fpvandoorn` | ```suggestion \| `(tactic\| finiteness $c:Aesop.tactic_clause* [$h,+]) => ``` I believe you can use this to ensure that there is at least one argument (the next line doesn't... |
| 2 | 0.884 | 0.00 | #18034 | `Tactic/Finiteness.lean` ← same file | `YaelDillies` | Ah oops I forgot half the config indeed |
| 3 | 0.884 | 0.08 | #18034 | `Tactic/Finiteness.lean` ← same file | `b-mehta` | Let's add some tests for this. Currently ``` example {a : ℝ≥0∞} : a + 3 < ∞ := by    finiteness_nonterminal ``` fails with error that it didn't close the goal, which seems... |
| 4 | 0.881 | 0.00 | #18034 | `Tactic/Finiteness.lean` ← same file | `hrmacbeth` | I have since learned that there is a better syntax for this, something like (untested) ```suggestion   liftMetaFinishingTactic Mathlib.Meta.Positivity.positivity ``` |
| 5 | 0.877 | 0.00 | #18034 | `Tactic/Finiteness.lean` ← same file | `hrmacbeth` | I don't remember, but looking now at the `aesop` docs, it seems that the `-50` is a *penalty*, i.e. (since it is negative) actually an incentive to apply these rules. |
| 6 | 0.877 | 0.00 | #18034 | `Tactic/Finiteness.lean` ← same file | `b-mehta` | Oh! In that case I need to flip my question - why is `intros` given such a high incentive; it seems like introducing the hypothesis `x = ⊤` would be unhelpful? |
| 7 | 0.877 | 0.07 | #18034 | `Tactic/Finiteness.lean` ← same file | `hrmacbeth` | Very reasonable question :). I see that one of the tests in the PFR version of the tactic addresses this,  ```lean example {α : Type*} (f : α → ℕ) : ∀ i, (f i : ℝ≥0∞) ≠ ∞ := b... |
| 8 | 0.877 | 0.00 | #18034 | `Tactic/Finiteness.lean` ← same file | `YaelDillies` | Hmm, not sure. @hrmacbeth, did you have a specific rationale here? |
| 9 | 0.877 | 0.04 | #18034 | `Tactic/Finiteness.lean` ← same file | `JLimperg` | > Is there a way to hard-code in failure (a cut in the search tree, I guess) for something clearly false? @JLimperg  No, but I think this would be a very nice feature to have!... |
| 10 | 0.877 | 0.03 | #18034 | `Tactic/Finiteness.lean` ← same file | `JLimperg` | > It doesn't look like that hypothesis is ever being introduced (according to each of my experiments with `set_option trace.aesop true`), although I don't quite understand why -... |

---

### B_same_file_topical_only — sample 5

- **Query PR**: #37335 — [Merged by Bors] - feat(AlgebraicTopology/SimplicialSet): induction principles for nondegenerate simplices
- **File**: `Mathlib/AlgebraicTopology/SimplicialSet/NonDegenerateSimplices.lean`  (line 60.0)
- **Reviewer**: `robin-carlier`  **Topics**: `t-algebraic-topology`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     (mk : ∀ (n : ℕ) (x : X.nonDegenerate n), motive (mk x.val x.property)) (s : X.N) :
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -53,6 +53,14 @@ lemma mk_surjective (x : X.N) :
       ∃ (n : ℕ) (y : X.nonDegenerate n), x = N.mk _ y.prop :=
     ⟨x.dim, ⟨_, x.nonDegenerate⟩, rfl⟩
   
  +/-- Induction principle for the type `X.N` of nondegenerate simp...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.732 | 0.00 | #28224 | `AlgebraicTopology/SimplicialSet/NonDegenerateSimplices.lean` ← same file | `dagurtomas` | ```suggestion /-- The type of non degenerate simplices of a simplicial set. -/ structure N extends X.S where mk' ::   nonDegenerate : simplex ∈ X.nonDegenerate _  namespace N  v... |
| 2 | 0.732 | 0.00 | #28224 | `AlgebraicTopology/SimplicialSet/NonDegenerateSimplices.lean` ← same file | `dagurtomas` | ```suggestion   · obtain ⟨f, _, hf⟩ := le_iff_exists_mono.1 h.le ``` |
| 3 | 0.705 | 0.00 | #28330 | `AlgebraicTopology/SimplicialSet/NonDegenerateSimplicesSubcomplex.lean` | `robin-carlier` | ```suggestion   grind [cases SSet.Subcomplex.N] ``` |
| 4 | 0.704 | 0.00 | #28330 | `AlgebraicTopology/SimplicialSet/NonDegenerateSimplicesSubcomplex.lean` | `robin-carlier` | ```suggestion   notMem := hd ▸ s.notMem ``` |
| 5 | 0.696 | 0.00 | #28330 | `AlgebraicTopology/SimplicialSet/NonDegenerateSimplices.lean` ← same file | `robin-carlier` | ```suggestion   grind [cases SSet.N] ``` |
| 6 | 0.694 | 0.00 | #21098 | `AlgebraicTopology/SimplicialSet/Degenerate.lean` | `gio256` | ```suggestion /-- An `n`-simplex of a simplicial set `X` is degenerate if it is in the range ``` I'm not actually certain if "an `n`-simplex" or "a `n`-simplex" is correct, b... |
| 7 | 0.692 | 0.00 | #21103 | `AlgebraicTopology/SimplicialSet/Degenerate.lean` | `gio256` | Would it be more idiomatic to mark the definitions and lemmas in this section `private` so that they do not accidentally become part of the API here? |
| 8 | 0.684 | 0.00 | #28330 | `AlgebraicTopology/SimplicialSet/NonDegenerateSimplicesSubcomplex.lean` | `robin-carlier` | ```suggestion we introduce the type `A.N` of nondegenerate simplices of `X` ``` |
| 9 | 0.679 | 0.00 | #21098 | `AlgebraicTopology/SimplicialSet/Degenerate.lean` | `gio256` | Yes, my assumption (and experience so far) is that `[m]ₙ₊₁` is about as complex an expression as we would need for the truncation level. If that seems reasonable, I think I will... |
| 10 | 0.678 | 0.00 | #21098 | `AlgebraicTopology/SimplicialSet/Degenerate.lean` | `gio256` | Not blocking, but I'm curious what the convention is for taking inputs in the `SimplexCategory`. i.e., when should we use `(m : ℕ) (f : [n] ⟶ [m])` vs. `(m : SimplexCategory) (f... |

---

### B_same_file_topical_only — sample 6

- **Query PR**: #37635 — [Merged by Bors] - chore(Analysis/Analytic): tag `ofScalars_norm_eq_mul` with `simp`
- **File**: `Mathlib/Analysis/Analytic/OfScalars.lean`  (line 179.0)
- **Reviewer**: `themathqueen`  **Topics**: `t-analysis`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Probably a new PR so that this can stay on topic (i.e., adding `@[simp]`)

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -175,6 +175,7 @@ open scoped Topology NNReal
   variable {𝕜 : Type*} (E : Type*) [NontriviallyNormedField 𝕜] [SeminormedRing E]
       [NormedAlgebra 𝕜 E] (c : ℕ → 𝕜) (n : ℕ)
   
  +@[simp]
   theorem ofScalars_norm_eq_mul :
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.799 | 0.00 | #17274 | `Analysis/RCLike/Basic.lean` | `b-mehta` | Interesting personal preference, but okay |
| 2 | 0.798 | 0.00 | #17274 | `Analysis/RCLike/Basic.lean` | `b-mehta` | do you want q and x here too? |
| 3 | 0.784 | 0.00 | #9104 | `Data/IsROrC/Basic.lean` | `urkud` | Please make `K` explicit in this formula. It doesn't appear on either side of the formula. |
| 4 | 0.767 | 0.00 | #11551 | `Analysis/NormedSpace/Basic.lean` | `Ruben-VandeVelde` | I would move these up to the line `variable [NormedField 𝕜] [SeminormedAddCommGroup E] [SeminormedAddCommGroup F]` |
| 5 | 0.757 | 0.00 | #28690 | `Analysis/Normed/Module/Basic.lean` | `loefflerd` | I think you can weaken the typeclass assumptions substantially (`SeminormedRing` and `NormOneClass` should be sufficient). |
| 6 | 0.748 | 0.00 | #28690 | `Analysis/Normed/Module/Basic.lean` | `loefflerd` | ```suggestion @[simp] lemma norm_natCast (α) [SeminormedRing α] [NormSMulClass ℤ α] [NormOneClass α]     (n : ℕ) : ‖(n : α)‖ = n := by   simpa using norm_natCast_eq_mul_norm... |
| 7 | 0.745 | 0.00 | #19816 | `Analysis/NormedSpace/Multilinear/Basic.lean` | `sgouezel` | I don't think this change is useful: the lemma `opNorm_smul_le` is only used to get the normed space structure, and once you have it the general lemma `norm_smul` applies. |
| 8 | 0.745 | 0.00 | #17274 | `Analysis/RCLike/Basic.lean` | `b-mehta` | Is RCLike really the right generality for norm_expect_le? |
| 9 | 0.741 | 0.00 | #18326 | `Topology/ContinuousMap/Compact.lean` | `urkud` | Please prove a `nnnorm` version. If you prove it first, then this one is `mod_cast nnnorm_smul_const f b`. |
| 10 | 0.738 | 0.00 | #20151 | `Analysis/Analytic/OfScalars.lean` ← same file | `EtienneC30` | You can make this more general: ```suggestion @[simp] lemma coeff_ofScalars {𝕜 : Type*} [NontriviallyNormedField 𝕜] {p : ℕ → 𝕜} {n : ℕ} :     (ofScalars 𝕜 p).coeff n = p n :... |

---

### B_same_file_topical_only — sample 7

- **Query PR**: #35939 — [Merged by Bors] - feat(Algebra/Homology): a homology exact sequence for triangles of cochain complexes
- **File**: `Mathlib/Algebra/Homology/DerivedCategory/HomologySequence.lean`  (line 208.0)
- **Reviewer**: `dagurtomas`  **Topics**: `t-category-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > I think we at least prefer `erw` to track the defeq abuse as technical debt

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -176,3 +178,97 @@ lemma mono_homologyMap_mor₂_iff :
   end HomologySequence
   
   end DerivedCategory
  +
  +namespace CochainComplex
  +
  +open HomologicalComplex
  +
  +variable {C} (T : Triangle (CochainComplex C ℤ))
  +
  +/-- If...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.810 | 0.00 | #13664 | `Algebra/Homology/DerivedCategory/HomologySequence.lean` ← same file | `erdOne` | ```suggestion @[reassoc] lemma δ_comp : δ T n₀ n₁ h ≫ (homologyFunctor C n₁).map T.mor₁ = 0 := ``` Or ```suggestion @[reassoc (attr := simp)] lemma δ_comp : δ T n₀ n₁ h ≫... |
| 2 | 0.807 | 0.00 | #13664 | `Algebra/Homology/DerivedCategory/HomologySequence.lean` ← same file | `erdOne` | ```suggestion @[reassoc] lemma comp_δ : (homologyFunctor C n₀).map T.mor₂ ≫ δ T n₀ n₁ h = 0 := ``` Or ```suggestion @[reassoc (attr := simp)] lemma comp_δ : (homologyFunc... |
| 3 | 0.803 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `erdOne` | Can you also fix `homologyIsoPos` as well so that this takes `NeZero n`? Thanks. |
| 4 | 0.798 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `dagurtomas` | ```suggestion   simp ``` |
| 5 | 0.796 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `dagurtomas` | Could the `f_comm` assumption be wrapped in a typeclass `ConnectData.Compatible`, providing an instance `ConnectData.compatible_comp`, making this statement less cluttered and p... |
| 6 | 0.796 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `erdOne` | Is this the right direction? This seems to be in contradiction with the direction of `Functor.map_comp`. Of course the inverse direction couldn't be tagged simp, so the questio... |
| 7 | 0.796 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `dagurtomas` | Not really. This comes from a project, right? Is this useful as a simp lemma there? |
| 8 | 0.796 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `dagurtomas` | I see. I'm still not convinced that this should be a simp lemma at all, do you have evidence that this is a good simp lemma? Otherwise LGTM |
| 9 | 0.794 | 0.00 | #31224 | `Algebra/Homology/Embedding/Connect.lean` | `dagurtomas` | ```suggestion   simp ``` |
| 10 | 0.767 | 0.00 | #8771 | `Algebra/Homology/HomologySequence.lean` | `jcommelin` | ```suggestion     (k : ι) (hk : c.next j = k) : ``` |

---

### B_same_file_topical_only — sample 8

- **Query PR**: #36007 — [Merged by Bors] - chore(Geometry/Manifold/Algebra): golf using custom elaborators
- **File**: `Mathlib/Geometry/Manifold/Algebra/LieGroup.lean`  (line 176.0)
- **Reviewer**: `PatrickMassot`  **Topics**: `t-differential-geometry`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     CMDiff n fun x ↦ f x / g x := by simp_rw [div_eq_mul_inv]; exact hf.mul hg.inv
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -138,41 +139,41 @@ end
   
   @[to_additive]
   theorem ContMDiffWithinAt.inv {f : M → G} {s : Set M} {x₀ : M}
  -    (hf : ContMDiffWithinAt I' I n f s x₀) : ContMDiffWithinAt I' I n (fun x => (f x)⁻¹) s x₀ :=
  +    (hf :...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.781 | 0.00 | #9766 | `Geometry/Manifold/Algebra/LieGroup.lean` ← same file | `j-loreaux` | one more section heading, please. |
| 2 | 0.763 | 0.00 | #9775 | `Geometry/Manifold/Algebra/LieGroup.lean` ← same file | `ocfnash` | ```suggestion ``` |
| 3 | 0.742 | 0.00 | #29459 | `Geometry/Manifold/Algebra/Monoid.lean` | `grunweg` | Please use \mapsto, thanks! |
| 4 | 0.728 | 0.00 | #25159 | `Geometry/Manifold/ContMDiff/Basic.lean` | `sgouezel` | the to_additive version is missing a deprecation. Same thing for the next lemma. |
| 5 | 0.723 | 0.00 | #31278 | `Geometry/Manifold/ContMDiff/Basic.lean` | `grunweg` | Same comment as below about location. |
| 6 | 0.720 | 0.00 | #29459 | `Geometry/Manifold/Algebra/Monoid.lean` | `grunweg` | Question to fellow reviewers: is that the preferred style to write functions (as opposed to pow composed with g)? |
| 7 | 0.720 | 0.00 | #29459 | `Geometry/Manifold/Algebra/Monoid.lean` | `fpvandoorn` | This is definitely preferred over anything that involves `Function.comp`. If `g ^ m` works (I don't know if it does), then that's also ok. |
| 8 | 0.720 | 0.00 | #9775 | `Geometry/Manifold/Algebra/LieGroup.lean` ← same file | `ocfnash` | Is there a reason not to put these results together in one file? |
| 9 | 0.712 | 0.00 | #31278 | `Geometry/Manifold/ContMDiff/Basic.lean` | `grunweg` | Same, for at least the second one. Can you also add `mDifferentiableWithinAt_empty`? I believe I forgot that one. Thank you! |
| 10 | 0.710 | 0.00 | #19296 | `Geometry/Manifold/MFDeriv/Basic.lean` | `grunweg` | Flagging this explicitly: this was simply a missing API lemma, which you added as its smooth counterpart existed? |

---

### B_same_file_topical_only — sample 9

- **Query PR**: #36657 — [Merged by Bors] - feat(RingTheory): adds two lemmas on `Module.length`
- **File**: `Mathlib/RingTheory/Length.lean`  (line 304.0)
- **Reviewer**: `chrisflav`  **Topics**: `t-ring-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > While this proof is not too long, it is quite a round-about way of proving this (it goes through additivity of length). I would suggest to use a more order theoretic proof, which also gives some other useful lemmas on the way:
  > ```
  > lemma Order.coheight_lt_top {α : Type*} [Preorder α] [FiniteDimensionalOrder α] (x : α) :
  >     Order.coheight x < ⊤ := by
  >   rw [← WithBot.coe_lt_coe]
  >   apply lt_of_le_...

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -289,3 +289,16 @@ lemma Module.length_eq_finrank
       (K M : Type*) [DivisionRing K] [AddCommGroup M] [Module K M] [Module.Finite K M] :
       Module.length K M = Module.finrank K M := by
     simp [Module.length_of_f...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.865 | 0.00 | #23679 | `RingTheory/Length.lean` ← same file | `alreadydone` | Thank you! Can you please change [Submodule.comapMkQRelIso](https://leanprover-community.github.io/mathlib4_docs/Mathlib/LinearAlgebra/Quotient/Basic.html#Submodule.comapMkQRelI... |
| 2 | 0.846 | 0.00 | #24133 | `RingTheory/Length.lean` ← same file | `erdOne` | ```suggestion lemma Submodule.length_lt [IsArtinian R M] [IsNoetherian R M] {N : Submodule R M} (h : N < ⊤) :     Module.length R N < Module.length R M := by   simpa only [←... |
| 3 | 0.837 | 0.08 | #24133 | `RingTheory/Length.lean` ← same file | `riccardobrasca` | ```suggestion     StrictMono (Order.height : Submodule R M → ℕ∞) := ``` I find this more readable, but do as you prefer. |
| 4 | 0.818 | 0.04 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | This would be subsumed by `[IsSimpleModule R M] : Module.length R M = 1` (this is actually iff, and we also know `IsSimpleModule R R` iff R is a division ring: [isSimpleModule_... |
| 5 | 0.812 | 0.00 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | ```suggestion   revert ι   apply Fintype.induction_empty_option ``` |
| 6 | 0.809 | 0.00 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | It turns out this one doesn't require StrongRankCondition (see [this commit](https://github.com/leanprover-community/mathlib4/commit/c7b0ae8f94cd272ffb8c3dd0a17835fd14f13f80)) b... |
| 7 | 0.809 | 0.00 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | I think we don't need to assume `StrongRankCondition R`, because if it fails then `Module.length R R = ⊤`~~; I'll submit a separate PR for this fact~~. |
| 8 | 0.809 | 0.05 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | Hmm, currently lengths are only defined over a CommRing, but we certainly want to e.g. compute the length of a matrix ring over itself (this is also how one recovers dimension i... |
| 9 | 0.809 | 0.00 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | The rest of my commit is PR'd to #23729. |
| 10 | 0.799 | 0.00 | #23682 | `RingTheory/Length.lean` ← same file | `alreadydone` | This is still true if `ι` is infinite because [Finsupp.lcoeFun](https://leanprover-community.github.io/mathlib4_docs/Mathlib/LinearAlgebra/Finsupp/Pi.html#Finsupp.lcoeFun) is in... |

---

### B_same_file_topical_only — sample 10

- **Query PR**: #36613 — [Merged by Bors] - refactor(CategoryTheory): one-field structure morphisms in the category of types
- **File**: `Mathlib/AlgebraicTopology/SimplicialNerve.lean`  (line 193.0)
- **Reviewer**: `robin-carlier`  **Topics**: `t-category-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     change EnrichedFunctor.comp SSet (SimplicialThickening.functor OrderHom.id) _ = _
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -213,17 +183,20 @@ The simplicial nerve of a simplicial category `C` is defined as the simplicial s
   `n`-simplices are given by the set of simplicial functors from the simplicial thickening of
   the linear order `Fi...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.864 | 0.00 | #19837 | `AlgebraicTopology/SimplicialNerve.lean` ← same file | `jcommelin` | As discussed in the other thread, I think we can make it a global simp lemma |
| 2 | 0.830 | 0.00 | #19057 | `AlgebraicTopology/SimplicialSet/Nerve.lean` | `joelriou` | ```suggestion def nerveFunctor : Cat.{v, u} ⥤ SSet where ``` |
| 3 | 0.792 | 0.00 | #31250 | `AlgebraicTopology/SimplicialSet/StrictSegal.lean` | `emilyriehl` | This reminds me that PR #25775 also modified this to be computable. I mention this just as an FYI in case anything there is useful. |
| 4 | 0.771 | 0.00 | #31250 | `AlgebraicTopology/SimplicialSet/StrictSegal.lean` | `robin-carlier` | ```suggestion           ((Arrow.mk_eq_mk_iff _ _).1             (DFunLike.congr_arg ComposableArrows.arrowEquiv h)).2.2 }) ``` |
| 5 | 0.733 | 0.00 | #25780 | `AlgebraicTopology/SimplicialSet/StdSimplex.lean` | `joelriou` | As I encountered similar definitions in my formalization of the homotopy theory of simplicial sets, I would suggest using the following two definitions which also uses your defi... |
| 6 | 0.731 | 0.00 | #11398 | `AlgebraicTopology/SimplicialCategory/Basic.lean` | `dagurtomas` | ```suggestion that it applies in particular to simplicial sets ``` |
| 7 | 0.729 | 0.00 | #28395 | `AlgebraicTopology/SimplicialSet/StdSimplex.lean` | `robin-carlier` | ```suggestion       left_inv _ := by aesop })) ``` auto-param finds `right_inv`. |
| 8 | 0.726 | 0.00 | #7999 | `CategoryTheory/ComposableArrows.lean` | `jcommelin` | I can imagine it might occasionally be useful to have this equality available for rewriting. Should it just get a name? |
| 9 | 0.726 | 0.00 | #7999 | `CategoryTheory/ComposableArrows.lean` | `jcommelin` | ```suggestion definitionally equal to `ComposableArrows C n`. -/ ``` |
| 10 | 0.723 | 0.00 | #21885 | `AlgebraicTopology/SimplicialSet/Nerve.lean` | `joelriou` | ```suggestion ``` |

---

## Bucket: C_no_obvious_match  (10 samples)

### C_no_obvious_match — sample 1

- **Query PR**: #36834 — [Merged by Bors] - feat(Tactic/Simps): add option to dsimplify LHS
- **File**: `MathlibTest/Simps.lean`  (line 871.0)
- **Reviewer**: `eric-wieser`  **Topics**: `t-meta`
- **Ground-truth comment** (what the reviewer actually wrote):

  > I think it's fine to skip the `symm_apply` assertions, if the goal is just to demonstrate a justification via the `_apply` lemmas alone.

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -833,6 +833,64 @@ example {α β γ δ : Type _} (x : α) (e₁ : α ≃ β) (e₂ : γ ≃ δ) (z
   
   end PrefixProjectionNames
   
  +namespace DsimpLhs
  +
  +structure Functor where
  +  obj : Type → Type
  +  map {X Y : Type} (f : X → Y) :...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.770 | 0.10 | #33888 | `CategoryTheory/NatIso.lean` | `robin-carlier` | Just a comment and not a suggestion: hopefully one day `rotate_isos%` will be alive and we won’t have to add extra lemmas for this. |
| 2 | 0.758 | 0.00 | #8541 | `CategoryTheory/NatIso.lean` | `jcommelin` | We often use `copy` as the name for a decl that changes some data up to propeq, for better defeqs. Since you only change `obj`, maybe this could be called ```suggestion def co... |
| 3 | 0.736 | 0.00 | #23197 | `CategoryTheory/Equivalence.lean` | `joelriou` | This should be in the `Equivalence` namespace. (I do not think dot notation is an option here, there this is very specific to isomorphisms in the category of equivalences.) I a... |
| 4 | 0.710 | 0.00 | #23197 | `CategoryTheory/Equivalence.lean` | `joelriou` | ```suggestion def functorFunctor : (C ≌ D) ⥤ C ⥤ D where ``` |
| 5 | 0.707 | 0.00 | #23197 | `CategoryTheory/Equivalence.lean` | `joelriou` | ```suggestion @[simp, reassoc] ``` |
| 6 | 0.707 | 0.00 | #23197 | `CategoryTheory/Equivalence.lean` | `joelriou` | ```suggestion @[simp, reassoc] ``` |
| 7 | 0.704 | 0.00 | #23197 | `CategoryTheory/Equivalence.lean` | `joelriou` | ```suggestion     mkHom (α ≫ β) = mkHom α ≫ mkHom β := ``` |
| 8 | 0.701 | 0.00 | #6261 | `CategoryTheory/Equivalence.lean` | `kbuzzard` | ```suggestion   /-- The natural isomorphisms compose to the identity. -/ ``` |
| 9 | 0.696 | 0.03 | #31807 | `CategoryTheory/Category/Cat.lean` | `callesonne` | Hmmm, I thought since it was an abbrev that one would not need to duplicate the API? But maybe even reducibly def-eq will be a problem for simp to detect, so we need to duplicat... |
| 10 | 0.696 | 0.02 | #31807 | `CategoryTheory/Category/Cat.lean` | `callesonne` | This example seems quite strange to me, as it is not something you should be doing anyways (looking at equalities of functors). I don' t think you should be looking at functors... |

---

### C_no_obvious_match — sample 2

- **Query PR**: #36906 — [Merged by Bors] - fix: don't lint imports for line length
- **File**: `Mathlib/Tactic/Linter/Style.lean`  (line 452.0)
- **Reviewer**: `tb65536`  **Topics**: `t-linter`
- **Ground-truth comment** (what the reviewer actually wrote):

  > hold on... you're telling me that all this time I could have just been adding `-- http` to the end of my long lines to disable the linter?

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -443,7 +449,7 @@ def longLineLinter : Linter where run := withSetOptionIn fun stx ↦ do
       let longLines := ((sstr.getD default).splitOn "\n").filter fun line ↦
         (100 < (fm.toPosition line.stopPos).column)...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.879 | 0.00 | #16652 | `Tactic/Linter/Lint.lean` | `kim-em` | ```suggestion           "\nYou can use \"string gaps\" to format long strings: within a string quotation, \ ``` |
| 2 | 0.877 | 0.00 | #16652 | `Tactic/Linter/Lint.lean` | `kim-em` | ```suggestion           using a '\' at the end of a line allows you to continue the string on the following line, removing all \ ``` |
| 3 | 0.851 | 0.00 | #16652 | `Tactic/Linter/Lint.lean` | `kim-em` | ```suggestion ``` |
| 4 | 0.806 | 0.09 | #17309 | `Tactic/Linter/Lint.lean` | `grunweg` | Good idea to add a comment! ```suggestion     -- In this case, the file has an allowed length, and the linter option is unnecessarily set. |
| 5 | 0.802 | 0.00 | #17309 | `Tactic/Linter/Lint.lean` | `grunweg` | ```     -- Note that either `lastLine ≤ defValue` and `defValue = linterBound` hold or     -- `candidate` is necessarily bigger than `lastLine` and hence bigger than `defValue`. |
| 6 | 0.802 | 0.00 | #17309 | `Tactic/Linter/Lint.lean` | `grunweg` | Note to self: triple-check this logic; I am not fully convinced any more that these are *all* possible cases. |
| 7 | 0.792 | 0.00 | #17309 | `Tactic/Linter/Lint.lean` | `grunweg` | Can you check that some test fails if you remove the second condition in the `if`? If not, please add a test :-) |
| 8 | 0.789 | 0.00 | #2190 | `scripts/lint-style.py` | `eric-wieser` | ```suggestion         # "!" excludes the porting marker comment         if "http" in line or "#align" in line or line[0] == '!': ``` |
| 9 | 0.786 | 0.08 | #15180 | `Tactic/Linter/Lint.lean` | `kmill` | I believe this is available: ```suggestion         let contents := (← getFileMap).source ```  You could also save rebuilding the filemap by creating the input context yours... |
| 10 | 0.769 | 0.00 | #17309 | `Tactic/Linter/Lint.lean` | `grunweg` | Fair enough: I'm also won't object to not verifying that situation super closely. |

---

### C_no_obvious_match — sample 3

- **Query PR**: #34204 — [Merged by Bors] - feat(LinearAlgebra/QuadraticForm): Sylvester's law of inertia
- **File**: `Mathlib/LinearAlgebra/QuadraticForm/Signature.lean`  (line 63.0)
- **Reviewer**: `vihdzp`  **Topics**: `t-algebra`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Why the casing? Isn't the bottom submodule vacuously positive definite?

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,228 @@
  +/-
  +Copyright (c) 2026 David Loeffler. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: David Loeffler
  +-/
  +
  +module
  +
  +public import Mathlib.Linea...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.689 | 0.00 | #7569 | `LinearAlgebra/QuadraticForm/Basic.lean` | `trivial1711` | - This section should be in the namespace `QuadraticForm` instead of `QuadraticMap`. - Every occurrence of `QuadraticMap` in this section should be replaced with `QuadraticForm`. |
| 2 | 0.689 | 0.00 | #34493 | `LinearAlgebra/QuadraticForm/Radical.lean` | `riccardobrasca` | Is it possible to unsqueeze the simp? |
| 3 | 0.672 | 0.00 | #34493 | `LinearAlgebra/QuadraticForm/Radical.lean` | `riccardobrasca` | ```suggestion /-- If `2` is invertible in the coefficient ring, the radical of a quadratic map is the kernel of its ``` |
| 4 | 0.672 | 0.00 | #34493 | `LinearAlgebra/QuadraticForm/Radical.lean` | `riccardobrasca` | ```suggestion /-- If `2` is invertible in the coefficient ring, the radical of a quadratic map is the kernel of its ``` |
| 5 | 0.668 | 0.00 | #34493 | `LinearAlgebra/QuadraticForm/Radical.lean` | `riccardobrasca` | ```suggestion /-- In characteristic different from `2`, a quadratic map is nondegenerate iff its associated bilinear map ``` If you like. |
| 6 | 0.665 | 0.00 | #34493 | `LinearAlgebra/QuadraticForm/Radical.lean` | `riccardobrasca` | Same as above. |
| 7 | 0.663 | 0.00 | #7569 | `LinearAlgebra/QuadraticForm/Basic.lean` | `eric-wieser` | Can you split this to its own PR (in the right place), then ask for help with `ring` on zulip? |
| 8 | 0.661 | 0.00 | #34493 | `LinearAlgebra/QuadraticForm/Radical.lean` | `riccardobrasca` | Can you use the bibtex entry? |
| 9 | 0.657 | 0.00 | #4432 | `LinearAlgebra/QuadraticForm/Basic.lean` | `Vierkantor` | I recall that we decided to only port the `FunLike` instances and skip the `CoeFun` instances (as also suggested by the comment in `LinearMap`). Did we change this at some point? |
| 10 | 0.656 | 0.00 | #4432 | `LinearAlgebra/QuadraticForm/Basic.lean` | `Vierkantor` | ```suggestion /-- The `simp` normal form for a quadratic form is `FunLike.coe`, not `toFun`. -/ ``` |

---

### C_no_obvious_match — sample 4

- **Query PR**: #36613 — [Merged by Bors] - refactor(CategoryTheory): one-field structure morphisms in the category of types
- **File**: `Mathlib/CategoryTheory/Limits/Shapes/ConcreteCategory.lean`  (line 114.0)
- **Reviewer**: `robin-carlier`  **Topics**: `t-category-theory`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     (Types.isTerminalEquivUnique (ToType X)).symm h
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -102,12 +105,13 @@ singleton. -/
   @[implicit_reducible]
   noncomputable def uniqueOfTerminalOfPreserves [PreservesLimit (Functor.empty.{0} C) (forget C)]
       (X : C) (h : IsTerminal X) : Unique (ToType X) :=
  -  Typ...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.727 | 0.00 | #17701 | `CategoryTheory/ChosenFiniteProducts.lean` | `joelriou` | ```suggestion lemma preservesTerminalIso_hom [PreservesLimit (Functor.empty.{0} C) F] : ``` |
| 2 | 0.725 | 0.00 | #17701 | `CategoryTheory/ChosenFiniteProducts.lean` | `joelriou` | ```suggestion def preservesTerminalIso [h : PreservesLimit (Functor.empty.{0} C) F] : F.obj (𝟙_ C) ≅ 𝟙_ D := ``` |
| 3 | 0.708 | 0.00 | #25784 | `CategoryTheory/Monoidal/Cartesian/Cat.lean` | `b-mehta` | one more non-terminal simp here! |
| 4 | 0.708 | 0.00 | #23702 | `CategoryTheory/Comma/Over/Pullback.lean` | `joelriou` | The docstring should be fixed. Also, I would suggest making explicit the parameter in the LHS `forget _ ≅...`. |
| 5 | 0.708 | 0.00 | #23702 | `CategoryTheory/Comma/Over/Pullback.lean` | `joelriou` | The current docstring may suggest this is the definition of an equivalence of categories (or that a functor is an equivalence). |
| 6 | 0.708 | 0.00 | #3709 | `Topology/Category/Top/Limits/Basic.lean` | `kim-em` | These should not have been removed? They are still there in mathlib. |
| 7 | 0.706 | 0.00 | #12502 | `Topology/Category/TopCat/Limits/Basic.lean` | `joelriou` | I am not sure there is a need for this change. If `by continuity` works in reasonable time, there is no need to change it by an explicit term. |
| 8 | 0.704 | 0.00 | #25781 | `CategoryTheory/Category/Cat/Terminal.lean` | `joelriou` | It would be nice to insert an instance: ```lean instance : HasTerminal Cat.{v, u} :=   IsTerminal.hasTerminal (X := Cat.of.{v, u} (ShrinkHoms PUnit)) (by     sorry) ``` so... |
| 9 | 0.701 | 0.00 | #25784 | `CategoryTheory/Monoidal/Cartesian/Cat.lean` | `b-mehta` | Yeah, that makes complete sense to me. |
| 10 | 0.700 | 0.00 | #25781 | `CategoryTheory/Category/Cat/Terminal.lean` | `joelriou` | ```suggestion noncomputable def terminalIsoOfUniqueOfIsDiscrete ``` |

---

### C_no_obvious_match — sample 5

- **Query PR**: #36489 — [Merged by Bors] - feat(Order/Partition/Finpartition): add `toSubtype` constructor
- **File**: `Mathlib/Data/Finset/Preimage.lean`  (line 138.0)
- **Reviewer**: `YaelDillies`  **Topics**: `t-order`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >   have hfinvs : ∀ x ∈ s, (f ∘ invFunOn f (f ⁻¹' ↑s)) x = id x := hf.invOn_invFunOn.2
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -131,6 +130,30 @@ theorem subset_map_iff {f : α ↪ β} {s : Finset β} {t : Finset α} :
     classical
     simp_rw [map_eq_image, subset_image_iff, eq_comm]
   
  +@[simp]
  +theorem sup_preimage_eq_sup_id_of_bij {α β : Type*}...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.840 | 0.00 | #33844 | `Order/CompleteLattice/Basic.lean` | `urkud` | You can just rewrite on `hf.image_eq`, then `iSup_image`. Also, please add `iUnion`/`iInter` versions. |
| 2 | 0.810 | 0.00 | #7382 | `Data/Finset/Sups.lean` | `eric-wieser` | At the point you're carrying around a separate `hf` assumption though, you can use `card_image` instead.  To be clear, I don't think this lemma does any harm, but I am surpris... |
| 3 | 0.810 | 0.00 | #7382 | `Data/Finset/Sups.lean` | `eric-wieser` | I think the awkward `map ⟨f, hf⟩` phrasing combined with the fact this assumes `[DecidableEq β]` means this lemma is probably never going to be useful. |
| 4 | 0.805 | 0.00 | #9377 | `Data/Finset/Lattice.lean` | `YaelDillies` | For rewriting, can we have the same lemma but turned around and with `(hs : s.Nonempty)`? Same elsewhere |
| 5 | 0.805 | 0.00 | #7382 | `Data/Finset/Sups.lean` | `eric-wieser` | ```suggestion lemma subset_sups_self : s ⊆ s ⊻ s := fun _a ha ↦ mem_sups.2 ⟨_, ha, _, ha, sup_idem⟩ ``` |
| 6 | 0.790 | 0.00 | #8735 | `Data/Finset/Lattice.lean` | `YaelDillies` | That's just `map_finset_sup` + `comp_id` |
| 7 | 0.787 | 0.00 | #7382 | `Data/Finset/Sups.lean` | `eric-wieser` | (and for the `Set` and `infs` versions) |
| 8 | 0.787 | 0.00 | #7382 | `Data/Finset/Sups.lean` | `eric-wieser` | To distinguish these from the lemma above, I think they should end in `_iff` |
| 9 | 0.785 | 0.00 | #12555 | `Data/Set/Function.lean` | `YaelDillies` | ```suggestion     (hrt : r ⊆ t) : f '' f.invFunOn s '' r = r := ``` |
| 10 | 0.785 | 0.00 | #12555 | `Data/Set/Function.lean` | `YaelDillies` | Why are you keeping the brackets? |

---

### C_no_obvious_match — sample 6

- **Query PR**: #33375 — [Merged by Bors] - feat(Probability): Local and stable properties
- **File**: `Mathlib/Probability/Process/LocalProperty.lean`  (line 166.0)
- **Reviewer**: `EtienneC30`  **Topics**: `t-measure-probability`
- **Ground-truth comment** (what the reviewer actually wrote):

  > I am guessing `suffices ... generalizing p` would avoid the duplication here.

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,398 @@
  +/-
  +Copyright (c) 2025 Rémy Degenne. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Rémy Degenne, Kexing Ying
  +-/
  +module
  +
  +public import Mathli...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.617 | 0.00 | #33063 | `Probability/Process/Adapted.lean` | `EtienneC30` | ```suggestion * `MeasureTheory.StronglyAdapted`: a sequence of functions `u` is said to be strongly adapted to a ``` |
| 2 | 0.616 | 0.00 | #33063 | `Probability/Process/Adapted.lean` | `EtienneC30` | We rather use "filtration". ```suggestion (progressively measurable) with respect to a filtration `f`, and proves some basic facts about them. ``` |
| 3 | 0.610 | 0.00 | #29430 | `Probability/Process/Stopping.lean` | `LorenzoLuccioli` | ```suggestion   refine fun s hs ↦ ⟨hs.1, fun i ↦ ?_⟩ ``` |
| 4 | 0.604 | 0.00 | #29430 | `Probability/Process/HittingTime.lean` | `LorenzoLuccioli` | ```suggestion     refine fun m hm hτ ↦ hm.trans_le <\| le_hittingBtwn ?_ x ``` |
| 5 | 0.600 | 0.00 | #29430 | `Probability/Martingale/BorelCantelli.lean` | `LorenzoLuccioli` | ```suggestion     rw [stoppedAbove, stoppedProcess, leastGE, hittingAfter_eq_top_iff.mpr] ``` |
| 6 | 0.595 | 0.00 | #29430 | `Probability/Martingale/BorelCantelli.lean` | `LorenzoLuccioli` | ```suggestion   have ht : ∀ᵐ ω ∂μ, ∀ i : ℕ, ∃ c, Tendsto (fun n => stoppedAbove f i n ω) atTop (𝓝 c) := by ``` |
| 7 | 0.590 | 0.00 | #29430 | `Probability/Martingale/BorelCantelli.lean` | `LorenzoLuccioli` | ```suggestion   rw [stoppedAbove, stoppedProcess, ENat.some_eq_coe] ``` |
| 8 | 0.590 | 0.00 | #32882 | `Probability/Process/Adapted.lean` | `RemyDegenne` | ```suggestion * `MeasureTheory.StronglyAdapted`: a sequence of functions `u` is said to be strongly adapted to a ``` |
| 9 | 0.587 | 0.00 | #34381 | `Probability/Process/HittingTime.lean` | `RemyDegenne` | ```suggestion     [WellFoundedLT ι] [Countable ι] {mβ : MeasurableSpace β} {f : Filtration ι m} {u : ι → Ω → β} ``` |
| 10 | 0.580 | 0.00 | #29430 | `Probability/Process/Stopping.lean` | `kex-y` | Can you add a lemma saying if \sigma is a.s. finite then we have a.s. equality? |

---

### C_no_obvious_match — sample 7

- **Query PR**: #35559 — [Merged by Bors] - feat(Analysis/Normed): weak-topology embedding into weak-star bidual and compactenss transfer theorem
- **File**: `Mathlib/Analysis/Normed/Module/DoubleDual.lean`  (line 128.0)
- **Reviewer**: `j-loreaux`  **Topics**: `t-analysis`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Since it's actually an embedding, we can remove this entirely and still anything that uses dot notation can just use the `IsEmbedding` version through the magic of `extends`.
  > ```suggestion
  > ```

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,165 @@
  +/-
  +Copyright (c) 2020 Heather Macbeth. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Heather Macbeth, Michał Świętek
  +-/
  +module
  +
  +public impo...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.765 | 0.00 | #27699 | `Analysis/Normed/Module/WeakDual.lean` | `themathqueen` | ```suggestion theorem toStrongDual_apply (x : WeakDual 𝕜 E) (y : E) : (toStrongDual x) y = x y := ``` with a deprecation. Same goes for the next two results below. |
| 2 | 0.756 | 0.00 | #4351 | `Analysis/NormedSpace/WeakDual.lean` | `mcdoll` | Shouldn't the RHS just be `WeakDual.instTopologicalSpace 𝕜 E`? For the RHS maybe just check what `infer_instance` outputs |
| 3 | 0.723 | 0.00 | #27699 | `Analysis/Normed/Module/WeakDual.lean` | `themathqueen` | ```suggestion `StrongDual 𝕜 E → WeakDual 𝕜 E` is continuous. This definition implements it as a continuous linear ``` |
| 4 | 0.679 | 0.00 | #27699 | `Analysis/InnerProductSpace/Dual.lean` | `themathqueen` | uh, can you change this to ```suggestion   (toStrongDual 𝕜 E).symm.toContinuousLinearEquiv.toContinuousLinearMap.comp B ``` |
| 5 | 0.674 | 0.00 | #27699 | `Analysis/Normed/Module/WeakDual.lean` | `themathqueen` | I think `WeakDual.toStrongDual_apply` is better. But now that I think about it, `WeakDual.toDual_apply` sounds ok too. Hmm. |
| 6 | 0.674 | 0.00 | #27699 | `Analysis/Normed/Module/WeakDual.lean` | `themathqueen` | shouldn't this be `toStrongDual` now? |
| 7 | 0.668 | 0.00 | #27699 | `Analysis/Normed/Module/Dual.lean` | `themathqueen` | There are more of these below. I think it would read better if we just keep it as "dual" or maybe "strong dual" or idk? |
| 8 | 0.668 | 0.00 | #27699 | `Analysis/Normed/Module/Dual.lean` | `themathqueen` | same thing here ```suggestion # The topological `StrongDual` of a normed space ``` or just leave it as "dual" |
| 9 | 0.666 | 0.00 | #27699 | `Analysis/InnerProductSpace/Dual.lean` | `themathqueen` | Same goes for the next two results. I think it makes sense to rename them to be `_toStrongDualMap_`. |
| 10 | 0.666 | 0.00 | #27699 | `Analysis/InnerProductSpace/Dual.lean` | `themathqueen` | ```suggestion theorem toStrongDualMap_apply {x y : E} : toStrongDualMap 𝕜 E x y = ⟪x, y⟫ := ``` |

---

### C_no_obvious_match — sample 8

- **Query PR**: #36174 — [Merged by Bors] - feat(Topology/Compactness): add countably compact sets
- **File**: `Mathlib/Topology/Compactness/CountablyCompact.lean`  (line 188.0)
- **Reviewer**: `j-loreaux`  **Topics**: `t-topology`
- **Ground-truth comment** (what the reviewer actually wrote):

  > Can you also provide the `↔` version in the `FirstCountableTopology` case?

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,305 @@
  +/-
  +Copyright (c) 2026 Michał Świętek. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Michał Świętek, Yongxi Lin
  +-/
  +module
  +
  +public import Mat...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.785 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `grunweg` | You can probably also condense the subsequent lines a bit. |
| 2 | 0.784 | 0.12 | #9107 | `Topology/Compactness/Lindelof.lean` | `grunweg` | Some more general advice on mathlib style: if you just have two subgoals, I think "constructor" might be more readable. In this case, you can combine these into one line. `refi... |
| 3 | 0.783 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `urkud` | Do you plan to add any instances of this typeclass? Any theorems about it? |
| 4 | 0.781 | 0.10 | #9107 | `Topology/Compactness/Lindelof.lean` | `grunweg` | As a closing tactic, `exact` is preferred over `refine` or `apply`. (In this case, you can just remove the `by refine`, just giving a proof term.) You have at least one other s... |
| 5 | 0.780 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `urkud` | One more typeclass I added in my PR is `StronglyLindelofSpace` assuming that every open set is Lindelof and implying that every set is Lindelof. |
| 6 | 0.779 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `grunweg` | Another trick: you can inline the first subgoal via `by simp`. (Also, you can remove the commented code.) |
| 7 | 0.777 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `urkud` | This lemma (and the previous one) follow from `Set.Countable.isLindelof` (not yet in the PR). |
| 8 | 0.776 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `urkud` | IMHO, "has a cluster point in `s`" is good enough. Also, please reference the filter-free definition `isLindelof_iff_countable_subcover` here. |
| 9 | 0.776 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `grunweg` | Combining the `apply`'s and inlining them, you can golf this to `exact { isLindelof_univ := isCompact_univ.isLindelof }`. (And then, `by` followed by `exact` can be replaced by... |
| 10 | 0.776 | 0.00 | #9107 | `Topology/Compactness/Lindelof.lean` | `grunweg` | I would inline this `have` at its only usage site. You can also combine subsequent `intro`s; then the last three lines could look like `exact fun is x hx ↦ mem_biUnion is ((hr... |

---

### C_no_obvious_match — sample 9

- **Query PR**: #34209 — [Merged by Bors] - feat(Analysis/Normed): Schauder basis definition and characterization via projections
- **File**: `Mathlib/Analysis/Normed/Module/Bases.lean`  (line 425.0)
- **Reviewer**: `faenuccio`  **Topics**: `t-analysis`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >   finrankRange (n : ℕ) : Module.finrank 𝕜 (P n).range = n
  > ```
  > In fact, you can implement this all over the file.

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,504 @@
  +/-
  +Copyright (c) 2025 Michał Świętek. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Michał Świętek
  +-/
  +module
  +
  +public import Mathlib.Analysi...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion -- For illustration purposes, the countable filter basis defining `(AtTop : Filter ℕ)` ``` |
| 2 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion /-- We say that a filter `l` has an antitone basis `s : ι → Set α`, if `t ∈ l` if and only if `t` ``` |
| 3 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion /-- If `f` is countably generated and `f.HasBasis p s`, then `f` admits a decreasing basis ``` |
| 4 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion /-- If `s : ι → Set α` is an indexed family of sets, then finite intersections of `s i` form a basis ``` |
| 5 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion /-- `IsAntitoneBasis s` means the image of `s` is a filter basis such that `s` is decreasing. -/ ``` |
| 6 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion /-- `IsCountablyGenerated f` means `f = generate s` for some countable `s`. -/ ``` |
| 7 | 0.616 | 0.00 | #1791 | `Order/Filter/Bases.lean` | `jcommelin` | ```suggestion /-- `IsCountableBasis p s` means the image of `s` bounded by `p` is a countable filter basis. -/ ``` |
| 8 | 0.606 | 0.00 | #29848 | `Analysis/Normed/Module/FiniteDimension.lean` | `eric-wieser` | Nice catch! |
| 9 | 0.606 | 0.00 | #29848 | `Analysis/Normed/Module/FiniteDimension.lean` | `themathqueen` | I say remove `FiniteDimensional` ```suggestion   [Module R M] [ContinuousSMul R M] (B : Module.Basis ι R M) ``` |
| 10 | 0.605 | 0.00 | #29848 | `Analysis/Normed/Module/FiniteDimension.lean` | `themathqueen` | and add this instead ```suggestion theorem continuous_coe_repr : Continuous (fun m : M => ⇑(B.repr m)) :=   have := Finite.of_basis B ``` |

---

### C_no_obvious_match — sample 10

- **Query PR**: #33683 — [Merged by Bors] - feat(AlgebraicTopology/SimplicialSet): the simplicial homotopy induced by a homotopy
- **File**: `Mathlib/AlgebraicTopology/SimplicialSet/Homotopy.lean`  (line 90.0)
- **Reviewer**: `dagurtomas`  **Topics**: `t-algebraic-topology`
- **Ground-truth comment** (what the reviewer actually wrote):

  > ```suggestion
  >     · simp [dsimp% SimplexCategory.δ_comp_σ_succ (i := Fin.last n),
  >         dsimp% stdSimplex.yonedaEquiv_symm_app_objEquiv_symm]
  > ```
  > This works if you put `dsimp%` on the LHS of the statement of `stdSimplex.δ_objEquiv_symm_apply`. I would guess automation can similarly be improved elsewhere in the proofs in this declaration

- **Query diff hunk head** (first 220 chars):

  ```
  @@ -0,0 +1,159 @@
  +/-
  +Copyright (c) 2026 Joël Riou. All rights reserved.
  +Released under Apache 2.0 license as described in the file LICENSE.
  +Authors: Joël Riou
  +-/
  +module
  +
  +public import Mathlib.AlgebraicTopology...
  ```

- **Top-10 retrieved comments** (from different PRs, strictly before cutoff):

| # | sim | F1 | PR | file | reviewer | comment |
|---|---|---|---|---|---|---|
| 1 | 0.859 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | The following names would be more standard: ```suggestion   h_zero_comp_δ_zero (n : ℕ) : h 0 ≫ Y.δ 0 = f.app (op ⦋n⦌)   h_last_comp_δ_last (n : ℕ) : h (Fin.last n) ≫ Y.δ (Fin.la... |
| 2 | 0.858 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | Whenever possible here, when we have parameters `i` or `j` which determine `n`, I think `n` should be implicit: ```suggestion   h {n : ℕ} (i : Fin (n + 1)) : (X _⦋n⦌ ⟶ Y _⦋n+1⦌)... |
| 3 | 0.857 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | The condition ` i ≤ j.castSucc` would be slightly better because it is an assumption for some of the simplicial relations. |
| 4 | 0.857 | 0.11 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | We do not usually put blank lines in the definition of a structure: ```suggestion ``` |
| 5 | 0.857 | 0.10 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | ```suggestion     h (n + 1) j.succ ≫ Y.δ j.castSucc.succ = h (n + 1) j.castSucc ≫ Y.δ j.castSucc.succ ``` It seems `Fin.castSucc_succ` is a simp lemma: we do not want that any u... |
| 6 | 0.854 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | ```suggestion @[ext] structure SimplicialHomotopy ``` Doing this make your definition of the `ext` lemma below unnecessary. |
| 7 | 0.852 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | These lemmas and attributes would be autogenerated by a syntax like ``` attribute [reassoc (attr := simp)] h_zero_comp_δ_zero h_last_comp_δ_last ``` Note that `[reassoc (attr :=... |
| 8 | 0.851 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | Is not `hjk` equivalent to `j ≤ i`? |
| 9 | 0.844 | 0.00 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | After the changes suggested above, this may become: ```lean /-- The constant homotopy from `f` to `f`. -/ @[simps] def refl (f : X ⟶ Y) : SimplicialHomotopy f f where   h i := X... |
| 10 | 0.843 | 0.10 | #32881 | `AlgebraicTopology/SimplicialObject/SimplicialHomotopy.lean` | `joelriou` | Using the following syntax (similarly as in the previous definition) would be more standard: ```suggestion       (((SimplicialObject.whiskering C D).obj F).map g) where   h i :=... |

---
