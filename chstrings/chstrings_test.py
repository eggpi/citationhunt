import chstrings
import config

import unittest

class CHStringsTest(unittest.TestCase):
    @classmethod
    def add_smoke_test(cls, cfg):
        def test(self):
            # We just want to see if this will blow up. Use the fallback
            # lang_tag across all tests.
            lang_tag = cfg.lang_code
            if cfg.accept_language:
                lang_tag = cfg.accept_language[-1]
            self.assertNotEqual({},
                chstrings.get_localized_strings(cfg, lang_tag))
        name = 'test_' + cfg.lang_code + '_smoke_test'
        setattr(cls, name, test)

if __name__ == '__main__':
    for lc in config.LANG_CODES_TO_LANG_NAMES:
        cfg = config.get_localized_config(lc)
        CHStringsTest.add_smoke_test(cfg)
    unittest.main()
