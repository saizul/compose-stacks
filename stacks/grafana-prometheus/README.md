# Grafana + Prometheus + node-exporter

A ready-to-use metrics stack for a server: node-exporter exposes CPU, memory,
disk and network metrics of the host, Prometheus stores them and Grafana shows
them. The Prometheus data source is provisioned, so there is nothing to click
through.

## Quick start

```bash
compose-stacks init grafana-prometheus ./monitoring
cd monitoring
docker compose up -d
```

Open Grafana at <http://127.0.0.1:3000>, log in with `GRAFANA_ADMIN_USER` /
`GRAFANA_ADMIN_PASSWORD` from `.env`, then *Dashboards > New > Import* and enter
ID **1860** (Node Exporter Full).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for published ports |
| `GRAFANA_PORT` | `3000` | Grafana port |
| `PROMETHEUS_PORT` | `9090` | Prometheus port |
| `GRAFANA_ADMIN_USER` | `admin` | Admin user |
| `GRAFANA_ADMIN_PASSWORD` | generated | Admin password |
| `GRAFANA_ROOT_URL` | `http://localhost:3000/` | Public URL |
| `PROMETHEUS_RETENTION` | `15d` | Data retention |

Scrape more targets by editing `prometheus/prometheus.yml` and reloading:
`curl -X POST http://127.0.0.1:9090/-/reload`.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `grafana` | 127.0.0.1:3000 | Dashboards |
| `prometheus` | 127.0.0.1:9090 | Metrics database |
| `node-exporter` | internal | Host metrics |

node-exporter reads the host filesystem read-only (`/:/host:ro`) and uses the
host PID namespace, as recommended upstream.

## Backups

Back up `grafana_data` (dashboards, users). Prometheus data can be rebuilt;
use snapshots (`POST /api/v1/admin/tsdb/snapshot` with the admin API enabled)
if you need history.

## Upgrading

Change the tags and `docker compose up -d`.

## Links

- node-exporter guide: <https://prometheus.io/docs/guides/node-exporter/>
- Grafana Docker docs: <https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/>
