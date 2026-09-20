from .library import tokenize


def score(request, candidate):
    if request["asset_type"] != candidate.asset_type:
        return 0.0
    request_type = set(tokenize(request["request_type"].replace("_", " ")))
    query = set(tokenize(request["query"] or ""))
    available = set(candidate.tokens)
    type_match = len(request_type & available) / len(request_type) if request_type else 0
    query_match = len(query & available) / len(query) if query else 0
    tag_bonus = .05 if candidate.tags else 0
    return round(min(1.0, .5 + .3 * type_match + .15 * query_match + tag_bonus), 6)
