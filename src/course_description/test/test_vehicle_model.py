import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import xacro

MODEL = Path(__file__).resolve().parents[1] / 'urdf' / 'vehicle.urdf.xacro'


def load_model(**arguments):
    return ET.fromstring(xacro.process_file(str(MODEL), mappings=arguments).toxml())


def xyz(element):
    return tuple(map(float, element.attrib['xyz'].split()))


@pytest.fixture(scope='module')
def model():
    return load_model()


def test_tree(model):
    links = [link.attrib['name'] for link in model.findall('link')]
    assert len(set(links)) == len(links) == 10
    parents = {}
    for joint in model.findall('joint'):
        parent = joint.find('parent').attrib['link']
        child = joint.find('child').attrib['link']
        assert parent in links and child in links
        assert child not in parents
        parents[child] = parent

    assert set(links) - parents.keys() == {'base_link'}
    for link in links:
        visited = set()
        while link != 'base_link':
            assert link not in visited, f'cycle at {link}'
            visited.add(link)
            link = parents[link]


@pytest.mark.parametrize('sensor', ['camera', 'lidar', 'imu'])
def test_sensor_frame(model, sensor):
    joint = model.find(f"joint[@name='{sensor}_joint']")
    assert joint.attrib['type'] == 'fixed'
    assert joint.find('parent').attrib['link'] == 'base_link'
    assert joint.find('child').attrib['link'] == f'{sensor}_link'
    assert xyz(joint.find('origin')) == pytest.approx((0.28, 0, 0.38))


@pytest.mark.parametrize('wheelbase, track, radius', [(0.8, 0.62, 0.12), (1.0, 0.7, 0.14)])
def test_wheel_geometry(wheelbase, track, radius):
    model = load_model(wheelbase=str(wheelbase), track=str(track), wheel_radius=str(radius))
    for side, y in [('left', track / 2), ('right', -track / 2)]:
        steering = model.find(f"joint[@name='front_{side}_steering_joint']")
        assert steering.attrib['type'] == 'revolute'
        assert xyz(steering.find('origin')) == pytest.approx((wheelbase / 2, y, 0))
        assert xyz(steering.find('axis')) == (0, 0, 1)

        for axle, position in [('front', (0, 0, 0)), ('rear', (-wheelbase / 2, y, 0))]:
            wheel = f'{axle}_{side}_wheel'
            joint = model.find(f"joint[@name='{wheel}_joint']")
            assert joint.attrib['type'] == 'continuous'
            assert xyz(joint.find('origin')) == pytest.approx(position)
            assert xyz(joint.find('axis')) == (0, 1, 0)
            link = model.find(f"link[@name='{wheel}']")
            for element in ('visual', 'collision'):
                shape = link.find(f'{element}/geometry/cylinder')
                assert float(shape.attrib['radius']) == pytest.approx(radius)
                assert float(shape.attrib['length']) == pytest.approx(0.07)


def test_geometry_and_mass(model):
    for link in model.findall('link'):
        name = link.attrib['name']
        if not name.endswith('_knuckle'):
            assert link.find('visual/geometry/*') is not None, name
            assert link.find('collision/geometry/*') is not None, name
        mass = float(link.find('inertial/mass').attrib['value'])
        assert math.isfinite(mass) and mass > 0, name
        inertia = link.find('inertial/inertia').attrib
        moments = sorted(float(inertia[axis]) for axis in ('ixx', 'iyy', 'izz'))
        assert 0 < moments[0] and moments[2] <= sum(moments[:2]), name

    body = model.find("link[@name='base_link']")
    for element in ('visual', 'collision'):
        size = body.find(f'{element}/geometry/box').attrib['size']
        assert tuple(map(float, size.split())) == pytest.approx((1.05, 0.52, 0.22))
