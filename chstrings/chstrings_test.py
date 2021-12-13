import chstrings
import config

import unittest

import mock

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

    def test_fallback_lang_tag(self):
        gcfg = config.get_global_config()
        cfg = config.get_localized_config(gcfg.fallback_lang_tag, api = False)
        fallback_strings = chstrings.get_localized_strings(
            cfg, gcfg.fallback_lang_tag)

        original = chstrings._load_strings_for_lang_tag(gcfg.fallback_lang_tag)
        with mock.patch('chstrings._load_strings_for_lang_tag') as m:
            # Simulate an incomplete strings file.
            def _load_strings_side_effect(lang_tag):
                if lang_tag == 'fake':
                    return {'tooltitle': 'Test Citation Hunt'}
                elif lang_tag == gcfg.fallback_lang_tag:
                    return original
                raise ValueError
            m.side_effect = _load_strings_side_effect

            # The incomplete strings must have been merged with the fallback
            # ones.
            strings = chstrings.get_localized_strings(cfg, 'fake')
            self.assertEqual('Test Citation Hunt', strings['tooltitle'])
            self.assertEqual(fallback_strings['instructions_goal'],
                strings['instructions_goal'])

if __name__ == '__main__':
    for lc in config.LANG_CODES_TO_LANG_NAMES:
        cfg = config.get_localized_config(lc, api = False)
        CHStringsTest.add_smoke_test(cfg)
    unittest.main()
