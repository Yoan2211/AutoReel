from core.timeline import source_to_cut_us

from .model import Event


def collect(edit, visual, camera, time_map, config):
    mappings = time_map["mappings"]
    events = []

    def add(kind, source_us, score, context, origin_ids):
        cut_us = source_to_cut_us(source_us, mappings)
        if cut_us is not None:
            events.append(Event(f"candidate{len(events):06d}", kind, source_us, cut_us,
                                round(score, 6), context, tuple(origin_ids)))

    passages = {item["id"]: item for item in edit["passages"]}
    role_by_passage = {}
    for role in edit["roles"]:
        role_by_passage.setdefault(role["passage_id"], set()).add(role["role"])
        if role["role"] == "HOOK" and role["passage_id"] in passages:
            passage = passages[role["passage_id"]]
            add("HOOK", passage["source_start_us"], .86, passage["text"], [passage["id"]])
    for passage in edit["passages"]:
        if passage["strength"] >= config.strong_passage_threshold and "HOOK" not in role_by_passage.get(passage["id"], set()):
            add("STRONG_PHRASE", passage["source_start_us"], .7, passage["text"], [passage["id"]])
    for section in edit["sections"][1:]:
        add("SECTION_CHANGE", section["source_start_us"], .68, section["title"], [section["id"]])
    for request in visual["requests"]:
        if request["disposition"] != "NONE" and request["cut_start_us"] is not None:
            base = .9 if request["priority"] == "HIGH" else .82 if request["priority"] == "MEDIUM" else .65
            roles = role_by_passage.get(request["passage_id"], set())
            context = f"{request['media_type'].casefold()} {'cta' if 'CTA' in roles else ''} {request['concept']}"
            add("VISUAL_APPEARANCE", request["source_start_us"], base, context, [request["id"]])
            if request["priority"] == "HIGH":
                add("CONCEPT_EMPHASIS", request["source_start_us"], .76,
                    f"important concept {request['concept']}", [request["id"]])
    previous_zoom = 1.0
    for shot in camera["shots"]:
        for keyframe in shot["keyframes"]:
            delta = abs(keyframe["zoom"] - previous_zoom)
            if delta >= config.zoom_delta_threshold:
                add("ZOOM", keyframe["source_us"], min(.75, .6 + delta), f"zoom delta {delta:.3f}", [shot["id"]])
            previous_zoom = keyframe["zoom"]
    for mapping in mappings[1:]:
        add("TRANSITION", mapping["source"]["start_us"], .66, "SOURCE discontinuity retained in CUT", [mapping["id"]])
    return sorted(events, key=lambda item: (item.cut_time_us, item.id))
