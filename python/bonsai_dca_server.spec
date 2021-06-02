# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['app.py'],
             pathex=['/Users/kdmukai/dev/bonsai_dca/python'],
             binaries=[],
             datas=[
                ('_templates', '_templates'),
                ('blueprints/credentials/_templates', 'blueprints/credentials/_templates'),
                ('blueprints/orders/_templates', 'blueprints/orders/_templates'),
                ('_static', '_static')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [('u', None, 'OPTION'), ],
          name='bonsai_dca_server',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
