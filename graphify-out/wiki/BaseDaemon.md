# BaseDaemon

> God node · 28 connections · `daemons/base.py`

## Connections by Relation

### contains
- [[base.py]] `EXTRACTED`

### inherits
- [[ABC]] `EXTRACTED`

### method
- [[.run()]] `EXTRACTED`
- [[._process_command()]] `EXTRACTED`
- [[._heartbeat()]] `EXTRACTED`
- [[._consume_commands()]] `EXTRACTED`
- [[._recover_state()]] `EXTRACTED`
- [[._ensure_consumer_group()]] `EXTRACTED`
- [[.__init__()]] `EXTRACTED`
- [[._on_started()]] `EXTRACTED`
- [[.publish_event()]] `EXTRACTED`
- [[._persist_state()]] `EXTRACTED`
- [[._transition()]] `EXTRACTED`
- [[._request_shutdown()]] `EXTRACTED`
- [[.stop()]] `EXTRACTED`

### rationale_for
- [[Abstract base class for gate daemons.      Responsibilities:     - Connect to Re]] `EXTRACTED`

### uses
- [[GateOutDaemon]] `INFERRED`
- [[GateInDaemon]] `INFERRED`
- [[BaseEvent]] `INFERRED`
- [[IntegrationDaemon]] `INFERRED`
- [[HeartbeatEvent]] `INFERRED`
- [[TestableDaemon]] `INFERRED`
- [[TestBaseDaemonLifecycle]] `INFERRED`
- [[TestStatePersistence]] `INFERRED`
- [[TestEventPublishing]] `INFERRED`
- [[TestCommandConsumption]] `INFERRED`
- [[TestHeartbeat]] `INFERRED`
- [[TestGracefulShutdown]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*