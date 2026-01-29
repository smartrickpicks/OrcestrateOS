# Resolver + Salesforce Matching (Plain English)

This page explains the **main bottleneck** we keep hitting:
- Resolver needs **something concrete** to fetch the contract file.
- Salesforce matching needs **enough identifiers** to confidently attach our extracted/standardized data to the right Salesforce records.

## 1) What the Resolver is
The Resolver is the stage that answers one question:

**“Where do I download this contract from?”**

It does not interpret the contract. It only tries to obtain an accessible URL.

### What inputs the Resolver can use
A contract is considered “resolvable” if it has at least one of these pointer types:
1. **Direct web link** (`file_url`) that is accessible (public or presigned https)
2. **Salesforce IDs** (ContentVersion / ContentDocument / Opportunity) that let us build a Salesforce download request
3. **S3 location** (bucket + key) that can be presigned by an approved service

### Pointer precedence
Resolver tries pointers in this general order:
1. `https_direct` (fastest and simplest)
2. `salesforce` (requires SF IDs)
3. `s3` (requires bucket + key)

## 2) Why “NO_RESOLVABLE_POINTERS” happens
You’ll see this when **none** of the above pointer types are available.

In practice it means:
- `file_url` is blank (or placeholder like “N/A”)
- AND there are **no** Salesforce IDs provided
- AND there are **no** S3 pointers provided

So the Resolver has nothing to fetch.

### Quick operator fixes
Pick one:
- Add a working `file_url` in the dataset row
- Provide the Salesforce IDs that point to the file
- Provide S3 bucket + key (through approved channels)

## 3) How Salesforce matching relates (and why we care)
Resolver gets us an accessible file. Then Extraction + QA run. Then the Salesforce Rules stage runs.

But there’s a second “Salesforce problem” we’re solving in parallel:

**“Which Salesforce records does this row belong to?”**

That’s what you referred to as “grabbing the keys” and “confidence based on how many match.”

### What we mean by “keys”
When we say “keys,” we mean stable identifiers we can use to attach our data to Salesforce objects, like:
- Account identifiers (name + other fields)
- Opportunity IDs (if we have them)
- ContentDocument / ContentVersion IDs (for the contract file)

If we don’t have a direct ID, we do a best-effort match using required fields.

## 4) Confidence scoring (simple model)
Confidence is just a score that answers:

**“How sure are we that this row matches that Salesforce record?”**

A simple approach:
- Choose a small set of **required match fields** for each object type (Account, Opportunity, etc.)
- Compare inbound row values against Salesforce record values
- Count how many fields match

Example (Account match):
- Required fields (example): account_name, billing_country, billing_city
- If 3/3 match → high confidence
- If 2/3 match → medium confidence
- If 1/3 match → low confidence

Important: confidence should be transparent and explainable (operators must see what matched and what didn’t).

## 5) How this ties into subtype → schema
Subtype is our shortcut to knowing **what data should exist**.

Example:
- If subtype = record_label
  - we expect label-like company fields
  - we do NOT expect artist_name to be populated

So subtype drives two things:
1. **Schema expectations** (what fields should exist / be blank)
2. **Match strategy** (which fields matter most for confidence)

## 6) How joins work across the pipeline
When we connect one stage’s output to another stage’s inputs:
1. Join on `contract_key`
2. If missing, join on `file_url`
3. If missing, join on `file_name`

If we can’t join, we do NOT guess. We emit an issue (that’s how we avoid silent data corruption).

## 7) Practical troubleshooting checklist
When a run fails or looks “empty,” check in this order:

### A) Loader
- Did we attach the dataset? If not, you’ll see `MISSING_DATASET_ATTACHMENT`.

### B) Packager
- Did we generate `contract_anchors`? If 0, there’s nothing to resolve.

### C) Resolver
- Are there usable pointers?
- If not, you’ll see “missing_match_inputs” / “NO_RESOLVABLE_POINTERS” style failures.

### D) QA
- If text quality is severely broken, mark for manual review.

### E) Salesforce Rules
- Rules require canonical fields (post-standardizer). If subtype isn’t available, it must be resolved from contract_context or flagged.

## 8) What we’re building toward
A workflow where operators can:
- See why Resolver failed (missing pointers)
- See Salesforce match confidence (what matched)
- Add new subtype/schema rules as they discover patterns
- Generate a config_pack patch safely (no code)
