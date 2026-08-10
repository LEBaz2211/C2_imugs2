# Extracted contract reference

This site contains only contracts obtained by static extraction from checked-in software and schema files.

!!! info "Extraction scope"
    FastAPI decorators and frontend calls are parsed from Python/TypeScript. ROS declarations and types are parsed from C++/Python plus `.msg`/`.srv` files. Enums and supported state transitions are parsed from source. Manually curated workflows, components, scenarios, and UI activities are not included.

Source digest: `0e0f1b2efeded4f9`

| Extracted contract | Count | Open |
|---|---:|---|
| HTTP endpoints | 26 | [HTTP API](http/index.md) |
| ROS topics | 23 | [ROS topics](ros-topics/index.md) |
| ROS services | 13 | [ROS services](ros-services/index.md) |
| ROS message/service types | 49 | [ROS types](ros-types/index.md) |
| Source enum groups | 17 (1 conflicts) | [Enums](enums/index.md) |
| Source-parsed state machines | 2 | [States](states/index.md) |
| JSON Schemas | 4 | [Schemas](schemas/index.md) |

## Limitations

Static extraction can miss names assembled dynamically at runtime. An entry proves that a declaration or definition was found in source; it does not prove that the interface was observed on a running ROS graph.
