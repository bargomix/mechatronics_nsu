#!/usr/bin/env python3
"""Repeat the live PR03 experiment in a sourced ROS 2 environment."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time


class Experiment:
    """Run real ROS processes and keep their output and exit codes."""

    def __init__(self, output):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.records = []
        self.children = []

    def run(self, name, args, expected=(0,), timeout=60):
        print('RUN', shlex.join(args), flush=True)
        result = subprocess.run(
            args, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=timeout,
        )
        (self.output / name).write_text(result.stdout)
        self.records.append({
            'file': name, 'command': shlex.join(args),
            'exit_code': result.returncode,
        })
        if result.returncode not in expected:
            raise RuntimeError(f'{name}: exit={result.returncode}\n{result.stdout}')
        print(result.stdout[:2000], end='', flush=True)
        return result.stdout

    def start(self, name, args, marker):
        print('START', shlex.join(args), flush=True)
        stream = (self.output / name).open('w')
        proc = subprocess.Popen(
            args, stdout=stream, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.children.append((proc, stream))
        self.records.append({
            'file': name, 'command': shlex.join(args),
            'pid': proc.pid, 'exit_code': None,
        })
        deadline = time.monotonic() + 60
        while marker not in (self.output / name).read_text():
            if proc.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError(f'{name}: not ready\n{(self.output / name).read_text()}')
            time.sleep(0.2)
        time.sleep(1)
        return proc

    def stop(self, proc):
        if proc.poll() is not None:
            raise RuntimeError(f'process {proc.pid} exited before SIGINT')
        print('SIGINT', proc.pid, flush=True)
        os.killpg(proc.pid, signal.SIGINT)
        code = proc.wait(timeout=20)
        for record in self.records:
            if record.get('pid') == proc.pid:
                record['exit_code'] = code
                record['stop'] = 'SIGINT, as with Ctrl+C'
                if code not in (0, 2, 130, -signal.SIGINT):
                    raise RuntimeError(f'{record["file"]}: exit={code}')
                if 'Traceback' in (self.output / record['file']).read_text():
                    raise RuntimeError(f'{record["file"]}: traceback during shutdown')

    def echo(self, name, topic):
        text = self.run(name, ['ros2', 'topic', 'echo', topic, '--once'])
        values = {}
        section = ''
        for line in text.splitlines():
            if line in ('linear:', 'angular:'):
                section = line[:-1] + '.'
            elif ': ' in line:
                key, value = line.strip().split(': ', 1)
                values[section + key] = float(value)
        return values

    def pose(self, name):
        value = self.echo(name, '/turtle1/pose')
        required = {'x', 'y', 'theta', 'linear_velocity', 'angular_velocity'}
        if not required <= value.keys():
            raise RuntimeError(f'{name}: incomplete pose: {value}')
        return value

    def nodes(self, name):
        return self.run(name, [
            'ros2', 'node', 'list', '--no-daemon', '--spin-time', '2',
        ]).splitlines()

    def close(self):
        for proc, stream in self.children:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGINT)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            stream.close()
        (self.output / 'executed-commands.json').write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2) + '\n',
        )


def moved(before, after):
    return math.hypot(after['x'] - before['x'], after['y'] - before['y']) > 0.05


def run_experiment(exp):
    """Check no pose, a working connection, the defect and its remap fix."""
    patrol = ['ros2', 'run', 'patrol', 'patrol']
    remapped = patrol + ['--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel']
    if exp.nodes('nodes-before.txt'):
        raise RuntimeError('Stop existing ROS nodes in this domain before the experiment')
    exp.run('patrol-prefix.txt', ['ros2', 'pkg', 'prefix', 'patrol'])
    exp.run('patrol-executable.txt', ['ros2', 'pkg', 'executables', 'patrol'])

    no_pose = exp.start('patrol-no-pose.txt', patrol, 'Patrol started')
    zero = exp.echo('command-no-pose.txt', '/cmd_vel')
    assert set(zero) == {f'{part}.{axis}' for part in ('linear', 'angular') for axis in 'xyz'}
    assert all(value == 0.0 for value in zero.values())
    exp.stop(no_pose)
    assert exp.nodes('nodes-after-no-pose.txt') == []

    sim = exp.start('turtlesim.txt', [
        'ros2', 'launch', 'turtle_bringup', 'sim.launch.py',
    ], 'Spawning turtle')
    pose_type = exp.run('pose-type.txt', ['ros2', 'topic', 'type', '/turtle1/pose']).strip()
    assert pose_type == 'turtlesim/msg/Pose', pose_type
    before = exp.pose('pose-before.txt')
    correct = exp.start('patrol-before.txt', remapped, 'Patrol started')
    assert sorted(exp.nodes('nodes-working.txt')) == ['/patrol', '/turtlesim']
    exp.run('node-working.txt', ['ros2', 'node', 'info', '/patrol'])
    working = exp.pose('pose-working.txt')
    assert moved(before, working)
    assert working['linear_velocity'] == 0.5
    assert abs(working['angular_velocity'] - 0.3) < 1e-6
    exp.stop(correct)
    time.sleep(2)
    stopped_before = exp.pose('pose-stopped-before-break.txt')
    assert stopped_before['linear_velocity'] == stopped_before['angular_velocity'] == 0

    broken = exp.start('patrol-broken.txt', patrol, 'Patrol started')
    exp.run('node-broken.txt', ['ros2', 'node', 'info', '/patrol'])
    wrong_info = exp.run('topic-broken.txt', ['ros2', 'topic', 'info', '/cmd_vel', '--verbose'])
    true_info = exp.run('topic-disconnected.txt', [
        'ros2', 'topic', 'info', '/turtle1/cmd_vel', '--verbose',
    ])
    assert 'Publisher count: 1' in wrong_info and 'Subscription count: 0' in wrong_info
    assert 'Publisher count: 0' in true_info and 'Subscription count: 1' in true_info
    wrong_cmd = exp.echo('command-broken.txt', '/cmd_vel')
    assert wrong_cmd['linear.x'] == 0.5 and wrong_cmd['angular.z'] == 0.3
    broken_pose = exp.pose('pose-broken.txt')
    time.sleep(2)
    broken_again = exp.pose('pose-broken-again.txt')
    assert stopped_before == broken_pose == broken_again
    exp.stop(broken)

    fixed = exp.start('patrol-fixed.txt', remapped, 'Patrol started')
    exp.run('node-fixed.txt', ['ros2', 'node', 'info', '/patrol'])
    fixed_info = exp.run('topic-fixed.txt', [
        'ros2', 'topic', 'info', '/turtle1/cmd_vel', '--verbose',
    ])
    assert 'Publisher count: 1' in fixed_info and 'Subscription count: 1' in fixed_info
    fixed_cmd = exp.echo('command-fixed.txt', '/turtle1/cmd_vel')
    assert fixed_cmd['linear.x'] == 0.5 and fixed_cmd['angular.z'] == 0.3
    fixed_pose = exp.pose('pose-fixed.txt')
    assert moved(broken_pose, fixed_pose)
    hz = exp.run('cmd-vel-hz.txt', [
        'timeout', '--signal=INT', '--kill-after=3s', '10s',
        'ros2', 'topic', 'hz', '/turtle1/cmd_vel',
    ], expected=(124,), timeout=20)
    rates = [float(value) for value in re.findall(r'average rate:\s*([\d.]+)', hz)]
    assert rates and 8.0 <= rates[-1] <= 12.0, hz
    exp.stop(fixed)
    time.sleep(2)
    stopped = exp.pose('pose-stopped.txt')
    time.sleep(2)
    stopped_again = exp.pose('pose-stopped-again.txt')
    assert stopped == stopped_again
    assert stopped['linear_velocity'] == stopped['angular_velocity'] == 0
    assert exp.nodes('nodes-after-patrol.txt') == ['/turtlesim']
    exp.stop(sim)
    assert exp.nodes('nodes-final.txt') == []
    result = {
        'ros_distribution': os.environ['ROS_DISTRO'],
        'ros_domain_id': int(os.environ['ROS_DOMAIN_ID']),
        'pose_type': pose_type, 'command_without_pose': zero,
        'before': before, 'working': working,
        'stopped_before_break': stopped_before,
        'broken': broken_pose, 'broken_again': broken_again,
        'fixed': fixed_pose, 'fixed_command': fixed_cmd,
        'measured_rate_hz': rates[-1], 'measurement_duration_s': 10,
        'stopped': stopped, 'stopped_again': stopped_again,
        'checks': {
            'zero_before_first_pose': True, 'initial_connection_works': True,
            'wrong_name_reproduced': True, 'remap_restores_movement': True,
            'command_rate_near_10_hz': True, 'turtlesim_stops_after_patrol': True,
            'all_started_nodes_stopped': True,
        },
    }
    (exp.output / 'observations.json').write_text(json.dumps(result, indent=2) + '\n')
    print('All PR03 live checks passed', flush=True)


def main():
    """Run from the workspace after sourcing ROS and its overlay."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('evidence/pr03'))
    args = parser.parse_args()
    exp = Experiment(args.output)
    try:
        run_experiment(exp)
    finally:
        exp.close()


if __name__ == '__main__':
    main()
