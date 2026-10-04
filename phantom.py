#!/usr/bin/env python3
"""PHANTOM v1.0: local, consent-based Kali security workbench."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

APP_DIR = Path.home() / '.local' / 'share' / 'phantom'
REPORTS = APP_DIR / 'reports'
STYLE = """QWidget { background: #11121a; color: #eceafa; font: 12px "DejaVu Sans"; }
QFrame#sidebar {background:#181824; border-right:1px solid #343245;}
QLabel#heading {font-size:22px; font-weight:700; color:#cbb6ff;}
QLabel#muted {color:#aaa8bc;}
QPushButton {background:#302743; border:1px solid #55436e; border-radius:7px; padding:9px 13px; text-align:left;}
QPushButton:hover {background:#48355f;} QPushButton:disabled {color:#777486; background:#24232f;}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit {background:#1c1d29; border:1px solid #454055; border-radius:6px; padding:7px;}
QPlainTextEdit {font:11px "DejaVu Sans Mono";}
QCheckBox {spacing:8px;}"""

def run_command(args, timeout=25):
    """Never use a shell; commands and flags are constructed by the application."""
    try:
        p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, check=False, env={**os.environ, 'LC_ALL': 'C'})
        return p.returncode, p.stdout[-45000:] or '(No output)'
    except subprocess.TimeoutExpired:
        return 124, f'Timed out after {timeout} seconds.'
    except FileNotFoundError:
        return 127, f'Missing command: {args[0]}. Install it first.'
    except OSError as exc:
        return 1, f'Could not start command: {exc}'

class Worker(QObject):
    done = Signal(int, str)
    def __init__(self, args, timeout):
        super().__init__()
        self.args, self.timeout = args, timeout
    def work(self):
        self.done.emit(*run_command(self.args, self.timeout))

class Pane(QWidget):
    def __init__(self, title, description):
        super().__init__()
        self.layout = QVBoxLayout(self)
        heading = QLabel(title); heading.setObjectName('heading')
        self.layout.addWidget(heading)
        desc = QLabel(description); desc.setObjectName('muted'); desc.setWordWrap(True)
        self.layout.addWidget(desc)
        self.form = QFormLayout(); self.layout.addLayout(self.form)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.log.setPlaceholderText('Results appear here.'); self.layout.addWidget(self.log, 1)
        self.busy = False
        self.thread = None
        self.worker = None
        self.last_output = ''

    def line(self, label, value=''):
        field = QLineEdit(value); self.form.addRow(label, field); return field
    def selection(self, label, choices=()):
        cb = QComboBox(); cb.addItems(choices); self.form.addRow(label, cb); return cb
    def button(self, name, fn):
        b = QPushButton(name); b.clicked.connect(fn); self.form.addRow('', b); return b
    def show_result(self, label, code, result):
        self.last_output = f'{label}\nExit status: {code}\n\n{result}'
        self.log.setPlainText(self.last_output)
        self.log.moveCursor(self.log.textCursor().MoveOperation.Start)
    def execute(self, label, args, timeout=25, callback=None):
        if self.busy:
            QMessageBox.information(self, 'Already running', 'Wait for the current operation to finish.')
            return
        self.busy = True
        self.log.setPlainText(f'{label}\nRunning: {args[0]} (please wait)...')
        thread = QThread(self); worker = Worker(args, timeout); worker.moveToThread(thread)
        thread.started.connect(worker.work)
        def finished(code, output):
            self.busy = False
            self.show_result(label, code, output)
            if callback: callback(code, output)
            thread.quit()
        worker.done.connect(finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.thread, self.worker = thread, worker
        thread.start()

class Phantom(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PHANTOM | Wireless Security Suite v1.0')
        self.resize(1100, 760)
        self.setStyleSheet(STYLE)
        self.panes = []
        center = QWidget(); self.setCentralWidget(center)
        root = QHBoxLayout(center); root.setContentsMargins(0, 0, 0, 0)
        side = QFrame(); side.setObjectName('sidebar'); side.setFixedWidth(230)
        side_layout = QVBoxLayout(side)
        mark = QLabel('👻 PHANTOM'); mark.setObjectName('heading'); side_layout.addWidget(mark)
        side_layout.addWidget(QLabel('v1.0  •  Kali Security Lab'))
        self.stack = QStackedWidget(); root.addWidget(side); root.addWidget(self.stack, 1)
        builders = [
            ('Network Radar', self.radar), ('Adapter Manager', self.adapters),
            ('WPS Inspector', self.wps), ('Password Lab', self.password),
            ('Handshake Analyzer', self.handshake), ('Device Explorer', self.devices),
            ('Security Reports', self.reports)]
        for name, build in builders:
            pane = build(); self.stack.addWidget(pane); self.panes.append(pane)
            button = QPushButton(name)
            index = len(self.panes) - 1
            button.clicked.connect(lambda checked=False, i=index: self.stack.setCurrentIndex(i))
            side_layout.addWidget(button)
        side_layout.addStretch()
        side_layout.addWidget(QLabel('Only test networks and\ndevices you control or\nhave permission to audit.'))
        self.statusBar().showMessage('Ready | No background scanning')

    def _interface(self, pane, label='Wireless adapter'):
        cb = pane.selection(label, ['wlan1', 'wlan0'])
        def refresh():
            code, output = run_command(['iw', 'dev'], 8)
            names = re.findall(r'^\s*Interface\s+(\S+)', output, re.M) if code == 0 else []
            if names:
                current = cb.currentText(); cb.clear(); cb.addItems(names)
                if current in names: cb.setCurrentText(current)
            pane.show_result('Wireless interfaces', code, output)
        pane.button('↻ Refresh detected adapters', refresh)
        return cb

    def radar(self):
        p = Pane('Network Radar', 'List nearby access points using NetworkManager. This does not capture credentials.')
        cb = self._interface(p)
        p.button('Scan nearby Wi-Fi', lambda: p.execute('Nearby networks',
             ['nmcli', '-f', 'IN-USE,SSID,CHAN,SIGNAL,SECURITY', 'device', 'wifi', 'list',
              'ifname', cb.currentText(), '--rescan', 'yes'], 30))
        return p

    def adapters(self):
        p = Pane('Adapter Manager', 'Inspect interfaces and supported wireless modes. Mode changes are intentionally manual to avoid disconnecting your internet.')
        self._interface(p)
        p.button('Show interface states', lambda: p.execute('Wireless interfaces', ['iw', 'dev'], 8))
        p.button('Show supported modes', lambda: p.execute('Adapter capabilities', ['iw', 'list'], 12))
        p.button('Show connection status', lambda: p.execute('Connection status', ['nmcli', 'device', 'status'], 12))
        return p

    def wps(self):
        p = Pane('WPS Inspector', 'Passive WPS advertisement inspection only. No PIN guessing, association attempts or lockout probing.')
        cb = self._interface(p)
        channel = QSpinBox(); channel.setRange(1, 14); channel.setValue(7)
        p.form.addRow('2.4 GHz channel', channel)
        p.button('Inspect WPS on channel', lambda: p.execute('Passive WPS advertisements',
             ['sudo', '-n', 'timeout', '15', 'wash', '-i', cb.currentText(), '-c', str(channel.value())], 22))
        p.log.setPlaceholderText('Requires monitor mode and preconfigured sudo permissions; use terminal for password prompts.')
        return p

    def password(self):
        p = Pane('Password Lab', 'Estimate password strength locally. No online attacks or captured network credentials required.')
        sample = p.line('Character-set size', '62')
        length = QSpinBox(); length.setRange(1, 128); length.setValue(16)
        p.form.addRow('Password length', length)
        rate = p.line('Guesses per second', '4462')
        def estimate():
            try:
                base = int(sample.text()); speed = float(rate.text())
                if not 1 < base <= 1000 or speed <= 0: raise ValueError
                possibilities = base ** length.value()
                seconds = possibilities / speed
                years = seconds / (365.2425 * 86400)
                result = (f'Search space: {possibilities:,}\n'
                          f'Worst-case time at {speed:,.0f} guesses/s: {years:.3e} years\n'
                          f'Average (uniform random password): {years/2:.3e} years\n\n'
                          'Assumes independent, uniformly random characters. Real passwords often have patterns.')
                p.show_result('Offline password-strength estimate', 0, result)
            except ValueError:
                QMessageBox.warning(p, 'Invalid values', 'Enter a character-set size of 2–1000 and a positive speed.')
        p.button('Estimate random-password resistance', estimate)
        p.button('Benchmark WPA2 (CPU)', lambda: p.execute('Hashcat WPA2 benchmark',
                 ['hashcat', '-b', '-m', '22000', '-D', '1'], 180))
        return p

    def handshake(self):
        p = Pane('Handshake Analyzer', 'Inspect a capture you own. Displays capture metadata only; does not collect handshakes or recover passwords.')
        path = p.line('Capture file (.pcap/.pcapng)')
        def browse():
            filename, _ = QFileDialog.getOpenFileName(p, 'Select your capture', str(Path.home()),
                                                     'Packet captures (*.pcap *.pcapng *.cap)')
            if filename: path.setText(filename)
        p.button('Choose capture', browse)
        def inspect():
            target = Path(path.text()).expanduser()
            if not target.is_file() or target.suffix.lower() not in ('.pcap', '.pcapng', '.cap'):
                QMessageBox.warning(p, 'Invalid capture', 'Choose an existing .pcap, .pcapng or .cap file.'); return
            p.execute('Capture metadata / EAPOL packet summary',
                      ['tshark', '-r', str(target), '-Y', 'eapol', '-T', 'fields',
                       '-e', 'frame.number', '-e', 'frame.time_relative', '-e', 'eapol.type'], 35)
        p.button('Inspect EAPOL packets', inspect)
        return p

    def devices(self):
        p = Pane('Device Explorer', 'Discover devices on your own LAN. Explicitly acknowledge authorization before scanning.')
        network = p.line('IPv4 subnet (CIDR)', '192.168.100.0/24')
        consent = QCheckBox('I own this network or have explicit permission to scan it.')
        p.form.addRow('', consent)
        def scan():
            value = network.text().strip()
            import ipaddress
            try:
                parsed = ipaddress.ip_network(value, strict=False)
                if parsed.version != 4 or parsed.num_addresses > 256: raise ValueError
            except ValueError:
                QMessageBox.warning(p, 'Invalid range', 'Enter a valid IPv4 subnet with no more than 256 addresses.'); return
            if not consent.isChecked():
                QMessageBox.warning(p, 'Permission required', 'Confirm that you are authorized to scan this network.'); return
            p.execute('Host discovery', ['nmap', '-sn', str(parsed)], 100)
        p.button('Discover authorized devices', scan)
        return p

    def reports(self):
        p = Pane('Security Reports', 'Save results locally as JSON. Reports may contain private network information.')
        source = p.selection('Module', ['Network Radar', 'Adapter Manager', 'WPS Inspector',
                                       'Password Lab', 'Handshake Analyzer', 'Device Explorer'])
        p.button('Save selected module result', lambda: self.save_report(p, source.currentText()))
        def show():
            REPORTS.mkdir(parents=True, exist_ok=True)
            p.show_result('Saved report files', 0, '\n'.join(str(x) for x in sorted(REPORTS.glob('*.json')))
                          or 'No reports saved yet.')
        p.button('List saved reports', show)
        return p

    def save_report(self, pane, name):
        lookup = {self.stack.widget(i).layout.itemAt(0).widget().text(): self.stack.widget(i)
                  for i in range(self.stack.count())}
        origin = lookup.get(name)
        if not origin or not origin.last_output:
            QMessageBox.information(pane, 'No results', 'Run the selected module first.'); return
        REPORTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        destination = REPORTS / f'{name.lower().replace(" ", "-")}-{stamp}.json'
        destination.write_text(json.dumps({'module': name, 'timestamp': datetime.now().isoformat(),
                                            'result': origin.last_output}, indent=2), encoding='utf-8')
        pane.show_result('Report saved', 0, str(destination))

def main():
    app = QApplication(sys.argv)
    app.setApplicationName('PHANTOM')
    window = Phantom(); window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
