from .model import ClassifiedEvent


GAINS = {"SOFT_IMPACT": -24.0, "POP": -25.0, "CLICK": -27.0, "WHOOSH": -23.0,
         "SWOOSH": -24.0, "RISER": -25.0, "ACCENT": -24.0}


def classify(event):
    if event.kind == "VISUAL_APPEARANCE":
        sound = "CLICK" if "cta" in event.context else "POP" if "icon_graphic" in event.context else "WHOOSH"
        reason = "Subtle cue for the selected visual appearance"
    elif event.kind == "HOOK":
        sound, reason = "SOFT_IMPACT", "Restrained impact supporting the opening hook"
    elif event.kind == "STRONG_PHRASE":
        sound, reason = "ACCENT", "Light accent for an unusually strong spoken passage"
    elif event.kind == "SECTION_CHANGE":
        sound, reason = "SOFT_IMPACT", "Optional cue for a SmartEdit topic change"
    elif event.kind == "ZOOM":
        sound, reason = "SWOOSH", "Optional soft motion cue for a punctual camera zoom"
    elif event.kind == "TRANSITION":
        sound, reason = "WHOOSH", "Optional cue at a retained-source discontinuity"
    else:
        sound, reason = "ACCENT", "Optional emphasis for an important concept"
    return ClassifiedEvent(event, sound, GAINS[sound], reason)
