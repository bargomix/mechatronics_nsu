# ПР01. Окружение и граф ROS 2

Среда: Docker, Ubuntu 24.04, ROS 2 Jazzy. Образ закреплён digest в
`docker-image.txt`, версия course kit и SHA-256 — в `course-kit.lock.json`.
Исходное задание: https://ros.lms.ci.nsu.ru/practices/pr01.

В этой работе используем готовые программы пакета `turtlesim`. Своя нода,
пакет и сборка `colcon` пока не нужны. Нода `/teleop_turtle` публикует команды
в `/turtle1/cmd_vel`, нода `/turtlesim` их принимает и публикует позу в
`/turtle1/pose`. Одинаковый домен позволяет участникам обнаружить друг друга.

## Запуск среды

В терминале хоста перейдите в эту папку и выполните:

```bash
./scripts/docker-start.sh
```

Скрипт подключает рабочую папку как `/work` и графический X11-сокет с cookie
текущей сессии. Файлы в `/work` сохраняются на хосте от вашего пользователя.
Скрипт рассчитан на Linux с Docker и X11/XWayland; для GUI нужен `xauth`.

Откройте три терминала A, B, C. В каждом перейдите в эту папку и запустите:

```bash
./scripts/ros-shell.sh
```

Все три терминала входят в один контейнер. ROS подключается через
`source /opt/ros/jazzy/setup.bash`, начальный `ROS_DOMAIN_ID=16`.
В аудитории замените 16 и 17 выделенной вам парой доменов во всех командах.
Перед опытом остановите прежние ROS-ноды через Ctrl+C.

## Исправный граф

Терминал A:

```bash
ros2 run turtlesim turtlesim_node
```

Терминал B:

```bash
ros2 run turtlesim turtle_teleop_key
```

Нажмите стрелки в терминале B: черепаха должна двигаться. Терминал C:

```bash
mkdir -p evidence/pr01
ros2 doctor --report > evidence/pr01/doctor.txt 2>&1
ros2 node list --no-daemon --spin-time 2
ros2 topic list -t
ros2 node info /turtlesim
ros2 topic type /turtle1/pose
POSE_TYPE=$(ros2 topic type /turtle1/pose)
ros2 topic echo /turtle1/pose --once
ros2 topic hz /turtle1/pose
```

Замер частоты оставьте работать минимум 10 секунд, затем нажмите Ctrl+C.
Поза публикуется и в покое. Тип в Jazzy: `turtlesim/msg/Pose`; ожидаемая
частота около 60–62,5 Гц, но в отчёт записывается фактический результат.

## Потеря связи

Симулятор A продолжает работать в домене 16. В B остановите teleop через
Ctrl+C и запустите его заново:

```bash
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
```

Стрелки больше не управляют черепахой. В C выполните:

```bash
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-broken.txt 2>&1
broken_exit=$?
printf 'exit=%s\n' "$broken_exit"
```

Ожидается только `/teleop_turtle`, нет `/turtlesim`. Проверка позы завершается
с кодом 124 (таймаут) без сообщения. Явный тип нужен, поскольку издатель
позы не обнаруживается в домене 17.

## Восстановление связи

В B остановите teleop через Ctrl+C и повторно запустите:

```bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtle_teleop_key
```

В C повторите тот же тест:

```bash
export ROS_DOMAIN_ID=16
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-fixed.txt 2>&1
fixed_exit=$?
printf 'exit=%s\n' "$fixed_exit"
```

Ожидаются обе ноды, сообщение позы и код 0. Стрелки снова управляют черепахой.
Значение `ROS_DOMAIN_ID` читается при запуске процесса: `export` влияет на
будущие процессы, поэтому teleop надо перезапустить. Симулятор остаётся
в исходном домене, переустановка ROS не требуется.

## Отчёт и сдача

Сохраните результаты опыта в `evidence/pr01/`: `doctor.txt`, `graph.md`,
`environment.json`, `report.json` и дополнительные исходные логи.
Использование ИИ описано в `AI_USAGE.md`. Поле `time` в шаблоне отчёта
показывает предусмотренную условием трудоёмкость: одна пара (2 академических
часа) и около 2 часов самостоятельной доработки.

Проверка из корня этого репозитория:

```bash
python3 -m json.tool evidence/pr01/environment.json > /dev/null
python3 .course-kit/v1/tools/check_practice.py PR01 --submission .
```

При отсутствии course kit скачайте архив по `archive_url` из
`course-kit.lock.json`, проверьте SHA-256 и распакуйте в `.course-kit`.
Checker проверяет комплектность и Git-историю; живой опыт повторяется локально.
CI на GitHub выполняет проверку JSON и официальный checker с той же ревизией kit.

Сдача содержит два коммита: A — README, скрипты, CI и зафиксированные версии;
B — только `evidence/pr01/` и `AI_USAGE.md`. В `report.json` укажите полный
SHA коммита A. После изменения реализации создайте A2 и новый отчёт B2.
Для сдачи нужны ссылка на личный репозиторий, SHA коммита B и ссылка на
успешный CI run именно этого коммита.

Перед защитой самостоятельно повторите три стадии опыта и объясните роли
нод, направление сообщений, тип позы, частоту и причину разрыва доменов.

## Завершение

Остановите ноды через Ctrl+C, выйдите из каждого терминала контейнера
командой `exit`, затем на хосте выполните:

```bash
docker stop mechatronics-pr01
```

Следующий запуск: `./scripts/docker-start.sh`. Рабочая папка и evidence
сохраняются независимо от контейнера.
