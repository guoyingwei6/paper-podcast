import unittest

from ai_generator import validate_script_coverage


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


if __name__ == "__main__":
    unittest.main()
