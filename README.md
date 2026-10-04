# PHANTOM v1.0 👻

A dark-themed PySide6 security workbench for **your own** Kali Linux lab. This is a functional first release, not an exploit framework.

## Setup on Kali

```bash
sudo apt update
sudo apt install -y python3-venv iw network-manager nmap tshark hashcat coreutils reaver
git clone https://github.com/Jonardi123/PHANTOM.git
cd PHANTOM
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python phantom.py
```

The `reaver` package normally provides `wash`. Your desktop needs an active graphical session. Network Radar uses an interface managed by NetworkManager; WPS Inspector requires a separate interface already in monitor mode and uses `sudo -n` to avoid hanging on password prompts.

## Modules

1. **Network Radar:** discover nearby Wi-Fi using `nmcli`.
2. **Adapter Manager:** inspect interfaces and supported modes with `iw` and `nmcli`.
3. **WPS Inspector:** inspect passive WPS advertisements on a selected 2.4 GHz channel.
4. **Password Lab:** estimate random-password search spaces and run a WPA2 Hashcat benchmark, without cracking automation.
5. **Handshake Analyzer:** inspect EAPOL packet metadata in an existing capture using `tshark`. EAPOL packets alone do not prove a valid handshake.
6. **Device Explorer:** permission-gated Nmap host discovery, limited to 256 IPv4 addresses.
7. **Security Reports:** save selected module output as local JSON.

PHANTOM does not collect Wi-Fi passwords, force disconnections, automate PIN guessing or run exploits.

Only assess networks and devices you own or are authorized to test. Reports may contain sensitive information and are stored under `~/.local/share/phantom/reports`.

Run offline regression checks with `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v`. These checks exercise command-thread handling and password estimates without scanning networks.
