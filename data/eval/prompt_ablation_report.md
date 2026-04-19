# Prompt-engineering ablation report

Date: 2026-04-18 11:42  Cases: 6

## Token usage and cost (gpt-5 pricing: $1.25/M in, $10/M out)

- v1: prompt=45,138  completion=14,140  ~$0.198
- v2: prompt=48,108  completion=22,004  ~$0.280

---

## Case 1: PR #38109 (open-pr, live open PR (no precomputed hits))

**File:** `Mathlib/GroupTheory/FinitelyPresentedGroup.lean` line=77.0

**New hunk (truncated):**

```
@@ -66,4 +66,17 @@ theorem equiv (iso : G ≃* H) (h : IsFinitelyPresented G) : IsFinitelyPresented
   refine ⟨n, (iso : G →* H).comp φ, iso.surjective.comp hφsurj, ?_⟩
   rwa [MonoidHom.ker_mulEquiv_comp φ iso]
 
+/-- The trivial group is the normal closure of a finite set of relations. -/
+theorem Subgroup.isNormalClosureFG_bot : Subgroup.IsNormalClosureFG (⊥ : Subgroup G) := by
+  use ∅
+  exact ⟨Finite.of_subsingleton, Subgroup.normalClosure_empty⟩
+
+/-- A free group (with a finite number of generators) is finitely presented. -/
+instance {n : ℕ} : Group.IsFinitelyPresented (FreeGroup (Fin n)) := by
+  use n, FreeGroup.map id
+  constructor
```

**Human reviewer said:**

> I would probably use `refine` here rather than `use` followed by `constructor`.

### Prompt v1  (confidence=high, strong=2, weak=1, tokens=6916/2532, 46.77s)

_summary_: Two applicable past comments: add @[to_additive] to the new subgroup lemma, and tweak the docstring wording to 'finitely many generators'.

**Strong matches:**

- PR #34784  (support: [])
  - excerpt: Shouldn't `normalClosure_empty` also get `@[to_additive]`ized?
  - why: The new lemma `Subgroup.isNormalClosureFG_bot` is a group-theoretic statement in the `Subgroup` context and likely should have an additive counterpart too.
  - adapt: Consider adding `[to_additive]` to `Subgroup.isNormalClosureFG_bot` so the additive version is generated.
- PR #30056  (support: [])
  - excerpt: on finitely many generators. -/
  - why: The new docstring says 'with a finite number of generators'; the past comment suggests the standard phrasing 'on finitely many generators'.
  - adapt: Rephrase the docstring to 'A free group on finitely many generators is finitely presented.'

**Weak observations:**
- Reviewers sometimes prefer adding simp or other helpful attributes to small structural lemmas.  (support: [11493])

### Prompt v2  (confidence=low, strong=0, weak=2, tokens=7411/3546, 61.84s)

_summary_: No concrete past reviewer advice clearly applies; only minor docstring phrasing parallels exist.

_no strong matches_

**Weak observations:**
- Consider phrasing “with finitely many generators” instead of “with a finite number of generators.”  (support: [30056])
- Docstring clarity/grammar tweaks (e.g., be precise: “trivial subgroup is the normal closure of the empty set”).  (support: [18620, 35033])

---

## Case 2: PR #38109 (open-pr, live open PR (no precomputed hits))

**File:** `Mathlib/GroupTheory/FinitelyPresentedGroup.lean` line=70.0

**New hunk (truncated):**

```
@@ -66,4 +66,17 @@ theorem equiv (iso : G ≃* H) (h : IsFinitelyPresented G) : IsFinitelyPresented
   refine ⟨n, (iso : G →* H).comp φ, iso.surjective.comp hφsurj, ?_⟩
   rwa [MonoidHom.ker_mulEquiv_comp φ iso]
 
+/-- The trivial group is the normal closure of a finite set of relations. -/
+theorem BotIsNormalClosureFG : Subgroup.IsNormalClosureFG (⊥ : Subgroup G) := by
```

**Human reviewer said:**

> `Subgroup.IsNormalClosureFG` is a class, so you should make this an instance and probably also remove the name.

