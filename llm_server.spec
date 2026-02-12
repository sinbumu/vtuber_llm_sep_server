# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
from PyInstaller.utils.hooks import collect_submodules


hiddenimports = (
    collect_submodules("open_llm_vtuber")
    + collect_submodules("llm_server")
    + ["llm_server.app"]
)

datas = []
if os.path.exists("conf.yaml"):
    datas.append(("conf.yaml", "."))
if os.path.exists("mcp_servers.json"):
    datas.append(("mcp_servers.json", "."))
if os.path.isdir("prompts"):
    datas.append(("prompts/utils", "prompts/utils"))
    if os.path.isdir("prompts/persona"):
        datas.append(("prompts/persona", "prompts/persona"))

analysis = Analysis(
    ["run_llm_server.py"],
    pathex=[".", "src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="llm_server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="llm_server",
)
