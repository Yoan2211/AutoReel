def decide(transcript, output_duration_us, mood_confidence, config):
    if transcript["status"] == "no_speech_recognized" or output_duration_us == 0:
        return "NONE", "LOW", "No recognized voice-led program to support with music"
    if output_duration_us < config.minimum_music_duration_us:
        return "NONE", "HIGH", "Program is too short; music would add clutter without settling"
    if output_duration_us < config.proposal_duration_us or mood_confidence == "LOW":
        return "REVIEW", "MEDIUM", "Music may help, but duration or thematic intent is ambiguous"
    return "MUSIC", "HIGH", "A stable low-level music bed can support rhythm without following micro-events"
