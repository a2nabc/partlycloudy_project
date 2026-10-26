"""CPU-only regression checks for v2 scheduling and run safeguards."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import qwen_whole_movie_scores as q


class WholeMovieTests(unittest.TestCase):
    def test_full_coverage_and_final_clip(self):
        for duration in (2.0, 6.0, 9.0, 10.0, 313.812):
            rows = q.windows_for(Path('/movie.mov'), duration)
            self.assertEqual(float(rows[0]['clip_start_s']), 0)
            self.assertAlmostEqual(float(rows[-1]['clip_end_s']), duration)
            covered = 0
            for i, row in enumerate(rows):
                start, end = float(row['clip_start_s']), float(row['clip_end_s'])
                self.assertEqual(row['clip_start_s'], row['focus_start_s'])
                self.assertEqual(row['clip_end_s'], row['focus_end_s'])
                self.assertAlmostEqual(end-start, min(6, duration))
                self.assertLessEqual(start, covered)
                if i < len(rows)-1:
                    self.assertEqual(start, i*3)
                covered = end
        self.assertEqual(len(rows), 104)
        self.assertAlmostEqual(float(rows[-1]['clip_start_s']), 307.812)

    def test_reject_missing_or_extended_clip_before_decode(self):
        rows = q.windows_for(Path('/movie.mov'), 12)
        for bad in (rows[:-1], rows[1:], [dict(r, clip_start_s='0') for r in rows]):
            with patch.object(q, 'film_duration', return_value=12), patch.object(q.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    q.validate_clips(bad)
                run.assert_not_called()

    def test_resume_preserves_completed_and_interrupted_bytes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(q, 'OUT', Path(tmp)), patch.object(q, 'RESULTS', Path(tmp)/'scores.jsonl'):
            rows = q.windows_for(Path('/movie.mov'), 12)
            record = dict(window_id=rows[0]['window_id'], settings_hash=rows[0]['settings_hash'], model=q.MODEL_ID)
            saved = json.dumps(record).encode()+b'\n'
            q.RESULTS.write_bytes(saved+b'{"window_id":')
            q.recover_interrupted_append()
            self.assertEqual(q.RESULTS.read_bytes(), saved)
            self.assertEqual((q.OUT/'interrupted_appends.bin').read_bytes(), b'{"window_id":\n')
            self.assertEqual(list(q.completed(rows)), [rows[0]['window_id']])

    def test_partial_ranking_is_blocked(self):
        with patch.object(q, 'read_windows', return_value=q.windows_for(Path('/movie.mov'), 12)), patch.object(q, 'completed', return_value={}):
            with self.assertRaisesRegex(ValueError, 'full run'):
                q.rank(10, 2)

    def test_entire_video_prompt_and_all_condition_evidence(self):
        prompt = q.PROMPT.format(rubric='\n'.join(q.RUBRIC.values())).lower()
        for forbidden in ('context', 'central', 'focus interval'):
            self.assertNotIn(forbidden, prompt)
        data = dict(actions='A moves.', visible_reactions='None visible.', uncertain_details='None.',
                    uncertainty='low', scores={k:0 for k in q.LABELS}, evidence={k:'Not visible.' for k in q.LABELS})
        self.assertIsNotNone(q.validated_scores(data))
        data['evidence']['Pain']=''
        self.assertIsNone(q.validated_scores(data))


if __name__ == '__main__':
    unittest.main()
