import unittest

from tts_engine import parse_script


class ParseScriptTests(unittest.TestCase):
    def test_requires_speaker_separator(self):
        script = (
            "女: 大家好。\n"
            "男: 我们聊聊。\n"
            "女性个体的表型差异明显。\n"
            "男性样本共有 200 个。"
        )

        segments = parse_script(script)

        self.assertEqual(
            segments,
            [
                {"gender": "female", "text": "大家好。"},
                {"gender": "male", "text": "我们聊聊。"},
            ],
        )

    def test_supports_bold_hosts(self):
        segments = parse_script("**女:** 第一句。\n**男:** 第二句。")

        self.assertEqual(
            segments,
            [
                {"gender": "female", "text": "第一句。"},
                {"gender": "male", "text": "第二句。"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
