# Feature Request: Streams and Event Subscriptions

Future extensibility includes file transfers via LXMF attachments and a publish/subscribe mechanism for events.
```
Reticulum itself has other capabilities (like real-time links, streams, etc.). Future extensibility might include:

* **Live Streams or LXMF Attachment handling:** Suppose in future we want to support a file transfer or streaming data as part of the API. Reticulum supports an LXMF packet containing an arbitrary payload or using additional protocols (like LXMF attachments or the LXMF “content destination” concept under development). We could extend the Service layer to handle a command that initiates a file transfer via RNS (perhaps using rncp or similar behind the scenes).
* **Event Subscription:** We could design a publish/subscribe mechanism on top of this. For example, a client might subscribe to a certain type of events (say, node status changes) and the server would push messages. Our current design is mostly request/response, but nothing prevents a controller or background task from sending an unsolicited LXMF message to a known client destination. The framework could later incorporate an **EventService** that controllers can use to emit notifications (where clients could register their address to receive those). This would be a significant extension but aligned with a real-time data need.
```

Support for these features would allow richer interactions beyond simple request/response messaging.
