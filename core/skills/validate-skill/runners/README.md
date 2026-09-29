# Runner adapters

These adapters translate the validator's backend-neutral execution request
into a foreground agent invocation. They do not grant permissions themselves.

The coordinator supplies the discovered target skill name. Each adapter invokes
that skill through the runtime's native mechanism: slash invocation for Claude
Code and Cursor, and explicit skill activation language for Codex and Gemini.
The case-runner prompt is supplemental execution policy; it must not load or
replay the target `SKILL.md` itself.

The Codex adapter uses `$skill-name` activation and starts from the Factory
repository root so repo-scoped skills are discovered the same way they are in
normal Factory use. The fixed disposable quickstart remains the case input and
target-output path. The launcher keeps Git commands inside that fixture from
inheriting the Factory repository's branch metadata.

The coordinator or the process wrapper must provide the actual execution
boundary:

- the workspace mount/write policy;
- network access or egress allowlisting;
- inherited authentication environment; and
- synchronous process completion.

`VALIDATE_ALLOWED_DOMAINS` is an interface for that outer boundary. It is not
a security control when passed only as an environment variable.

The Cursor adapter intentionally targets the foreground CLI. It never creates
a Cursor Background Agent implicitly. The Gemini adapter uses headless
`--prompt` mode with explicit approval handling; it never creates a separate
hosted/background session.
