# Assistant prompts

Each directory is an immutable prompt version selected with
`C2_IMUGS2_LLM_PROMPT_VERSION` (default: `v3`). To make a material prompt
change, copy the current directory to a new version and edit the copy so an
assistant response can always report the prompt version it used.

Files in each version:

- `system.txt` defines runtime authority, safety, and mission-design rules.
- `mission_contract.txt` gives the model the canonical mission shape and
  behavior-specific drafting constraints. Literal JSON braces must be doubled.
- `user_message.txt` lays out the current operational picture and operator
  message. It must retain the `picture_revision`, `picture_observed_at`,
  `operational_picture_json`, and `user_message` placeholders.
- `structured_output.txt` defines the optional response envelope. Literal JSON
  braces must be doubled because LangChain prompt templates use braces for
  variables.

Prompt edits do not change mission validity. Every proposed mission still
requires deterministic schema/semantic/environment-binding validation and operator review;
planner feasibility is a separate future check.
