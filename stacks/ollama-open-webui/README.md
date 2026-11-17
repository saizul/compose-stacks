# Ollama + Open WebUI

Run open-weight language models (Llama, Qwen, Mistral, Gemma and many more) on
your own hardware with [Ollama](https://ollama.com), and use them through
[Open WebUI](https://openwebui.com), a feature-rich chat interface with users,
document chat (RAG) and model management.

## Quick start

```bash
compose-stacks init ollama-open-webui ./local-llm
cd local-llm
docker compose up -d
docker compose exec ollama ollama pull llama3.2
```

Open <http://127.0.0.1:3080>. The first account you create becomes the admin.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for published ports |
| `OLLAMA_PORT` | `11434` | Ollama API port |
| `OPEN_WEBUI_PORT` | `3080` | Web UI port |
| `WEBUI_URL` | `http://localhost:3080` | Public URL |
| `WEBUI_SECRET_KEY` | generated | Session signing key |
| `ENABLE_SIGNUP` | `true` | Allow sign-up |
| `DEFAULT_USER_ROLE` | `pending` | New users need admin approval |
| `OLLAMA_KEEP_ALIVE` | `5m` | Keep models loaded |
| `OLLAMA_NUM_PARALLEL` | `1` | Parallel requests |

### NVIDIA GPU

Install the NVIDIA Container Toolkit on the host, then add to the `ollama` service:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### Hardware

Plan for roughly 8 GB of RAM for 7-8B models and 16 GB+ for 13-14B models on CPU.
Models are stored in the `ollama_data` volume.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `open-webui` | 127.0.0.1:3080 | Chat UI |
| `ollama` | 127.0.0.1:11434 | Ollama API (also a compatible chat-completions API under `/v1`) |

The Ollama API has no authentication. Keep it on `127.0.0.1`.

## Backups

Back up `open_webui_data` (accounts and chats). Models can be pulled again.

## Upgrading

Change both tags and `docker compose up -d`.

## Links

- Open WebUI docs: <https://docs.openwebui.com>
- Ollama Docker docs: <https://github.com/ollama/ollama/blob/main/docs/docker.md>
- Model library: <https://ollama.com/library>
