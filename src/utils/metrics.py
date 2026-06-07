from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

# Path Prometheus scrapes. Must match `metrics_path` in
# docker/prometheus/prometheus.yml for the `fastapi` job.
METRICS_PATH = "/TheNchy135_Dawy_Test_Metrics"


def setup_metrics(app: FastAPI):
    """
    Instrument the app with prometheus-fastapi-instrumentator.

    This emits the standard metric names the community "FastAPI Observability"
    dashboard (Grafana ID 16110) expects, e.g.:
      - http_requests_total{handler, method, status}
      - http_request_duration_seconds_bucket{handler, method}
      - http_request_duration_highr_seconds_bucket

    Latency is labeled by `handler` (the route template, e.g.
    /api/v1/nlp/index/answer/{project_id}) instead of the raw URL path, which
    avoids creating a new time-series per project id (high cardinality).
    """
    Instrumentator(
        should_group_status_codes=False,    # keep exact codes (200, 400, 404, ...)
        should_ignore_untemplated=False,    # still record unmatched paths (404s)
        excluded_handlers=[METRICS_PATH],   # don't measure the scrape endpoint itself
    ).instrument(app).expose(
        app,
        endpoint=METRICS_PATH,
        include_in_schema=False,
    )
