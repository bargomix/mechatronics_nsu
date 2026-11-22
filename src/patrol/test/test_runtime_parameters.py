import pytest
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter

from patrol.patrol import Patrol


@pytest.fixture
def patrol_node():
    context = Context()
    rclpy.init(args=[], context=context)
    try:
        node = Patrol(context=context)
        try:
            yield node
        finally:
            node.destroy_node()
    finally:
        rclpy.try_shutdown(context=context)


def test_timer_replacement(patrol_node):
    original, = patrol_node.timers
    result = patrol_node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])

    assert result.successful
    replacement, = patrol_node.timers
    assert replacement is not original
    assert replacement.timer_period_ns == 200_000_000
    assert patrol_node.get_parameter('publish_hz').value == patrol_node.settings.publish_hz == 5.0

    result = patrol_node.set_parameters_atomically([Parameter('turn_rate', value=-0.2)])
    assert result.successful
    assert tuple(patrol_node.timers) == (replacement,)
    assert patrol_node.get_parameter('turn_rate').value == patrol_node.settings.turn_rate == -0.2


def test_invalid_batch(patrol_node):
    timer, = patrol_node.timers
    settings = patrol_node.settings
    result = patrol_node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8),
        Parameter('publish_hz', value=0.0),
    ])

    assert not result.successful
    assert 'publish_hz' in result.reason
    assert patrol_node.settings is settings
    assert patrol_node.get_parameter('linear_speed').value == settings.linear_speed
    assert patrol_node.get_parameter('publish_hz').value == settings.publish_hz
    assert tuple(patrol_node.timers) == (timer,)
    assert not timer.is_canceled()


def test_other_callback_rejects_change(patrol_node):
    timer, = patrol_node.timers

    def reject_change(_parameters):
        return SetParametersResult(successful=False, reason='rejected by another callback')

    patrol_node.add_on_set_parameters_callback(reject_change)
    result = patrol_node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])

    assert not result.successful
    assert result.reason == 'rejected by another callback'
    assert patrol_node.get_parameter('publish_hz').value == patrol_node.settings.publish_hz == 10.0
    assert tuple(patrol_node.timers) == (timer,)
    assert not timer.is_canceled()