### Prompt v1  (confidence=high, strong=1, weak=2, tokens=5731/2372, 34.6s)

_summary_: One prior comment directly addresses the ambiguous phrase “normal closure of a finite set” used in the new docstring and suggests clarifying wording.

**Strong matches:**

- PR #36996  (support: [])
  - excerpt: explicitly say how to use it. Is 'normal closure of a finite set' standard? Might be read as 'smallest subset' not 'smallest subgroup'.
  - why: The new docstring states 'The trivial group is the normal closure of a finite set of relations,' using the same potentially ambiguous phrase.
  - adapt: Clarify the docstring, e.g. 'The trivial subgroup is the normal closure of the empty set (hence of finitely many relations),' to avoid subset vs subgroup ambiguity.

**Weak observations:**
- Prefer phrasing like 'finitely many generators/relations' over 'finite generators/relations' for clarity.  (support: [30056])
- Foundational equalities often get @[simp] to aid automation (e.g., normalClosure_empty).  (support: [35029, 11493])

### Prompt v2  (confidence=medium, strong=2, weak=2, tokens=6226/3940, 46.29s)

_summary_: Clarify the docstring’s terminology and consider adding @[to_additive]; the current phrasing “trivial group … finite set of relations” is misleading for a Subgroup lemma.

**Strong matches:**

- PR #36996  (support: [36996])
  - excerpt: `IsNormalClosureFG N` says that the subgroup `N` is the normal closure of a finitely-generated subgroup.
  - why: Your docstring says “trivial group … normal closure of a finite set of relations,” echoing the earlier phrasing the reviewer asked to clarify to ‘finitely generated subgroup’.
  - adapt: Reword to “The trivial subgroup is the normal closure of a finitely generated subgroup (namely, ⊥ = normalClosure ∅).”
- PR #34784  (support: [34784])
  - excerpt: Shouldn't `normalClosure_empty` also get `@[to_additive]`ized?
  - why: This is a group-specific lemma about subgroups; providing the additive analogue via @[to_additive] follows the same pattern as for `normalClosure_empty`.
  - adapt: Add `@[to_additive]` to generate the additive version for `AddSubgroup` automatically.

**Weak observations:**
- Use “trivial subgroup” (not “trivial group”) in the docstring when the statement is about `⊥ : Subgroup G`.  (support: [34890])
- Rename to lowerCamelCase following the property_bot pattern, e.g. `isNormalClosureFG_bot` (cf. `fg_bot`).  (support: [11177])

---

## Case 3: PR #38109 (open-pr, live open PR (no precomputed hits))

**File:** `Mathlib/GroupTheory/FinitelyPresentedGroup.lean` line=72.0

**New hunk (truncated):**

```
@@ -66,4 +66,17 @@ theorem equiv (iso : G ≃* H) (h : IsFinitelyPresented G) : IsFinitelyPresented
   refine ⟨n, (iso : G →* H).comp φ, iso.surjective.comp hφsurj, ?_⟩
   rwa [MonoidHom.ker_mulEquiv_comp φ iso]
 
+/-- The trivial group is the normal closure of a finite set of relations. -/
+theorem BotIsNormalClosureFG : Subgroup.IsNormalClosureFG (⊥ : Subgroup G) := by
+  use ∅
+  exact ⟨Finite.of_subsingleton, Subgroup.normalClosure_empty⟩
```

**Human reviewer said:**

> If you move the `∅` into the angle brackets, you can make this a one-liner in term mode.

### Prompt v1  (confidence=medium, strong=1, weak=2, tokens=5822/2466, 30.15s)

_summary_: One past comment about correcting a docstring referring to the trivial subgroup applies; consider saying “trivial subgroup” rather than “trivial group”.

**Strong matches:**

- PR #34890  (support: [])
  - excerpt: The trivial subgroup `{1}` is normal.
  - why: Both deal with docstrings about the trivial subgroup; the new docstring currently says “trivial group” while the theorem is about a Subgroup.
  - adapt: Adjust the docstring to “The trivial subgroup is the normal closure of a finite set of relations.”

