from pathlib import Path

from .config import AssetManagerConfig
from .contracts import load_inputs, validate
from .library import scan
from .output import write
from .probe import FFprobeMediaProbe
from .requests import collect_requests
from .resolution import resolve


def resolve_assets(visual_plan_path, sound_plan_path, music_plan_path,
                   asset_library_path, assets_manifest_path, config=None,
                   *, project_root_path=None, media_probe=None):
    config = config or AssetManagerConfig()
    inputs = [Path(item).resolve(strict=True) for item in
              (visual_plan_path, sound_plan_path, music_plan_path)]
    library_root = Path(asset_library_path).resolve(strict=True)
    if not library_root.is_dir():
        raise NotADirectoryError(f"Asset library is not a directory: {library_root}")
    project_root = (Path(project_root_path).resolve(strict=True) if project_root_path
                    else library_root.parent.resolve())
    output = Path(assets_manifest_path).absolute()
    if output in inputs or output == library_root:
        raise FileExistsError("Assets manifest must not overwrite an input")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Assets manifest exists: {output}")
    visual, sound, music, hashes = load_inputs(*inputs)
    requests = collect_requests(visual, sound, music)
    candidates, scan_issues = scan(library_root, config.recursive)
    decisions, assets, validation_issues = resolve(
        requests, candidates, project_root, config,
        media_probe or FFprobeMediaProbe(config.ffprobe_path))
    issues = scan_issues + validation_issues
    warnings = []
    if not candidates:
        warnings.append("EMPTY_LIBRARY")
    if any(item["status"] == "UNRESOLVED" for item in decisions):
        warnings.append("UNRESOLVED_REQUESTS")
    if issues:
        warnings.append("INVALID_LIBRARY_ASSETS")
    if any(item["path_kind"] == "ABSOLUTE" for item in assets):
        warnings.append("ABSOLUTE_ASSET_PATHS")
    source = {"visual_plan_path": str(inputs[0]), "visual_plan_sha256": hashes["visual_plan_sha256"],
              "sound_plan_path": str(inputs[1]), "sound_plan_sha256": hashes["sound_plan_sha256"],
              "music_plan_path": str(inputs[2]), "music_plan_sha256": hashes["music_plan_sha256"],
              "media_path": visual["source"]["media_path"], "media_sha256": visual["source"]["media_sha256"]}
    manifest = {"schema_version": "1.0.0", "module": {"id": "M6", "version": "1.0.0"},
                "stage": "asset_manager", "source": source,
                "library": {"root": str(library_root), "project_root": str(project_root),
                            "recursive": config.recursive},
                "policy": config.to_contract(), "requests": decisions, "assets": assets,
                "library_issues": issues,
                "summary": {"request_count": len(decisions),
                            "resolved_count": sum(item["status"] == "RESOLVED" for item in decisions),
                            "review_count": sum(item["status"] == "REVIEW" for item in decisions),
                            "unresolved_count": sum(item["status"] == "UNRESOLVED" for item in decisions),
                            "unique_asset_count": len(assets), "library_issue_count": len(issues)},
                "warnings": warnings}
    validate(manifest, "assets-manifest-1.0.0.json")
    write(output, manifest)
    return manifest
