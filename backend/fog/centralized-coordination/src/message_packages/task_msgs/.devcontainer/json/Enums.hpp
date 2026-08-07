#pragma once
namespace task_msgs::json::enums
{
    enum class RequestState
    {
        INACTIVATE = 0, // inactivate client & do nothing
        ACTIVATE = 1    // activate the client & start tasks
    };

    enum class State
    {
        INACTIVE = 0, // inactive
        ACTIVE = 1    // active
    };

    enum class TaskRequestState
    {
        STOP = 0,    // request to stop the task & re-init
        EXECUTE = 1, // request to execute the task
        PAUSE = 2,   // request to pause the task
        DELETE = 3   // request to delete the task
    };

    enum class TaskState
    {
        STOPPED = 0,   // stopped, but not completed or started
        STARTED = 1,   // started
        PAUSED = 2,    // paused
        COMPLETED = 3, // completed the task
        ABORTED = 4,   // aborted
        DELETED = 5    // deleted
    };

    enum class TaskType
    {
        DRIVE = 0,                     // waypoint drive task
        EXAMPLE_PERIPHERAL_CAMERA = 1, // move camera task (example)
        EXAMPLE_DEFENSE_SHIELDS = 2,   // move camera task (example)
    };
}