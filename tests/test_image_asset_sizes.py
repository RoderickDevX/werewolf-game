from pathlib import Path
import re


STATIC_DIR = Path(__file__).resolve().parents[1] / "src" / "werewolf_langgraph" / "static"


def test_avatar_webp_assets_are_small_enough_for_mobile_lobby():
    avatar_dir = STATIC_DIR / "assets" / "avatars"
    max_avatar_bytes = 15 * 1024

    for avatar_path in avatar_dir.glob("*.webp"):
        assert avatar_path.stat().st_size <= max_avatar_bytes, avatar_path.name


def test_static_image_payload_stays_small_for_mobile_visits():
    asset_dir = STATIC_DIR / "assets"
    max_single_image_bytes = 100 * 1024
    max_total_image_bytes = 300 * 1024
    desktop_only_assets = {"game-desktop-village-background.webp"}
    image_paths = [
        image_path
        for image_path in sorted(asset_dir.glob("*.webp")) + sorted((asset_dir / "avatars").glob("*.webp"))
        if image_path.name not in desktop_only_assets
    ]

    for image_path in image_paths:
        assert image_path.stat().st_size <= max_single_image_bytes, image_path.name

    assert sum(image_path.stat().st_size for image_path in image_paths) <= max_total_image_bytes


def test_desktop_game_background_uses_fullscreen_layered_scene():
    styles = (STATIC_DIR / "styles.css").read_text()
    root_rules = re.search(r":root \{(?P<body>.*?)\n\}", styles, re.DOTALL)
    background_rules = re.search(r"\.game-background \{(?P<body>.*?)\n\}", styles, re.DOTALL)
    background_blur = re.search(r"\.game-background::before \{(?P<body>.*?)\n\}", styles, re.DOTALL)
    background_scene = re.search(r"\.game-background::after \{(?P<body>.*?)\n\}", styles, re.DOTALL)

    assert root_rules is not None
    assert background_rules is not None
    assert background_blur is not None
    assert background_scene is not None

    root_body = root_rules.group("body")
    assert '--room-bg-image: url("/static/assets/game-desktop-village-background.webp");' in root_body
    assert "--bg-scale:" in root_body
    assert "--bg-position-x:" in root_body
    assert "--bg-position-y:" in root_body

    layer_rules = background_rules.group("body")
    assert "position: fixed;" in layer_rules
    assert "inset: 0;" in layer_rules
    assert "width: 100vw;" in layer_rules
    assert "height: 100vh;" in layer_rules
    assert "z-index: 0;" in layer_rules
    assert "pointer-events: none;" in layer_rules

    blur_rules = background_blur.group("body")
    assert "background-size: cover;" in blur_rules
    assert "filter: blur(14px) brightness(0.95) saturate(1.12);" in blur_rules
    assert "opacity: 0.25;" in blur_rules

    scene_rules = background_scene.group("body")
    assert "var(--room-bg-image)" in scene_rules
    assert "var(--bg-scene-size)" in scene_rules
    assert "transform:" not in scene_rules
    assert "var(--bg-position-x, 50%) var(--bg-position-y, 52%)" in scene_rules
    assert "rgba(0, 0, 0, 0.06) 65%" in scene_rules
    assert "rgba(0, 0, 0, 0.18) 100%" in scene_rules

    content_rules = re.search(r"\.game-content \{(?P<body>.*?)\n\}", styles, re.DOTALL)
    assert content_rules is not None
    assert "z-index: 1;" in content_rules.group("body")

    mobile_background = re.search(
        r"@media \(max-width: 680px\).*?\.game-screen \{(?P<body>.*?)\n  \}",
        styles,
        re.DOTALL,
    )
    assert mobile_background is not None
    mobile_rules = mobile_background.group("body")
    assert '--room-bg-image: url("/static/assets/game-mobile-character-background.webp");' in mobile_rules
    assert "--bg-scene-size: auto 100lvh;" in mobile_rules


def test_desktop_room_panels_stay_translucent_enough_to_show_background():
    styles = (STATIC_DIR / "styles.css").read_text()
    root_rules = re.search(r":root \{(?P<body>.*?)\n\}", styles, re.DOTALL)

    assert root_rules is not None

    root_body = root_rules.group("body")
    assert "--panel-bg: rgba(7, 12, 30, 0.28);" in root_body
    assert "--panel-bg-strong: rgba(7, 12, 30, 0.28);" in root_body
    assert "--panel-bg-soft: rgba(7, 12, 30, 0.28);" in root_body
    assert "--card-bg: rgba(255, 255, 255, 0.045);" in root_body
    assert "--card-bg-hover: rgba(255, 255, 255, 0.065);" in root_body
    assert "backdrop-filter: none;" in styles
    assert "-webkit-backdrop-filter: none;" in styles
