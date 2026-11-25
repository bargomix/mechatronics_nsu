import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from turtlesim.msg import Pose


class PoseRelay(Node):
    def __init__(self, **kwargs):
        super().__init__('pose_relay', **kwargs)
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        publisher = self.create_publisher(Pose, 'sensor_pose', qos)
        self.create_subscription(Pose, 'pose', publisher.publish, 10)
        self.get_logger().info('Relaying pose to sensor_pose with best_effort')


def main(args=None):
    rclpy.init(args=args)
    node = PoseRelay()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
