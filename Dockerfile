FROM python:3.12.2-slim
WORKDIR /experiment
COPY policy.py server.py ledger.py run_experiments.py run_persistence.py ./
USER 65534:65534
ENTRYPOINT ["python", "run_experiments.py", "--output", "/tmp/results/latest.json"]
