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

    def assertAllIn(self, checked, expected):
        self.assertTrue(all(x in expected for x in checked),
            u"{} not all found in {}".format(checked, expected))

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
        required = ('dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg')
        suggest = self.h.suggest('dpg')
        self.assertIsInstance(suggest, tuple)
        self.assertAllIn(required, suggest)

    def test_hunspell_suggest_utf8(self):
        required = (u'café', u'Cerf')
        for variant in ('cefé', u'cefé'):
            suggest = self.h.suggest(variant)
            self.assertIsInstance(suggest, tuple)
            self.assertAllIn(required, suggest)

    def test_hunspell_stem(self):
        self.assertEqual(self.h.stem('dog'), ('dog',))
        self.assertEqual(self.h.stem('permanently'), ('permanent',))

    def test_hunspell_bulk_suggest(self):
        self.h.set_concurrency(3)
        suggest = self.h.bulk_suggest(['dog', 'dpg'])
        self.assertEqual(sorted(suggest.keys()), ['dog', 'dpg'])
        self.assertIsInstance(suggest['dog'], tuple)
        self.assertAllIn(('dog',), suggest['dog'])

        required = ('dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg')
        self.assertIsInstance(suggest['dpg'], tuple)
        self.assertAllIn(required, suggest['dpg'])

        checked = ['bjn', 'dog', 'dpg', 'dyg', 'foo', 'frg', 'opg', 'pgg', 'qre', 'twg']
        suggest = self.h.bulk_suggest(checked)
        self.assertEqual(sorted(suggest.keys()), checked)

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