**Weak observations:**
- Basic equalities often get @[simp] to aid rewriting (e.g., normalClosure_empty, closure lemmas).  (support: [35029, 11493])
- Prefer clearer phrasing like “finitely many generators” over “finite generators” in docstrings.  (support: [30056])

### Prompt v2  (confidence=high, strong=1, weak=4, tokens=6317/5444, 81.28s)

_summary_: You can golf the proof using the `[simp]` lemma `normalClosure_empty`; also consider small docstring/naming improvements.

**Strong matches:**

- PR #35029  (support: [35029])
  - excerpt: Consider tagging this as a simp lemma ... The proof can also be simplified ...
```suggestion
@[simp] lemma normalClosure_empty :
  normalClosure (∅ : Set G) = (⊥ : Subgroup G) := by
  simpa [normalClosure, conjugatesOfSet_empty]
```
  - why: Your proof finishes by citing `Subgroup.normalClosure_empty`. With it marked as `[simp]`, both finiteness of `∅` and `normalClosure ∅ = ⊥` can be discharged by `simp`.
  - adapt: Golf to: `theorem isNormalClosureFG_bot ... := by use ∅; simp` (or `refine ⟨∅, ?_, ?_⟩; simp`).

**Weak observations:**
- Prefer a conventional lemma name like `isNormalClosureFG_bot` (cf. `fg_bot`).  (support: [11177])
- Docstring likely should say “trivial subgroup” rather than “trivial group,” since the statement is about a `Subgroup`.  (support: [34890])
- If you want phrasing tweaks, consider “finitely many relations” instead of “a finite set of relations.”  (support: [30056])
- Past feedback queried the phrase “normal closure of a finite set”; if relevant, you might clarify it (e.g., as the normal closure of a finitely generated subgroup).  (support: [36996])

---

## Case 4: PR #36007 (heldout-closed, known-good (LLM judge label=2))

**File:** `Mathlib/Geometry/Manifold/Algebra/LieGroup.lean` line=176.0

**New hunk (truncated):**

```
@@ -138,41 +139,41 @@ end
 
 @[to_additive]
 theorem ContMDiffWithinAt.inv {f : M → G} {s : Set M} {x₀ : M}
-    (hf : ContMDiffWithinAt I' I n f s x₀) : ContMDiffWithinAt I' I n (fun x => (f x)⁻¹) s x₀ :=
+    (hf : CMDiffAt[s] n f x₀) : CMDiffAt[s] n (fun x => (f x)⁻¹) x₀ :=
   (contMDiff_inv I n).contMDiffAt.contMDiffWithinAt.comp x₀ hf <| Set.mapsTo_univ _ _
 
 @[to_additive]
-theorem ContMDiffAt.inv {f : M → G} {x₀ : M} (hf : ContMDiffAt I' I n f x₀) :
-    ContMDiffAt I' I n (fun x => (f x)⁻¹) x₀ :=
+theorem ContMDiffAt.inv {f : M → G} {x₀ : M} (hf : CMDiffAt n f x₀) :
+    CMDiffAt n (fun x => (f x)⁻¹) x₀ :=
   (contMDiff_inv I n).contMDiffAt.comp x₀ hf
 
 @[to_additive]
-theorem ContMDiffOn.inv {f : M → G} {s : Set M} (hf : ContMDiffOn I' I n f s) :
-    ContMDiffOn I' I n (fun x => (f x)⁻¹) s := fun x hx => (hf x hx).inv
+theorem ContMDiffOn.inv {f : M → G} {s : Set M} (hf : CMDiff[s] n f) :
+    CMDiff[s] n (fun x => (f x)⁻¹) := fun x hx => (hf x hx).inv
 
 @[to_additive]
-theorem ContMDiff.inv {f : M → G} (hf : ContMDiff I' I n f) : ContMDiff I' I n fun x => (f x)⁻¹ :=
+theorem ContMDiff.inv {f : M → G} (hf : CMDiff n f) : CMDiff n fun x => (f x)⁻¹ :=
   fun x => (hf ...
```

**Human reviewer said:**

