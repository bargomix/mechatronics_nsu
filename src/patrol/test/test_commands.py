"""Check command selection without starting ROS or turtlesim."""

import pytest
from turtlesim.msg import Pose

from patrol.commands import choose_command


@pytest.mark.parametrize('speeds', [(), (0.25, -0.2)])
def test_no_pose_produces_zero_command(speeds):
    """A timer tick before the first pose must not move the turtle."""
    command = choose_command(None, *speeds)

    assert command.linear.x == 0.0
    assert command.linear.y == 0.0
    assert command.linear.z == 0.0
    assert command.angular.x == 0.0
    assert command.angular.y == 0.0
    assert command.angular.z == 0.0


@pytest.mark.parametrize('x, y, theta', [
    (0.0, 0.0, 0.0),
    (5.544, 5.544, 1.2),
    (2.0, 8.0, -3.0),
])
def test_received_pose_produces_patrol_command(x, y, theta):
    """Any received pose enables the specified forward and angular speeds."""
    pose = Pose(x=x, y=y, theta=theta)

    command = choose_command(pose)

    assert command.linear.x == 0.5
    assert command.angular.z == 0.3
    assert command.linear.y == command.linear.z == 0.0
    assert command.angular.x == command.angular.y == 0.0
    assert (pose.x, pose.y, pose.theta) == pytest.approx((x, y, theta))


def test_commands_do_not_share_mutable_state():
    """Changing an old command must not affect subsequent timer results."""
    pose = Pose(x=5.0, y=5.0, theta=0.0)
    previous = choose_command(pose)
    previous.linear.x = 99.0
    previous.angular.z = -99.0

    following = choose_command(pose)

    assert following.linear.x == 0.5
    assert following.angular.z == 0.3


def test_configured_speeds():
    command = choose_command(Pose(), linear_speed=0.25, turn_rate=-0.2)

    assert command.linear.x == 0.25
    assert command.angular.z == -0.2
