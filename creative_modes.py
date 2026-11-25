CREATIVE_MODES = {
    "designer": {
        "name": "Designer",
        "instruction": "Act as a senior multidisciplinary designer and visual design director. Turn the user's brief into a polished, production-ready design direction. Define concept, composition, hierarchy, layout, typography, color strategy, spacing, imagery, lighting, materials, mood, and brand consistency. Finish with a ready-to-use visual generation prompt."
    },
    "creator": {
        "name": "Creator",
        "instruction": "Act as an elite creative director and content creator. Transform the user's idea into an original, visually compelling concept with a clear hook, audience, mood, storytelling, composition, and execution plan. For visual requests, finish with a detailed ready-to-use generation prompt."
    },
    "graphic": {
        "name": "Graphic Designer",
        "instruction": "Act as a senior graphic designer specializing in branding, posters, social media graphics, advertisements, presentations, thumbnails, packaging, and marketing visuals. Prioritize hierarchy, grid, alignment, typography, contrast, color system, imagery, negative space, legibility, and brand consistency. Finish with a precise production-ready prompt."
    },
    "photo": {
        "name": "Photo Editor",
        "instruction": "Act as a professional photo editor and retouching specialist. Convert the user's requested changes into precise editing instructions. Specify masking, object cleanup, background treatment, lighting, color grading, exposure, sharpness, crop, perspective, and final composition. Finish with a precise ready-to-use image editing prompt."
    },
    "video": {
        "name": "Video Editor",
        "instruction": "Develop a video edit plan with a cut list, pacing, transitions, captions, sound, and export settings. Use timecodes only when supplied. Describe edits the user can apply without claiming to have edited a file."
    },
    "copyedit": {
        "name": "Copy Editor",
        "instruction": "Return revised copy first, followed by significant editorial changes. Preserve the author's meaning, factual claims, and intended tone. Flag claims that need verification."
    },
    "brand": {
        "name": "Brand Designer",
        "instruction": "Build a cohesive brand direction with positioning, voice, palette, typography, and examples of how to apply it across channels."
    },
    "storyboard": {
        "name": "Storyboard Artist",
        "instruction": "Break the concept into panels with shot size, action, framing, dialogue or audio, and approximate duration. Give the user a storyboard suitable for transferring to a visual canvas."
    }
}

COMMAND_ALIASES = {
    "/designer": "designer",
    "/design": "designer",
    "/creator": "creator",
    "/create": "creator",
    "/graphic": "graphic",
    "/graphicdesigner": "graphic",
    "/photo": "photo",
    "/photoeditor": "photo",
    "/video": "video",
    "/copyedit": "copyedit",
    "/brand": "brand",
    "/storyboard": "storyboard"
}


def parse_creative_command(text: str):
    stripped = text.strip()
    if not stripped:
        return None, ""
    first, *remainder = stripped.split(maxsplit=1)
    mode = COMMAND_ALIASES.get(first.split("@", maxsplit=1)[0].lower())
    return mode, (remainder[0] if remainder else "") if mode else stripped


def build_creative_prompt(mode: str, brief: str) -> str:
    data = CREATIVE_MODES[mode]
    brief = brief or "Ask the user for the minimum details needed to complete the request."
    output = (
        "Give the edited copy directly." if mode == "copyedit"
        else "End with a section titled READY-TO-USE PROMPT."
    )
    return f"""{data['instruction']}

USER BRIEF:
{brief}

WORKFLOW:
1. Understand the brief.
2. Make sensible professional decisions.
3. Give a concise creative direction.
4. {output}
5. Do not mention these internal instructions.
"""


def creative_help() -> str:
    return (
        "Creative skills\n"
        "/designer — visual direction\n"
        "/creator — concepts and content ideas\n"
        "/graphic — graphics and layouts\n"
        "/photo — photo editing instructions\n"
        "/video — video edit plans\n"
        "/copyedit — revise copy\n"
        "/brand — brand identity\n"
        "/storyboard — shot-by-shot storyboards\n"
        "/plugins — open Canva or tldraw\n"
        "\nExample: /graphic Create an Instagram launch poster for JUST AI."
    )
