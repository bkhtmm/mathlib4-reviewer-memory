# mathlib4 reviewer-memory tool — worked-examples gallery

This is a small read-only gallery of what a retrieval-grounded review-suggestion tool
produces, run on **10 currently-open PRs** in `leanprover-community/mathlib4`.

Each PR in this gallery is one where a human reviewer left a comment that was *not*
in the tool's training/retrieval index (the index covers closed PRs only). For each
case the gallery shows, side by side:

- the new hunk,
- what the human reviewer actually wrote,
- what the tool returned (summary, confidence, the past PRs it cited, and a
  counter-argument it self-generated for each citation).

## What this tool is — and is not

- It is **not an "AI reviewer"**. It cannot replace any of the mathlib maintainers
  or reviewers. The held-out evaluation makes that clear (see the `eval/` link below).
- It is a **memory** over ~158k past reviewer comments on ~35k closed mathlib4 PRs.
  Given a new hunk, it tries to find past reviewer comments that would plausibly
  apply, and asks an LLM (GPT-5) to ground each suggestion in a specific past
  comment quote — explicitly allowed to say "no relevant past reviews found".
- It is intended for **contributors** who want to sanity-check a PR for the kinds
  of nits past reviewers have flagged before, *before* sending it to a reviewer.
  For reviewers, it might be a "have we seen this before?" sidekick — but that is
  a maybe, not a claim.

## How to read this gallery

Each card is graded into one of five buckets:

| Badge | Meaning |
|---|---|
| 🟢 **WIN** | The tool surfaced the same concern the human did, or one the human missed but is real. |
| 🟡 **PARTIAL** | The tool surfaced related/adjacent advice; some genuine overlap with what a reviewer would say. |
| ⚪ **CORRECT-SILENT** | The tool honestly said it had nothing to suggest, and the human's concern was the kind of thing no past comment could surface. |
| 🔴 **OFF-AXIS** | The tool was confident but pointed at the wrong concern. Real failure mode. |
| 🔴 **MISSED-SILENT** | The tool went silent when a clear past precedent existed. Real failure mode. |

**Composition of this gallery:** 2 WIN, 4 PARTIAL, 1 CORRECT-SILENT, 1 OFF-AXIS, 2 MISSED-SILENT.

Roughly half the gallery is failure modes or honest silences. That's intentional: a
gallery that hides its failure modes can't be trusted.

## A note on prompt tuning (please read before grading)

The current prompt (v3.1) was iterated by looking at where the previous version (v3)
failed on a 20-case open-PR sweep — and the 10 cards in this gallery are drawn from
that same 20-case sweep. So the gallery is best read as **"best-current-prompt on
PRs the prompt was tuned to handle"**, *not* as a clean held-out evaluation.

The genuinely held-out quantitative numbers (20 closed-PR queries the prompt has
never seen, judged by an LLM judge) live in
[`data/eval/llm_judge_report.md`](../data/eval/llm_judge_report.md). That's the
un-tuned generalization metric; this gallery is the qualitative companion.


## What I'd like from you

If you have 5 minutes, scroll the cards and tell me — for the ones marked WIN or
PARTIAL — whether the cited past comment is _actually_ the kind of advice you'd
give on the new hunk. That's the signal I'd use to decide whether this is worth
improving further or shelving.

For the failure-mode cards, I'm not asking you to fix them; I'm just being upfront
about how it fails today.

## Roster