> ```suggestion
>     CMDiff n fun x ↦ f x / g x := by simp_rw [div_eq_mul_inv]; exact hf.mul hg.inv
> ```

### Prompt v1  (confidence=high, strong=1, weak=1, tokens=9414/3283, 42.52s)

_summary_: One past comment strongly applies: prefer pointwise operation notation (and auto-generating lambda variants) instead of explicit lambdas for operations like inv/div on functions.

**Strong matches:**

- PR #33723  (support: [])
  - excerpt: Can this be auto-generated from the non-compositional version by using the `to_fun` decorator?
  - why: Both hunks prove C^n lemmas for pointwise operations on functions but write the target as an explicit lambda; the past review suggests using the pointwise operation notation and deriving the lambda form automatically.
  - adapt: State these as CMDiff… (f⁻¹) and CMDiff… (f / g), and if a lambda form is desirable, provide it as an auto-generated alias rather than the primary statement.

**Weak observations:**
- Consider using ↦ for lambdas for consistency in mathlib style.  (support: [29459])

### Prompt v2  (confidence=high, strong=2, weak=1, tokens=9909/2400, 31.04s)

_summary_: Use pointwise function notation (f⁻¹, f / g) instead of lambdas, and if keeping lambdas prefer ↦ over =>.

**Strong matches:**

- PR #33723  (support: [33723])
  - excerpt: … : ContDiffWithinAt 𝕜 n (f • g) s x :=
  - why: The new lemmas state CMDiff properties for fun x => (f x)⁻¹ and fun x => f x / g x; past review preferred using pointwise operations on functions instead of explicit lambdas.
  - adapt: State these as CMDiff… f⁻¹ and CMDiff… (f / g) (and analogously within/at/on), avoiding fun x => ….
- PR #29459  (support: [29459])
  - excerpt: Please use \mapsto, thanks!
  - why: The new hunk uses lambdas with =>; past review asked to prefer the ↦ arrow in such lambda expressions.
  - adapt: If you keep the lambda form anywhere, change fun x => … to fun x ↦ ….

**Weak observations:**
- You already have @[to_additive] on these lemmas; no action needed.  (support: [13951])

---

## Case 5: PR #37009 (heldout-closed, known-good (LLM judge label=2))

**File:** `Mathlib/Algebra/Algebra/StrictPositivity.lean` line=83.0

**New hunk (truncated):**

```
@@ -76,6 +76,12 @@ lemma _root_.Units.isStrictlyPositive_iff [LE A] [Monoid A] [Zero A] {a : Aˣ} :
 lemma _root_.Units.isStrictlyPositive_of_le [LE A] [Monoid A] [Zero A] {a : Aˣ}
     (h : (0 : A) ≤ a) : IsStrictlyPositive (a : A) := a.isStrictlyPositive_iff.mpr h
 
+@[nontriviality]
+lemma isStrictlyPositive_of_subsingleton [PartialOrder A] [Monoid A] [Zero A] [Subsingleton A]
+    {a : A} : IsStrictlyPositive a := by
+  rw [IsStrictlyPositive.iff_of_unital]
+  exact ⟨by simp, isUnit_of_subsingleton _⟩
```

**Human reviewer said:**

> ```suggestion
>     {a : A} : IsStrictlyPositive a := iff_of_unital.mpr ⟨by simp, isUnit_of_subsingleton _⟩
> ```

### Prompt v1  (confidence=none, strong=0, weak=2, tokens=6537/1683, 22.13s)

_summary_: No past reviewer comment directly applies to this new nontriviality lemma for subsingletons.

_no strong matches_

**Weak observations:**
- Consider whether an existing lemma or a shorter proof (e.g., via a direct simpa) is available.  (support: [31783, 27436])
- Think about lemma placement; some reviewers prefer moving general lemmas out of specialized files.  (support: [30050])

### Prompt v2  (confidence=low, strong=0, weak=1, tokens=7032/3088, 33.23s)

_summary_: No past comment directly targets this lemma; the only echo is a general style hint to prefer a simp/simpa proof over rw; exact.

_no strong matches_

