"""Python-stdlib core for the self-contained Windows GUI patcher."""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

PATCH_DIR = Path(__file__).resolve().parent
TOOLS_DIR = PATCH_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(PATCH_DIR) not in sys.path:
    sys.path.insert(0, str(PATCH_DIR))

import apply_patch as engine


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _stage(directory, filename, data):
    fd, temp_name = tempfile.mkstemp(prefix="." + filename + ".", suffix=".tmp", dir=directory)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            temp.unlink()
        except OSError:
            pass
        raise
    return temp


def install(game_dir, patch_dir=None):
    root = Path(game_dir).expanduser().resolve()
    assets = Path(patch_dir or PATCH_DIR).resolve()
    manifest_path = assets / "patch.json"
    atlas_source = assets / "assets" / engine.ATLAS
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    engine.need(manifest.get("format") == "momo1-151-zh-source-patch-v1", "补丁清单格式不受支持。")
    engine.need(manifest.get("source_sha256") == engine.ORIGINAL, "补丁清单与支持的游戏版本不匹配。")

    original_path = root / "momo1_v151.exe"
    engine.need(original_path.is_file(), "所选文件夹中找不到 momo1_v151.exe，请选择游戏根目录。")
    original = original_path.read_bytes()
    engine.need(_hash(original) == engine.ORIGINAL,
                "游戏版本或文件已修改；未写入任何文件。请确认这是官方 Momodora 1.51 原版。")

    atlas_bytes = atlas_source.read_bytes()
    engine.need(_hash(atlas_bytes) == manifest.get("atlas_sha256"), "中文图集校验失败。请重新下载完整补丁。")
    target_exe = root / engine.OUTPUT
    graphic_dir = root / "data" / "graphic"
    engine.need(graphic_dir.is_dir(), "缺少 data\\graphic 目录；请选择完整的游戏目录。")
    target_atlas = graphic_dir / engine.ATLAS
    receipt_path = graphic_dir / "momo1_zh_install.json"

    expected_exe = manifest["target_sha256"]
    collisions = [(target_exe, expected_exe), (target_atlas, manifest["atlas_sha256"])]
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        engine.need(receipt.get("patch_format") == manifest["format"] and
                    receipt.get("exe_sha256") == manifest["target_sha256"] and
                    receipt.get("atlas_sha256") == manifest["atlas_sha256"],
                    "存在不属于本补丁版本的安装记录；未更改文件。")
        for path, expected in collisions:
            engine.need(path.is_file(),
                        "安装记录存在但汉化文件缺失：" + path.name + "。请先卸载残缺补丁，再重新安装。")
            engine.need(_hash(path.read_bytes()) == expected,
                        "现有汉化文件已被更改；为保护文件，未覆盖。请手动检查。")
        return {"result": "already-installed", "game_dir": str(root), "exe": str(target_exe)}

    for path, expected in collisions:
        if path.exists():
            engine.need(_hash(path.read_bytes()) == expected,
                        "发现未知的同名文件：" + path.name + "。为避免覆盖，已停止。")
            engine.need(False, "检测到无安装记录的现有补丁文件；请先核实并手动移走。")
    engine.need(not receipt_path.exists(), "发现未知安装记录；已停止。")

    patched, plain_hash = engine.make_patched(original, manifest)
    engine.need(_hash(patched) == expected_exe,
                "补丁输出与已验证校验值不一致；未写入任何文件。")
    engine.need(_hash(original_path.read_bytes()) == engine.ORIGINAL,
                "原版文件在处理中发生变化；已停止。")

    receipt = {
        "patch_format": manifest["format"],
        "version": manifest["version"],
        "exe_sha256": _hash(patched),
        "atlas_sha256": _hash(atlas_bytes),
    }
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    staged = []
    installed = []
    try:
        staged.append((_stage(root, target_exe.name, patched), target_exe))
        staged.append((_stage(graphic_dir, target_atlas.name, atlas_bytes), target_atlas))
        staged.append((_stage(graphic_dir, receipt_path.name, receipt_bytes), receipt_path))
        for temp, destination in staged:
            # os.rename fails rather than replacing an existing file on Windows.
            os.rename(temp, destination)
            installed.append(destination)
    except Exception:
        for temp, _ in staged:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        for destination in reversed(installed):
            try:
                destination.unlink()
            except OSError:
                pass
        raise
    return {
        "result": "installed",
        "game_dir": str(root),
        "exe": str(target_exe),
        "exe_sha256": _hash(patched),
        "decoded_payload_sha256": plain_hash,
    }


def remove(game_dir, patch_dir=None):
    root = Path(game_dir).expanduser().resolve()
    assets = Path(patch_dir or PATCH_DIR).resolve()
    manifest = json.loads((assets / "patch.json").read_text(encoding="utf-8"))
    graphic_dir = root / "data" / "graphic"
    paths = [root / engine.OUTPUT, graphic_dir / engine.ATLAS,
             graphic_dir / "momo1_zh_install.json"]
    receipt_path = paths[-1]
    engine.need(receipt_path.is_file(), "找不到汉化安装记录，没有可安全卸载的补丁。")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    engine.need(receipt.get("patch_format") == manifest["format"] and
                receipt.get("exe_sha256") == manifest["target_sha256"] and
                receipt.get("atlas_sha256") == manifest["atlas_sha256"],
                "安装记录不匹配；未删除任何文件。")
    for path, key in ((paths[0], "exe_sha256"), (paths[1], "atlas_sha256")):
        if path.exists():
            engine.need(_hash(path.read_bytes()) == receipt.get(key),
                        "检测到已修改的文件：" + path.name + "。为保护文件，未删除。")
    removed = []
    for path in paths:
        if path.exists():
            path.unlink()
            removed.append(path.name)
    return {"result": "removed", "removed": removed, "original_preserved": True}
