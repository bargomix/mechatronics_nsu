"""Choose a velocity command without ROS nodes, callbacks or side effects."""

from geometry_msgs.msg import Twist
from turtlesim.msg import Pose


def choose_command(pose: Pose | None) -> Twist:
    """Stay still until the first pose, then move forward along an arc."""
    command = Twist()
    if pose is not None:
        command.linear.x = 0.5
        command.angular.z = 0.3
    return command
