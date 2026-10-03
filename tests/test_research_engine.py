"""The CLI is an instruction scaffold, not a research executor."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.research_engine import ResearchEngine, ResearchMode, ResearchPhase, main


class ResearchEngineInstructionsTest(unittest.TestCase):
    def test_requested_output_directory_controls_saved_state_and_report_path(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'chosen-deliverable'
            engine = ResearchEngine(ResearchMode.QUICK, output_dir=destination)
            with contextlib.redirect_stdout(io.StringIO()):
                report_path = Path(engine.run_pipeline('Test question'))
            self.assertEqual(report_path.parent, destination)
            self.assertTrue(list(destination.glob('research_state_*.json')))

    def test_default_output_directory_uses_topic_and_date(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.research_engine.Path.home', return_value=Path(directory)):
                engine = ResearchEngine(ResearchMode.QUICK)
                with contextlib.redirect_stdout(io.StringIO()):
                    report_path = Path(engine.run_pipeline('Test question: approaches?'))
            self.assertEqual(report_path.parent.parent, Path(directory) / 'Documents')
            self.assertRegex(report_path.parent.name,
                             r'^Test_question_approaches_Research_\d{8}$')
            self.assertTrue(list(report_path.parent.glob('research_state_*.json')))

    def test_phase_guidance_keeps_worker_boundaries_and_user_output_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = ResearchEngine(ResearchMode.DEEP, output_dir=Path(directory))
            retrieve = engine.get_phase_instructions(ResearchPhase.RETRIEVE)
            package = engine.get_phase_instructions(ResearchPhase.PACKAGE)
            self.assertIn('lead registers', retrieve)
            self.assertIn('exclusive output path', retrieve)
            self.assertIn('sequentially', retrieve)
            self.assertIn('untrusted data', retrieve)
            self.assertIn('user-requested destination', package)
            self.assertIn('HTML/PDF only when requested', package)
            self.assertIn('linked dossiers', package)

    def test_quick_mode_includes_coverage_scope_and_retrieval_stop(self):
        engine = ResearchEngine(ResearchMode.QUICK)
        phases = engine._get_phases_for_mode()
        self.assertEqual(phases, [ResearchPhase.SCOPE, ResearchPhase.RETRIEVE,
                                  ResearchPhase.PACKAGE])
        self.assertIn('coverage.json', engine.get_phase_instructions(ResearchPhase.SCOPE))
        retrieval = engine.get_phase_instructions(ResearchPhase.RETRIEVE)
        self.assertIn('queries.jsonl', retrieval)
        self.assertIn('two subsequent low-yield residual probe rounds', retrieval)
        self.assertIn('zero new relevant canonical sources in the round', retrieval)
        self.assertNotIn('sources for high-priority facets', retrieval)
        self.assertIn('budget-exhausted', retrieval)

    def test_cli_reports_instruction_scaffold_not_completed_research(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.research_engine.Path.home', return_value=Path(directory)):
                with patch('sys.argv', ['research_engine.py', '--query', 'Test question',
                                        '--mode', 'quick']):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        main()
            self.assertIn('Now the agent should execute each phase', output.getvalue())
            self.assertNotIn('Research complete!', output.getvalue())
            self.assertNotIn('RESEARCH PIPELINE COMPLETE', output.getvalue())
            self.assertFalse(list(Path(directory).rglob('research_report_*.md')))


if __name__ == '__main__':
    unittest.main()
