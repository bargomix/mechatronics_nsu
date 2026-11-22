import pytest

from patrol.settings import Settings, merge


def test_frequency_change():
    defaults = Settings()
    updated = merge(defaults, {'publish_hz': 5.0})

    assert defaults == Settings(linear_speed=0.5, turn_rate=0.3, publish_hz=10.0)
    assert defaults.period_s == 0.1
    assert updated == Settings(linear_speed=0.5, turn_rate=0.3, publish_hz=5.0)
    assert updated.period_s == 0.2


@pytest.mark.parametrize('frequency', [0.0, -5.0, float('nan'), float('inf'), 30.1, True])
def test_invalid_frequency(frequency):
    active = Settings(publish_hz=5.0)

    with pytest.raises(ValueError, match='publish_hz'):
        merge(active, {'linear_speed': 0.25, 'publish_hz': frequency})

    assert active.linear_speed == 0.5
    assert active.publish_hz == 5.0
    assert active.period_s == 0.2


@pytest.mark.parametrize('name, value', [
    ('linear_speed', -0.1),
    ('linear_speed', 1.1),
    ('turn_rate', -1.1),
    ('turn_rate', 1.1),
])
def test_velocity_out_of_range(name, value):
    with pytest.raises(ValueError, match=name):
        merge(Settings(), {name: value})


@pytest.mark.parametrize('settings', [Settings(0.0, -1.0, 1.0), Settings(1.0, 1.0, 30.0)])
def test_range_limits(settings):
    changes = {
        'linear_speed': settings.linear_speed,
        'turn_rate': settings.turn_rate,
        'publish_hz': settings.publish_hz,
    }

    assert merge(Settings(), changes) == settings
