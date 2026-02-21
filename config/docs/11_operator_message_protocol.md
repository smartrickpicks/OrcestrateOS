# Operator Message Protocol

## Purpose
Define the standard JSON envelope format for communication between agents (REPLIT, KIWI, ZAC_REVIEW) and operators within the Semantic Control Board.

## Scope
- Governance-only messaging
- Offline-first, artifact-driven
- No APIs, credentials, or prompts

---

## JSON Envelope Standard

Every message follows this structure:

```json
{
  "envelope_id": "<unique-id>",
  "target": {
    "agent": "<REPLIT | KIWI | ZAC_REVIEW>"
  },
  "intent": "<TASK | REVIEW | INFO | AWAITING_OPERATOR_INPUT>",
  "operator_action": "<NONE | RUN_COMMANDS | PASTE_OUTPUT | APPROVE>",
  "payload": {
    // intent-specific content
  }
}
```

### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `envelope_id` | Yes | Unique identifier for traceability (e.g., `TASK-REPLIT-001`) |
| `target.agent` | Yes | The agent that should process this message |
| `intent` | Yes | What the message is requesting |
| `operator_action` | Yes | What the operator must do (if anything) |
| `payload` | Yes | Intent-specific content and instructions |

### Intent Values

| Intent | Description |
|--------|-------------|
| `TASK` | Agent should execute a task autonomously |
| `REVIEW` | Agent should review artifacts and provide feedback |
| `INFO` | Informational message, no action required |
| `AWAITING_OPERATOR_INPUT` | Agent is blocked until operator provides input |

### operator_action Values

| Value | Description |
|-------|-------------|
| `NONE` | Agent proceeds autonomously; operator not required |
| `RUN_COMMANDS` | Operator must run specified shell commands |
| `PASTE_OUTPUT` | Operator must paste output from an external system |
| `APPROVE` | Operator must review and approve before agent continues |

---

## Examples

### Example 1: TASK to REPLIT

```json
{
  "envelope_id": "TASK-REPLIT-001",
  "target": { "agent": "REPLIT" },
  "intent": "TASK",
  "operator_action": "NONE",
  "payload": {
    "goal": "Run smoke test and capture baseline evidence",
    "commands": ["bash scripts/replit_smoke.sh"],
    "deliverables": ["out/sf_packet.preview.json"],
    "acceptance_criteria": ["Smoke test passes with no diff"]
  }
}
```

### Example 2: TASK to KIWI

```json
{
  "envelope_id": "TASK-KIWI-001",
  "target": { "agent": "KIWI" },
  "intent": "TASK",
  "operator_action": "NONE",
  "payload": {
    "goal": "Validate rule SF_R1_LABEL_NOT_ARTIST against example dataset",
    "rule_id": "SF_R1_LABEL_NOT_ARTIST",
    "dataset": "examples/standardized_dataset.example.json",
    "expected_outcome": "Two warnings for record_label subtypes with artist_name populated"
  }
}
```

### Example 3: REVIEW to ZAC_REVIEW

```json
{
  "envelope_id": "REVIEW-ZAC-001",
  "target": { "agent": "ZAC_REVIEW" },
  "intent": "REVIEW",
  "operator_action": "APPROVE",
  "payload": {
    "artifact": "config/config_pack.example.patch.json",
    "review_type": "semantic_change",
    "checklist": [
      "Rule intent is clear and documented",
      "base_version matches current base",
      "Preview passes on example dataset"
    ],
    "notes": "New rule deprecates SF_R0_LEGACY; requires approval before merge"
  }
}
```

---

## Handling AWAITING_OPERATOR_INPUT

When an agent sets `intent: AWAITING_OPERATOR_INPUT`, execution is paused until the operator provides the required input.

### What the Agent Should Do

1. Set `intent` to `AWAITING_OPERATOR_INPUT`
2. Set `operator_action` to the specific action required (`RUN_COMMANDS`, `PASTE_OUTPUT`, or `APPROVE`)
3. Include clear instructions in `payload.instructions`
4. Include `payload.resume_with` describing what format the operator's response should take

### What the Operator Must Do

1. Read `payload.instructions` carefully
2. Perform the requested action:
   - `RUN_COMMANDS`: Execute the specified commands and capture output
   - `PASTE_OUTPUT`: Paste the requested data from an external system
   - `APPROVE`: Review the artifact and confirm approval
3. Provide the result in a follow-up message

### Example: AWAITING_OPERATOR_INPUT

```json
{
  "envelope_id": "AWAIT-REPLIT-001",
  "target": { "agent": "REPLIT" },
  "intent": "AWAITING_OPERATOR_INPUT",
  "operator_action": "RUN_COMMANDS",
  "payload": {
    "reason": "Git operations are restricted in agent environment",
    "instructions": "Please run the following commands in your terminal",
    "commands": [
      "git add docs/replit_baseline.md CHANGELOG.md",
      "git commit -m \"docs(governance): lock baseline evidence\"",
      "git push"
    ],
    "resume_with": "Paste the output of `git log --oneline -n 3` to confirm"
  }
}
```

---

## Rules

1. **Never block on operator unless required**: Agents should only set `operator_action` to a blocking value (`RUN_COMMANDS`, `PASTE_OUTPUT`, `APPROVE`) when they genuinely cannot proceed autonomously.

2. **Default to autonomous execution**: If `operator_action` is `NONE`, the agent proceeds without waiting for operator input.

3. **Be explicit about requirements**: When operator input is needed, the `payload` must include clear instructions and expected response format.

4. **Envelope IDs are for traceability**: Use consistent naming (e.g., `TASK-<AGENT>-<SEQ>`) to enable audit trails.

5. **Respect agent boundaries**: Only send messages to agents that can process the specified intent.
