from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "src" / "werewolf_langgraph" / "static"


def test_avatar_webp_assets_are_small_enough_for_mobile_lobby():
    avatar_dir = STATIC_DIR / "assets" / "avatars"
    max_avatar_bytes = 15 * 1024

    for avatar_path in avatar_dir.glob("*.webp"):
        assert avatar_path.stat().st_size <= max_avatar_bytes, avatar_path.name
