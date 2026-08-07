# AutonomyStatus.msg

unique_identifier_msgs/UUID autonomy_objective_id  # The current objective being executed
uint8 status  # Overall status of the autonomy system
AutonomyPrimitiveStatus[] primitive_statuses # List of primitives being executed within the current objective


# Status Codes
uint8 PENDING = 0
uint8 ACTIVE = 1
uint8 COMPLETED = 2
uint8 FAILED = 3
uint8 ABORTED = 4
