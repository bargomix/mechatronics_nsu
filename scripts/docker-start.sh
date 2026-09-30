#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
container="mechatronics-pr01"
image="$(cat "$repo_dir/docker-image.txt")"

if docker container inspect "$container" >/dev/null 2>&1; then
  workspace="$(docker inspect --format '{{ index .Config.Labels "mechatronics.workspace" }}' "$container")"
  if [[ "$workspace" != "$repo_dir" ]]; then
    echo "Контейнер $container принадлежит другой папке. Остановитесь и проверьте его." >&2
    exit 1
  fi
  if [[ "$(docker inspect --format '{{.State.Running}}' "$container")" == true ]]; then
    echo "Контейнер уже работает. В трёх терминалах выполните ./scripts/ros-shell.sh"
    exit 0
  fi
fi

command -v xauth >/dev/null
: "${DISPLAY:?Для turtlesim нужна графическая сессия с DISPLAY}"
test -d /tmp/.X11-unix
mkdir -p "$repo_dir/.local"
auth_file="$repo_dir/.local/ros.xauth"
touch "$auth_file"
chmod 600 "$auth_file"
# Cookie остаётся локальным и не попадает в Git. FamilyWild позволяет
# использовать его при отличающемся имени хоста внутри контейнера.
auth_data="$(xauth nlist "$DISPLAY")"
if [[ -z "$auth_data" ]]; then
  echo "Не найден X11 cookie для DISPLAY=$DISPLAY. Проверьте XAUTHORITY." >&2
  exit 1
fi
printf '%s\n' "$auth_data" | sed 's/^..../ffff/' | xauth -f "$auth_file" nmerge -
unset auth_data

if docker container inspect "$container" >/dev/null 2>&1; then
  docker start "$container" >/dev/null
else
  if timeout 60s docker run --detach --init \
    --name "$container" \
    --label "mechatronics.workspace=$repo_dir" \
    --network host \
    --user "$(id -u):$(id -g)" \
    --mount "type=bind,source=$repo_dir,target=/work" \
    --mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly \
    --mount "type=bind,source=$auth_file,target=/tmp/ros.xauth,readonly" \
    --env "DISPLAY=$DISPLAY" \
    --env XAUTHORITY=/tmp/ros.xauth \
    --env HOME=/tmp/ros-home \
    --env ROS_DOMAIN_ID=16 \
    --env QT_QPA_PLATFORM=xcb \
    --env QT_X11_NO_MITSHM=1 \
    --workdir /work \
    "$image" \
    bash -lc 'mkdir -p "$HOME"; exec sleep infinity' >/dev/null; then
    :
  else
    echo "Docker не запустил контейнер за 60 секунд или вернул ошибку. Проверьте docker ps и службу Docker." >&2
    exit 1
  fi
fi

echo "Контейнер готов. В трёх терминалах выполните ./scripts/ros-shell.sh"
