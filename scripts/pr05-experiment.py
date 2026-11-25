#!/usr/bin/env python3
"""Run the PR05 QoS checks and save the MCAP and logs."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess

import yaml

TOPIC = '/robot_a/sensor_pose'
POSE = 'turtlesim/msg/Pose'
GRAPH = ('--no-daemon', '--spin-time', '4')
LIVE_NODES = {'/turtlesim', '/robot_a/patrol', '/robot_a/pose_relay', '/robot_a/pose_subscriber'}


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


class Experiment:
    def __init__(self, output):
        self.output = output
        self.commands = {}

    def log(self, name, args):
        path = self.output / f'{name}.txt'
        entry = {'file': path.name, 'command': shlex.join(args)}
        print(f'$ {entry["command"]}', flush=True)
        self.commands[name] = entry
        return path, entry

    def run(self, name, *args, expected=0):
        path, entry = self.log(name, args)
        with path.open('w') as stream:
            result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, timeout=30)
        entry['exit_code'] = result.returncode
        output = path.read_text()
        check(result.returncode == expected, f'{name}: exit {result.returncode}\n{output}')
        return output

    @contextmanager
    def process(self, name, args):
        path, entry = self.log(name, args)
        with path.open('w') as stream:
            process = subprocess.Popen(
                args, stdout=stream, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            try:
                yield
            finally:
                if process.poll() is None:
                    if args[:2] == ('ros2', 'launch'):
                        # Launch stops its children itself.
                        process.send_signal(signal.SIGINT)
                    else:
                        os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                entry['exit_code'] = process.returncode
        output = path.read_text()
        check(process.returncode == 0 and 'process has died' not in output,
              f'{name}: exit {process.returncode}\n{output}')

    def nodes(self, name, expected):
        for attempt in range(4):
            log_name = name if attempt == 0 else f'{name}-{attempt + 1}'
            output = self.run(log_name, 'ros2', 'node', 'list', *GRAPH)
            observed = set(output.splitlines())
            if observed == expected:
                return
        raise RuntimeError(f'{name}: expected {expected}, found {observed}')

    def profile(self, stage, reliability):
        output = self.run(f'{stage}-info', 'ros2', 'topic', 'info', TOPIC, '--verbose', *GRAPH)
        publisher, _, subscribers = output.partition('Subscription count:')
        check('Publisher count: 1' in publisher and 'Reliability: BEST_EFFORT' in publisher, output)
        check(f'Reliability: {reliability.upper()}' in subscribers, output)

    def echo(self, stage, reliability):
        expected = 124 if reliability == 'reliable' else 0
        output = self.run(f'{stage}-echo', 'timeout', '--signal=INT', '--kill-after=3s', '8s',
                          'ros2', 'topic', 'echo', TOPIC, POSE, '--once',
                          '--qos-reliability', reliability, *GRAPH, expected=expected)
        check(('theta:' in output) == (expected == 0), output)

    def received(self, name):
        output = (self.output / f'{name}.txt').read_text()
        counts = re.findall(r'received=(\d+)', output)
        check(counts, f'{name}: missing subscriber count')
        return max(map(int, counts))

    def summary(self, name, entries):
        with (self.output / f'{name}.txt').open('w') as stream:
            for key in entries:
                entry = self.commands[key]
                output = (self.output / entry['file']).read_text()
                stream.write(f'$ {entry["command"]}\n{output.rstrip()}\n')
                stream.write(f'exit={entry["exit_code"]}\n\n')


def live(exp, bag):
    launch = ('ros2', 'launch', 'course_bringup', 'patrol.launch.py', 'namespace:=robot_a',
              f'bag_dir:={bag}')
    with exp.process('launch-before', (*launch, 'subscriber_reliability:=reliable', 'record:=false')):
        exp.nodes('nodes-before', LIVE_NODES)
        topics = exp.run('topics-before', 'ros2', 'topic', 'list', '-t', *GRAPH)
        check(f'{TOPIC} [{POSE}]' in topics and '/robot_a/cmd_vel' not in topics, topics)
        exp.profile('live-before', 'reliable')
        exp.echo('live-before', 'reliable')
        check(exp.received('launch-before') == 0, 'Reliable subscriber received live poses')
    check(not bag.exists(), 'record:=false created a bag')
    exp.nodes('nodes-between', set())

    with exp.process('launch-after', (*launch, 'subscriber_reliability:=best_effort', 'record:=true')):
        exp.nodes('nodes-recording', LIVE_NODES | {'/rosbag2_recorder'})
        exp.profile('live-after', 'best_effort')
        exp.echo('live-after', 'best_effort')
        command = exp.run('cmd-vel', 'timeout', '10s', 'ros2', 'topic', 'echo',
                          '/turtle1/cmd_vel', 'geometry_msgs/msg/Twist', '--once', *GRAPH)
        check('\n  x: 0.5\n' in command and '\n  z: 0.3\n' in command, command)
        received = exp.received('launch-after')
        check(received > 0, 'Best-effort subscriber received no live poses')
    exp.nodes('nodes-before-replay', set())
    return received


def replay(exp, bag, override):
    play = ('ros2', 'bag', 'play', str(bag), '--loop', '--disable-keyboard-controls',
            '--qos-profile-overrides-path', str(override))
    with exp.process('playback', play):
        for reliability, stage in (('reliable', 'replay-before'), ('best_effort', 'replay-after')):
            node = f'replay_{reliability}'
            subscribe = ('ros2', 'run', 'course_bringup', 'pose_subscriber', '--ros-args',
                         '-r', '__ns:=/robot_a', '-r', f'__node:={node}',
                         '-p', f'reliability:={reliability}')
            log = f'{stage}-subscriber'
            with exp.process(log, subscribe):
                exp.nodes(f'{stage}-nodes', {'/rosbag2_player', f'/robot_a/{node}'})
                exp.profile(stage, reliability)
                exp.echo(stage, reliability)
                received = exp.received(log)
                check((received > 0) == (reliability == 'best_effort'), f'{stage}: {received}')
    exp.nodes('nodes-final', set())
    return received


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory for the bag and logs')
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    exp = Experiment(output)
    bag = output / 'bag'
    override = Path(__file__).resolve().parents[1] / 'config/qos-overrides.yaml'
    try:
        check(not exp.run('nodes-initial', 'ros2', 'node', 'list', *GRAPH).strip(),
              'Use a free ROS_DOMAIN_ID')
        live_count = live(exp, bag)
        metadata = bag / 'metadata.yaml'
        info = yaml.safe_load(metadata.read_text())['rosbag2_bagfile_information']
        topics = info['topics_with_message_count']
        check(info['storage_identifier'] == 'mcap' and len(topics) == 1, str(topics))
        check(topics[0]['topic_metadata']['name'] == TOPIC and topics[0]['message_count'] > 0,
              str(topics))
        mcap, = bag.glob('*.mcap')
        digest = hashlib.sha256(mcap.read_bytes()).hexdigest()
        shutil.copyfile(metadata, output / 'bag-metadata.yaml')
        exp.run('bag-info', 'ros2', 'bag', 'info', str(bag))

        replay_count = replay(exp, bag, override)
        check(hashlib.sha256(mcap.read_bytes()).hexdigest() == digest, 'MCAP changed during replay')
        exp.summary('qos-before', ('topics-before', 'live-before-info', 'live-before-echo',
                                   'launch-before', 'replay-before-info', 'replay-before-echo',
                                   'replay-before-subscriber'))
        exp.summary('qos-after', ('live-after-info', 'live-after-echo', 'launch-after', 'cmd-vel',
                                  'replay-after-info', 'replay-after-echo', 'replay-after-subscriber',
                                  'bag-info'))
        results = {'topic': TOPIC, 'pose_type': POSE, 'bag_messages': topics[0]['message_count'],
                   'mcap_sha256': digest, 'live_received': live_count, 'replay_received': replay_count}
        summary = json.dumps(results, indent=2) + '\n'
        (output / 'measurements.json').write_text(summary)
        print(summary, end='')
    finally:
        commands = json.dumps(list(exp.commands.values()), indent=2) + '\n'
        (output / 'commands.json').write_text(commands)


if __name__ == '__main__':
    main()
