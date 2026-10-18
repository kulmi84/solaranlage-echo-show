"""Local desktop setup. Cloud changes only after the explicit setup button."""
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import installer


def cloud_setup(out, mapping, progress):
    """Provision a fresh relay; never reuse an existing installation directory."""
    out = Path(out).resolve()
    installer.validate_mapping(mapping)
    if out.exists():
        raise installer.SetupError('Dieser Ausgabeordner existiert bereits. Bitte einen neuen wählen.')
    npx = shutil.which('npx.cmd' if os.name == 'nt' else 'npx')
    if not npx:
        raise installer.SetupError('Node.js mit npm fehlt. Bitte Node.js LTS installieren und den Assistenten neu öffnen.')
    # A fresh random name prevents accidentally selecting the user's live worker.
    name = 'solaranlage-' + secrets.token_hex(8)
    stage = out.parent / ('.' + name)
    stage.mkdir(parents=True, exist_ok=False)
    config = stage / 'wrangler.jsonc'
    config.write_text(json.dumps({'name': name, 'compatibility_date': '2026-10-17'}), encoding='utf-8')

    def run(args, timeout=180):
        result = subprocess.run([npx, '--yes', 'wrangler@4', *args], cwd=str(stage),
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            # Raw vendor output can contain credentials; never expose it in the UI.
            raise installer.SetupError('Cloudflare-Schritt fehlgeschlagen: ' + args[0] +
                                       '. Konto/Berechtigungen und Internet prüfen. Teilressource: ' + name)
        return result.stdout

    progress('Cloudflare-Anmeldung im Browser bestätigen …')
    run(['login'], timeout=360)
    progress('Neue Datenbank erstellen …')
    output = run(['d1', 'create', name, '--config', str(config)])
    match = re.search(r'"database_id"\s*:\s*"([a-fA-F0-9-]{36})"', output)
    if not match:
        raise installer.SetupError('Datenbank-ID konnte nicht gelesen werden. Teilressource: ' + name)
    installer.generate(out, mapping, 'https://' + name + '.invalid/pv', name, match.group(1))
    # The generated config is the only target used after initial creation.
    config = out / 'relay/wrangler.jsonc'
    progress('Datenbankschema einrichten …')
    run(['d1', 'execute', name, '--remote', '--file', str(out / 'relay/schema.sql'), '--config', str(config)])
    progress('Zugriffsschlüssel und Worker bereitstellen …')
    output = run(['deploy', '--config', str(config)])
    match = re.search(r'https://' + re.escape(name) + r'\.[a-zA-Z0-9-]+\.workers\.dev\b', output)
    if not match:
        raise installer.SetupError('Relay-Adresse nicht gefunden. Dateien bleiben unter ' + str(out))
    run(['secret', 'bulk', str(out / 'relay/secrets.json'), '--config', str(config)])
    url = match.group(0) + '/pv'
    relay = out / 'alexa/relay_config.json'
    data = json.loads(relay.read_text(encoding='utf-8'))
    data['url'] = url
    relay.write_text(json.dumps(data, indent=2), encoding='utf-8')
    ha = out / 'home-assistant/secrets-ergaenzen.yaml'
    ha.write_text(ha.read_text(encoding='utf-8').replace('https://' + name + '.invalid/pv', url), encoding='utf-8')
    (out / 'NAECHSTE-SCHRITTE.md').write_text(
        '# Relay ist eingerichtet\n\n' +
        '1. home-assistant/pv_beta.yaml und gegebenenfalls pv_history.yaml in dein eingebundenes HA-Package-Verzeichnis kopieren.\n' +
        '2. secrets-ergaenzen.yaml an secrets.yaml anhängen; bestehende Einträge nicht ersetzen.\n' +
        '3. HA-Konfiguration prüfen und REST-Befehle sowie Automationen neu laden; beim erstmaligen Einbinden von Packages HA neu starten.\n' +
        '4. Beide neuen Automationen einmal ausführen. Im Assistenten Verbindung prüfen.\n' +
        '5. Neuen Custom-Skill (Deutsch, Alexa-hosted Python) bei Amazon anlegen.\n' +
        '6. alexa/interaction-model.de-DE.json importieren und bauen, APL aktivieren.\n' +
        '7. lambda_function.py und relay_config.json aus alexa/ im Alexa-Codeeditor unter lambda/ speichern und deployen.\n' +
        '8. Development aktivieren; „Alexa, öffne meine Solaranlage.“ testen.\n\n' +
        'Nur Package-Weg verwenden; der alternative Blueprint ist nicht zusätzlich nötig.\n' +
        'Dieser Ordner enthält Schlüssel und darf nicht veröffentlicht werden.\n', encoding='utf-8')
    progress('Relay bereit. Jetzt Home Assistant und Alexa nach der erzeugten Checkliste verbinden.')
    return out


def main():
    import tkinter as tk
    from tkinter import ttk, messagebox
    root = tk.Tk()
    root.title('Solaranlage – Einrichtung')
    root.geometry('900x840')
    root.minsize(760, 650)
    box = ttk.Frame(root, padding=16)
    box.pack(fill='both', expand=True)
    ttk.Label(box, text='1. Home Assistant verbinden', font=('', 14, 'bold')).pack(anchor='w')
    ttk.Label(box, text='Zugang wird nur zum Lesen verwendet. Bestehende Anlagen werden nicht geändert.').pack(anchor='w')
    url, token = tk.StringVar(), tk.StringVar()
    ttk.Entry(box, textvariable=url).pack(fill='x', pady=4)
    ttk.Label(box, text='HA-Adresse oben; persönlicher HA-Zugangstoken unten (wird nicht gespeichert):').pack(anchor='w')
    ttk.Entry(box, textvariable=token, show='•').pack(fill='x', pady=4)
    states = {}
    choices = {}
    status = tk.StringVar(value='HA verbinden oder Sensor-IDs direkt eingeben. Optionale Felder dürfen leer bleiben.')
    busy = [False]
    def progress(text):
        root.after(0, status.set, text)
    def task(work):
        if busy[0]:
            return
        busy[0] = True
        def worker():
            try:
                work()
            except installer.SetupError as error:
                progress(str(error))
            except Exception:
                progress('Schritt fehlgeschlagen. Netzwerk, Adresse und gültiges TLS-Zertifikat prüfen. Vorhandene Dateien bleiben erhalten.')
            finally:
                busy[0] = False
                root.after(0, token.set, '')
        threading.Thread(target=worker, daemon=True).start()
    def connect():
        address, credential = url.get().strip(), token.get()
        try:
            installer.endpoint(address)
        except installer.SetupError as error:
            messagebox.showerror('Adresse prüfen', str(error)); return
        if address.startswith('http:') and not messagebox.askyesno('HTTP im Heimnetz', 'Der HA-Token wird unverschlüsselt übertragen. Diese HTTP-Verbindung bewusst verwenden?'):
            return
        def work():
            found = installer.load_states(address, credential)
            def update():
                states.clear(); states.update(found)
                for key, _, original, kind in installer.SENSORS:
                    units = {'power': ('W', 'kW'), 'percent': ('%',), 'energy': ('Wh', 'kWh', 'MWh')}[kind]
                    entities = sorted(e for e, v in found.items() if e.startswith('sensor.') and v.get('attributes', {}).get('unit_of_measurement') in units)
                    choices[key]['values'] = [''] + entities
                    if original in entities:
                        choices[key].set(original)
                status.set('Verbunden. Sensoren auswählen; Vorschläge bitte prüfen.')
            root.after(0, update)
        task(work)
    ttk.Button(box, text='Sensoren laden', command=connect).pack(anchor='w', pady=4)
    ttk.Label(box, text='2. Sensoren auswählen', font=('', 14, 'bold')).pack(anchor='w', pady=(10, 4))
    ttk.Label(box, text='PV-Gesamtleistung enthält BKW. Energiezähler sind kumulierte kWh-Zähler, keine Tageshelfer.').pack(anchor='w')
    grid = ttk.Frame(box); grid.pack(fill='both', expand=True, pady=5)
    grid.columnconfigure(1, weight=1)
    for row, (key, label, _, _) in enumerate(installer.SENSORS):
        ttk.Label(grid, text=label + (' *' if key == 'power_w' else '')).grid(row=row, column=0, sticky='w', padx=(0, 12))
        control = ttk.Combobox(grid)
        control.grid(row=row, column=1, sticky='ew', pady=2)
        choices[key] = control
    ttk.Label(box, text='3. Neues Relay automatisch einrichten', font=('', 14, 'bold')).pack(anchor='w', pady=(8, 4))
    ttk.Label(box, text='Erstellt einen neuen Cloudflare-Worker und eine neue Datenbank in deinem Konto.\nKein kostenpflichtiger Tarif wird gebucht. Cloudflare-Nutzungsgrenzen gelten.').pack(anchor='w')
    target = tk.StringVar(value=str(installer.ROOT / '.private' / ('installation-' + secrets.token_hex(4))))
    ttk.Entry(box, textvariable=target).pack(fill='x', pady=5)
    def provision():
        mapping = {key: field.get().strip() for key, field in choices.items()}
        try:
            installer.validate_mapping(mapping)
            problems = installer.issues(mapping, states) if states else []
            errors = [text for level, text in problems if level == 'FEHLER']
            if errors:
                raise installer.SetupError('\n'.join(errors))
        except installer.SetupError as error:
            messagebox.showerror('Sensoren prüfen', str(error)); return
        if not messagebox.askyesno('Neue Cloudflare-Ressourcen', 'Jetzt ein neues Relay in deinem Cloudflare-Konto erstellen und die ausgewählten Sensorkonfigurationen lokal erzeugen? Bestehende Relay-Dienste werden nicht ausgewählt.'):
            return
        out = target.get().strip()
        task(lambda: cloud_setup(out, mapping, progress))
    ttk.Button(box, text='Neues Relay erstellen und Dateien erzeugen', command=provision).pack(anchor='w')
    def check():
        path = Path(target.get()) / 'alexa/relay_config.json'
        def work():
            from beta_live_reader import read_pv
            data = json.loads(path.read_text(encoding='utf-8'))
            value = read_pv(data['url'], data['read_token'])
            progress('Verbindung steht, Upload ist veraltet. HA-Automation prüfen.' if value['stale'] else 'Verbindung steht, aktuelle HA-Daten empfangen.')
        task(work)
    actions = ttk.Frame(box); actions.pack(fill='x', pady=8)
    ttk.Button(actions, text='Dateien und Checkliste öffnen', command=lambda: webbrowser.open(Path(target.get()).resolve().as_uri())).pack(side='left')
    ttk.Button(actions, text='Verbindung prüfen', command=check).pack(side='left', padx=10)
    ttk.Label(box, textvariable=status, wraplength=850).pack(anchor='w', pady=6)
    root.mainloop()


if __name__ == '__main__':
    main()