**Weak observations:**
- Consider shortening the proof to a one-liner with simpa instead of rw; exact, e.g. `simpa [IsStrictlyPositive.iff_of_unital] using ⟨by simp, isUnit_of_subsingleton _⟩`.  (support: [31783])

---

## Case 6: PR #35939 (heldout-closed, hard      (LLM judge max label=0))

**File:** `Mathlib/Algebra/Homology/DerivedCategory/HomologySequence.lean` line=208.0

**New hunk (truncated):**

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
+/-- If `T` is a triangle in `CochainComplex C ℤ`, this is the connecting homomorphism
+`T.obj₃.homology n₀ ⟶ T.obj₁.homology n₁` in homology when `n₀ + 1 = n₁`. -/
+noncomputable def homologyδOfTriangle (n₀ n₁ : ℤ) (h : n₀ + 1 = n₁) :
+    T.obj₃.homology n₀ ⟶ T.obj₁.homology n₁ :=
+  homologyMap T.mor₃ n₀ ≫
+    ((homologyFunctor C (.up ℤ) 0).shiftIso 1 n₀ n₁ (by lia)).hom.app _
+
+set_option backward.isDefEq.respectTransparency false in
+@[reassoc (attr := simp)]
+lemma homologyFunctorFactors_hom_app_homologyδOfTriangle (n₀ n₁ : ℤ) (h : n₀ + 1 = n₁) :
+    (DerivedCategory.homologyFunctorFactors C n₀).hom.app T.obj₃ ≫
+      homologyδOfTriangle T n₀ n₁ h =
+    DerivedCategory.HomologySequence.δ
+      (DerivedCategory.Q.mapTriangle.obj T) n₀ n₁ h ≫
+        (DerivedCategory.homologyFunctorFactors C n₁).hom.app T.obj₁ := by
+  have := DerivedCategory.shiftMap_homologyFunctor_map_Q T.mor₃ n₀ n₁ (by lia)
+  dsimp [ShiftedHom.map] at this
+  dsimp [DerivedCategory.HomologyS...
```

**Human reviewer said:**

> I think we at least prefer `erw` to track the defeq abuse as technical debt

### Prompt v1  (confidence=low, strong=0, weak=3, tokens=10718/1804, 21.5s)

_summary_: No past comments directly apply to this new hunk; the added lemma already carries @[reassoc (attr := simp)] and other patterns differ.

_no strong matches_

**Weak observations:**
- Consider whether omega could solve simple ℤ index equalities instead of lia/linarith.  (support: [14084])
- Compositional lemmas often benefit from @[reassoc] and sometimes (attr := simp); your lemma already follows this convention.  (support: [13664])
- Be mindful of lemma naming conventions for naturality lemmas (avoid generic _hom names).  (support: [31046, 33360])

### Prompt v2  (confidence=medium, strong=2, weak=1, tokens=11213/3586, 41.13s)

_summary_: Past guidance about marking composition lemmas with @[reassoc] (often also simp) applies to the new composition identity; the new code already follows this pattern.

**Strong matches:**

- PR #13664  (support: [13664])
  - excerpt: @[reassoc]
lemma δ_comp : ... :=
-- or @[reassoc (attr := simp)]
  - why: The new lemma is an equality of compositions of morphisms and is naturally used under reassociation; adding @[reassoc] (and possibly simp) is the standard idiom.
  - adapt: Keeping @[reassoc (attr := simp)] on homologyFunctorFactors_hom_app_homologyδOfTriangle is good; add the same attribute to any similar composition lemmas introduced nearby.
- PR #13664  (support: [13664])
  - excerpt: @[reassoc]
lemma comp_δ : ... :=
-- or @[reassoc (attr := simp)]
  - why: Same pattern: a compositional equality involving δ-like maps benefits from reassoc/simp attributes for usability.
  - adapt: Ensure analogous composition lemmas in this section carry @[reassoc] (and possibly simp) for consistency with homologyδOfTriangle’s lemma.

**Weak observations:**
- Consider whether goals like (by lia) could use omega if indices are naturals/ints and omega fits better.  (support: [14084])
