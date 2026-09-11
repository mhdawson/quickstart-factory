# Reasoning Guardrails for validate-skill

These concern areas help validate a Factory skill without contaminating its fixtures or bypassing its safety boundaries.

## How to Use

Reason freely about each case, then check whether fixture isolation, intent, safety, and evaluation evidence have all been considered. Skip concerns that do not apply.

## Concern Areas

### Fixture isolation

Consider whether the exact disposable target was reset and whether any output can leak between cases. Inspect copied paths and generated artifacts, not assumptions about cleanup.

### Faithful invocation

Consider whether the target received the exact case prompt and only the fixture state it would have in a real run. Do not reinterpret `run-skill-command` as a shell command or add requirements not stated by the fixture.

### Question handling and authority

Consider whether an answer is objectively established by the fixture. A fixture can answer factual setup questions, but never grants permission for destructive changes, external writes, credentials, or cluster operations.

### Baseline quality

Consider whether expected artifacts specify observable behavior rather than incidental formatting. Distinguish legitimate dynamic values from unexpected drift, and distinguish a missing baseline from a target-skill failure.

### Rating integrity

Consider whether the score reflects evidence and functional importance. Do not use a score to hide a blocked run; report it as blocked with the exact question instead.

## When to Stop Checking

Stop once every case has a reproducible starting state, an execution result, and evidence-backed rating or explicit blocker. Do not continue by changing fixtures to make a target skill pass.