| # | Verdict | PR | File | Reviewer concern |
|---|---|---|---|---|
| 1 | WIN | [#36621](https://github.com/leanprover-community/mathlib4/pull/36621) | `TopPair.lean` | _module-structure / file header_ |
| 2 | WIN | [#23929](https://github.com/leanprover-community/mathlib4/pull/23929) | `NFA.lean` | _naming (lemma rename)_ |
| 3 | PARTIAL + bonus | [#33664](https://github.com/leanprover-community/mathlib4/pull/33664) | `Basic.lean` | _docstring suggestion_ |
| 4 | PARTIAL | [#22919](https://github.com/leanprover-community/mathlib4/pull/22919) | `Pi.lean` | _refactor (unnecessary transport)_ |
| 5 | PARTIAL | [#33355](https://github.com/leanprover-community/mathlib4/pull/33355) | `VertexConnectivity.lean` | _naming + edge case_ |
| 6 | PARTIAL (interesting) | [#24627](https://github.com/leanprover-community/mathlib4/pull/24627) | `ValuedField.lean` | _suggestion block (proof rewrite)_ |
| 7 | CORRECT-SILENT | [#31425](https://github.com/leanprover-community/mathlib4/pull/31425) | `Basic.lean` | _needs explanatory comment_ |
| 8 | OFF-AXIS | [#28349](https://github.com/leanprover-community/mathlib4/pull/28349) | `NamePolyVars.lean` | _design smell: string output_ |
| 9 | MISSED-SILENT | [#20431](https://github.com/leanprover-community/mathlib4/pull/20431) | `Basic.lean` | _design smell: _root_ placement_ |
| 10 | MISSED-SILENT + bonus | [#34007](https://github.com/leanprover-community/mathlib4/pull/34007) | `Dual.lean` | _generalize: two modules M₁/M₂ not one_ |

---

## 1. [🟢 WIN] PR [#36621](https://github.com/leanprover-community/mathlib4/pull/36621) — `Mathlib/Topology/Category/TopPair.lean` (line 15)

**Reviewer:** [@vlad902](https://github.com/vlad902) &nbsp; · &nbsp; **Concern:** _module-structure / file header_

### New hunk

```diff
... [5 lines above hidden]
+-/
+import Mathlib.Topology.Defs.Basic
+import Mathlib.Topology.Category.TopCat.Basic
+import Mathlib.Topology.Defs.Induced
+import Mathlib.CategoryTheory.Category.Basic
+import Mathlib.CategoryTheory.CommSq
+import Mathlib.Topology.Homotopy.Basic
+import Mathlib.Topology.Category.TopCat.Limits.Basic
+import Mathlib.CategoryTheory.Limits.Shapes.BinaryProducts
+import Mathlib.Topology.UnitInterval
+import Mathlib.Topology.Category.TopCat.Limits.Basic
```

### What the human reviewer actually said

> `#min_imports` gives a much smaller set of imports you could replace this with. Also you are not using the new module structure, look at another file and copy its header structure (e.g. add `module` at the top, these will be `public` imports, and add a `@[expose] public section` below.)

### What the tool produced (confidence: **high**)

> The new file only contains imports (including a duplicate), so prior feedback about minimizing and deduplicating imports applies; also consider adding a module docstring.

**Strong matches:**

- **Past PR [#11334](https://github.com/leanprover-community/mathlib4/pull/11334)** &nbsp; · &nbsp; `Mathlib/Topology/Instances/AddCircle.lean` &nbsp; · &nbsp; axis: `imports-module`
  > _Past reviewer:_ can you run `#minimize_imports` on this file? I think there is some redundancy here
  - **Why it applies:** This new file is just a list of imports, and one import appears twice; running #minimize_imports would remove the duplicate and any unnecessary imports.
  - **Suggested adaptation:** Please run #minimize_imports and drop redundant imports (there is also a duplicate `TopCat.Limits.Basic` import).
  - **Counter-argument:** Future additions to the file might require some of these imports.

- **Past PR [#2508](https://github.com/leanprover-community/mathlib4/pull/2508)** &nbsp; · &nbsp; `Mathlib/Topology/Order/ScottTopology.lean` &nbsp; · &nbsp; axis: `imports-module`
  > _Past reviewer:_ Can you trim down the imports? Only a few are actually needed.
  - **Why it applies:** Given the file currently only imports many modules (with a duplicate), trimming to the minimal necessary set is appropriate.
  - **Suggested adaptation:** Trim the import list to only what is needed for this file and remove the duplicated line.
  - **Counter-argument:** Without seeing the upcoming contents, it's hard to know the exact minimal set.

**Weak observations:**

- The same import `Mathlib.Topology.Category.TopCat.Limits.Basic` appears twice; remove the duplicate. &nbsp; (axis: `imports-module`; support: [#11334](https://github.com/leanprover-community/mathlib4/pull/11334), [#2508](https://github.com/leanprover-community/mathlib4/pull/2508))
- Consider adding a short module-level docstring (`/-! ... -/`) describing the purpose of `TopPair`. &nbsp; (axis: `docstring`; support: [#22827](https://github.com/leanprover-community/mathlib4/pull/22827))

### Verdict

Tool surfaced two on-target past PRs about minimizing imports — and independently flagged a duplicate import the human reviewer didn't mention.

---

## 2. [🟢 WIN] PR [#23929](https://github.com/leanprover-community/mathlib4/pull/23929) — `Mathlib/Computability/NFA.lean` (line 194)

**Reviewer:** [@meithecatte](https://github.com/meithecatte) &nbsp; · &nbsp; **Concern:** _naming (lemma rename)_

### New hunk

```diff
... [33 lines above hidden]
+        by rw [evalFrom_cons, mem_evalFrom_iff_exists, stepSet_singleton] at h; exact h
+      let ⟨s', h₁, h₂⟩ := h
+      let ⟨p'⟩ := Path.evalFrom_iff_nonempty.1 h₂
+      ⟨Path.cons s' _ _ _ _ h₁ p'⟩
+  mpr p := match p with
+    | ⟨nil s⟩ => by simp
+    | ⟨cons s' s t a x h₁ h₂⟩ => by
+      rw [evalFrom_cons, stepSet_singleton, mem_evalFrom_iff_exists]
+      exact ⟨s', h₁, Path.evalFrom_iff_nonempty.2 ⟨h₂⟩⟩
+
+theorem Path.accepts_iff_nonempty {x : List α} :
```

### What the human reviewer actually said

> Okay, I assume I should also rename `Path.evalFrom_iff_nonempty` to `mem_evalFrom_iff_exists_path`.

### What the tool produced (confidence: **high**)

> A prior naming suggestion for the evalFrom ↔ Nonempty Path lemma applies here; prefer the conventional mem_evalFrom_iff_nonempty_path name.

**Strong matches:**

- **Past PR [#25321](https://github.com/leanprover-community/mathlib4/pull/25321)** &nbsp; · &nbsp; `Mathlib/Computability/NFA.lean` &nbsp; · &nbsp; axis: `naming`
  > _Past reviewer:_ theorem mem_evalFrom_iff_nonempty_path {s t : σ} {x : List α} :
  - **Why it applies:** The new lemma `Path.evalFrom_iff_nonempty` proves the same equivalence `t ∈ M.evalFrom {s} x ↔ Nonempty (M.Path s t x)`. The earlier review asked to use the conventional `mem_evalFrom_iff_nonempty_path` naming.
  - **Suggested adaptation:** Rename `Path.evalFrom_iff_nonempty` to `mem_evalFrom_iff_nonempty_path` to match mathlib naming conventions for membership-iff lemmas.
  - **Counter-argument:** The author may be intentionally grouping the lemma under a `Path.*` naming scheme rather than the usual `mem_*` pattern.

### Verdict

Near-verbatim hit: tool retrieved a past PR with the exact `mem_evalFrom_iff_<X>_path` naming template the reviewer ended up asking for.

---

## 3. [🟡 PARTIAL + bonus] PR [#33664](https://github.com/leanprover-community/mathlib4/pull/33664) — `Mathlib/Geometry/Convex/Cone/Pointed/Face/Basic.lean` (line 44)

**Reviewer:** [@eric-wieser](https://github.com/eric-wieser) &nbsp; · &nbsp; **Concern:** _docstring suggestion_

### New hunk

```diff
... [34 lines above hidden]
+open Submodule
+
+@[expose] public section
+
+namespace PointedCone
+
+variable {R M N : Type*}
+
+variable [Semiring R] [PartialOrder R] [IsOrderedRing R] [AddCommGroup M] [Module R M] in
+/-- A pointed cone `F` is a face of another pointed cone `C` if `F ≤ C` and if `a • x + y` is in `F`
+for all `x, y` in `C` and positive scalars `a`, then `x` ist also in `F`. -/
```

### What the human reviewer actually said

> ```suggestion
> for all `x, y` in `C` and positive scalars `a`, then `x` is also in `F`. -/
> ```

### What the tool produced (confidence: **medium**)

> Docstring wording/grammar improvements apply; prior feedback about clearer English phrasing for cone documentation fits this new file’s docstrings/comments.

**Strong matches:**

- **Past PR [#6437](https://github.com/leanprover-community/mathlib4/pull/6437)** &nbsp; · &nbsp; `Mathlib/Analysis/Convex/Cone/Pointed.lean` &nbsp; · &nbsp; axis: `docstring`
  > _Past reviewer:_ A *pointed cone* is defined to be a convex cone which contains `0`.
  - **Why it applies:** Both PRs introduce core notions about cones and include English explanations; the new hunk’s docstrings have awkward phrasing/typos and would benefit from the same kind of careful rewording for clarity.
  - **Suggested adaptation:** Tighten the docstrings: fix typos (“with”, “is”), and rephrase the face description to “whenever a > 0, x,y ∈ C and a • x + y ∈ F, then x ∈ F (and hence y ∈ F)” or similar.
  - **Counter-argument:** The current wording may be considered acceptable, and the content differs (faces vs pointed cones), so the exact sentence from the past comment cannot be copied verbatim.

**Weak observations:**

- Fix typos in docstrings/comments: “wth” → “with”, “ist” → “is”, and consider clarifying “positive combination” with explicit quantifiers. &nbsp; (axis: `docstring`; support: [#6437](https://github.com/leanprover-community/mathlib4/pull/6437))

### Verdict

Right axis (docstring), close direction; bonus: caught two real typos (`wth`→`with`, `ist`→`is`) that the human reviewer didn't mention.

---

## 4. [🟡 PARTIAL] PR [#22919](https://github.com/leanprover-community/mathlib4/pull/22919) — `Mathlib/Data/Fintype/Pi.lean` (line 235)

**Reviewer:** [@eric-wieser](https://github.com/eric-wieser) &nbsp; · &nbsp; **Concern:** _refactor (unnecessary transport)_

### New hunk

```diff
... [76 lines above hidden]
+        ext i
+        cases i using Fin.lastCases <;> simp }
+
+instance RelHom.instFintype {α β} {r : α → α → Prop} {s : β → β → Prop}
+    [Fintype α] [Fintype β] [DecidableEq α] [DecidableRel r]
+    [∀ a b [Decidable (a = b)], Decidable (s a b)] :
+    Fintype (r →r s) :=
+  (truncFinBijection β).recOnSubsingleton fun ⟨b, hb⟩ ↦
+    (truncEquivFin α).recOnSubsingleton fun a ↦
+      haveI (x y) : Decidable (b x = b y) := decidable_of_iff (x = y) hb.injective.eq_iff.symm
+      haveI : DecidableRel (b ⁻¹'o s) := fun x y => inferInstanceAs (Decidable (s (b x) (b y)))
```

### What the human reviewer actually said

> I'm a little confused by what's going on with this; it looks like you're somehow transporting `β` to `Fin n` to avoid needing a decidability argument? Note that due to my refactor above, there is now no other reason to do this transport!

### What the tool produced (confidence: **medium**)

> The new code adds a global Fintype instance for RelHom and uses inferInstanceAs; this risks an instance diamond with SimpleGraph.Hom and could be slightly simplified.

**Strong matches:**

- **Past PR [#12273](https://github.com/leanprover-community/mathlib4/pull/12273)** &nbsp; · &nbsp; `Mathlib/Data/Fintype/Pi.lean` &nbsp; · &nbsp; axis: `instance-diamond`
  > _Past reviewer:_ This is a bad instance since it causes a non-defeq diamond with the existing `SimpleGraph.Hom.instFintype`.
  - **Why it applies:** The new hunk introduces a global `instance RelHom.instFintype … : Fintype (r →r s)`. SimpleGraph.Hom is essentially a `RelHom` for adjacency; if its own `instFintype` still exists, there may be two non-defeq `Fintype` instance paths.
  - **Suggested adaptation:** Please ensure this does not create a non-defeq diamond with `SimpleGraph.Hom.instFintype` — e.g., remove or define the graph instance via this general one so there’s a single canonical path.
  - **Counter-argument:** If the graph-specific instance was removed or already derives from this one in the PR, then no diamond occurs.

- **Past PR [#37315](https://github.com/leanprover-community/mathlib4/pull/37315)** &nbsp; · &nbsp; `Mathlib/Combinatorics/SimpleGraph/Walks/Counting.lean` &nbsp; · &nbsp; axis: `refactor-simplify`
  > _Past reviewer:_ Is this not just `inferInstance`?
  - **Why it applies:** The new code writes `haveI : DecidableRel (b ⁻¹'o s) := fun x y => inferInstanceAs (Decidable (s (b x) (b y)))`, which can typically be shortened to `fun _ _ => inferInstance`.
  - **Suggested adaptation:** You can simplify `fun x y => inferInstanceAs (Decidable (s (b x) (b y)))` to `fun _ _ => inferInstance`.
  - **Counter-argument:** If type inference needs `inferInstanceAs` here for disambiguation, the longer form may be necessary.

### Verdict

Off the human's exact axis (which was an unnecessary `Fin n` transport), but surfaced a different concrete concern — instance-diamond risk against `SimpleGraph.Hom.instFintype` — that is itself a plausible reviewer comment.

---

## 5. [🟡 PARTIAL] PR [#33355](https://github.com/leanprover-community/mathlib4/pull/33355) — `Mathlib/Combinatorics/SimpleGraph/Connectivity/VertexConnectivity.lean` (line 130)

**Reviewer:** [@vihdzp](https://github.com/vihdzp) &nbsp; · &nbsp; **Concern:** _naming + edge case_

### New hunk

```diff
... [120 lines above hidden]
+  ⟨lt_of_le_of_lt hkl hc.1,
+   fun u v huv ↦ IsVertexReachable.anti (Nat.cast_le.mpr hkl) (hc.2 u v huv)⟩
+
+/-- Vertex connectivity is monotonic in the graph. -/
+@[gcongr]
+lemma IsVertexConnected.mono [Fintype V] {k : ℕ} (hGH : G ≤ H) (hc : G.IsVertexConnected k) :
+    H.IsVertexConnected k :=
+  ⟨hc.1, fun u v huv ↦ IsVertexReachable.mono hGH (hc.2 u v huv)⟩
+
+/-- The complete graph on `n` vertices is `(n-1)`-vertex-connected. -/
+lemma completeGraph_isVertexConnected [Fintype V] (h : 1 < Fintype.card V) :
```

### What the human reviewer actually said

> The lemma should be named like this:
> ```suggestion
> lemma isVertexConnected_completeGraph [Fintype V] (h : 1 < Fintype.card V) :
> ```
> Also, isn't this true for `#V = 1` as well?

### What the tool produced (confidence: **medium**)

> Past feedback requesting convenient k≠0-to-(pre)connected/Reachable lemmas for edge connectivity also applies here for vertex connectivity/vertex reachability to keep APIs parallel.

**Strong matches:**

- **Past PR [#32870](https://github.com/leanprover-community/mathlib4/pull/32870)** &nbsp; · &nbsp; `Mathlib/Combinatorics/SimpleGraph/Connectivity/EdgeConnectivity.lean` &nbsp; · &nbsp; axis: `unify-with-existing`
  > _Past reviewer:_ Could you provide
  > 
  > lemma IsEdgeReachable.reachable (hk : k \ne 0) ...
  > 
  > and similarly for `IsEdgeConnected`?
  - **Why it applies:** This new file introduces IsVertexConnected and uses IsVertexReachable. By analogy with the edge API, it would be useful to add lemmas deriving Reachable from IsVertexReachable when k ≠ 0, and deriving Preconnected/Connected from IsVertexConnected.
  - **Suggested adaptation:** Please add IsVertexReachable.reachable (hk ≠ 0) and IsVertexConnected.preconnected/connected lemmas, mirroring the edge connectivity API.
  - **Counter-argument:** These lemmas might already exist elsewhere in the file or a nearby module not shown in the snippet.

### Verdict

Off-axis from the human (rename + edge case) but surfaced a real API-completeness concern: mirror the edge-connectivity convenience lemmas for the new vertex-connectivity API.

---

## 6. [🟡 PARTIAL] PR [#24627](https://github.com/leanprover-community/mathlib4/pull/24627) — `Mathlib/Topology/Algebra/Valued/ValuedField.lean` (line 410)

**Reviewer:** [@loefflerd](https://github.com/loefflerd) &nbsp; · &nbsp; **Concern:** _suggestion block (proof rewrite)_

### New hunk

```diff
... [22 lines above hidden]
+        rwa [map_inv₀, inv_le_one₀]
+        rwa [Valued.v.pos_iff]
+      suffices IsOpen {x⁻¹} by
+        simp only [isOpen_iff_mem_nhds, Set.mem_singleton_iff, forall_eq] at this ⊢
+        have := continuousAt_inv₀ hx0 this
+        rw [Filter.mem_map] at this
+        simpa using this
+      have : IsOpen ({⟨x⁻¹, hx⟩} : Set 𝒪[K]) := isOpen_discrete _
+      simpa using hk.isOpenMap_subtype_val _ this
+  · intro h
+    infer_instance
```

### What the human reviewer actually said

> 🏌️ 
> ```suggestion
>   refine ⟨fun _ ↦ singletons_open_iff_discrete.mp fun x ↦ ?_, fun _ ↦ inferInstance⟩
>   have hk : IsOpen (𝒪[K] : Set K) := isOpen_integer K
>   rcases le_total (Valued.v x) 1 with hx | hx
>   · simpa using hk.isOpenMap_subtype_val _ (show IsOpen {⟨x, hx⟩} from isOpen_discrete _)
>   · have hx0 : x ≠ 0 := v.pos_iff.mp <| hx.trans_lt' zero_lt_one
>     replace hx : Valued.v x⁻¹ ≤ 1 := by rwa [map_inv₀, inv_le_one₀ (zero_lt_one.trans_le hx)]
>     have h1 : IsOpen ({⟨x⁻¹, hx⟩} : Set 𝒪[K]) := isOpen_discrete _
>     have h2 : IsOpen {x⁻¹} := by simpa using hk.isOpenMap_subtype_val _ h1   
>     simp only [isOpen_iff_mem_nhds, Set.mem_singleton_iff, forall_eq] at h2
>     simpa [isOpen_iff_mem_nhds, -Filter.map_inv] using continuousAt_inv₀ hx0 h2
> ```

### What the tool produced (confidence: **medium**)

> The new lemma is added under Valued and uses Valued.v/𝒪[K]; past feedback suggests generalizing away from Valued to any Valuation and avoiding expanding the Valued-based API.

**Strong matches:**

- **Past PR [#27265](https://github.com/leanprover-community/mathlib4/pull/27265)** &nbsp; · &nbsp; `Mathlib/Topology/Algebra/Valued/ValuationTopology.lean` &nbsp; · &nbsp; axis: `generalize-signature`
  > _Past reviewer:_ Should this be stated for any `Valuation` rather than just `Valued.v`?
  - **Why it applies:** The lemma assumes `[Valued K Γ₀]` and uses `Valued.v` and `𝒪[K]`. It could be formulated for an arbitrary `v : Valuation K Γ₀` using `v.valuationSubring`, then specialize to the Valued instance.
  - **Suggested adaptation:** State a version `DiscreteTopology (v.valuationSubring) ↔ DiscreteTopology K` for any `v : Valuation K Γ₀`, and (optionally) provide the `Valued`-instance corollary via `Valued.v`.
  - **Counter-argument:** The notation `𝒪[K]` is tied to a `Valued` instance and the file may intentionally target the `Valued`-based API.

- **Past PR [#27465](https://github.com/leanprover-community/mathlib4/pull/27465)** &nbsp; · &nbsp; `Mathlib/Topology/Algebra/Valued/ValuativeRel.lean` &nbsp; · &nbsp; axis: `design-smell-architectural`
  > _Past reviewer:_ avoid adding API if on the long run we want to discourage the use of `Valued`.
  - **Why it applies:** This adds a new `Valued.discreteTopology_…` lemma relying on the `Valued` class; past guidance advises against expanding `Valued`-centric API in favor of `Valuation`-based formulations.
  - **Suggested adaptation:** Move the statement to the `Valuation`-based API (in the `Valuation` namespace) and only derive the `Valued` version if really needed.
  - **Counter-argument:** This file may be the designated place for `Valued`-centric results, and an immediate `Valuation` refactor might be outside this PR’s scope.

**Weak observations:**

- Lemma lacks a docstring; consider adding a brief description of the equivalence. &nbsp; (axis: `docstring`; support: [#36532](https://github.com/leanprover-community/mathlib4/pull/36532))

### Verdict

Human asked for proof-golf. Tool instead surfaced two _higher-level_ concerns (generalize away from `Valued`; don't expand `Valued`-centric API). Different axis but real reviewer concerns.

---

## 7. [⚪ CORRECT-SILENT] PR [#31425](https://github.com/leanprover-community/mathlib4/pull/31425) — `Mathlib/Topology/Defs/Basic.lean` (line 207)

**Reviewer:** [@eric-wieser](https://github.com/eric-wieser) &nbsp; · &nbsp; **Concern:** _needs explanatory comment_

### New hunk

```diff
... [3 lines above hidden]
 
+namespace TopologicalSpace
+open Topology Lean Meta PrettyPrinter.Delaborator SubExpr
+
+/-- Delaborate unary notation referring to non-standard topologies. -/
+def delabUnary (mkStx : Term → DelabM Term) : Delab :=
+  withOverApp 2 <| whenPPOption Lean.getPPNotation do
+    let α ← withNaryArg 0 getExpr
+    let .some synthInst ← Meta.trySynthInstance (← Meta.mkAppM ``TopologicalSpace #[α]) | failure
+    let inst ← withNaryArg 1 getExpr
+    if ← Meta.isDefEq inst synthInst then failure
```

### What the human reviewer actually said

> This line would probably benefit from a comment explaining why, and for the binary one

### What the tool produced (confidence: **low**)

> No past comments directly apply; closest observations concern potentially unused or suboptimal `open`s around Topology-related delaborators.

**Weak observations:**

- Consider removing or scoping unnecessary `open`s (e.g., `open Topology`) if they are not used in this namespace. &nbsp; (axis: `style-syntax`; support: [#22048](https://github.com/leanprover-community/mathlib4/pull/22048), [#29728](https://github.com/leanprover-community/mathlib4/pull/29728))

### Verdict

Human asked for an explanatory comment — exactly the kind of advice that no past reviewer comment can be retrieved for. Tool said `low` and offered nothing concrete. Right behaviour.

---

## 8. [🔴 OFF-AXIS] PR [#28349](https://github.com/leanprover-community/mathlib4/pull/28349) — `Mathlib/Tactic/Ring/NamePolyVars.lean` (line 288)

**Reviewer:** [@eric-wieser](https://github.com/eric-wieser) &nbsp; · &nbsp; **Concern:** _design smell: string output_

### New hunk

```diff
... [312 lines above hidden]
+/-- Initialise the environmental extension to locally store polynomial-like notations. -/
+initialize declaredExt : DeclaredExt ← registerSimpleScopedEnvExtension <|
+  { addEntry old new := insert new old
+    initial := {} }
+
+/-- Given a declaration of polynomial-like notation (e.g. `(Fin 37)[x,y,z][[t]]`), parse it fully to
+return the head (e.g. `(Fin 37)`), the raw body (e.g. `"[x,y,z][[t]]`"), the total type generated
+(e.g. `PowerSeries (MvPolynomial (Fin 3) (Fin 37))`), and the terms corresponding to each declared
+identifier (e.g. `x := PowerSeries.C (MvPolynomial.X 0)`). -/
+def _root_.Lean.TSyntax.parsePolyesqueFull (p : Polyesque) :
+    CoreM (String × String × Bool × Term × Array Term × Array (Ident × Term)) := do
```

### What the human reviewer actually said

> Returning this as a string feels like a wart to me; can you explain in a comment why `Syntax` is no good?

### What the tool produced (confidence: **high**)

> The new command syntax likely should use ppSpace rather than a trailing space in the literal; also a small docstring typo is present.

**Strong matches:**

- **Past PR [#34582](https://github.com/leanprover-community/mathlib4/pull/34582)** &nbsp; · &nbsp; `Mathlib/Tactic/Ring/NamePolyVars.lean` &nbsp; · &nbsp; axis: `style-syntax`
  > _Past reviewer:_ Does `over` need the same treatment? Doesn't this lead to `ppSpace` followed by " over ", that is, two spaces?
  - **Why it applies:** The new syntax uses a space inside the literal: `"name_poly_vars " polyesque`. Prior feedback in this file recommended replacing literal spaces with `ppSpace` near this command to control pretty-print spacing.
  - **Suggested adaptation:** Use `syntax (name := declare) "name_poly_vars" ppSpace polyesque : command` instead of embedding a trailing space in the string literal.
  - **Counter-argument:** The current form may still parse and print fine since there is no following fixed literal like " over ".

**Weak observations:**

- Docstring example likely has an extra closing parenthesis: `Polynomial (MvPolynomial (Fin 2) R))`. &nbsp; (axis: `docstring`; support: [#10866](https://github.com/leanprover-community/mathlib4/pull/10866))

### Verdict

Cleanest failure mode: surface similarity (same file, similar code area) tricked the model into a `ppSpace`-formatting suggestion when the human's actual concern was a design wart (returning a string instead of `Syntax`).

---

## 9. [🔴 MISSED-SILENT] PR [#20431](https://github.com/leanprover-community/mathlib4/pull/20431) — `Mathlib/RingTheory/AdicCompletion/Basic.lean` (line 535)

**Reviewer:** [@chrisflav](https://github.com/chrisflav) &nbsp; · &nbsp; **Concern:** _design smell: _root_ placement_

### New hunk

```diff
... [4 lines above hidden]
+variable {I M} in
+lemma _root_.IsHausdorff.iff_injective :
+    IsHausdorff I M ↔ Injective (AdicCompletion.of I M) := by
+  simp [injective_iff_map_eq_zero, isHausdorff_iff, SModEq.zero, AdicCompletion.ext_iff]
+
+variable {I M} in
+lemma _root_.IsPrecomplete.iff_surjective :
+    IsPrecomplete I M ↔ Surjective (AdicCompletion.of I M) := by
+  simp [Function.Surjective, (AdicCompletion.mk_surjective I M).forall,
+    AdicCompletion.ext_iff, isPrecomplete_iff, AdicCauchySequence, Subtype.forall,
+    eq_comm (a := Submodule.Quotient.mk _)]
```

### What the human reviewer actually said

> Maybe move these after `end AdicCompletion` to get rid of the ugly `_root_`?

### What the tool produced (confidence: **low**)

> No past comments directly apply; only general naming/docstring style observations seem tangentially relevant.

**Weak observations:**

- Check lemma names fit house style; prior feedback in this file suggested clearer names within the IsHausdorff namespace. &nbsp; (axis: `naming`; support: [#26384](https://github.com/leanprover-community/mathlib4/pull/26384))
- Consider adding brief docstrings for new equivalence lemmas to clarify intent. &nbsp; (axis: `docstring`; support: [#23027](https://github.com/leanprover-community/mathlib4/pull/23027))

### Verdict

Hunk literally contains `lemma _root_.IsHausdorff.iff_injective`. Human said "move it to avoid the ugly `_root_`". Tool's plausible-concerns list didn't even include `namespace-organization`. Clear miss.

---

## 10. [🔴 MISSED-SILENT (with bonus)] PR [#34007](https://github.com/leanprover-community/mathlib4/pull/34007) — `Mathlib/Algebra/Module/Submodule/Dual.lean` (line 49)

**Reviewer:** [@joelriou](https://github.com/joelriou) &nbsp; · &nbsp; **Concern:** _generalize: two modules M₁/M₂ not one_

### New hunk

```diff
... [39 lines above hidden]
+namespace Submodule
+
+variable {R : Type*} [CommSemiring R]
+variable {M : Type*} [AddCommMonoid M] [Module R M]
+variable {N : Type*} [AddCommMonoid N] [Module R N]
+variable {p : M →ₗ[R] N →ₗ[R] R} {s t : Set M}
+
+variable (p s) in
+/-- The dual span of a set `s` with respect to a bilinear pairing `p` is the submodule
+  consisting of the points `y` such that for all points `x ∈ s` we have `0 = p x y`. -/
+def dual : Submodule R N where
```

### What the human reviewer actually said

> We already have similar definitions in a slightly less general context at https://leanprover-community.github.io/mathlib4_docs/Mathlib/LinearAlgebra/SesquilinearForm/Basic.html#Submodule.orthogonalBilin and https://leanprover-community.github.io/mathlib4_docs/Mathlib/LinearAlgebra/BilinearForm/Orthogonal.html#LinearMap.BilinForm.orthogonal
> It would seem sensible to me to unify all of these.

### What the tool produced (confidence: **low**)

> No past review comment maps cleanly; only minor docstring/style echoes (typo/capitalization and variable-binder explicitness already followed) are observable.

**Weak observations:**

- Docstring polish: there’s a likely typo “LinealMap.id” → “LinearMap.id”; similar small docstring wording/capitalization tweaks are common. &nbsp; (axis: `docstring`; support: [#27699](https://github.com/leanprover-community/mathlib4/pull/27699))
- Good use of `variable (p s) in` to localize explicitness; this matches guidance to avoid making parameters explicit globally. &nbsp; (axis: `style-syntax`; support: [#16707](https://github.com/leanprover-community/mathlib4/pull/16707))

### Verdict

Human linked two existing similar definitions and asked to unify. Tool's plausible-concerns list didn't include `unify-with-existing`. Did catch a real typo (`LinealMap`→`LinearMap`) as a weak observation.

---

## Appendix

- **Full 20-case run** (raw JSON, including the 10 cases not shown in this gallery): `data/eval/openpr_v3_1_all20.jsonl`
- **Per-case prompt + completion transcripts** for inspection: `data/eval/transcripts/openpr_*.txt`
- **Held-out closed-PR evaluation** (LLM-judge report): `data/eval/llm_judge_report.md`
- **Prompt-engineering ablation** (v1 vs v2, with cost numbers): `data/eval/prompt_ablation_report.md`
- **The retrieval index itself** (≈35k closed PRs, ≈158k review comments): `data/curated/mathlib4/*.parquet`

## Caveats worth saying out loud

- **n=20.** This gallery is a qualitative sample, not a benchmark. The held-out
  quantitative numbers live in `eval/`. Don't generalise from one card.
- **Index is "closed PRs only".** Any concern that depends on very recent mathlib
  features (e.g. the new `module` / `@[expose] public section` syntax) will have
  thin coverage in the index, and the tool will tend to miss it. That's a real
  known limitation.
- **Counter-arguments are self-generated.** Each suggestion ships with the model's
  own "why this might not apply" sentence. Read those, especially when grading.
- **No claim of correctness.** Some "Past reviewer said" quotes are short paraphrases
  of longer comments. Click the past-PR link to read the full thread.
