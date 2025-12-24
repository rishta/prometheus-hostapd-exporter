### CHANGELOG

#### V1.0 - 20190327
- First version

#### V1.1 - 20190405
- Minor fixes in order to follow prometheus best practices regarding metrics naming. Using os.listdir insted of linux commands. 

#### V1.2 - 20190426
- Compatible with python3

#### V1.3 - 20190705
- Minor fix to avoid error if hostapd ctrl iface was created but didn't work

#### V1.4 - 20200521
- Minor fix to find config.json in a proper way

#### V2.0 - 20251224
- Complete refactor for Debian 12+ and Python 3.12 compatibility.
- Replaced `config.json` with 12-factor environment variables (`/etc/default/prometheus-hostapd-exporter`).
- Implemented "Strict" systemd sandboxing and least-privilege execution (user: prometheus).
- Integrated `setproctitle` for better process visibility.
- Migrated to `pyproject.toml` (PEP 621) and `hatchling` build backend.
- Full Debianization with automated user/group management.
