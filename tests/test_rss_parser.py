import unittest

from article_sources import (
    _extract_biorxiv_abstract,
    _first_europe_pmc_result,
    extract_doi,
    extract_europe_pmc_xml_text,
)
from rss_parser import clean_title, extract_article_text


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

    def test_extract_doi_from_redirect_link(self):
        doi = extract_doi("https://doi.org/10.1101/2026.06.29.735168?rss=1")

        self.assertEqual("10.1101/2026.06.29.735168", doi)

    def test_first_europe_pmc_result_returns_empty_dict_when_absent(self):
        result = _first_europe_pmc_result({"resultList": {"result": []}})

        self.assertEqual({}, result)

    def test_extract_biorxiv_abstract_uses_latest_collection_entry(self):
        abstract = _extract_biorxiv_abstract(
            {
                "collection": [
                    {"version": "1", "abstract": "Older abstract."},
                    {"version": "2", "abstract": "Updated abstract."},
                ]
            }
        )

        self.assertEqual("Updated abstract.", abstract)

    def test_extract_europe_pmc_xml_text_keeps_main_sections(self):
        xml = (
            "<article>"
            "<front><article-meta>"
            "<abstract><p>Open abstract text.</p></abstract>"
            "</article-meta></front>"
            "<body>"
            "<sec><title>Introduction</title><p>Background paragraph.</p></sec>"
            "<sec><title>Results</title><p>Result paragraph.</p></sec>"
            "<sec><title>References</title><p>Should not appear.</p></sec>"
            "</body>"
            "</article>"
        )

        text = extract_europe_pmc_xml_text(xml)

        self.assertIn("## Abstract", text)
        self.assertIn("Open abstract text.", text)
        self.assertIn("## Results", text)
        self.assertNotIn("Should not appear.", text)


class CleanTitleTests(unittest.TestCase):
    def test_strips_italic_tags_and_collapses_newlines(self):
        raw = (
            "Early-life colonization with\n"
            "                    <i>Clostridioides difficile</i>\n"
            "                    remodels the developing gut"
        )

        self.assertEqual(
            clean_title(raw),
            "Early-life colonization with Clostridioides difficile remodels the developing gut",
        )

    def test_unescapes_entities(self):
        self.assertEqual(clean_title("Wnt&amp;Notch signalling"), "Wnt&Notch signalling")

    def test_keeps_subscript_and_gene_numbers_attached(self):
        raw = (
            "Forest canopy decline under elevated CO\n"
            "                    <sub>2</sub>\n"
            "                    during the Paleocene-Eocene Thermal Maximum"
        )

        self.assertEqual(
            clean_title(raw),
            "Forest canopy decline under elevated CO2 during the Paleocene-Eocene Thermal Maximum",
        )

    def test_keeps_trailing_digit_attached_to_gene_symbol(self):
        raw = (
            "Resequencing Identifies\n"
            "                    <scp>RASAL</scp>\n"
            "                    2 as a Candidate Gene"
        )

        self.assertEqual(clean_title(raw), "Resequencing Identifies RASAL2 as a Candidate Gene")

    def test_tightens_parentheses_around_stripped_tags(self):
        raw = (
            "Exoribonuclease 2 (\n"
            "                    <i>DIS3L2</i>\n"
            "                    ) Gene and Weaning Weight"
        )

        self.assertEqual(clean_title(raw), "Exoribonuclease 2 (DIS3L2) Gene and Weaning Weight")

    def test_keeps_real_spaces_between_words(self):
        raw = "Ascertainment Bias in Cattle <scp>SNP</scp> Arrays and Implications"

        self.assertEqual(
            clean_title(raw),
            "Ascertainment Bias in Cattle SNP Arrays and Implications",
        )

    def test_leaves_plain_title_unchanged(self):
        title = "Whole genome sequencing of 1427 Mexican individuals"

        self.assertEqual(clean_title(title), title)


if __name__ == "__main__":
    unittest.main()
