# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('db', 'db'), ('assets', 'assets'), ('services', 'services')]
binaries = []
hiddenimports=[
    'services.auto_topic',
    'services.auto_report',
    'services.auto_report_topic',
    'services.ai_helper2',
    'pandas',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.skiplist',
    'google.genai'
]
excludes=[
    'matplotlib',
    'scipy',
    'IPython',
    'jupyter',
    'pytest',
]
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Digivla_Analyst_Tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.png'],
)
