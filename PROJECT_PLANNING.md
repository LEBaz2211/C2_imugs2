# Project Planning

## Purpose

This file is the living high-level plan for the project. It records the main objective, the order of major work, and the compatibility rules that should guide implementation choices.

Read it at the start of every new working session involving architecture, ROS integration, mission contracts, the UI/backend boundary, LLM integration, scenarios, or benchmarking. Keep detailed implementation notes in their relevant technical documents; keep this file focused on project-wide goals.

If a new session reveals a recurring problem, compatibility trap, or important fact that future sessions could otherwise miss, add a short entry to the **Session Problem Log** at the end. Do not log temporary progress, routine test results, or problems already explained in the documentation.

## Main Objective

The first objective is to create a reliable multi-robot system with a clear, practical UI and a backend that uses the correct mission, task, map, agent, REST, and ROS contracts.

Once that system works reliably, integrate an LLM that accepts natural language, retrieves the correct operational and contract context, and creates valid mission definitions. Then create representative multi-robot scenarios and a repeatable benchmark. In the far future, the LLM may control the wider system through safe, observable, and explicitly bounded tools.

The LLM and benchmark must build on a working multi-robot system; they should not replace or bypass the system's contracts.

## Non-Negotiable Compatibility Rules

Do not edit `legacy_ros/` unless the task explicitly asks for a legacy-code change, and do not replace real legacy nodes with mocks during compatibility testing. Prefer fixes in adapters, configuration, tests, UI, or documentation.

Preserve message and service structures, topic and service names, numeric enums, mission and task-plan shapes, and coordinate conventions. Keep legacy normalization and ROS behavior in the backend. Any necessary contract migration requires documentation, compatibility handling, tests, and user approval. Explicit legacy changes should be minimal and verified against the actual Dockerized stack.

## ZE Plan

- [x] Run the actual legacy ROS fog, planner, fleet, edge, and autonomy components in Docker.
- [x] Provide a map-based UI and FastAPI compatibility adapter around the legacy runtime.
- [ ] Complete and verify a reliable multi-robot mission flow with a clear UI, diagnostics, and modular backend boundaries.
- [ ] Update the backend to adapt to STANAG 4817, and make sure all features tested and working.
- [ ] Integrate with MQTT system.
- [ ] Create context retrieval to provide to LLM
- [ ] NL to Mission description generation and pipeline.
- [ ] Test for small reapetable mission.
- [ ] Create large level scenarios for benchmarking.

## Refactor Legacy backend

This is the subtasks of task 3 of ZE Plan

- [x] Create new backend that is the copy of the legacy, but that we will modify to adapt to our needs. This totally is a place holder as there might be some architectural changes.
- [x] List out all the present feature and different use cases (examples of workflows), detailed with code block explanation. One document with first the list of features and list of possible workflows/use cases and when we click it goes to the specific explanation. Also need a short review of the architecturein general, and how it is done in ros.
- [ ] We select and think of different behaviour of different elements to our needs. Maybe architectural changes.
- [ ] We implement the changes one by one and test them, with unit tests where possible.
- [ ] Test with the UI.


## ZE Log
