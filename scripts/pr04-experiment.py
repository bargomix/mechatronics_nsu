#!/usr/bin/env python3
"""Run the PR04 experiment and save the logs."""

import argparse
from contextlib import contextmanager
import difflib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
from tempfile import TemporaryDirectory
import time


PATROL = ('ros2', 'run', 'patrol', 'patrol', '--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel')
GRAPH_FLAGS = ('--no-daemon', '--spin-time', '2')
COMMAND_TOPIC = '/turtle1/cmd_vel'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Experiment:
    def __init__(self, output):
        self.output = output
        self.commands = []

    def record(self, name, args):
        record = {'file': f'{name}.txt', 'command': shlex.join(args)}
        self.commands.append(record)
        print(f'$ {record["command"]}', flush=True)
        return self.output / record['file'], record

    def run(self, name, *args, expected=(0,)):
        path, record = self.record(name, args)
        with path.open('w') as log:
            result = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=35)
        record['exit_code'] = result.returncode
        output = path.read_text()
        require(result.returncode in expected, f'{name}: exit={result.returncode}\n{output}')
        return output

    @contextmanager
    def node(self, name, args, ready, *, env=None):
        path, record = self.record(name, args)
        with path.open('w') as log:
            process = subprocess.Popen(
                args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=env,
            )
        try:
            deadline = time.monotonic() + 25
            while ready not in path.read_text():
                require(process.poll() is None and time.monotonic() < deadline,
                        f'{name} did not start: {path.read_text()}')
                time.sleep(0.1)
            time.sleep(1)
            yield process
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
            record['exit_code'] = process.returncode

    def nodes(self, name):
        output = self.run(name, 'ros2', 'node', 'list', '--no-daemon', '--spin-time', '4')
        return set(output.splitlines())

    def wait_for_nodes(self, name, expected):
        for attempt in range(4):
            log = name if attempt == 0 else f'{name}-retry-{attempt}'
            observed = self.nodes(log)
            if observed == expected:
                return
        raise RuntimeError(f'Expected ROS nodes {expected}, found {observed}.')

    def set_parameter(self, log, name, value):
        output = self.run(log, 'ros2', 'param', 'set', '/patrol', name, value, *GRAPH_FLAGS)
        require('Set parameter successful' in output, output)

    def frequency(self, name, expected_hz):
        output = self.run(name, 'timeout', '--signal=INT', '--kill-after=3s', '8s',
                          'ros2', 'topic', 'hz', COMMAND_TOPIC, expected=(124,))
        rates = re.findall(r'average rate: ([\d.]+)', output)
        require(rates and abs(float(rates[-1]) - expected_hz) < 0.5, output)
        return float(rates[-1])


def reproduce_defect(exp, broken_dir):
    package = Path(__file__).resolve().parents[1] / 'src/patrol/patrol'
    broken_package = broken_dir / 'patrol'
    shutil.copytree(package, broken_package, ignore=shutil.ignore_patterns('__pycache__'))
    settings = broken_package / 'settings.py'
    original = settings.read_text()
    marker = 'if not low <= value <= high:'
    require(original.count(marker) == 1, 'Could not find the range check.')
    broken = original.replace(marker, "if name != 'publish_hz' and not low <= value <= high:")
    settings.write_text(broken)
    filename = 'src/patrol/patrol/settings.py'
    diff = difflib.unified_diff(original.splitlines(keepends=True), broken.splitlines(keepends=True),
                                fromfile=f'a/{filename}', tofile=f'b/{filename}')
    (exp.output / 'defect.patch').write_text(''.join(diff))

    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(filter(None, (str(broken_dir), env.get('PYTHONPATH'))))
    with exp.node('patrol-defect', PATROL, 'Patrol started:', env=env) as node:
        exp.set_parameter('set-five-defect', 'publish_hz', '5.0')
        exp.run('zero-defect', 'timeout', '--signal=INT', '--kill-after=3s', '20s',
                'ros2', 'param', 'set', '/patrol', 'publish_hz', '0.0', *GRAPH_FLAGS,
                expected=(124,))
        require(node.wait(timeout=10) == 1, 'The invalid period did not terminate patrol.')
        require('ZeroDivisionError: float division by zero' in
                (exp.output / 'patrol-defect.txt').read_text(), 'Missing divide-by-zero traceback.')
    exp.wait_for_nodes('nodes-after-defect', {'/turtlesim'})


def check_fixed(exp):
    with exp.node('patrol-fixed', PATROL, 'Patrol started:'):
        initial = exp.frequency('hz-initial', 10.0)
        exp.set_parameter('set-five', 'publish_hz', '5.0')
        five = exp.frequency('hz-five', 5.0)
        exp.set_parameter('set-linear-speed', 'linear_speed', '0.25')
        exp.set_parameter('set-turn-rate', 'turn_rate', '-0.2')
        result = exp.run('zero-rejected', 'ros2', 'param', 'set', '/patrol', 'publish_hz',
                         '0.0', *GRAPH_FLAGS, expected=(0, 1))
        require('Setting parameter failed' in result and 'got 0.0' in result, result)
        saved = exp.run('frequency-after-zero', 'ros2', 'param', 'get', '/patrol',
                        'publish_hz', *GRAPH_FLAGS)
        require('Double value is: 5.0' in saved, saved)
        after_zero = exp.frequency('hz-after-zero', 5.0)
        command = exp.run('command-after-zero', 'ros2', 'topic', 'echo', COMMAND_TOPIC,
                          'geometry_msgs/msg/Twist', '--once', *GRAPH_FLAGS)
        require('linear:\n  x: 0.25\n' in command and '\n  z: -0.2\n' in command, command)
        log = (exp.output / 'patrol-fixed.txt').read_text()
        require(re.findall(r'timers=(\d+)', log) == ['1'] * 4, log)

        cleared = exp.run('clear-service', 'ros2', 'service', 'call', '/clear',
                          'std_srvs/srv/Empty', '{}')
        require('Empty_Response' in cleared, cleared)
        actions = exp.run('actions', 'ros2', 'action', 'list', '-t')
        require('/turtle1/rotate_absolute' in actions, actions)

    return {'initial_hz': initial, 'changed_hz': five, 'after_rejected_zero_hz': after_zero}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory for the logs')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    exp = Experiment(args.output)
    try:
        require(not exp.nodes('nodes-initial'), 'Choose an unused ROS_DOMAIN_ID for the experiment.')
        daemon = exp.run('daemon-start', 'ros2', 'daemon', 'start')
        try:
            sim = ('ros2', 'launch', 'turtle_bringup', 'sim.launch.py')
            with exp.node('simulator', sim, 'Spawning turtle'):
                exp.run('pose-type', 'ros2', 'topic', 'type', '/turtle1/pose', *GRAPH_FLAGS)
                with TemporaryDirectory(prefix='pr04-defect-') as broken_dir:
                    reproduce_defect(exp, Path(broken_dir))
                measurements = check_fixed(exp)
            require(not exp.nodes('nodes-final'), 'Some ROS nodes did not shut down.')
            (exp.output / 'measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')
            print(f'PR04: {measurements}', flush=True)
        finally:
            if 'has been started' in daemon:
                exp.run('daemon-stop', 'ros2', 'daemon', 'stop')
    finally:
        (exp.output / 'commands.json').write_text(json.dumps(exp.commands, indent=2) + '\n')


if __name__ == '__main__':
    main()
