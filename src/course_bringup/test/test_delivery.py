import time

import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy
from turtlesim.msg import Pose

from course_bringup.pose_relay import PoseRelay
from course_bringup.pose_subscriber import PoseSubscriber


def test_relay_qos():
    context = Context()
    rclpy.init(args=[], context=context)
    executor = SingleThreadedExecutor(context=context)
    nodes = []
    try:
        options = {'namespace': 'pr05_test', 'context': context}
        source = Node('source', **options)
        nodes.append(source)
        relay = PoseRelay(**options)
        nodes.append(relay)
        for reliability in ('reliable', 'best_effort'):
            nodes.append(PoseSubscriber(
                cli_args=['--ros-args', '-r', f'__node:={reliability}'],
                parameter_overrides=[Parameter('reliability', value=reliability)],
                **options,
            ))
        reliable, best_effort = nodes[-2:]
        publisher = source.create_publisher(Pose, 'pose', 10)
        poses = []
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        source.create_subscription(Pose, 'sensor_pose', poses.append, qos)

        for node in nodes:
            executor.add_node(node)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if publisher.get_subscription_count() and relay.count_subscribers('sensor_pose') == 3:
                break
            executor.spin_once(timeout_sec=0.05)
        assert publisher.get_subscription_count() == 1
        assert relay.count_subscribers('sensor_pose') == 3

        pose = Pose(x=2.5, y=4.0, theta=0.5)
        for _ in range(12):
            publisher.publish(pose)
            for _ in range(4):
                executor.spin_once(timeout_sec=0.02)

        assert best_effort.received > 0
        assert reliable.received == 0
        assert poses and all(message == pose for message in poses)
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        rclpy.try_shutdown(context=context)
