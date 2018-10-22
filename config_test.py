import config

import re
import unittest

class ConfigTest(unittest.TestCase):
    @classmethod
    def add_validate_categories_test(cls, cfg):
        def test(self):
            # Categories must have underscores instead of spaces.
            self.assertNotIn(' ', cfg.hidden_category)
            self.assertNotIn(' ', cfg.citation_needed_category)
        name = 'test_' + cfg.lang_code + '_category_names_underscores'
        setattr(cls, name, test)

    @classmethod
    def add_validate_templates_test(cls, cfg):
        def test(self):
            # Templates should contain spaces, not underscores.
            for tpl in cfg.citation_needed_templates:
                self.assertNotIn('_', tpl)
        setattr(cls, 'test_' + cfg.lang_code + '_template_names_spaces', test)

    @classmethod
    def add_validate_wikipedia_domain_test(cls, cfg):
        def test(self):
            self.assertTrue(re.match('^[a-z]+.wikipedia.org$',
                cfg.wikipedia_domain))
        setattr(cls, 'test_' + cfg.lang_code + '_wikipedia_domain', test)

if __name__ == '__main__':
    for lc in config.LANG_CODES_TO_LANG_NAMES:
        cfg = config.get_localized_config(lc)
        ConfigTest.add_validate_categories_test(cfg)
        ConfigTest.add_validate_templates_test(cfg)
        ConfigTest.add_validate_wikipedia_domain_test(cfg)
    unittest.main()
