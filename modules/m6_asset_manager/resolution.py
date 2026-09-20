from .scoring import score
from .validation import asset_id, validate_candidate


STRONG_UPSTREAM = {"AUTO", "PROPOSED", "MUSIC"}


def portable_path(path, project_root):
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix(), "PROJECT_RELATIVE"
    except ValueError:
        return str(resolved), "ABSOLUTE"


def resolve(requests, candidates, project_root, config, probe):
    validations = {}
    issues = []
    asset_records = {}
    decisions = []
    for request in requests:
        ranked = sorted(((score(request, item), item) for item in candidates if item.asset_type == request["asset_type"]),
                        key=lambda pair: (-pair[0], pair[1].path.as_posix().casefold()))
        chosen = chosen_score = None
        for candidate_score, candidate in ranked:
            if candidate_score < config.review_score_threshold:
                break
            key = candidate.path.resolve()
            if key not in validations:
                try:
                    validations[key] = validate_candidate(candidate, probe)
                except (OSError, ValueError) as exc:
                    validations[key] = None
                    issues.append({"path": str(candidate.path), "reason": str(exc)})
            if validations[key] is not None:
                chosen, chosen_score = validations[key], candidate_score
                break
        decision = dict(request)
        decision.update({"asset_id": None, "match_score": 0.0, "status": "UNRESOLVED",
                         "reason": "No compatible validated local asset met the review threshold"})
        if chosen is not None:
            identifier = asset_id(chosen)
            status = ("RESOLVED" if chosen_score >= config.resolved_score_threshold and
                      request["upstream_status"] in STRONG_UPSTREAM else "REVIEW")
            decision.update({"asset_id": identifier, "match_score": chosen_score, "status": status,
                             "reason": "Best deterministic local-library match; file validated before assignment"})
            if identifier not in asset_records:
                path_text, path_kind = portable_path(chosen.path, project_root)
                asset_records[identifier] = {"asset_id": identifier, "asset_type": chosen.asset_type,
                                             "path": path_text, "path_kind": path_kind,
                                             "sha256": chosen.sha256, "size_bytes": chosen.size_bytes,
                                             "metadata": chosen.metadata, "request_ids": []}
            asset_records[identifier]["request_ids"].append(request["request_id"])
        decisions.append(decision)
    return decisions, sorted(asset_records.values(), key=lambda item: item["asset_id"]), issues
