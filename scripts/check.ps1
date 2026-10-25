[CmdletBinding()]
param(
    [string]$PythonPath = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'),
    [string]$NodePath = 'node'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) {
        throw 'Python fehlt. Siehe DEVELOPMENT.md zum Einrichten der .venv oder nutze -PythonPath.'
    }
    if (-not (Get-Command $NodePath -ErrorAction SilentlyContinue)) {
        throw 'Node.js fehlt. Installiere Node.js oder nutze -NodePath.'
    }
    & $PythonPath -c 'import yaml, jinja2, aiohttp, voluptuous'
    if ($LASTEXITCODE -ne 0) { throw 'Testabhaengigkeiten fehlen: python -m pip install -r requirements-test.txt' }

    & $PythonPath -m unittest discover -v
    if ($LASTEXITCODE -ne 0) { throw 'Python-Tests fehlgeschlagen.' }

    & $NodePath --test cloudflare/worker.test.mjs cloudflare/public-beta/worker.test.mjs cloudflare/display/sessions.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Worker-Tests fehlgeschlagen.' }

    & $PythonPath build_skill.py
    if ($LASTEXITCODE -ne 0) { throw 'Skill-Build fehlgeschlagen.' }
    Write-Host 'Alle Projektpruefungen erfolgreich.'
}
finally {
    Pop-Location
}
