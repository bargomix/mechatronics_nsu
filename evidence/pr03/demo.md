# ПР03. Поза, таймер и remap

Среда: Docker `mechatronics-pr01`, Ubuntu 24.04, ROS 2 Jazzy,
`ROS_DOMAIN_ID=16`. Образ закреплён в `docker-image.txt`.
Тип позы проверен командой `ros2 topic type /turtle1/pose`:
`turtlesim/msg/Pose`, зависимость пакета — `turtlesim`.
Teleop и прежние ROS-ноды перед опытом остановлены.

## Сборка и первый запуск

Пакет создан командой:

```bash
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  --node-name patrol patrol --dependencies rclpy geometry_msgs
```

Сначала в каркас добавлены только `rclpy.init`, нода `patrol` и `rclpy.spin`.
Эта промежуточная версия сохранена в [minimal-node.py](minimal-node.py).
После `colcon build --symlink-install --packages-select patrol` и
`source install/setup.bash` запущена команда `ros2 run patrol patrol`.
В графе появилась `/patrol`: [nodes-minimal.txt](nodes-minimal.txt),
лог [minimal-run.txt](minimal-run.txt), статус [minimal-check.json](minimal-check.json).

Затем добавлены подписка на `/turtle1/pose`, сохранение последней позы,
издатель относительного `cmd_vel` и таймер с периодом `0.1 с`.
Подписка, издатель и таймер хранятся как поля объекта ноды.
Callback подписки только сохраняет сообщение; публикация выполняется таймером.
Чистая функция `choose_command` создаёт новый Twist: без позы все поля нулевые,
после первой позы `linear.x=0.5`, `angular.z=0.3`, остальные поля нулевые.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

Сборка: [build.txt](build.txt). Все 5 тестов прошли:
[tests.txt](tests.txt). Проверены отсутствие позы, три разных сообщения Pose
и отсутствие общего изменяемого состояния у возвращаемых команд.

## Команда до первой позы

До запуска turtlesim запущен `ros2 run patrol patrol`.
```console
$ ros2 topic echo /cmd_vel --once
linear:
  x: 0.0
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.0
---
```

Проверены все шесть компонент Twist: они нулевые. Затем нода остановлена
SIGINT; граф пуст. Это отдельная проверка реального таймера, дополнительно
к тестам чистой функции.

## Исправный запуск

В A запущен `ros2 launch turtle_bringup sim.launch.py`, в B:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В C проверены `ros2 node list --no-daemon --spin-time 2` и
`ros2 node info /patrol`: видны `/turtlesim` и `/patrol`, у patrol есть
подписка на `/turtle1/pose` и публикация в `/turtle1/cmd_vel`.
Логи: [nodes-working.txt](nodes-working.txt), [node-working.txt](node-working.txt).
Поза изменилась, скорости стали `0.5` и примерно `0.3`:
[pose-before.txt](pose-before.txt), [pose-working.txt](pose-working.txt).
Patrol остановлена SIGINT; после двух секунд скорости нулевые.

## Сбой имени

При работающем turtlesim запущена та же нода без remap:

```bash
ros2 run patrol patrol
```

Проверки:

```bash
ros2 node info /patrol
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /cmd_vel --once
ros2 topic echo /turtle1/pose --once
```

| Топик во время сбоя | Издатели | Подписчики |
| --- | --- | --- |
| `/cmd_vel` | 1, `/patrol` | 0 |
| `/turtle1/cmd_vel` | 0 | 1, `/turtlesim` |

Полные снимки endpoint: [topic-broken.txt](topic-broken.txt) и
[topic-disconnected.txt](topic-disconnected.txt). Команда в `/cmd_vel`
ненулевая — поза действительно уже поступила в patrol:
[command-broken.txt](command-broken.txt). При этом две проверки позы,
разделённые паузой две секунды, совпали с позой после остановки исправного
запуска: [pose-broken.txt](pose-broken.txt),
[pose-broken-again.txt](pose-broken-again.txt).

При `echo /cmd_vel` CLI временно добавляет своего подписчика для чтения
команды. Подписчиком turtlesim он не становится; таблица отражает снимок
до запуска echo. Разрыв вызван разными полными именами, хотя тип Twist,
домен и QoS совместимы. Обнаружение издателя не означает доставку turtlesim.

## Исправление через remap и частота

