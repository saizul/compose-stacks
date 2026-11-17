# Meilisearch

[Meilisearch](https://www.meilisearch.com) is an open-source search engine with
instant, typo-tolerant results and a simple REST API. This stack runs it in
production mode, so a master key is required and the dashboard is disabled.

## Quick start

```bash
compose-stacks init meilisearch ./meilisearch
cd meilisearch
docker compose up -d
. ./.env
curl -s -H "Authorization: Bearer $MEILI_MASTER_KEY" http://127.0.0.1:7700/keys
```

The `/keys` call lists the default *search* and *admin* API keys. Use the search
key in front-end code and the admin key on your server.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `MEILI_PORT` | `7700` | Host port |
| `MEILI_MASTER_KEY` | generated | Master key |
| `MEILI_MAX_INDEXING_MEMORY` | `1GiB` | Indexing memory budget |
| `MEILI_LOG_LEVEL` | `INFO` | Log level |

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `meilisearch` | 127.0.0.1:7700 | REST API |

## Backups

Create a dump through the API (`POST /dumps`) or a snapshot; files land in the
`meili_data` volume under `dumps/` and `snapshots/`.

## Upgrading

Meilisearch v1.x can usually upgrade in place; check the release notes. For
large version jumps create a dump first and import it with `--import-dump`.

## Links

- Self-hosting guide: <https://www.meilisearch.com/docs/learn/self_hosted/getting_started_with_self_hosted_meilisearch>
- Security and keys: <https://www.meilisearch.com/docs/learn/security/basic_security>
