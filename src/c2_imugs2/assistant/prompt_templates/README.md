# Assistant prompts

Each directory is an immutable prompt release selected with
`C2_IMUGS2_LLM_PROMPT_VERSION` (default: `mission/v4`). A response records that
exact ID.

New releases use a family-qualified layout:

```text
<family>/<release>/prompt.json
```

The manifest declares ordered `system` and optional `examples` file lists plus
one `mission_contract`, `user_message`, and `structured_output` file. Component
paths are relative to the release directory. This permits parallel families
and model-specific experiments without changing the loader or crowding one
system file. Historical flat `v1` through `v3` directories use the original
four-file layout and remain loadable for reproducibility.

To make a material change, copy an entire release to a new immutable release
ID, update the manifest's `version`, edit only the copy, and select the new ID
through the environment. Never silently change a release that has produced
recorded results.

Prompt requirements:

- `user_message` must retain `picture_revision`, `picture_observed_at`,
  `operational_picture_json`, and `user_message` placeholders.
- Literal JSON braces in every component must be doubled because LangChain
  interprets braces as template variables.
- Keep stable behavior in system components, request-specific environment data
  in `user_message`, and machine-consumed response shape in
  `structured_output`.
- Examples should be short, correct, representative, and kept in a deliberate
  order.

Prompt edits do not change mission validity. Every proposed mission still
requires deterministic schema/semantic/environment-binding validation and operator review;
planner feasibility is a separate future check.
