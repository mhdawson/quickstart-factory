---
description: Resolve which quickstart this test-suite session applies to
---

# Validation Skill — Quickstart Slug Resolution

## Your Role

Resolve the quickstart repository for this `rh-qs-test-suite` session. This skill runs inside `.rhoai-qs/<slug>/`, while `../` contains every quickstart. A wrong resolution can change the wrong repository, so ambiguity must stop for user input.

## Instructions

**Input Parameters:**
- `{user_message}`: the user's raw request
- `{existing_slugs}`: entries returned by `ls -1 ../ 2>/dev/null`, with no filtering
- `{is_entry_point}`: always `false`
- `{calling_skill}`: always `rh-qs-test-suite`

1. Match an explicit slug or human-readable quickstart name in `{user_message}` against `{existing_slugs}`. Resolve a clear match; return `needs_user_input` for an ambiguous match.
2. If the message names no quickstart and exactly one slug exists, return it with `confirm_with_user: true`.
3. If no slug exists, return `error`. If multiple exist, return `needs_user_input` and list them.
4. Never guess silently.

## Output

Return only this JSON structure:

```json
{
  "resolution": "resolved | needs_user_input | error",
  "slug": "<matched slug or null>",
  "confidence": "high | medium | low",
  "confirm_with_user": false,
  "question_for_user": null,
  "error_message": null
}
```
