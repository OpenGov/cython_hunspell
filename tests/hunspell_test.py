# This import fixes sys.path issues
import parentpath

import os
import unittest
import hunspell
from hunspell import Hunspell

DICT_DIR = os.path.join(os.path.dirname(__file__), '..', 'dictionaries')

class HunspellTest(unittest.TestCase):
    def test_hunspell_create_destroy(self):
        d = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        del d

    def test_hunspell_spell(self):
        d = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertFalse(d.spell('dpg'))
        self.assertTrue(d.spell('dog'))
        del d

    def test_hunspell_suggest(self):
        d = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertListEqual(d.suggest('dpg'), ['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'])
        del d

    def test_hunspell_stem(self):
        d = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertListEqual(d.stem('dog'), ['dog'])
        self.assertListEqual(d.stem('permanently'), ['permanent'])
        del d

    def test_hunspell_bulk_suggest(self):
        d = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertDictEqual(d.bulk_action("suggest", ['dog', 'dpg']), {
            'dpg': ['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'],
            'dog': ['dog']
        })
        self.assertDictEqual(d.bulk_action("suggest", ['dog', 'dpg', 'pgg', 'opg', 'dyg', 'frg', 'twg', 'bjn', 'foo', 'qre']), {
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
        del d

    def test_hunspell_bulk_stem(self):
        d = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
        self.assertDictEqual(d.bulk_action("stem", ['dog', 'permanently']), {
            'permanently': ['permanent'],
            'dog': ['dog']
        })
        self.assertDictEqual(d.bulk_action("stem", ['dog', 'twigs', 'permanently', 'unrecorded']), {
            'unrecorded': ['recorded'],
            'permanently': ['permanent'],
            'twigs': ['twig'],
            'dog': ['dog']
        })
        del d

if __name__ == '__main__':
    unittest.main()
