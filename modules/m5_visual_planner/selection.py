def select(candidates, config):
    """Resolve density conflicts by score, then restore chronological order."""
    selected = []
    section_counts = {}
    ordered = sorted(candidates, key=lambda item: (-item.score, item.cut_start_us, item.passage_id))
    for candidate in ordered:
        if section_counts.get(candidate.section_id, 0) >= config.maximum_visuals_per_section:
            continue
        if any(not (candidate.cut_end_us + config.minimum_gap_us <= item.cut_start_us or
                    item.cut_end_us + config.minimum_gap_us <= candidate.cut_start_us)
               for item in selected):
            continue
        selected.append(candidate)
        section_counts[candidate.section_id] = section_counts.get(candidate.section_id, 0) + 1
    return sorted(selected, key=lambda item: (item.cut_start_us, item.passage_id))
