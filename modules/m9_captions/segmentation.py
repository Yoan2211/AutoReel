import re


STRONG_END = re.compile(r"[.!?;:]\s*$")
SMALL_WORD = re.compile(r"^[\W_]*(?:à|a|de|du|le|la|les|un|une|et|ou|en|y)[\W_]*$", re.IGNORECASE)


def _should_break(group, current, following, config):
    if len(group) >= config.maximum_words:
        return True
    if STRONG_END.search(current.text):
        return True
    if following is not None and following.timeline_start_us - current.timeline_end_us >= config.pause_break_us:
        return True
    return len(group) >= config.target_words


def segment(words, config):
    groups, current = [], []
    for index, word in enumerate(words):
        candidate_text = "".join(item.text for item in current + [word]).strip()
        if current and len(candidate_text) > config.maximum_lines * config.maximum_characters_per_line:
            groups.append(current); current = []
        if len(word.text.strip()) > config.maximum_lines * config.maximum_characters_per_line:
            raise ValueError("A spoken token cannot fit within the configured caption lines")
        current.append(word)
        following = words[index + 1] if index + 1 < len(words) else None
        if following is None or _should_break(current, word, following, config):
            groups.append(current); current = []
    index = 0
    while index < len(groups):
        group = groups[index]
        if len(group) == 1 and SMALL_WORD.match(group[0].text.strip()):
            if index + 1 < len(groups) and len(groups[index + 1]) < config.maximum_words:
                groups[index + 1] = group + groups[index + 1]; groups.pop(index); continue
            if index > 0 and len(groups[index - 1]) < config.maximum_words:
                groups[index - 1].extend(group); groups.pop(index); continue
        index += 1
    return groups


def text_and_lines(words, maximum_characters):
    text = "".join(item.text for item in words).strip()
    if len(text) <= maximum_characters or len(words) == 1:
        return text, [text]
    best = None
    for split in range(1, len(words)):
        left = "".join(item.text for item in words[:split]).strip()
        right = "".join(item.text for item in words[split:]).strip()
        if len(left) > maximum_characters or len(right) > maximum_characters:
            continue
        score = (max(len(left), len(right)), abs(len(left) - len(right)))
        if best is None or score < best[0]:
            best = score, [left, right]
    if best is not None:
        return text, best[1]
    if len(text) <= 2 * maximum_characters:
        return text, [text[:maximum_characters], text[maximum_characters:]]
    raise ValueError("Caption text cannot fit within two configured lines")
