# autonomy_msgs/msg/VehicleConstraints

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleConstraints.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `geometry_msgs/Twist` | `max_speed` |
| message | `geometry_msgs/Accel` | `max_acceleration` |
| message | `float64` | `max_weight` |
| message | `float64` | `max_tilt_angle` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Autonomy publishes the Themis vehicle profile

!!! success "Runtime Observed"
    Phase: robot discovery.

```json
{
  "active_autonomy_mode": 1,
  "vehicle_constraints": {
    "max_speed": {
      "linear": {
        "x": 4.5,
        "y": 0.0,
        "z": 0.0
      },
      "angular": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      }
    },
    "max_acceleration": {
      "linear": {
        "x": 8.0,
        "y": 0.0,
        "z": 0.0
      },
      "angular": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      }
    },
    "max_weight": 16.0,
    "max_tilt_angle": 1.8
  },
  "vehicle_info": {
    "vehicle_type": "ugv",
    "fuel_status_pct": 85,
    "fuel_hours": 1.5,
    "battery_status_pct": 90,
    "battery_hours": 3.0,
    "sensor_list": [
      {
        "type": 1,
        "status": 1,
        "field_of_view": [
          360.0,
          3.14
        ]
      },
      {
        "type": 2,
        "status": 1,
        "field_of_view": [
          120.0,
          2.0
        ]
      },
      {
        "type": 3,
        "status": 1,
        "field_of_view": [
          180.0,
          3.14
        ]
      }
    ],
    "vehicle_dimensions": [
      0.9,
      0.6,
      0.55
    ]
  }
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleConstraints.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleConstraints.msg#L1)
