# ПР05. Launch, QoS и повтор записи

Один `turtlesim` работает в корневом namespace. `patrol`, `pose_relay` и
`pose_subscriber` запускаются в `/robot_a`. `patrol` отправляет команды в
`/turtle1/cmd_vel`, а relay пересылает позу в `/robot_a/sensor_pose` с `best_effort`.

## Сборка

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol course_bringup
source install/setup.bash
colcon test --packages-select turtle_bringup patrol course_bringup
colcon test-result --verbose
```

## Запуск

Первый запуск с `reliable` и без записи.

```bash
ros2 launch course_bringup patrol.launch.py subscriber_reliability:=reliable record:=false
```

В другом терминале с тем же `ROS_DOMAIN_ID` можно проверить топик.

```bash
ros2 topic info /robot_a/sensor_pose --verbose
timeout 8s ros2 topic echo /robot_a/sensor_pose --qos-reliability reliable --once
```

После остановки запустить с `best_effort` и записать в новый каталог.

```bash
ros2 launch course_bringup patrol.launch.py \
  subscriber_reliability:=best_effort record:=true bag_dir:=.local/pr05-bag
```

На исправленном запуске позу можно получить с `best_effort`.

```bash
ros2 topic echo /robot_a/sensor_pose --qos-reliability best_effort --once
```

После остановки живых нод можно проиграть приложенную запись.
QoS издателя задаёт `config/qos-overrides.yaml`.

```bash
ros2 bag play evidence/pr05/bag --loop --qos-profile-overrides-path config/qos-overrides.yaml
```

Весь опыт можно повторить скриптом в свободном ROS-домене.

```bash
ROS_DOMAIN_ID=30 QT_QPA_PLATFORM=offscreen \
  python3 scripts/pr05-experiment.py --output .local/pr05-repeat
```

## Результат

И на живом потоке, и на записи `reliable` дал таймаут с кодом 124.
С `best_effort` поза пришла, код выхода 0. В MCAP один топик
`/robot_a/sensor_pose`. После повтора SHA-256 файла совпал.
[До](qos-before.txt) · [После](qos-after.txt) · [Запись](bag/bag_0.mcap) · [Тесты](tests.txt)
