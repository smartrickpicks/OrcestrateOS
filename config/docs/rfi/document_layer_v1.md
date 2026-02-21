# Document Layer RFI — V1

Status: Open RFI  
Created: 2026-02-09  
Scope: Contract → Document cardinality, roles, and governance

---

## 1. Cardinality Questions

| Question | Context |
|----------|---------|
| Is a contract always 1:1 with a PDF? | Current assumption: yes. Some document types (amendments, addenda) may introduce 1:N. |
| Can a single PDF contain multiple contracts? | Edge case: combined execution packages. |
| Do document types change cardinality? | e.g., MSA with multiple SOWs attached. |

**Decision needed**: Define canonical cardinality per document type.

---

## 2. Mandatory vs Inferred Document Roles

| Role | Current State | Question |
|------|--------------|----------|
| Primary Agreement | Inferred from file name heuristics | Should this require explicit classification? |
| Amendment | Inferred | Same — inferred vs mandatory tag? |
| Addendum | Not yet supported | When added, mandatory or inferred? |
| Supporting Document | Catch-all | Should there be a structured sub-taxonomy? |

**Decision needed**: Which roles require explicit human classification vs automated inference?

---

## 3. Approval Path for New Document Type

Proposed workflow:
1. Admin or Architect proposes new document type via Schema Tree Editor.
2. Proposal creates a patch artifact routed through standard lifecycle.
3. Verifier reviews type definition (fields, cardinality, role).
4. Admin promotes to active config.

**Open question**: Should new types be tenant-scoped first, then promoted globally?

---

## 4. Confidence / Human-Gate Thresholds

| Scenario | Proposed Threshold | Gate |
|----------|--------------------|------|
| Document role inference confidence < 70% | Require human confirmation | Analyst |
| OCR quality score < 50% | Block as OCR_UNREADABLE | Pre-Flight |
| File name pattern match < 60% | Flag for review | Analyst |

**Decision needed**: Exact threshold values and which role handles each gate.

---

## 5. Rollup Behavior: Document Ambiguity → Contract State

When a document's type or role is ambiguous:
- Should the parent contract be blocked?
- Should it be flagged as "needs review" but not blocking?
- Should it only affect the document-level record?

**Proposed**: Ambiguity flags the contract as `needs_review` but does not block downstream processing. Blocking only occurs when OCR is unreadable or required fields are missing.

---

## 6. Tenant-Scoped vs Global Document Type Promotion

| Approach | Pros | Cons |
|----------|------|------|
| Tenant-first | Safe, isolated testing | Configuration drift across tenants |
| Global-first | Consistency | Risk of breaking other tenants |
| Tenant with promotion | Best of both | Requires promotion workflow |

**Proposed**: Tenant-scoped by default. Architect role can promote to global via TruthPack calibration flow.

---

## Next Steps

- [ ] Collect stakeholder input on cardinality per document type
- [ ] Define confidence thresholds with QA team
- [ ] Prototype document role confirmation UI
- [ ] Draft document type schema for Schema Tree Editor
