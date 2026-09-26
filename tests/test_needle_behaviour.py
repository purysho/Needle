import os, tempfile, time, unittest
from pathlib import Path

from needle.indexer import SearchIndex, make_snippet


class NeedleBehaviourTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.root = Path(self._tmp.name)
    def tearDown(self):
        self._tmp.cleanup()

    def put(self, rel, text=None, data=None):
        p = self.root / rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data) if data is not None else p.write_text(text, encoding='utf-8'); return p

    def names(self, idx, q, **kw):
        return [r['name'] for r in idx.search(q, **kw)['results']]

    def test_rebuild_reuses_unchanged_files_and_notices_edits_and_deletions(self):
        a = self.put('a.txt', 'alpha one'); self.put('b.txt', 'beta two')
        idx = SearchIndex(); self.assertEqual(idx.build([self.root]).changed, 2)
        self.assertEqual(idx.build([self.root]).changed, 0)
        a.write_text('alpha one gamma'); os.utime(a, (time.time() + 5, time.time() + 5)); (self.root / 'b.txt').unlink()
        stats = idx.build([self.root])
        self.assertEqual((stats.changed, stats.removed, stats.indexed), (1, 1, 1))
        self.assertEqual(self.names(idx, 'gamma'), ['a.txt'])

    def test_phrases_must_match_exactly(self):
        self.put('yes.md', 'the quick brown fox'); self.put('no.md', 'brown quick the fox')
        self.assertEqual(self.names(idx := self._built(), '"quick brown"'), ['yes.md'])

    def test_typos_are_tolerated_and_suggested(self):
        self.put('doc.txt', 'reconciliation of evidence'); idx = self._built()
        payload = idx.search('reconcilation')
        self.assertEqual([r['name'] for r in payload['results']], ['doc.txt'])
        self.assertIn('reconciliation', payload['suggestions']['reconcilation'])
        self.assertEqual(idx.search('reconcilation', typo_tolerance=False)['results'], [])

    def test_filename_matches_rank_above_body_matches(self):
        self.put('recovery.md', 'recovery notes'); self.put('other.md', 'recovery notes'); idx = self._built()
        self.assertEqual(self.names(idx, 'recovery')[0], 'recovery.md')

    def test_hidden_ignored_binary_and_unknown_files_are_skipped(self):
        self.put('ok.txt', 'findme'); self.put('.hidden/x.txt', 'findme'); self.put('node_modules/p/x.js', 'findme')
        self.put('blob.txt', data=b'\x00\x01findme'); self.put('image.png', 'findme')
        self.assertEqual(self.names(self._built(), 'findme'), ['ok.txt'])

    def test_latin1_text_is_indexed_as_text(self):
        data = 'Résumé naïve café!'.encode('cp1252'); self.assertEqual(len(data) % 2, 0)  # even: would 'decode' as UTF-16
        self.put('cv.txt', data=data)
        self.assertEqual(self.names(self._built(), 'résumé'), ['cv.txt'])

    def test_utf16_with_bom_is_indexed(self):
        self.put('notes.txt', data='﻿unicode notes here'.encode('utf-16-le'))
        self.assertEqual(self.names(self._built(), 'unicode'), ['notes.txt'])

    def test_single_file_root_and_browse_by_extension(self):
        f = self.put('solo.md', 'lonely words'); idx = SearchIndex(); idx.build([f])
        self.assertEqual(idx.doc_count, 1)
        self.assertEqual([r['name'] for r in idx.search('', ext='.md')['results']], ['solo.md'])
        self.assertEqual(idx.search('', ext='.py')['results'], [])

    def test_snippet_centres_on_the_match(self):
        f = self.put('long.txt', 'filler ' * 200 + 'the needle is here ' + 'filler ' * 200)
        snippet = make_snippet(f, ['needle'])
        self.assertIn('needle', snippet.lower()); self.assertLess(len(snippet), 600)

    def _built(self):
        idx = SearchIndex(); idx.build([self.root]); return idx


if __name__ == '__main__':
    unittest.main()
