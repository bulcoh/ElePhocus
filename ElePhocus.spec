# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['work_timer.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/hongsangkwon/Desktop/worktimer/License.txt', 'Contents/Resources')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='ElePhocus',
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
    icon=['app_icon.icns'],
)
app = BUNDLE(
    exe,
    name='ElePhocus.app',
    icon='app_icon.icns',
    bundle_identifier='com.redelephant.elephocus',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'CFBundleName': 'ElePhocus',
        'CFBundleDisplayName': 'ElePhocus',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 붉은코끼리. All rights reserved.\n무단 상업적 이용 금지.\n앱스토어 배포 금지.',
    },
)