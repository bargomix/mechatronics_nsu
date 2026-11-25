from geometry_msgs.msg import Twist
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
import rclpy
from rclpy.exceptions import InvalidParameterTypeException, InvalidParameterValueException
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from turtlesim.msg import Pose

from patrol.commands import choose_command
from patrol.settings import DESCRIPTIONS, LIMITS, Settings, merge


def _own_changes(parameters: list[Parameter]) -> dict[str, object]:
    return {item.name: item.value for item in parameters if item.name in LIMITS}


class Patrol(Node):
    def __init__(self, **kwargs):
        super().__init__('patrol', **kwargs)
        defaults = Settings()
        declared = {}
        for name, (low, high, unit) in LIMITS.items():
            descriptor = ParameterDescriptor(
                description=DESCRIPTIONS[name],
                additional_constraints=f'{low} to {high} {unit}',
            )
            declared[name] = self.declare_parameter(name, getattr(defaults, name), descriptor).value
        self._settings = merge(defaults, declared)

        self._last_pose: Pose | None = None
        self._pose_subscription = self.create_subscription(
            Pose, 'turtle1/pose', self._on_pose, 10,
        )
        self._command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self._timer = self.create_timer(self._settings.period_s, self._on_timer)
        self.add_on_set_parameters_callback(self._check_parameters)
        self.add_post_set_parameters_callback(self._apply_parameters)
        self.get_logger().info(f'Patrol started: {self._describe()}')

    @property
    def settings(self) -> Settings:
        return self._settings

    def _describe(self) -> str:
        settings = self._settings
        return (
            f'linear_speed={settings.linear_speed} m/s, turn_rate={settings.turn_rate} rad/s, '
            f'publish_hz={settings.publish_hz} Hz, timer period={settings.period_s:.3f} s, '
            f'timers={len(list(self.timers))}'
        )

    def _on_pose(self, message: Pose) -> None:
        self._last_pose = message

    def _on_timer(self) -> None:
        self._command_publisher.publish(choose_command(
            self._last_pose, self._settings.linear_speed, self._settings.turn_rate,
        ))

    def _check_parameters(self, parameters: list[Parameter]) -> SetParametersResult:
        try:
            merge(self._settings, _own_changes(parameters))
        except ValueError as error:
            self.get_logger().warning(f'Rejected: {error}')
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def _apply_parameters(self, parameters: list[Parameter]) -> None:
        changes = _own_changes(parameters)
        if not changes:
            return
        updated = merge(self._settings, changes)
        if updated.publish_hz != self._settings.publish_hz:
            period = updated.period_s
            self._timer.cancel()
            self.destroy_timer(self._timer)
            self._timer = self.create_timer(period, self._on_timer)
        self._settings = updated
        self.get_logger().info(f'Applied {changes}: {self._describe()}')


def main(args=None):
    rclpy.init(args=args)
    try:
        node = Patrol()
    except (ValueError, InvalidParameterTypeException, InvalidParameterValueException) as error:
        rclpy.logging.get_logger('patrol').fatal(f'Invalid parameters: {error}')
        rclpy.try_shutdown()
        return 1
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
