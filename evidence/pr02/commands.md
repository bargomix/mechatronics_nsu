# PR02: команды и наблюдения

Опыт выполнен в Docker `mechatronics-pr01`, Ubuntu 24.04, ROS 2 Jazzy,
`ROS_DOMAIN_ID=16`, workspace `/work`. Использован существующий X11/XWayland
для GUI. Teleop и прежние turtlesim перед опытом отсутствовали.
Точные команды, коды завершения и соответствующие логи перечислены в
[executed-commands.json](executed-commands.json). Пустой вывод `node list`
после остановки означает, что нод не обнаружено; код завершения равен 0.

## Терминал и пустой пакет

На хосте выполнен `./scripts/docker-start.sh`; дальнейшие ROS-команды —
внутри контейнера. В каждой ROS-сессии подключена базовая установка:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
mkdir -p src evidence/pr02
```

Три использованные команды Linux:

| Команда | Назначение | Фактический результат |
| --- | --- | --- |
| `pwd` | Показать текущий каталог workspace | `/work` |
| `ls -a` | Показать файлы, включая скрытые | Видны `.git`, `.course-kit`, `src`, `evidence`, `build`, `install` |
| `printenv ROS_DISTRO ROS_DOMAIN_ID` | Прочитать среду текущего процесса | `jazzy` и `16` |

Полный результат этих команд, путей пакетов и пустого графа после первой
сборки: [empty-package.txt](empty-package.txt).

`>` перенаправляет stdout в файл и перезаписывает его; `2>&1` направляет stderr
в тот же поток. `|` передаёт stdout на stdin следующей программы, например
`tee` одновременно показывает вывод и сохраняет его. `set -o pipefail`
не позволяет успешному `tee` скрыть ошибку `colcon`.

`source файл` исполняет файл в текущем Bash, поэтому изменения `PATH`,
`AMENT_PREFIX_PATH` и других переменных остаются в этой оболочке. Запуск
новой программы создаёт дочерний процесс; его изменения среды не меняют
среду родительского Bash.

Пакет создан до добавления launch:

```bash
cd src
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  turtle_bringup --dependencies launch launch_ros turtlesim
cd ..
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build-empty.txt
```

```console
$ colcon build --symlink-install --packages-select turtle_bringup
Starting >>> turtle_bringup
Finished <<< turtle_bringup [10.4s]

Summary: 1 package finished [13.2s]
```


В свежей оболочке после `source install/setup.bash` команда
`ros2 pkg prefix turtle_bringup` вернула `/work/install/turtle_bringup`,
а `ros2 node list --no-daemon --spin-time 2` — пустой вывод.
Обнаружение установленного пакета не запускает ноду.
`ros2 pkg prefix turtlesim` вернул `/opt/ros/jazzy`: это установленный
базовый пакет, а `/work` — каталог исходного workspace.

## Launch: установка, запуск и остановка

В исходники добавлены `launch/sim.launch.py` и запись `glob('launch/*.launch.py')`
в `data_files` файла `setup.py`. Сохранены маркер ament, `setup.cfg`, XML и
зависимости `launch`, `launch_ros`, `turtlesim`. Итоговая сборка выполнена
в новой оболочке с базовой ROS, без подключения overlay:

```console
$ colcon build --symlink-install --packages-select turtle_bringup
Starting >>> turtle_bringup
Finished <<< turtle_bringup [3.16s]

Summary: 1 package finished [3.39s]
```


В терминале запуска выполнено `source install/setup.bash`.

```console
$ ros2 pkg prefix turtle_bringup
/work/install/turtle_bringup
```

```console
$ ls -l /work/install/turtle_bringup/share/turtle_bringup/launch
total 4
drwxr-xr-x 2 ubuntu ubuntu 4096 Nov  2 08:49 __pycache__
lrwxrwxrwx 1 ubuntu ubuntu   47 Nov  2 08:47 sim.launch.py -> /work/build/turtle_bringup/launch/sim.launch.py
```


Запущен `ros2 launch turtle_bringup sim.launch.py`, без remap и teleop.

```console
$ ros2 node list --no-daemon --spin-time 2
/turtlesim
```


Затем всей группе процессов launch передан SIGINT — тот же сигнал, который
посылает Ctrl+C. Launch завершился с кодом 0, дочерний turtlesim завершился
успешно. Полный лог: [launch-stop.txt](launch-stop.txt).

```console
$ ros2 node list --no-daemon --spin-time 2

