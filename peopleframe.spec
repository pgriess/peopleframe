# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = [
    ('/opt/homebrew/lib/libMagickWand-7.Q16HDRI.10.dylib', '.'),
    ('/opt/homebrew/lib/libMagickCore-7.Q16HDRI.10.dylib', '.'),
    ('/opt/homebrew/lib/libomp.dylib', '.'),
	('/opt/homebrew/lib/liblcms2.2.dylib', '.'),
	('/opt/homebrew/lib/liblqr-1.0.dylib', '.'),
	('/opt/homebrew/lib/libglib-2.0.0.dylib', '.'),
	('/opt/homebrew/lib/libintl.8.dylib', '.'),
	('/opt/homebrew/lib/libfontconfig.1.dylib', '.'),
	('/opt/homebrew/lib/libfreetype.6.dylib', '.'),
	('/opt/homebrew/lib/libltdl.7.dylib', '.'),
	('/opt/homebrew/lib/libpng16.16.dylib', '.'),
	('/opt/homebrew/lib/libpcre.1.dylib', '.'),
]
hiddenimports = []
tmp_ret = collect_all('osxphotos')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('photoscript')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


block_cipher = None


a = Analysis(['peopleframe/main.py'],
             pathex=[],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             hooksconfig={},
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
          [],
          name='peopleframe',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
