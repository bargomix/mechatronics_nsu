"""Receive turtlesim poses and publish a command every 0.1 seconds."""

from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose

from patrol.commands import choose_command


class Patrol(Node):
    """Keep the last pose and let the timer select the next command."""

    def __init__(self):
        super().__init__('patrol')
        self._last_pose: Pose | None = None
        self._pose_subscription = self.create_subscription(
            Pose, '/turtle1/pose', self._on_pose, 10,
        )
        self._command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self._timer = self.create_timer(0.1, self._on_timer)
        self.get_logger().info('Patrol started: command timer 0.1 s')

    def _on_pose(self, message: Pose) -> None:
        self._last_pose = message

    def _on_timer(self) -> None:
        self._command_publisher.publish(choose_command(self._last_pose))


def main(args=None):
    """Initialize ROS, serve callbacks, then clean up after Ctrl+C."""
    rclpy.init(args=args)
    node = Patrol()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
