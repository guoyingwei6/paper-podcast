import unittest
from unittest.mock import patch

from ai_generator import generate_podcast_script, validate_script_coverage


class FakeAnalysis:
    def to_prompt_text(self):
        return "研究问题：测试问题。方法：测试方法。结果：测试结果。局限：测试局限。"

    def to_summary(self):
        return "测试摘要"


class ScriptCoverageTests(unittest.TestCase):
    def test_validate_script_coverage_accepts_required_article_markers(self):
        script = """
        女: 文章 1 研究问题是热应激如何影响奶牛基因组选择，方法是GWAS。
        男: 关键结果包括准确率从0.41提升到0.58，局限是只在一个群体验证。
        女: 文章 2 研究问题是泛基因组如何帮助结构变异解释表型，方法是图基因组分析。
        男: 关键结果保留了具体比较，局限是样本量仍需扩大。
        """

        validate_script_coverage(script, expected_count=2)

    def test_validate_script_coverage_rejects_missing_article(self):
        script = """
        女: 文章 1 研究问题是热应激如何影响奶牛基因组选择，方法是GWAS。
        男: 关键结果包括准确率从0.41提升到0.58，局限是只在一个群体验证。
        """

        with self.assertRaises(ValueError):
            validate_script_coverage(script, expected_count=2)

    def test_generate_podcast_script_retries_a_batch_with_missing_article(self):
        summaries = [
            {"title": "Alpha genome study", "title_zh": "甲基因组研究", "analysis": FakeAnalysis()},
            {"title": "Beta genome study", "title_zh": "乙基因组研究", "analysis": FakeAnalysis()},
        ]
        incomplete = "女: 文章 1 讨论 Alpha genome study。"
        complete = (
            "女: 文章 1 讨论 Alpha genome study。\n"
            "男: 文章 2 讨论 Beta genome study。"
        )

        with patch("ai_generator._chat", side_effect=[incomplete, complete]) as chat:
            script = generate_podcast_script(summaries)

        self.assertEqual(script, complete)
        self.assertEqual(chat.call_count, 2)
        self.assertIn("遗漏了文章 2", chat.call_args_list[1].args[0])

    @patch("ai_generator.generate_podcast_script", return_value="女: 文章 1 测试。")
    @patch("ai_generator.translate_titles", return_value={})
    @patch("ai_generator.analyze_article")
    def test_process_articles_retries_invalid_analysis(self, analyze, _translate, _script):
        analyze.side_effect = [ValueError("invalid JSON"), FakeAnalysis()]
        articles = [{"title": "Alpha genome study", "content": "text"}]

        from ai_generator import process_articles

        self.assertEqual(process_articles(articles), "女: 文章 1 测试。")
        self.assertEqual(analyze.call_count, 2)


if __name__ == "__main__":
    unittest.main()
