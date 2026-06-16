# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for BrainSquared Mac app binary."""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Collect dynamic-import-heavy packages in full
fastapi_datas, fastapi_binaries, fastapi_hiddenimports = collect_all('fastapi')
uvicorn_datas, uvicorn_binaries, uvicorn_hiddenimports = collect_all('uvicorn')
anyio_datas, anyio_binaries, anyio_hiddenimports = collect_all('anyio')
starlette_datas, starlette_binaries, starlette_hiddenimports = collect_all('starlette')
anthropic_datas, anthropic_binaries, anthropic_hiddenimports = collect_all('anthropic')
httpx_datas, httpx_binaries, httpx_hiddenimports = collect_all('httpx')

all_datas = (
    fastapi_datas + uvicorn_datas + anyio_datas + starlette_datas +
    anthropic_datas + httpx_datas +
    [
        ('brain/web', 'brain/web'),
        ('brain/templates', 'brain/templates'),
        ('brainsquared-favicon.ico', '.'),
        ('credentials.json', '.'),
        # Root-level legacy modules loaded dynamically by brain.integration_context
        # (_load_legacy_module). Without these, daily-note integration data is empty.
        ('config.py', '.'),
        ('gmail_client.py', '.'),
        ('calendar_client.py', '.'),
        ('notion_client.py', '.'),
        ('news_client.py', '.'),
    ]
)

all_binaries = fastapi_binaries + uvicorn_binaries + anyio_binaries + starlette_binaries + anthropic_binaries + httpx_binaries

all_hiddenimports = (
    fastapi_hiddenimports + uvicorn_hiddenimports + anyio_hiddenimports +
    starlette_hiddenimports + anthropic_hiddenimports + httpx_hiddenimports +
    collect_submodules('brain') +
    [
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        'h11',
        'yaml',
        'dotenv',
        'feedparser',
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.oauth2',
        'google.oauth2.credentials',
        'google_auth_oauthlib',
        'google_auth_oauthlib.flow',
        'googleapiclient',
        'googleapiclient.discovery',
        'requests',
    ]
)

a = Analysis(
    ['brain/app_entry.py'],
    pathex=['.'],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'PIL', 'wx', 'PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BrainServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BrainServer',
)
