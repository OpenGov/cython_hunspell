#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This import fixes sys.path issues
from . import parentpath

import os
import unittest
from hunspell import Hunspell

DICT_DIR = os.path.join(os.path.dirname(__file__), '..', 'dictionaries')

class HunspellTest(unittest.TestCase):
    def setUp(self):
        self.h = Hunspell('test', hunspell_data_dir=DICT_DIR)

    def tearDown(self):
        try:
            del self.h
        except AttributeError:
            pass

    def test_hunspell_create_destroy(self):
        del self.h

    def test_missing_dict(self):
        with self.assertRaises(IOError):
            Hunspell('not_avail', hunspell_data_dir=DICT_DIR)

    def test_hunspell_spell(self):
        self.assertFalse(self.h.spell('dpg'))
        self.assertTrue(self.h.spell('dog'))

    def test_hunspell_spell_utf8(self):
        self.assertTrue(self.h.spell(u'café'))
        self.assertFalse(self.h.spell(u'uncafé'))

    def test_hunspell_suggest(self):
        self.assertEqual(self.h.suggest('dpg'), ('dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'))

    def test_hunspell_suggest_utf8(self):
        self.assertEqual(self.h.suggest('cefé'), (u'café', u'Cerf'))
        self.assertEqual(self.h.suggest(u'cefé'), (u'café', u'Cerf'))

    def test_hunspell_stem(self):
        self.assertEqual(self.h.stem('dog'), ('dog',))
        self.assertEqual(self.h.stem('permanently'), ('permanent',))

    def test_hunspell_bulk_suggest(self):
        self.h.set_concurrency(3)
        self.assertDictEqual(self.h.bulk_suggest(['dog', 'dpg']), {
            'dpg': ('dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'),
            'dog': ('dog',)
        })
        self.assertDictEqual(self.h.bulk_suggest(['dog', 'dpg', 'pgg', 'opg', 'dyg', 'frg', 'twg', 'bjn', 'foo', 'qre']), {
            'pgg': ('pg', 'peg', 'egg', 'pig', 'pug', 'pkg', 'pg g', 'PG'),
            'foo': ('few', 'goo', 'fop', 'foot', 'fool', 'food', 'foe', 'for', 'fro', 'too', 'fol', 'coo', 'fog', 'moo', 'fob'),
            'frg': ('fr', 'frig', 'frog', 'erg', 'fig', 'fag', 'fro', 'fog', 'fry', 'fr g'),
            'twg': ('twig', 'tag', 'two', 'tog', 'tug', 'twp'),
            'bjn': ('bin', 'ban', 'bun', 'Bjorn'),
            'dog': ('dog',),
            'dpg': ('dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg', 'GDP'),
            'opg': ('op', 'pg', 'ope', 'ops', 'opt', 'mpg', 'opp', 'o pg', 'op g', 'GPO'),
            'dyg': ('dug', 'dye', 'deg', 'dig', 'dog', 'dying'),
            'qre': ('qr', 're', 'ere', 'ire', 'are', 'ore', 'Ore', 'Dre', 'q re', 'qr e')
        })

    def test_hunspell_bulk_stem(self):
        self.h.set_concurrency(3)
        self.assertDictEqual(self.h.bulk_stem(['dog', 'permanently']), {
            'permanently': ('permanent',),
            'dog': ('dog',)
        })
        self.assertDictEqual(self.h.bulk_stem(['dog', 'twigs', 'permanently', 'unrecorded']), {
            'unrecorded': ('recorded',),
            'permanently': ('permanent',),
            'twigs': ('twig',),
            'dog': ('dog',)
        })

if __name__ == '__main__':
    unittest.main()
