from creative_modes import build_creative_prompt, parse_creative_command


def test_parse_creative_commands():
    assert parse_creative_command("/designer modern landing page") == ("designer", "modern landing page")
    assert parse_creative_command("/graphic Instagram poster") == ("graphic", "Instagram poster")
    assert parse_creative_command("/photo remove the background") == ("photo", "remove the background")
    assert parse_creative_command("hello") == (None, "hello")


def test_build_creative_prompt_contains_brief_and_output_instruction():
    prompt = build_creative_prompt("creator", "Create a launch visual for JUST AI")
    assert "Create a launch visual for JUST AI" in prompt
    assert "READY-TO-USE PROMPT" in prompt


def test_creative_commands_support_telegram_suffix_and_multiline_briefs():
    assert parse_creative_command("/video@JustAIBot\nEdit this interview") == (
        "video", "Edit this interview"
    )
    assert parse_creative_command("/copyedit Tighten this heading") == (
        "copyedit", "Tighten this heading"
    )
