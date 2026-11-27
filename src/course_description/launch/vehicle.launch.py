from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('course_description')
    model = LaunchConfiguration('model')
    description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' "', model, '"']), value_type=str,
    )
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value=PathJoinSubstitution([
            share, 'urdf', 'vehicle.urdf.xacro',
        ])),
        DeclareLaunchArgument('rviz', default_value='false', choices=['false', 'true']),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description}], output='screen'),
        Node(package='rviz2', executable='rviz2', arguments=[
            '-d', PathJoinSubstitution([share, 'rviz', 'vehicle.rviz']),
        ], condition=IfCondition(LaunchConfiguration('rviz')), output='screen'),
    ])
