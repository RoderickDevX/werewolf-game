import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


class PackageStaticAssetsTest(unittest.TestCase):
    def test_wheel_includes_frontend_static_assets(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as output_dir:
            source_dir = Path(output_dir) / "project"
            source_dir.mkdir()
            for filename in ("pyproject.toml", "setup.py", "README.md", "requirements.txt"):
                shutil.copy2(project_root / filename, source_dir / filename)
            shutil.copytree(project_root / "src", source_dir / "src")

            wheel_dir = Path(output_dir) / "wheels"
            wheel_dir.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    ".",
                    "--no-build-isolation",
                    "--no-deps",
                    "-w",
                    str(wheel_dir),
                ],
                cwd=source_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            wheels = list(wheel_dir.glob("*.whl"))
            self.assertEqual(len(wheels), 1)

            with zipfile.ZipFile(wheels[0]) as wheel:
                names = set(wheel.namelist())

        expected_assets = {
            "werewolf_langgraph/static/index.html",
            "werewolf_langgraph/static/home.html",
            "werewolf_langgraph/static/styles.css",
            "werewolf_langgraph/static/home.css",
            "werewolf_langgraph/static/app.js",
            "werewolf_langgraph/static/assets/uploaded-opening-poster.webp",
            "werewolf_langgraph/static/assets/game-cartoon-background.webp",
            "werewolf_langgraph/static/assets/game-mobile-character-background.webp",
            "werewolf_langgraph/static/assets/avatars/human.webp",
            "werewolf_langgraph/static/assets/avatars/garfield.webp",
        }
        self.assertTrue(expected_assets.issubset(names), sorted(expected_assets - names))


if __name__ == "__main__":
    unittest.main()
