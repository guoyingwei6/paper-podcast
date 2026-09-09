import unittest

from feed_generator import _get_episode_description


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


if __name__ == "__main__":
    unittest.main()
