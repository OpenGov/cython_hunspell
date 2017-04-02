# This import fixes sys.path issues
from . import parentpath

import os
import unittest
from hunspell import Hunspell

DICT_DIR = os.path.join(os.path.dirname(__file__), '..', 'dictionaries')

class HunspellTest(unittest.TestCase):
    def setUp(self):
        self.h = Hunspell('en_US', hunspell_data_dir=DICT_DIR)

    def tearDown(self):
        try:
            del self.h
        except AttributeError:
            pass

    def test_hunspell_create_destroy(self):
        del self.h

    def test_hunspell_spell(self):
        self.h = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertFalse(self.h.spell('dpg'))
        self.assertTrue(self.h.spell('dog'))

    def test_hunspell_suggest(self):
        self.h = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertListEqual(self.h.suggest('dpg'), ['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'])

    def test_hunspell_stem(self):
        self.h = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertListEqual(self.h.stem('dog'), ['dog'])
        self.assertListEqual(self.h.stem('permanently'), ['permanent'])

    def test_hunspell_bulk_suggest(self):
        self.h = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertDictEqual(self.h.bulk_action("suggest", ['dog', 'dpg']), {
            'dpg': ['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'],
            'dog': ['dog']
        })
        self.assertDictEqual(self.h.bulk_action("suggest", ['dog', 'dpg', 'pgg', 'opg', 'dyg', 'frg', 'twg', 'bjn', 'foo', 'qre']), {
            'pgg': ['pg', 'peg', 'egg', 'pig', 'pug', 'pkg', 'pg g', 'PG'],
            'foo': ['few', 'goo', 'fop', 'foot', 'fool', 'food', 'foe', 'for', 'fro', 'too', 'fol', 'coo', 'fog', 'moo', 'fob'],
            'frg': ['fr', 'frig', 'frog', 'erg', 'fig', 'fag', 'fro', 'fog', 'fry', 'fr g'],
            'twg': ['twig', 'tag', 'two', 'tog', 'tug', 'twp'],
            'bjn': ['bin', 'ban', 'bun', 'Bjorn'],
            'dog': ['dog'],
            'dpg': ['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'],
            'opg': ['op', 'pg', 'ope', 'ops', 'opt', 'mpg', 'opp', 'o pg', 'op g', 'GPO'],
            'dyg': ['dug', 'dye', 'deg', 'dig', 'dog', 'dying'],
            'qre': ['qr', 're', 'ere', 'ire', 'are', 'ore', 'Ore', 'Dre', 'q re', 'qr e']
        })

    def test_hunspell_bulk_stem(self):
        self.h = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        for thread_count in [1, 4]:
            self.h.set_concurrency(thread_count)
            self.assertDictEqual(self.h.bulk_action("stem", ['dog', 'permanently']), {
                'permanently': ['permanent'],
                'dog': ['dog']
            })
            self.assertDictEqual(self.h.bulk_action("stem", ['dog', 'twigs', 'permanently', 'unrecorded']), {
                'unrecorded': ['recorded'],
                'permanently': ['permanent'],
                'twigs': ['twig'],
                'dog': ['dog']
            })

if __name__ == '__main__':
    unittest.main()
