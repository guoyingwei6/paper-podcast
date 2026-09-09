import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from feed_generator import _add_item, _get_episode_description, _get_mp3_duration


class EpisodeDescriptionTests(unittest.TestCase):
    def test_includes_doi_link_and_chinese_title(self):
        articles = [
            {
                "title": "Heat stress adaptation in Ethiopian zebu cattle",
                "title_zh": "埃塞俄比亚瘤牛热应激适应研究",
                "journal": "PLOS One",
                "published": "2026-09-03",
                "doi": "10.1371/journal.pone.1234567",
            }
        ]

        description = _get_episode_description(articles)

        self.assertIn("PLOS One, 2026-09-03", description)
        self.assertIn("Heat stress adaptation in Ethiopian zebu cattle", description)
        self.assertIn("埃塞俄比亚瘤牛热应激适应研究", description)
        self.assertIn("https://doi.org/10.1371/journal.pone.1234567", description)

    def test_omits_doi_line_when_missing(self):
        articles = [
            {
                "title": "Some paper",
                "title_zh": "某论文",
                "journal": "Nature",
                "published": "2026-09-02",
            }
        ]

        description = _get_episode_description(articles)

        self.assertNotIn("doi.org", description)

    def test_duration_uses_hours_for_long_episodes(self):
        try:
            import mutagen.mp3  # noqa: F401
        except ImportError:
            self.skipTest("mutagen is not installed in this test environment")

        fake_mp3 = type("MP3", (), {"info": SimpleNamespace(length=4504.2)})

        with patch("mutagen.mp3.MP3", fake_mp3):
            duration = _get_mp3_duration("episode.mp3")

        self.assertEqual("1:15:04", duration)

    def test_pub_date_is_explicit_beijing_time(self):
        import xml.etree.ElementTree as ET

        with tempfile.NamedTemporaryFile(suffix=".mp3") as audio, patch(
            "feed_generator._get_mp3_duration", return_value="1:00:00"
        ):
            rss = ET.Element("rss")
            channel = ET.SubElement(rss, "channel")
            _add_item(channel, "2026-09-09", audio.name, [])

        pub_date = channel.find("item/pubDate").text

        self.assertIn("09 Sep 2026 00:00:00 +0800", pub_date)


if __name__ == "__main__":
    unittest.main()
