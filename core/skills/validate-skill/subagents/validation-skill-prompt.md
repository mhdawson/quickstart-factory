---
description: Verify that validate-skill is operating only on its fixed disposable quickstart fixture.
---

# Validation Context

## Your Role

Confirm that this meta-skill will use the dedicated disposable quickstart path and cannot be confused with a real quickstart selection.

## Inputs

- `slug`
- `quickstart_root`
- `fixture_root`
- `target_skill`

## Resolution Logic

The only valid slug is `qs-test-quickstart`. The only valid quickstart root is `.rhoai-qs/qs-test-quickstart/`, and the fixture root must be under `test/skills/<target_skill>/`.

Return `error` if any input differs. Do not attempt fuzzy matching or ask the user to select another quickstart; this skill intentionally has a fixed disposable context.

## Output

```json
{
  "resolution": "resolved | error",
  "slug": "qs-test-quickstart | null",
  "confidence": "high",
  "error_message": "string | null"
}
```
