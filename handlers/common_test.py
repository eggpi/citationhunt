import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import common
import config

import mock
import unittest

class HandlersCommonTest(unittest.TestCase):
    def _test_load_strings_for_request(self, allowed_lang_tags,
            lang_code, accept_language_hdr, accept_language = []):
        tested_lang_tags = []
        cfg = config.Config(accept_language = accept_language)
        def fake_get_localized_strings(_, lang_tag):
            tested_lang_tags.append(lang_tag)
            if lang_tag.lower() in allowed_lang_tags:
                return {'ok': True}
            return {}
        with mock.patch(
            'common.chstrings.get_localized_strings',
            side_effect = fake_get_localized_strings):
            lang_tag, strings = common.load_strings_for_request(
                lang_code, cfg, accept_language_hdr)
        # Must have eventually loaded a valid set of strings
        self.assertEquals(strings, {'ok': True})
        return lang_tag, tested_lang_tags

    def test_ui_lang_simple_en(self):
        r, tested_lang_tags = self._test_load_strings_for_request(
            ['en', 'en-gb', 'fr', 'fi'], 'en', 'en-US,en;q=0.5')
        self.assertEquals(r, 'en')
        self.assertEquals(tested_lang_tags, ['en-US', 'en'])

    def test_ui_lang_simple_fr(self):
        # Just another smoke test, with the difference that fr, unlike en,
        # has no variants.
        r, tested_lang_tags = self._test_load_strings_for_request(
            ['en', 'en-gb', 'fr', 'fi'], 'fr', 'fr,en;q=0.5')
        self.assertEquals(r, 'fr')
        self.assertEquals(tested_lang_tags, ['fr'])

    def test_ui_lang_en_with_hdr_en_gb(self):
        # Header should override URL, but only for selecting a locale variant.
        r, tested_lang_tags = self._test_load_strings_for_request(
            ['en', 'en-gb', 'fr', 'fi'], 'en', 'en-GB,en-US;q=0.5,en;q=0.5')
        self.assertEquals(r, 'en-GB')
        self.assertEquals(tested_lang_tags, ['en-GB'])

    def test_ui_lang_fr_with_hdr_en_gb(self):
        # We should still respect the URL if it chooses a locale that we know,
        # even if it disagrees with the header, when the header doesn't provide
        # a variant of the URL's locale.
        r, tested_lang_tags = self._test_load_strings_for_request(
            ['en', 'en-gb', 'fr', 'fi'], 'fr', 'en-GB,en-US;q=0.5,en;q=0.5')
        self.assertEquals(r, 'fr')
        self.assertEquals(tested_lang_tags, ['fr'])

    # zh_{hans,hant} differ from en/en-gb because the lang tag doesn't match
    # the lang code ever (- vs. _) so we always use the fallback.
    def test_ui_lang_zh_hant_with_hdr_tw_fallback_zh_hant(self):
        r, tested_lang_tags = self._test_load_strings_for_request(
            ['en', 'fr', 'fi', 'zh-hant', 'zh-hans'], 'zh_hant',
            'zh-TW,en;q=0.5', accept_language = ['zh-TW', 'zh-Hant'])
        self.assertEquals(r, 'zh-Hant')
        self.assertEquals(tested_lang_tags, ['zh-TW', 'zh', 'zh-Hant'])

    def test_ui_lang_zh_hant_with_hdr_en_fallback_zh_hant(self):
        # Here the user doesn't accept any of the language tags expected by the
        # config, we should still use the fallback.
        r, tested_lang_tags = self._test_load_strings_for_request(
            ['en', 'fr', 'fi', 'zh-hant', 'zh-hans'], 'zh_hant',
            'en-US,en;q=0.5', accept_language = ['zh-TW', 'zh-Hant'])
        self.assertEquals(r, 'zh-Hant')
        self.assertEquals(tested_lang_tags, ['zh-Hant'])

if __name__ == '__main__':
    unittest.main()
