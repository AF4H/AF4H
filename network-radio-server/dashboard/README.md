# Dashboard Skeleton

This is intentionally lightweight. The first dashboard should expose:

- service state from `systemctl`
- USB/IP device binding status
- serial port inventory
- audio bridge health
- host identity and network reachability

Good first implementations:

- a small static page that polls a local JSON endpoint
- a minimal Flask/FastAPI backend
- later, a richer UI if the basic status surface proves useful

Keep the dashboard read-only at first. Control surfaces tend to get messy fast.
