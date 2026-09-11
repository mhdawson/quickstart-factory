# Fixture Contract

Each immediate child directory of `test/skills/<skill-name>/` is a validation case:

```text
test/skills/<skill-name>/<case-name>/
├── input-repo/                 # Required: source quickstart copied to .rhoai-qs/qs-test-quickstart/
├── expected-output-repo/       # Required: approved baseline for evaluation
├── test-config.yaml            # Required: target-skill prompt, question-answer context, and validation options
└── comparison-ignore            # Optional: newline-delimited glob paths excluded from comparison
```

`input-repo/` contains the complete starting state the target skill should receive. `expected-output-repo/` is the complete repository tree after a known-good run of the target skill: it includes the original files from `input-repo/` plus every generated or modified file. It must not contain `.git/`, credentials, secrets, or runtime state.

`test-config.yaml` has this shape:

```yaml
run-skill-command: Add nightly testing to qs-test-quickstart.
question-answer-context: |
  The test fixture is a disposable quickstart. Use only details in its files.
validation-options:
  mode: full-baseline
  additional-instructions: |
    Confirm the generated workflow retains its concurrency group.
execution:
  network: required
  external-dependencies:
    - https://github.com/rh-ai-quickstart/quickstart-ci-testing
```

To run the target skill without a supplemental prompt, use an empty mapping:

```yaml
{}
```

`run-skill-command` is optional. When present, it must be a non-empty string and is the exact user request sent to the target skill. When absent, the target skill is invoked without an added user request. It is never executable shell. State the target slug explicitly as `qs-test-quickstart` when the target skill needs a slug.

`question-answer-context` is optional and must be a non-empty string when present. It is additional factual context the runner can use to answer a target skill's question. It cannot approve external actions, disclose a credential, or choose whether to overwrite unanticipated user work.

`validation-options` is optional and must be a YAML mapping when present. It controls evaluation only; it does not change how the target skill is invoked. Its optional `additional-instructions` entry must be a non-empty string when present. It is passed only to the output rater to add fixture-specific checks or explain what differences matter. In `full-baseline` mode, it cannot waive required baseline artifacts; in either mode, it cannot authorize external actions.

`validation-options.mode` is optional and defaults to `full-baseline`.

`execution` is optional and defaults to no network requirement. Set `execution.network: required` when the target skill must reach an external service or repository. List each required Git repository under `external-dependencies`; the validator preflights these with `git ls-remote` and must launch the case runner in a network-enabled execution context. The runner command must also have read/write access to the repository and the fixed disposable path `.rhoai-qs/qs-test-quickstart/`. `--network-profile network` declares the required execution profile but does not grant permissions by itself. A failed preflight is recorded as infrastructure evidence, but does not authorize skipping target-skill execution.

The validator's case-runner gate is synchronous: `run_case.py` waits for the runner process to exit, accepts only a runner result with `status: completed`, and then creates the validator-owned output manifest and tree hash. Baseline comparison and rating must not start until that completion record exists. Runner commands and adapter prompt files may use `{runner_output}`, `{quickstart_root}`, and `{case_path}` placeholders; these are expanded by the coordinator without invoking a shell.

The optional runner adapters (`codex`, `claude`, `cursor`, and `gemini`) invoke foreground clients only. They preserve the caller's environment and workspace, and they do not themselves enforce network allowlists. Network enforcement belongs to the host/container/proxy that launches the adapter.

- `full-baseline` requires a complete approved `expected-output-repo/`; all baseline artifacts remain part of the evaluation. Additional instructions can add checks but cannot remove baseline requirements.
- `targeted` requires `validation-options.additional-instructions`. Those instructions are the exclusive evaluation scope, so baseline-tree differences outside that scope do not affect the score. `expected-output-repo/` must still exist but may be empty or contain only `.gitkeep`.

For example, a targeted privilege check is:

```yaml
validation-options:
  mode: targeted
  additional-instructions: |
    Validate only that the skill flags cluster-admin privilege as required.
```

The rater compares the actual copied quickstart to `expected-output-repo/` as follows:

- Every baseline path is required: regular files are compared by content, and directories (including empty directories) are compared by presence and type.
- Additional actual files or directories are reported as differences.
- Use `comparison-ignore` only for genuinely nondeterministic paths, such as timestamped reports. Each line is a path glob relative to the quickstart root; blank lines and `#` comments are ignored.
- A baseline is an approved oracle, not permission to copy it into the actual output during ordinary validation.

Keep test reports and debugging archives in `test/skills/reports/<skill-name>/<case-name>/`; the top-level `reports/` directory is not a test case. The archive is a capture of generated output only and must never be used as a baseline. An empty `expected-output-repo/` (or one containing only `.gitkeep`) is intentionally invalid until an approved baseline is added through the normal fixture-maintenance workflow.
