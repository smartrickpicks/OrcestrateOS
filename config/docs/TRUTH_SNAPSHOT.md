# TRUTH_SNAPSHOT

## Purpose
Define what is considered ground truth for semantics at any point in time and how that truth is governed, versioned, and audited within the Kiwi Semantic Control Board.

## Definition of Semantic Ground Truth
Semantic ground truth is the approved set of meanings, expectations, and rule behaviors captured as human-authored, reviewable configuration artifacts. It is independent of runtime execution and remains stable even when downstream systems fail or behave unexpectedly.

Ground truth is:
- Plain-English intent documented for operators and verifiers
- Structured rules expressed as versioned config files
- Audited through documented rationale and changelog entries

Ground truth is not:
- Runtime behavior or system availability
- Code, prompts, or integrations
- A substitute for operational policies or API contracts

## Relationship Between Base, Patches, and Truth
- config_pack.base.json: The baseline semantic model. It defines canonical structures, naming, and initial rules.
- Patch files (config_pack.patch.json): Reviewed changes that refine, extend, or deprecate elements of the base. Each patch references the base_version it builds upon.
- Canonical truth at time T: The base plus all approved patches merged in order on the main branch. Deprecated elements are excluded once a patch explicitly deprecates them.

## Versioning and Changelog
- Every approved change increments a version identifier.
- The changelog records why the change is needed, how it was validated, and what was impacted.
- Each changelog entry links to the reviewed patch and any example previews used during evaluation.

## Verifier Decision: What Becomes Canonical
A rule or change becomes canonical only when verifiers confirm that it:
- States intent clearly in plain English
- Aligns with canonical schemas and naming
- Passes offline preview on example datasets
- Does not introduce unresolved conflicts
- Documents downstream risk considerations
- Includes a complete changelog entry and version update

If any item above fails, the change is not canonical and must be revised.

## When Downstream Systems Disagree with the Control Board
- The control board remains the single source of semantic truth.
- Disagreements (unexpected runtime behavior, parser limitations, or system bugs) do not alter ground truth.
- Operators file an issue referencing the relevant rule, the preview, and the observed divergence.
- If semantics must change, submit a new patch with updated intent, review, preview, and changelog. Prior truth is not retroactively edited.
