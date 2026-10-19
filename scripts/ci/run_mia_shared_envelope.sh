#!/usr/bin/env bash
# GitHub-only isolated common parent; never run against production containers.
set -euo pipefail

mia_group=/sys/fs/cgroup/miap23.slice
mia_parent=miap23.slice
mia_results=$MIA_P23_REPORT_DIR
mkdir -p "$mia_results"

cleanup() {
    mia_result=$?
    set +e
    for mia_file in cpu.max cpu.stat memory.max memory.swap.max memory.current memory.peak memory.events; do
        if [ -r "$mia_group/$mia_file" ]; then
            cp "$mia_group/$mia_file" "$mia_results/cgroup-final-$mia_file.txt"
        fi
    done
    docker inspect --format '{{.Name}} {{.Image}} {{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}' \
        miap23-mysql miap23-redis > "$mia_results/container-final.txt" 2>&1
    docker logs miap23-mysql > "$mia_results/mysql.log" 2>&1
    docker logs miap23-redis > "$mia_results/redis.log" 2>&1
    if [[ "${MIA_P23_MODE:-capacity}" =~ ^(app-lifecycle|reply-smoke|reply-stages|reply-latency|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]]; then
        docker stop --time 5 miap23-mysql miap23-redis > "$mia_results/container-stop.txt" 2>&1
        docker inspect --format '{{.Name}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Running}}' \
            miap23-mysql miap23-redis > "$mia_results/container-stopped.txt" 2>&1
    fi
    docker rm -fv miap23-mysql miap23-redis >/dev/null 2>&1
    sudo systemctl stop miap23-measure.service miap23.slice >/dev/null 2>&1
    if [[ "${MIA_P23_MODE:-capacity}" =~ ^(app-lifecycle|reply-smoke|reply-stages|reply-latency|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]] && [ -f "$mia_results/app-lifecycle-results.json" ]; then
        if ! python "$GITHUB_WORKSPACE/scripts/ci/verify_mia_app_lifecycle.py" --finalize; then
            mia_result=1
        fi
    fi
    exit "$mia_result"
}
trap cleanup EXIT

test "$(stat -fc %T /sys/fs/cgroup)" = cgroup2fs
docker info --format '{{.CgroupDriver}}' > "$mia_results/docker-cgroup-driver.txt"
if [ "$(cat "$mia_results/docker-cgroup-driver.txt")" != systemd ]; then
    mia_parent=/miap23.slice
fi
sudo tee /run/systemd/system/miap23.slice >/dev/null <<'UNIT'
[Unit]
Description=Mia isolated P23 common service envelope
[Slice]
CPUAccounting=yes
CPUQuota=200%
CPUQuotaPeriodSec=100ms
MemoryAccounting=yes
MemoryMax=2147483648
MemorySwapMax=0
UNIT
sudo systemctl daemon-reload
sudo systemctl start miap23.slice
docker run -d --name miap23-mysql --cgroup-parent="$mia_parent" --network host \
    -e MYSQL_ROOT_PASSWORD=mia-ci-only -e MYSQL_DATABASE=xiaozhi_esp32_server \
    -e MYSQL_ROOT_HOST=127.0.0.1 mysql:8.4 --bind-address=127.0.0.1 >/dev/null
docker run -d --name miap23-redis --cgroup-parent="$mia_parent" --network host \
    redis:8 redis-server --bind 127.0.0.1 >/dev/null

for mia_attempt in $(seq 1 90); do
    if docker exec miap23-mysql mysqladmin ping -h 127.0.0.1 -pmia-ci-only --silent >/dev/null 2>&1 \
        && [ "$(docker exec miap23-redis redis-cli ping)" = PONG ]; then
        break
    fi
    test "$mia_attempt" -lt 90
    sleep 1
done
mia_mysql_pid=$(docker inspect --format '{{.State.Pid}}' miap23-mysql)
mia_redis_pid=$(docker inspect --format '{{.State.Pid}}' miap23-redis)
mia_database_pids=$(python - "$mia_mysql_pid" "$mia_redis_pid" <<'PY'
import json, sys
print(json.dumps(dict(zip(('mysql', 'redis'), map(int, sys.argv[1:])))))
PY
)
mia_classpath="target/test-classes:target/classes:$(cat "$RUNNER_TEMP/mia-p23-classpath.txt"):$HOME/.m2/repository/org/junit/platform/junit-platform-console-standalone/1.10.1/junit-platform-console-standalone-1.10.1.jar"
mia_python=$(command -v python)
mia_script=$GITHUB_WORKSPACE/scripts/ci/verify_mia_shared_envelope.py
if [[ "${MIA_P23_MODE:-capacity}" =~ ^(app-lifecycle|reply-smoke|reply-stages|reply-latency|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]]; then
    mia_script=$GITHUB_WORKSPACE/scripts/ci/verify_mia_app_lifecycle.py
fi
mia_provider_environment=()
mia_sudo_environment=()
if [[ "${MIA_P23_MODE:-capacity}" =~ ^(reply-(smoke|stages|latency)|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]]; then
    mia_provider_environment=(--setenv=MIA_TEST_LLM_API_KEY --setenv=MIA_TEST_LLM_BASE_URL)
    mia_sudo_environment=(--preserve-env=MIA_TEST_LLM_API_KEY,MIA_TEST_LLM_BASE_URL)
fi

# Only the already-built Java test process and its Python child run here.
# No Maven JVM, model export, or compile runs in the measured group.
sudo "${mia_sudo_environment[@]}" systemd-run --unit=miap23-measure --slice=miap23.slice --wait --pipe --collect \
    --uid="$(id -u)" --gid="$(id -g)" \
    --property="WorkingDirectory=$MIA_SCOPE_UPSTREAM/main/manager-api" \
    --setenv="PATH=$PATH" --setenv="LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" \
    --setenv="GITHUB_SHA=$GITHUB_SHA" \
    --setenv="MIA_SCOPE_UPSTREAM=$MIA_SCOPE_UPSTREAM" \
    --setenv="MIA_SCOPE_KEYSTORE=$MIA_SCOPE_KEYSTORE" \
    --setenv="MIA_SCOPE_CA=$MIA_SCOPE_CA" \
    --setenv="MIA_TLS_CERT_FILE=$MIA_TLS_CERT_FILE" --setenv="MIA_TLS_KEY_FILE=$MIA_TLS_KEY_FILE" \
    --setenv="MIA_EMBEDDING_DIR=$MIA_EMBEDDING_DIR" \
    --setenv="MIA_P23_REPORT_DIR=$mia_results" \
    --setenv="MIA_P23_SCRIPT=$mia_script" \
    --setenv="MIA_P23_PYTHON=$mia_python" \
    --setenv="MIA_P23_MODE=${MIA_P23_MODE:-capacity}" \
    --setenv="MIA_P23_DATABASE_PIDS=$mia_database_pids" \
    --setenv="SPRING_DATASOURCE_DRUID_URL=jdbc:mysql://127.0.0.1:3306/xiaozhi_esp32_server?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC&nullCatalogMeansCurrent=true&allowPublicKeyRetrieval=true&useSSL=false" \
    --setenv=SPRING_DATASOURCE_DRUID_PASSWORD=mia-ci-only \
    --setenv=SPRING_DATA_REDIS_HOST=127.0.0.1 \
    --setenv=OMP_NUM_THREADS=2 --setenv=OPENBLAS_NUM_THREADS=2 \
    "${mia_provider_environment[@]}" \
    "$JAVA_HOME/bin/java" -Xmx512m -XX:MaxMetaspaceSize=256m -XX:ActiveProcessorCount=2 -Xss512k \
    -cp "$mia_classpath" org.junit.platform.console.ConsoleLauncher execute \
    --select-class=xiaozhi.modules.device.MiaPerformanceIntegrationTest \
    --fail-if-no-tests --details=summary --reports-dir="$mia_results/junit" \
    > "$mia_results/manager.log" 2>&1
