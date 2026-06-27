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
    image_paths = sorted(asset_dir.glob("*.webp")) + sorted((asset_dir / "avatars").glob("*.webp"))

    for image_path in image_paths:
        assert image_path.stat().st_size <= max_single_image_bytes, image_path.name

    assert sum(image_path.stat().st_size for image_path in image_paths) <= max_total_image_bytes


def test_desktop_game_background_covers_wide_viewports_without_mobile_strip():
    styles = (STATIC_DIR / "styles.css").read_text()
    desktop_background = re.search(r"\.game-screen::before \{(?P<body>.*?)\n\}", styles, re.DOTALL)
    assert desktop_background is not None

    desktop_rules = desktop_background.group("body")
    assert "background-size: cover;" in desktop_rules
    assert "background-position: center 34%;" in desktop_rules
    assert "background-repeat: no-repeat;" in desktop_rules

    mobile_background = re.search(
        r"@media \(max-width: 680px\).*?\.game-screen::before \{(?P<body>.*?)\n  \}",
        styles,
        re.DOTALL,
    )
    assert mobile_background is not None
    assert "background-size: auto 100lvh;" in mobile_background.group("body")
