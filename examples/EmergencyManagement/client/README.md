# Emergency Management northbound client

The full stack setup—including the shared LXMF client, FastAPI gateway, and CLI demo—is documented in the consolidated [Emergency Management README](../README.md). Refer to that guide for configuration values, startup commands, and build instructions. The sample [`client_config.json`](client_config.json) now also includes a `shared_instance_rpc_key` entry so the CLI, web gateway, and LXMF service can all authenticate with the bundled Reticulum configuration under [`../.reticulum`](../.reticulum).