```


Для опыта launch запущен повторно той же командой. В графе одна `/turtlesim`:
[nodes-experiment.txt](nodes-experiment.txt),
[node-info.txt](node-info.txt), [topics.txt](topics.txt).
Итоговый лог запуска и завершения: [launch-experiment.txt](launch-experiment.txt).

`generate_launch_description()` возвращает `LaunchDescription` со списком
действий. `Node(package='turtlesim', executable='turtlesim_node')` запускает
готовую программу, соответствующую `ros2 run turtlesim turtlesim_node`.
Launch-файл — файл на диске; `/turtlesim` — нода работающего процесса;
Twist — сообщение, а не процесс и не файл. Сборка и `source` нод не создают.

## Исправная одиночная команда

Ожидание: при `linear.x=1.0` и `angular.z=0.5` черепаха движется вперёд
с поворотом против часовой стрелки. Остальные компоненты Twist равны нулю.

```console
$ ros2 topic type /turtle1/pose
turtlesim/msg/Pose
```

```console
$ ros2 topic echo /turtle1/pose --once
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
---
```

```console
$ ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
publisher: beginning loop
publishing #1: geometry_msgs.msg.Twist(linear=geometry_msgs.msg.Vector3(x=1.0, y=0.0, z=0.0), angular=geometry_msgs.msg.Vector3(x=0.0, y=0.0, z=0.5))
```


После публикации выждали две секунды:

```console
$ ros2 topic echo /turtle1/pose --once
x: 6.509308815002441
y: 5.796990871429443
theta: 0.5040000081062317
linear_velocity: 0.0
angular_velocity: 0.0
---
```


Координаты и theta изменились в ожидаемом направлении. Одна публикация
не задаёт бесконечное движение: после таймаута последней команды turtlesim
остановился, обе скорости в полученной позе равны нулю.

## Сбой: `/cmd_vel` вместо `/turtle1/cmd_vel`

Запущен непрерывный издатель:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

`--wait-matching-subscriptions 0` позволяет публиковать без подписчиков.
`--once` по умолчанию ждал бы одного подписчика. Для опыта использована
непрерывная публикация с частотой 1 Гц. Издатель продолжал работать во время
всех проверок ниже, см. [publish-broken.txt](publish-broken.txt).

```console
$ ros2 topic info /cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: _ros2cli_696
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: PUBLISHER
GID: 01.0f.64.99.b8.02.09.4a.00.00.00.00.00.00.07.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 0
```

```console
$ ros2 topic info /turtle1/cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 0

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: SUBSCRIPTION
GID: 01.0f.64.99.5b.02.20.d6.00.00.00.00.00.00.1d.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite
```

```console
$ ros2 topic echo /turtle1/pose --once
x: 6.509308815002441
y: 5.796990871429443
theta: 0.5040000081062317
linear_velocity: 0.0
angular_velocity: 0.0
---
```


Повторное чтение через две секунды дало ту же позу:
[pose-broken-again.txt](pose-broken-again.txt). Тип, тело сообщения и домен
правильные, но полное имя топика отличается. У `/cmd_vel` есть издатель,
но нет подписчика; `/turtlesim` подписан на `/turtle1/cmd_vel`.

## Исправление только полного имени

Ошибочный издатель остановлен SIGINT. Повторена та же команда с единственной
заменой `/cmd_vel` на `/turtle1/cmd_vel`:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Частота 1 Гц, домен 16 и значения Twist сохранены.

```console
$ ros2 topic info /turtle1/cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: _ros2cli_747
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: PUBLISHER
GID: 01.0f.64.99.eb.02.80.98.00.00.00.00.00.00.07.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: SUBSCRIPTION
GID: 01.0f.64.99.5b.02.20.d6.00.00.00.00.00.00.1d.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite
```

```console
$ ros2 topic echo /turtle1/pose --once
x: 6.153402328491211
y: 9.44690227508545
theta: 2.8239998817443848
linear_velocity: 1.0
angular_velocity: 0.5
---
```


Теперь у одного полного имени есть и издатель, и подписчик `/turtlesim`.
Поза изменилась, скорости во время публикации ненулевые — команда доставлена.
Издатель остановлен SIGINT; через две секунды:

```console
$ ros2 topic echo /turtle1/pose --once
x: 5.794905662536621
y: 9.527667999267578
theta: 3.007999897003174
linear_velocity: 0.0
angular_velocity: 0.0
---
```


Ещё через две секунды поза осталась той же:
[pose-fixed-stopped-again.txt](pose-fixed-stopped-again.txt).
После явного SIGINT издатели `ros2 topic pub` в этой установке завершились
с кодом 2, без traceback; это прерывание непрерывной команды, а не ошибка
сборки. Точные коды сохранены в `executed-commands.json`.

Наличие издателя в графе подтверждает обнаружение конечной точки DDS.
Доставку здесь подтверждают совпадение полного имени и типа, совместимые
QoS, присутствие подписчика и фактическое изменение позы. Само обнаружение
издателя с правильным типом не доказывает, что его сообщения получает turtlesim.

## Сравнение до / сбой / после

| Стадия | Поза: x; y; theta | Наблюдение |
| --- | --- | --- |
| До команды | 5.544445; 5.544445; 0.000000 | Скорости равны 0 |
| После `--once` | 6.509309; 5.796991; 0.504000 | Движение по дуге; затем остановка |
| Сбой `/cmd_vel` | 6.509309; 5.796991; 0.504000 | Поза не меняется; издатель 1, подписчик 0 |
| Исправление имени | 6.153402; 9.446902; 2.824000 | Движение; издатель 1, подписчик 1 |
| После остановки издателя | 5.794906; 9.527668; 3.008000 | Скорости 0; повторная поза идентична |

Числа округлены до шести знаков только в таблице; полная точность —
в исходных логах и [observations.json](observations.json).

В конце launch остановлен SIGINT с кодом 0. Граф снова пуст:
[nodes-final.txt](nodes-final.txt), код команды 0.

## Проверки

`python3 -m py_compile src/turtle_bringup/launch/sim.launch.py` завершилась
с кодом 0. Синтаксис YAML и всех Bash-шагов CI проверен локально.
Точный ROS-шаг CI выполнен в одноразовом контейнере закреплённого образа
на отдельной чистой копии `src/`, без прежних `build/` и `install/`:

```console
$ docker run --rm <pinned ROS image> bash -ec <build + installed launch check + py_compile>
Starting >>> turtle_bringup
Finished <<< turtle_bringup [3.12s]

Summary: 1 package finished [3.35s]
```


Последняя строка обозначает проверенный шаг workflow; его точные аргументы
находятся в `.github/workflows/ci.yml`, а вывод сборки приведён без изменений.
Это локальное повторение шага CI; результат удалённого GitHub Actions run
нужно смотреть отдельно после push.

Официальная проверка комплекта и истории:

```bash
python3 .course-kit/v1/tools/check_practice.py PR02 --submission . --json
```

Её результат сохраняется в `checker.json`. Checker проверяет комплектность;
поведение ROS проверено приведённым выше живым опытом.