Ошибочный процесс остановлен SIGINT и перезапущен с единственным изменением:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Исходники, период таймера, скорости и домен не менялись. Remap преобразует
относительное имя издателя в нужное полное имя. Подписка на позу сохранена.
У `/turtle1/cmd_vel` теперь один издатель `/patrol` и один подписчик
`/turtlesim`: [topic-fixed.txt](topic-fixed.txt),
[node-fixed.txt](node-fixed.txt). Команда имеет прежние значения:
[command-fixed.txt](command-fixed.txt); поза снова изменяется:
[pose-fixed.txt](pose-fixed.txt).

Реальная частота измерена командой, работавшей 10 секунд:
```console
$ timeout --signal=INT --kill-after=3s 10s ros2 topic hz /turtle1/cmd_vel
average rate: 9.995
	min: 0.100s max: 0.101s std dev: 0.00032s window: 11
average rate: 10.001
	min: 0.099s max: 0.101s std dev: 0.00048s window: 22
average rate: 9.998
	min: 0.099s max: 0.101s std dev: 0.00043s window: 32
average rate: 9.999
	min: 0.099s max: 0.101s std dev: 0.00043s window: 43
average rate: 9.998
	min: 0.099s max: 0.101s std dev: 0.00044s window: 54
average rate: 9.998
	min: 0.099s max: 0.101s std dev: 0.00050s window: 64
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00049s window: 75
```

Код 124 означает завершение по заданному времени, а не сбой ноды.
Последняя усреднённая частота — **10.000 Гц**.
Заданный период 0,1 с соответствует номинальным 10 Гц; измеренное значение
зависит от планирования таймера и наблюдателя.

## Остановка и сравнение

| Состояние | x; y; theta |
| --- | --- |
| До первого исправного запуска | 5.544445; 5.544445; 0.000000 |
| Исправная нода получает позу и движется | 6.954302; 8.093598; 2.126400 |
| После остановки, перед сбоем | 6.565454; 8.525314; 2.476800 |
| Сбой, неверное имя топика | 6.565454; 8.525314; 2.476800 |
| Сбой, повторное чтение | 6.565454; 8.525314; 2.476800 |
| После исправления remap | 3.876898; 7.109153; -1.511985 |
| После остановки ноды и ожидания | 7.046359; 7.925255; 2.011215 |

Числа округлены только в таблице; точные значения — в исходных логах и
[observations.json](observations.json). После остановки patrol выждали две
секунды, получили нулевые скорости, затем ещё через две секунды получили
идентичную позу: [pose-stopped.txt](pose-stopped.txt),
[pose-stopped-again.txt](pose-stopped-again.txt).
В графе остался только turtlesim; после остановки launch граф пуст.

## Что делают init, spin, callback и Ctrl+C

- `rclpy.init()` создаёт контекст ROS и обрабатывает ROS-аргументы, включая remap.
- Конструктор `Patrol` создаёт ноду, подписку, издателя и таймер.
- `rclpy.spin(node)` обслуживает готовые события: сообщения подписки и таймер.
- `_on_pose` сохраняет последнюю позу. `_on_timer` выбирает и публикует команду.
- Ctrl+C посылает SIGINT. Обработчик завершения освобождает ноду и контекст ROS.
  Наша нода при выходе не посылает отдельную команду торможения. Turtlesim ещё
  некоторое время исполняет последнюю команду, а затем останавливается по её
  таймауту. Поэтому исчезновение процесса само по себе не доказывает остановку:
  в опыте дождались нулевых скоростей и проверили неизменность повторной позы.

## Повтор и автопроверка

Весь живой опыт повторяется в контейнере после сборки и подключения overlay:

```bash
python3 scripts/pr03-experiment.py --output .local/pr03-repeat
```

Скрипт запускает настоящие ROS-процессы и проверяет наблюдения.
Команды и реальные коды завершения: [executed-commands.json](executed-commands.json).
Сигналы SIGINT в скрипте соответствуют Ctrl+C в отдельном терминале.
Шаг сборки и тестов из workflow также выполнен локально в чистом одноразовом
контейнере: [ci-local.txt](ci-local.txt), [ci-local.json](ci-local.json).
Это локальная проверка шага; удалённый GitHub Actions run ещё не запускался.

```bash
python3 .course-kit/v1/tools/check_practice.py PR03 --submission . --json
```

Результат checker сохраняется в `checker.json`. Он проверяет комплектность
и историю Git; работу подписки, таймера, remap и остановку подтверждает опыт.
