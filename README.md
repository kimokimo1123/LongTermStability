# LongTermStability Switching Controller

Dieses Projekt liefert ein minimales aber vollständiges Python-Toolkit, um einen HP 3488A Multiplexer
(u.a. mit dem 44470A Karten-Einsatz) über einen ICS 9065 LAN/GPIB-Controller zu steuern und anschließend
Messungen mit einem Fluke 8588 Multimeter (ebenfalls via LAN) zu erfassen.

## Features
- Komfortable YAML-Konfiguration für IP-Adressen, GPIB-Adressen und Messkanäle
- Kontextmanager für den pyvisa-ResourceManager inklusive Timeout- und Terminierungs-Einstellungen
- High-Level-Klasse `HP3488A`, die Slot-/Kanal-Operationen wie `open_channel`, `close_all` oder `scan`
  kapselt
- Helper-Klasse `Fluke8588Dmm`, die Standardbefehle (`*IDN?`, `READ?`, `MEAS:VOLT:DC?` usw.) bereitstellt
- Einfacher CLI-Einstieg (`longtermstability ...`) mit Subkommandos zum Identifizieren der Geräte,
  Durchschalten definierter Kanäle und Auslösen einer Mess-Serie

## Installation
1. Python 3.11+ installieren
2. Virtuelle Umgebung aufsetzen und Abhängigkeiten installieren

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Konfiguration
Erstelle eine Datei `config.yaml` auf Basis der bereitgestellten `config.example.yaml`:

```yaml
resource_manager: "@py"  # pyvisa Backend
ics:
  host: 172.16.8.107
  gpib_board: 0
  gpib_address: 26
multiplexer:
  cards:
    - name: voltage_output  # Modul 1: 4 Kanäle, Ausgangsspannung
      slot: 1
      channels: [1, 2, 3, 4]
    - name: thermistors     # Modul 2: 8 Kanäle, 10 kOhm NTCs
      slot: 2
      channels: [1, 2, 3, 4, 5, 6, 7, 8]
dmm:
  resource: "TCPIP::172.16.8.106::inst0::INSTR"
  function: "MEAS:VOLT:DC?"
```

Im Beispiel oben wird außerdem davon ausgegangen, dass dein Steuer-Laptop unter
`172.16.8.108` erreichbar ist und gemeinsam mit ICS 9065 (`172.16.8.107`) und
Fluke 8588 (`172.16.8.106`) im selben Subnetz liegt.

Die `cards[].channels` Einträge werden vom CLI für den Befehl `scan` genutzt.

Passe die Kanal-Listen an, sobald du die endgültige Zuordnung der einzelnen Relais festgelegt hast.

## CLI verwenden

```bash
longtermstability id
longtermstability select --slot 1 --channel 5
longtermstability scan temp
longtermstability measure temp --samples 5
```

Jedes Subkommando druckt aussagekräftige Logs auf STDOUT und kann über `--config` auf eine
alternative YAML-Konfigurationsdatei verweisen.

## Tests pro Messaufbau

Für jeden Messaufbau kannst du ein eigenes Python-File in `tests/` ablegen. Als Vorlage dient
`tests/channel_sweep_test.py`. Das Skript liest deine `config.yaml`, schaltet nacheinander alle in
`multiplexer.cards` definierten Kanäle und liest – sofern ein DMM konfiguriert ist – direkt den Messwert aus.

```bash
python tests/channel_sweep_test.py --card voltage_output
python tests/channel_sweep_test.py --card thermistors --samples 3 --settle-ms 200 \
    --test-name "thermistor_burn_in"
```

Lässt du den `--card` Parameter weg, werden standardmäßig beide oben beschriebenen Module getestet.
Für jede Ausführung erzeugt das Skript außerdem automatisch eine CSV-Datei auf deinem Desktop
(oder in dem via `--output-dir` gesetzten Ordner). Jede Zeile enthält Datum, Uhrzeit, den vergebenen
Testnamen und den Messwert für einen Kanal/Sample. So hast du pro Testlauf eine separate Datei,
die sich leicht archivieren oder weiterverarbeiten lässt.

## Sicherheitshinweise
- Der Code sendet keine automatischen Trigger an das Multimeter. Verwende ggf. `INIT`/`TRIG`
  SCPI-Kommandos, falls dein Aufbau dies benötigt.
- Stelle sicher, dass nur ein Programm gleichzeitig auf den HP 3488A zugreift.
- Passe Timeouts und Terminierungs-Zeichen in der Konfiguration an deine Instrumente an.
