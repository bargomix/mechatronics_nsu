# ПР06. Модель робота и tf2

Из SDF взяты база 0.80 м, колея 0.62 м и радиус колеса 0.12 м. Ось X направлена
вперёд, Y влево, Z вверх. Корпуса датчиков для RViz условные, их фреймы стоят
в точках из SDF.

Все связи публикует `robot_state_publisher`. Координаты в таблице даны в метрах
при нулевых углах сочленений.

| Родитель | Дочерний фрейм | Смещение и ось | Топик |
| --- | --- | --- | --- |
| `base_link` | `camera_link` | `(0.28, 0, 0.38)`, фиксирован | `/tf_static` |
| `base_link` | `lidar_link` | `(0.28, 0, 0.38)`, фиксирован | `/tf_static` |
| `base_link` | `imu_link` | `(0.28, 0, 0.38)`, фиксирован | `/tf_static` |
| `base_link` | `front_left_knuckle` | `(0.40, 0.31, 0)`, поворот вокруг Z | `/tf` |
| `base_link` | `front_right_knuckle` | `(0.40, -0.31, 0)`, поворот вокруг Z | `/tf` |
| `front_left_knuckle` | `front_left_wheel` | `(0, 0, 0)`, вращение вокруг Y | `/tf` |
| `front_right_knuckle` | `front_right_wheel` | `(0, 0, 0)`, вращение вокруг Y | `/tf` |
| `base_link` | `rear_left_wheel` | `(-0.40, 0.31, 0)`, вращение вокруг Y | `/tf` |
| `base_link` | `rear_right_wheel` | `(-0.40, -0.31, 0)`, вращение вокруг Y | `/tf` |

## Запуск

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select course_description
source install/setup.bash
ros2 launch course_description vehicle.launch.py rviz:=true
```

Чтобы RViz показал колёса, во втором терминале с тем же `ROS_DOMAIN_ID`
запустить публикацию нулевых положений.

```bash
ros2 topic pub -r 10 /joint_states sensor_msgs/msg/JointState \
  '{header: auto, name: [front_left_steering_joint, front_right_steering_joint, front_left_wheel_joint, front_right_wheel_joint, rear_left_wheel_joint, rear_right_wheel_joint], position: [0, 0, 0, 0, 0, 0]}'
```

## Результат

В копии модели лидар привязал к камере, оставив то же локальное смещение.
`tf2_echo base_link lidar_link` показал `(0.56, 0, 0.76)`. С родителем
`base_link` получилось `(0.28, 0, 0.38)`. `check_urdf` принял обе версии,
а тест родителя лидара упал на дефектной. [Патч](defect.patch) · [Проверки](model-check.txt)

На `/tf_static` поздний подписчик с `transient_local` получил три связи.
С `volatile` вышел по таймауту. [QoS и вывод](tf-qos.txt)

[RViz с дефектом](rviz-broken.png) · [RViz после исправления](rviz-fixed.png)

[Дерево с дефектом](frames-broken.gv) · [Исправленное дерево](frames-fixed.gv)
