from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    record = LaunchConfiguration('record')
    bag_dir = LaunchConfiguration('bag_dir')
    reliability = LaunchConfiguration('subscriber_reliability')
    sensor_topic = PathJoinSubstitution(['/', namespace, 'sensor_pose'])

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        DeclareLaunchArgument('record', default_value='false', choices=['false', 'true']),
        DeclareLaunchArgument('bag_dir', default_value='evidence/pr05/bag'),
        DeclareLaunchArgument('subscriber_reliability', default_value='best_effort',
                              choices=['best_effort', 'reliable']),
        LogInfo(msg=['Recording ', sensor_topic, ': ', record, ', subscriber: ', reliability]),
        Node(package='turtlesim', executable='turtlesim_node', namespace='/', output='screen'),
        Node(
            package='patrol', executable='patrol', namespace=namespace, output='screen',
            remappings=[('turtle1/pose', '/turtle1/pose'), ('cmd_vel', '/turtle1/cmd_vel')],
        ),
        Node(
            package='course_bringup', executable='pose_relay', namespace=namespace,
            remappings=[('pose', '/turtle1/pose')], output='screen',
        ),
        Node(
            package='course_bringup', executable='pose_subscriber', namespace=namespace,
            parameters=[{'reliability': reliability}], output='screen',
        ),
        ExecuteProcess(
            cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir, '--topics', sensor_topic],
            condition=IfCondition(record), output='screen',
        ),
    ])
