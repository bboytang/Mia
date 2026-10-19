#!/usr/bin/env bash
# GitHub-only isolated common parent; never run against production containers.
set -euo pipefail

youmi_group=/sys/fs/cgroup/youmip23.slice
youmi_parent=youmip23.slice
youmi_results=$MIA_P23_REPORT_DIR
mkdir -p "$youmi_results"

cleanup() {
    youmi_result=$?
    set +e
    for youmi_file in cpu.max cpu.stat memory.max memory.swap.max memory.current memory.peak memory.events; do
        if [ -r "$youmi_group/$youmi_file" ]; then
            cp "$youmi_group/$youmi_file" "$youmi_results/cgroup-final-$youmi_file.txt"
        fi
    done
    docker inspect --format '{{.Name}} {{.Image}} {{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}' \
        youmip23-mysql youmip23-redis > "$youmi_results/container-final.txt" 2>&1
    docker logs youmip23-mysql > "$youmi_results/mysql.log" 2>&1
    docker logs youmip23-redis > "$youmi_results/redis.log" 2>&1
    if [[ "${MIA_P23_MODE:-capacity}" =~ ^(app-lifecycle|reply-smoke|reply-stages|reply-stages-replay|reply-latency|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]]; then
        docker stop --time 5 youmip23-mysql youmip23-redis > "$youmi_results/container-stop.txt" 2>&1
        docker inspect --format '{{.Name}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Running}}' \
            youmip23-mysql youmip23-redis > "$youmi_results/container-stopped.txt" 2>&1
    fi
    docker rm -fv youmip23-mysql youmip23-redis >/dev/null 2>&1
    sudo systemctl stop youmip23-measure.service youmip23.slice >/dev/null 2>&1
    if [[ "${MIA_P23_MODE:-capacity}" =~ ^(app-lifecycle|reply-smoke|reply-stages|reply-stages-replay|reply-latency|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]] && [ -f "$youmi_results/app-lifecycle-results.json" ]; then
        if ! python "$GITHUB_WORKSPACE/scripts/ci/verify_youmi_app_lifecycle.py" --finalize; then
            youmi_result=1
        fi
    fi
    exit "$youmi_result"
}
trap cleanup EXIT

test "$(stat -fc %T /sys/fs/cgroup)" = cgroup2fs
docker info --format '{{.CgroupDriver}}' > "$youmi_results/docker-cgroup-driver.txt"
if [ "$(cat "$youmi_results/docker-cgroup-driver.txt")" != systemd ]; then
    youmi_parent=/youmip23.slice
fi
sudo tee /run/systemd/system/youmip23.slice >/dev/null <<'UNIT'
[Unit]
Description=Youmi isolated P23 common service envelope
[Slice]
CPUAccounting=yes
CPUQuota=200%
CPUQuotaPeriodSec=100ms
MemoryAccounting=yes
MemoryMax=2147483648
MemorySwapMax=0
UNIT
sudo systemctl daemon-reload
sudo systemctl start youmip23.slice
docker run -d --name youmip23-mysql --cgroup-parent="$youmi_parent" --network host \
    -e MYSQL_ROOT_PASSWORD=youmi-ci-only -e MYSQL_DATABASE=youmi_esp32_server \
    -e MYSQL_ROOT_HOST=127.0.0.1 mysql:8.4 --bind-address=127.0.0.1 >/dev/null
docker run -d --name youmip23-redis --cgroup-parent="$youmi_parent" --network host \
    redis:8 redis-server --bind 127.0.0.1 >/dev/null

for youmi_attempt in $(seq 1 90); do
    if docker exec youmip23-mysql mysqladmin ping -h 127.0.0.1 -pyoumi-ci-only --silent >/dev/null 2>&1 \
        && [ "$(docker exec youmip23-redis redis-cli ping)" = PONG ]; then
        break
    fi
    test "$youmi_attempt" -lt 90
    sleep 1
done
youmi_mysql_pid=$(docker inspect --format '{{.State.Pid}}' youmip23-mysql)
youmi_redis_pid=$(docker inspect --format '{{.State.Pid}}' youmip23-redis)
youmi_database_pids=$(python - "$youmi_mysql_pid" "$youmi_redis_pid" <<'PY'
import json, sys
print(json.dumps(dict(zip(('mysql', 'redis'), map(int, sys.argv[1:])))))
PY
)
youmi_classpath="target/test-classes:target/classes:$(cat "$RUNNER_TEMP/mia-p23-classpath.txt"):$HOME/.m2/repository/org/junit/platform/junit-platform-console-standalone/1.10.1/junit-platform-console-standalone-1.10.1.jar"
youmi_python=$(command -v python)
youmi_script=$GITHUB_WORKSPACE/scripts/ci/verify_youmi_shared_envelope.py
if [[ "${MIA_P23_MODE:-capacity}" =~ ^(app-lifecycle|reply-smoke|reply-stages|reply-stages-replay|reply-latency|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]]; then
    youmi_script=$GITHUB_WORKSPACE/scripts/ci/verify_youmi_app_lifecycle.py
fi
youmi_provider_environment=()
youmi_sudo_environment=()
if [[ "${MIA_P23_MODE:-capacity}" =~ ^(reply-(smoke|stages|latency)|worker-smoke|worker-extraction|worker-faults|worker-fairness|worker-fairness-diagnostic|worker-shutdown)$ ]]; then
    youmi_provider_environment=(--setenv=MIA_TEST_LLM_API_KEY --setenv=MIA_TEST_LLM_BASE_URL)
    youmi_sudo_environment=(--preserve-env=MIA_TEST_LLM_API_KEY,MIA_TEST_LLM_BASE_URL)
fi

# Only the already-built Java test process and its Python child run here.
# No Maven JVM, model export, or compile runs in the measured group.
sudo "${youmi_sudo_environment[@]}" systemd-run --unit=youmip23-measure --slice=youmip23.slice --wait --pipe --collect \
    --uid="$(id -u)" --gid="$(id -g)" \
    --property="WorkingDirectory=$MIA_SCOPE_UPSTREAM/main/manager-api" \
    --setenv="PATH=$PATH" --setenv="LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" \
    --setenv="GITHUB_SHA=$GITHUB_SHA" \
    --setenv="MIA_SCOPE_UPSTREAM=$MIA_SCOPE_UPSTREAM" \
    --setenv="MIA_SCOPE_KEYSTORE=$MIA_SCOPE_KEYSTORE" \
    --setenv="MIA_SCOPE_CA=$MIA_SCOPE_CA" \
    --setenv="MIA_TLS_CERT_FILE=$MIA_TLS_CERT_FILE" --setenv="MIA_TLS_KEY_FILE=$MIA_TLS_KEY_FILE" \
    --setenv="MIA_EMBEDDING_DIR=$MIA_EMBEDDING_DIR" \
    --setenv="MIA_P23_REPORT_DIR=$youmi_results" \
    --setenv="MIA_P23_SCRIPT=$youmi_script" \
    --setenv="MIA_P23_PYTHON=$youmi_python" \
    --setenv="MIA_P23_MODE=${MIA_P23_MODE:-capacity}" \
    --setenv="MIA_P23_DATABASE_PIDS=$youmi_database_pids" \
    --setenv="SPRING_DATASOURCE_DRUID_URL=jdbc:mysql://127.0.0.1:3306/youmi_esp32_server?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC&nullCatalogMeansCurrent=true&allowPublicKeyRetrieval=true&useSSL=false" \
    --setenv=SPRING_DATASOURCE_DRUID_PASSWORD=youmi-ci-only \
    --setenv=SPRING_DATA_REDIS_HOST=127.0.0.1 \
    --setenv=OMP_NUM_THREADS=2 --setenv=OPENBLAS_NUM_THREADS=2 \
    "${youmi_provider_environment[@]}" \
    "$JAVA_HOME/bin/java" -Xmx512m -XX:MaxMetaspaceSize=256m -XX:ActiveProcessorCount=2 -Xss512k \
    -cp "$youmi_classpath" org.junit.platform.console.ConsoleLauncher execute \
    --select-class=xiaozhi.modules.device.YoumiPerformanceIntegrationTest \
    --fail-if-no-tests --details=summary --reports-dir="$youmi_results/junit" \
    > "$youmi_results/manager.log" 2>&1
