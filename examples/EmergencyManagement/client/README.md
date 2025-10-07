# Emergency Management northbound client

The full stack setup—including the shared LXMF client, FastAPI gateway, and CLI demo—is documented in the consolidated [Emergency Management README](../README.md). Refer to that guide for configuration values, startup commands, and build instructions. The CLI now presents an interactive menu that lets operators:

- create new emergency action messages,
- update existing records,
- list all stored messages,
- retrieve individual messages by callsign, and
- delete records when they are no longer needed.

Behind the scenes the client issues the same LXMF commands as the gateway. Emergency action message flows map to
`CreateEmergencyActionMessage`, `PutEmergencyActionMessage`, `ListEmergencyActionMessage`, `RetrieveEmergencyActionMessage`,
and `DeleteEmergencyActionMessage`. Test seeding also exercises the event catalogue (`CreateEvent`, `PutEvent`, `ListEvent`,
`RetrieveEvent`, and `DeleteEvent`) so the mesh service contains representative data for the web UI.

All operations use the shared LXMF client and message codecs, so the CLI mirrors the behaviour of the gateway and northbound API. Populate [`client_config.json`](client_config.json) with values that match your mesh. In addition to the LXMF configuration paths and RPC key, the client understands:

- `request_timeout_seconds` – per-command timeout budget,
- `generate_test_messages` – optional seeding of random demo data,
- `enable_interactive_menu` – turn the interactive prompt on or off (useful for automation),
- `test_message_count` / `test_event_count` – payload counts for the seeding routine.
