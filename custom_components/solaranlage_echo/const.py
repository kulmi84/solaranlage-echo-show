"""Configuration and the small, explicit data allowlist."""
DOMAIN = "solaranlage_echo"
DEFAULT_RELAY = "https://solaranlage-kontodienst.kulmi84.workers.dev"
LEGACY_RELAY = "https://solaranlage-public-beta.kulmi84.workers.dev"
FIELDS = {
    "power_w": ("Gesamte Solarleistung (Pflicht)", "power"),
    "pv_dc_w": ("PV-Anlage einzeln (optional)", "power"),
    "bkw_w": ("Balkonkraftwerk einzeln (optional)", "power"),
    "home_w": ("Hausverbrauch", "power"),
    "grid_import_w": ("Netzbezug", "power"),
    "grid_export_w": ("Einspeisung", "power"),
    "battery_soc": ("Akkustand", "percent"),
    "battery_charge_w": ("Akku-Ladeleistung", "power"),
    "battery_discharge_w": ("Akku-Entladeleistung", "power"),
    "energy_pv": ("PV-Energie ohne BKW", "energy"),
    "energy_bkw": ("BKW-Energie", "energy"),
    "energy_import": ("Netzbezugsenergie", "energy"),
    "energy_export": ("Einspeiseenergie", "energy"),
    "energy_charge": ("Akku-Ladeenergie", "energy"),
    "energy_discharge": ("Akku-Entladeenergie", "energy"),
}
ENERGY_KEYS = tuple(key for key, (_, kind) in FIELDS.items() if kind == "energy")
