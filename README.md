# Prometheus hostapd Exporter

A hardened telemetry collector for WiFi Access Points.

## Features
- **Zero Config**: Automatically detects hostapd interfaces.
- **BOfH Approved**: Strict systemd sandboxing (Read-only VFS, private /tmp).
- **Lightweight**: Minimal Python dependencies, no heavy parsers.

## Installation (Debian)
```bash
apt install ./prometheus-hostapd-exporter_2.0-1_all.deb
```

## Configuration

Edit `/etc/default/prometheus-hostapd-exporter`.

Default port: `9551`.

## Security

Runs as `prometheus:prometheus` with supplementary group `netdev`.
Uses `ProtectSystem=strict` to prevent filesystem mutation.
