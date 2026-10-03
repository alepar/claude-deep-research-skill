"""The CLI is an instruction scaffold, not a research executor."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.research_engine import ResearchEngine, ResearchMode, ResearchPhase, main


class ResearchEngineInstructionsTest(unittest.TestCase):
    def test_quick_mode_includes_coverage_scope_and_retrieval_stop(self):
        engine = ResearchEngine(ResearchMode.QUICK)
        phases = engine._get_phases_for_mode()
        self.assertEqual(phases, [ResearchPhase.SCOPE, ResearchPhase.RETRIEVE,
                                  ResearchPhase.PACKAGE])
        self.assertIn('coverage.json', engine.get_phase_instructions(ResearchPhase.SCOPE))
        retrieval = engine.get_phase_instructions(ResearchPhase.RETRIEVE)
        self.assertIn('queries.jsonl', retrieval)
        self.assertIn('two subsequent low-yield residual probe rounds', retrieval)
        self.assertIn('budget-exhausted', retrieval)

    def test_cli_reports_instruction_scaffold_not_completed_research(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.research_engine.Path.home', return_value=Path(directory)):
                with patch('sys.argv', ['research_engine.py', '--query', 'Test question',
                                        '--mode', 'quick']):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        main()
            self.assertIn('Now Claude should execute each phase', output.getvalue())
            self.assertNotIn('Research complete!', output.getvalue())
            self.assertNotIn('RESEARCH PIPELINE COMPLETE', output.getvalue())
            self.assertFalse(list(Path(directory).rglob('research_report_*.md')))


if __name__ == '__main__':
    unittest.main()
