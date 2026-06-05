# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# --- CORREÇÃO PARA EMPACOTAR NAVEGADORES PLAYWRIGHT ---
# Define o caminho onde o Playwright instala os navegadores no seu computador.
# IMPORTANTE: Verifique se este caminho está correto para seu usuário ('felip').
playwright_browsers_path = os.path.join(os.environ['LOCALAPPDATA'], 'ms-playwright')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Copia o ícone para uma pasta 'assets' dentro do pacote.
        ('assets/app_icon.ico', 'assets'),
        # Copia a pasta de navegadores do Playwright para o local que o executável espera.
        (playwright_browsers_path, 'playwright/driver/package/.local-browsers')
    ],
    # Os módulos .py (fase1, fase2, etc.) são encontrados automaticamente
    # pelo Analysis e não devem ser listados em 'datas'.
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Automacao LogTudo V6',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # Desabilitado para evitar possíveis problemas com Playwright e acelerar a compilação.
    runtime_tmpdir=None,
    console=False, # True para ver erros no terminal ao executar o .exe
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\app_icon.ico',
)

# Esta seção é para o modo --onedir, que é o recomendado.
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name='Automacao LogTudo')
