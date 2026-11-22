# ПР04. Параметризуем движение

| Параметр | По умолчанию | Диапазон |
| --- | ---: | --- |
| `linear_speed` | 0.5 м/с | 0–1 м/с |
| `turn_rate` | 0.3 рад/с | −1–1 рад/с |
| `publish_hz` | 10.0 Гц | 1–30 Гц |

При смене частоты `patrol` заменяет таймер. Период равен `1 / publish_hz`.
В команды `ros2 param set` передаю числа с точкой.

## Запуск

Команды внутри контейнера с ROS 2 Jazzy.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

Симулятор и `patrol` запускаются в разных терминалах с одним `ROS_DOMAIN_ID`.

```bash
ros2 launch turtle_bringup sim.launch.py
```

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

## Что получилось

```bash
timeout --signal=INT --kill-after=3s 8s ros2 topic hz /turtle1/cmd_vel
ros2 param set /patrol publish_hz 5.0
ros2 param set /patrol linear_speed 0.25
ros2 param set /patrol turn_rate -0.2
ros2 param set /patrol publish_hz 0.0
ros2 param get /patrol publish_hz
```

Поток команд был около 10 Гц. После установки `5.0` он стал около 5 Гц,
в логе один таймер с периодом 0.2 с. Ноль отклонён, частота осталась
около 5 Гц. `ros2 param get` вернул `5.0`, в `Twist` скорости `0.25` и `-0.2`.
[Замеры](measurements.json) · [Отказ](zero-rejected.txt) · [Twist](command-after-zero.txt)

В отдельной копии пропустил проверку частоты. При `0.0` нода упала с
`ZeroDivisionError` и кодом 1, а команда установки вышла по таймауту с кодом 124.
[Правка для опыта](defect.patch) · [Ошибка ноды](patrol-defect.txt)

```bash
ros2 service call /clear std_srvs/srv/Empty '{}'
ros2 action list -t
```

Сервис `/clear` очищает след и возвращает ответ. Действию
`/turtle1/rotate_absolute` передаётся цель поворота, есть обратная связь,
результат и отмена. [Ответ сервиса](clear-service.txt) · [Действия](actions.txt)

## Повтор и проверка

```bash
ROS_DOMAIN_ID=28 QT_QPA_PLATFORM=offscreen \
  python3 scripts/pr04-experiment.py --output .local/pr04-repeat
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```

Для повтора нужен свободный ROS-домен и новый каталог вывода.
[Команды и коды выхода](commands.json) · [Тесты](tests.txt) · [Отчёт](report.json)
