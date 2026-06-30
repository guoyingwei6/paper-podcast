import os
import tempfile
import unittest
from unittest.mock import patch

from main import publish


class PublishTests(unittest.TestCase):
    def test_publish_stops_when_git_add_fails(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3") as audio:
            audio.write(b"fake audio")
            audio.flush()

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["gh", "release", "create"]:
                    return type("Result", (), {"returncode": 0, "stderr": ""})()
                if cmd[:2] == ["git", "add"]:
                    return type("Result", (), {"returncode": 1, "stderr": "add failed"})()
                return type("Result", (), {"returncode": 0, "stderr": ""})()

            with patch("main.update_feed", return_value=os.devnull), patch("main.subprocess.run", side_effect=fake_run):
                ok = publish("2026-06-30", audio.name, [], "")

        self.assertFalse(ok)
        self.assertNotIn(["git", "push"], calls)


if __name__ == "__main__":
    unittest.main()
