from geometry_msgs.msg import Twist
from turtlesim.msg import Pose

from patrol.settings import Settings

_DEFAULTS = Settings()


def choose_command(
    pose: Pose | None,
    linear_speed: float = _DEFAULTS.linear_speed,
    turn_rate: float = _DEFAULTS.turn_rate,
) -> Twist:
    command = Twist()
    if pose is not None:
        command.linear.x = linear_speed
        command.angular.z = turn_rate
    return command
