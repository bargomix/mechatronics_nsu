from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from turtlesim.msg import Pose

RELIABILITY = {
    'best_effort': ReliabilityPolicy.BEST_EFFORT,
    'reliable': ReliabilityPolicy.RELIABLE,
}


class PoseSubscriber(Node):
    def __init__(self, **kwargs):
        super().__init__('pose_subscriber', **kwargs)
        reliability = self.declare_parameter(
            'reliability', 'best_effort', ParameterDescriptor(read_only=True),
        ).value
        if reliability not in RELIABILITY:
            raise ValueError('reliability must be best_effort or reliable')

        self.received = 0
        qos = QoSProfile(depth=10, reliability=RELIABILITY[reliability])
        self.create_subscription(Pose, 'sensor_pose', self.on_pose, qos)
        self.create_timer(1.0, self.log_count)
        self.get_logger().info(f'reliability={reliability}')

    def on_pose(self, _pose):
        self.received += 1

    def log_count(self):
        self.get_logger().info(f'received={self.received}')


def main(args=None):
    rclpy.init(args=args)
    node = PoseSubscriber()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
