from collections.abc import Mapping
from dataclasses import dataclass, replace

LIMITS = {
    'linear_speed': (0.0, 1.0, 'm/s'),
    'turn_rate': (-1.0, 1.0, 'rad/s'),
    'publish_hz': (1.0, 30.0, 'Hz'),
}
DESCRIPTIONS = {
    'linear_speed': 'Forward speed (m/s)',
    'turn_rate': 'Turn rate (rad/s)',
    'publish_hz': 'Command frequency (Hz)',
}


@dataclass(frozen=True)
class Settings:
    linear_speed: float = 0.5
    turn_rate: float = 0.3
    publish_hz: float = 10.0

    @property
    def period_s(self) -> float:
        return 1.0 / self.publish_hz


def merge(settings: Settings, changes: Mapping[str, object]) -> Settings:
    checked = {}
    for name, value in changes.items():
        if name not in LIMITS:
            raise ValueError(f'unknown parameter {name}')
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{name} must be a number, got {value!r}')
        low, high, unit = LIMITS[name]
        if not low <= value <= high:
            raise ValueError(f'{name} must be from {low} to {high} {unit}, got {value}')
        checked[name] = float(value)
    return replace(settings, **checked)
