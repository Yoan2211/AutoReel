from .classification import classify


KIND_PRIORITY = {"VISUAL_APPEARANCE": 6, "HOOK": 5, "STRONG_PHRASE": 4,
                 "CONCEPT_EMPHASIS": 4, "TRANSITION": 3, "SECTION_CHANGE": 2, "ZOOM": 1}


def resolve(events, config):
    classified = [classify(item) for item in events]
    winners = set()
    conflict_losers = {}
    groups = []
    for item in classified:
        if not groups or item.event.cut_time_us - groups[-1][-1].event.cut_time_us > config.conflict_window_us:
            groups.append([item])
        else:
            groups[-1].append(item)
    for group in groups:
        winner = max(group, key=lambda item: (item.event.score, KIND_PRIORITY[item.event.kind], -item.event.cut_time_us, item.event.id))
        winners.add(winner.event.id)
        for item in group:
            if item.event.id != winner.event.id:
                conflict_losers[item.event.id] = winner.event.id
    kept = []
    density_losers = set()
    for item in sorted((item for item in classified if item.event.id in winners),
                       key=lambda item: (-item.event.score, -KIND_PRIORITY[item.event.kind], item.event.cut_time_us, item.event.id)):
        too_close = any(abs(item.event.cut_time_us - other.event.cut_time_us) < config.minimum_gap_us for other in kept)
        in_window = sum(abs(item.event.cut_time_us - other.event.cut_time_us) < config.density_window_us for other in kept)
        if too_close or in_window >= config.maximum_sfx_per_window:
            density_losers.add(item.event.id)
        else:
            kept.append(item)
    kept_ids = {item.event.id for item in kept}
    return classified, kept_ids, conflict_losers, density_losers
