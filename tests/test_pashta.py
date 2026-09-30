"""Small reading fixtures for the demonstrative pashta correction."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preprocess_corpus import transliterate_word
from rhyme import extract_signature

class PashtaTests(unittest.TestCase):
    def test_known_readings(self):
        for hebrew, expected in [
            ('תֹ֙הוּ֙', 'tóhu'), ('וָבֹ֔הוּ', 'vavóhu'),
            ('בְּבֵיתֶ֙ךָ֙', 'beveytékha'), ('בְּשִׁבְתְּךָ֤', 'beshivtekhá'),
            ('מַ֙יִם֙', 'máyim'), ('אוֹר֑', 'ór'), ('אוֹרֽ', 'ór'),
        ]:
            with self.subTest(hebrew=hebrew):
                self.assertEqual(transliterate_word(hebrew), expected)

    def test_signature_boundaries(self):
        def segments(word):
            return extract_signature(transliterate_word(word)).segments
        self.assertEqual(segments('תֹ֙הוּ֙'), segments('וָבֹ֔הוּ'))
        self.assertNotEqual(segments('בְּבֵיתֶ֙ךָ֙'), segments('בְּשִׁבְתְּךָ֤'))

if __name__ == '__main__':
    unittest.main()
