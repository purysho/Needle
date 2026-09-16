import tempfile
import unittest
from pathlib import Path
from needle.indexer import SearchIndex

class NeedleTests(unittest.TestCase):
    def test_build_search_save_load(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'alpha.txt').write_text('needle finds private local files quickly', encoding='utf-8')
            (root / 'beta.md').write_text('something unrelated', encoding='utf-8')
            idx = SearchIndex()
            stats = idx.build([str(root)])
            self.assertEqual(stats.indexed, 2)
            payload = idx.search('private local')
            results = payload['results']
            self.assertTrue(results)
            self.assertEqual(results[0]['name'], 'alpha.txt')
            out = root / 'index.json'; idx.save(out)
            loaded = SearchIndex.load(out)
            self.assertEqual(loaded.stats()['documents'], 2)
            self.assertTrue(loaded.search('needle')['results'])

    def test_extension_filter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'one.py').write_text('searchable token', encoding='utf-8')
            (root / 'two.txt').write_text('searchable token', encoding='utf-8')
            idx = SearchIndex(); idx.build([str(root)])
            results = idx.search('searchable', ext='.py')['results']
            self.assertEqual([r['name'] for r in results], ['one.py'])

if __name__ == '__main__':
    unittest.main()
