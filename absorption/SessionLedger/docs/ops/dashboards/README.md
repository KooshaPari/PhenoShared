# SessionLedger dashboards

`sessionledger-red.json` is an importable Grafana dashboard for the aggregate
HTTP RED counters exported by `sl-daemon` at `GET /metrics`.

## Prometheus scrape

Run the daemon on port 8080 and add this target to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: sl-daemon
    scrape_interval: 15s
    static_configs:
      - targets: ["host.docker.internal:8080"]
```

Use `127.0.0.1:8080` instead when Prometheus runs directly on the host. On
Linux with Prometheus in a container, use the daemon's reachable host address
or add `host-gateway` for `host.docker.internal`.

## Import

In Grafana, choose **Dashboards → New → Import**, upload
`sessionledger-red.json`, and select the Prometheus data source. The dashboard
defaults to the `sl-daemon` scrape job and supports filtering by instance.

The Wave-6 dashboard panels target aggregate counters only. As of Wave-19
(`#169`), `/metrics` also emits per-route `route` labels and histogram buckets
(`sl_http_request_duration_seconds_bucket{route=...}`). Wave-20 adds route-level
request rate, error ratio, and p95 latency panels that consume those labels.

## Provisioning

To provision the dashboard from disk, mount this directory into Grafana and add
a dashboard provider such as:

```yaml
apiVersion: 1

providers:
  - name: sessionledger
    orgId: 1
    folder: SessionLedger
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/sessionledger/dashboards
```

Place `sessionledger-red.json` under that path and restart Grafana, or wait for
the provider refresh. The dashboard expects a Prometheus data source; keep its
UID stable or choose the data source during manual import.

Load `../alerts/sessionledger-slo.yaml` into Prometheus with `rule_files`:

```yaml
rule_files:
  - /etc/prometheus/rules/sessionledger-slo.yaml
```

After Prometheus reloads, Grafana can show the same rules through the
Prometheus data source's alerting/rules view. Keep the Prometheus scrape job
named `sl-daemon`, or update both the dashboard variables and alert-rule label
matchers to the deployed job name.
