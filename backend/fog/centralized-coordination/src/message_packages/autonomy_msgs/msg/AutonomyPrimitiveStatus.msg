unique_identifier_msgs/UUID primitive_id  # Unique identifier for the primitive
string primitive_type  # Type of primitive (e.g., "waypoint", "search_mine", "dispose_mine")
uint8 status  # Execution status of the primitive (see codes below)
float64 progress  # Progress percentage (0.0 to 100.0)
string feedback  # Optional feedback message

# Status Codes
uint8 PENDING = 0    # Primitive is waiting to be executed
uint8 ACTIVE = 1     # Primitive is currently executing
uint8 COMPLETED = 2  # Primitive finished successfully
uint8 FAILED = 3     # Primitive failed during execution
uint8 ABORTED = 4    # Primitive was forcefully stopped before completion
