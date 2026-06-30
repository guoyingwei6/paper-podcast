import unittest

from paper_analysis import PaperAnalysis, parse_paper_analysis_json


class PaperAnalysisTests(unittest.TestCase):
    def test_parse_paper_analysis_json_accepts_complete_model_output(self):
        raw = """
        ```json
        {
          "research_question": "Which loci shape cattle heat tolerance?",
          "why_it_matters": "Heat stress affects breeding decisions.",
          "study_design": "Genome-wide association study.",
          "data_and_samples": "2,400 cattle with temperature-humidity records.",
          "methods": "GWAS and functional annotation.",
          "key_findings_with_numbers": ["Three loci explained 12% of variance."],
          "mechanism_or_interpretation": "Candidate genes point to sweat gland biology.",
          "limitations": "Validation was limited to one population.",
          "field_context": "Useful for animal genomics and climate adaptation.",
          "talking_points_for_podcast": ["Why heat tolerance matters", "How GWAS found the loci"],
          "caveats_for_hosts": ["Do not present association as causation."]
        }
        ```
        """

        analysis = parse_paper_analysis_json(raw)

        self.assertIsInstance(analysis, PaperAnalysis)
        self.assertIn("Three loci", analysis.key_findings_with_numbers[0])
        self.assertIn("association as causation", analysis.caveats_for_hosts[0])

    def test_parse_paper_analysis_json_rejects_missing_required_fields(self):
        raw = '{"research_question": "What changed?"}'

        with self.assertRaises(ValueError):
            parse_paper_analysis_json(raw)


if __name__ == "__main__":
    unittest.main()
