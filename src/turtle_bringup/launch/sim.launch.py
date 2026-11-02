"""Start the standard turtlesim node for practice PR02."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Create the actions that start one turtlesim process."""
    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            output='screen',
        ),
    ])
