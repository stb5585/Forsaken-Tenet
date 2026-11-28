"""PyInstaller onedir definition for the supported desktop distribution."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PyInstaller.utils.hooks import collect_data_files


repository_root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(repository_root))
from tools.export_runtime_art import stage_runtime_art

data_files = collect_data_files("src.core.data", include_py_files=False)
data_files.extend(
    collect_data_files(
        "src.ui_pygame.assets",
        include_py_files=False,
        excludes=["**/*review_sheet.png", "**/__pycache__/**"],
    )
)

runtime_art_stage = TemporaryDirectory(prefix="tenet-runtime-art-")
data_files = [
    (str(stage_runtime_art(Path(source), destination, Path(runtime_art_stage.name))), destination)
    for source, destination in data_files
]

analysis = Analysis(
    [str(repository_root / "game_pygame.py")],
    pathex=[str(repository_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "scipy"],
    noarchive=False,
)
python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="forsaken-tenet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="forsaken-tenet",
)

runtime_art_stage.cleanup()
