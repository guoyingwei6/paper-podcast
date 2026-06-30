import unittest

from rss_parser import extract_article_text


class ArticleTextExtractionTests(unittest.TestCase):
    def test_extract_article_text_prefers_scientific_sections(self):
        html = """
        <html><body>
          <nav>Subscribe Login Metrics</nav>
          <article>
            <h2>Abstract</h2><p>We tested genomic prediction in cattle.</p>
            <h2>Methods</h2><p>We used sequence variants and cross-validation.</p>
            <h2>Results</h2><p>Accuracy increased from 0.41 to 0.58.</p>
            <h2>Discussion</h2><p>The gain may depend on breed composition.</p>
            <h2>References</h2><p>Reference 1. Reference 2.</p>
          </article>
        </body></html>
        """

        text = extract_article_text(html)

        self.assertIn("## Abstract", text)
        self.assertIn("Accuracy increased from 0.41 to 0.58.", text)
        self.assertNotIn("Subscribe Login", text)
        self.assertNotIn("Reference 1", text)


if __name__ == "__main__":
    unittest.main()
