import unittest

from modules.m3_smartedit.analyze import decisions, roles, sections
from modules.m3_smartedit.config import SmartEditConfig
from modules.m3_smartedit.model import Passage


def passage(index, text, tokens, strength=.5):
    return Passage(f"passage{index:06d}", index*1000, index*1000+900, text,
                   (f"w{index}",), tuple(tokens), strength)


class AnalysisTests(unittest.TestCase):
    def test_hook_intro_conclusion_and_cta(self):
        items = [passage(0, "Pourquoi cela change tout ?", ("pourquoi", "change")),
                 passage(1, "Aujourd'hui je vais expliquer la méthode.", ("expliquer", "méthode")),
                 passage(2, "En conclusion, abonne-toi.", ("conclusion", "abonne"))]
        found = roles(items)
        self.assertEqual({item["role"] for item in found}, {"HOOK", "INTRODUCTION", "CONCLUSION", "CTA"})

    def test_sections_split_on_topic_shift(self):
        items = [passage(0, "caméra cadre", ("caméra", "cadre")),
                 passage(1, "cadre visage", ("cadre", "visage")),
                 passage(2, "musique rythme", ("musique", "rythme"))]
        found = sections(items, SmartEditConfig())
        self.assertEqual([item["passage_ids"] for item in found],
                         [["passage000000", "passage000001"], ["passage000002"]])

    def test_exact_duplicate_defaults_to_review(self):
        items = [passage(0, "Une idée forte.", ("idée", "forte"), .6),
                 passage(1, "Une idée forte.", ("idée", "forte"), .8)]
        found = decisions(items, SmartEditConfig())
        exact = next(item for item in found if item["kind"] == "EXACT_DUPLICATE")
        self.assertEqual(exact["disposition"], "REVIEW")
        self.assertEqual(exact["preferred_passage_id"], "passage000001")

    def test_exact_duplicate_can_be_explicitly_automatic(self):
        items = [passage(0, "Même texte.", ("même", "texte")),
                 passage(1, "Même texte.", ("même", "texte"))]
        found = decisions(items, SmartEditConfig(auto_remove_exact_duplicates=True))
        self.assertEqual(found[0]["disposition"], "AUTO_REMOVE")

    def test_duplicate_cluster_keeps_one_global_preferred_passage(self):
        items = [passage(0, "Même texte.", ("même", "texte"), .4),
                 passage(1, "Même texte.", ("même", "texte"), .9),
                 passage(2, "Même texte.", ("même", "texte"), .6)]
        found = decisions(items, SmartEditConfig(auto_remove_exact_duplicates=True))
        exact = [item for item in found if item["kind"] == "EXACT_DUPLICATE"]
        self.assertEqual(len(exact), 2)
        self.assertEqual({item["preferred_passage_id"] for item in exact}, {"passage000001"})
        self.assertEqual({item["source_start_us"] for item in exact}, {0, 2000})

    def test_semantic_repetition_and_weaker_formulation_require_review(self):
        items = [passage(0, "Peut-être une méthode montage rapide.", ("méthode", "montage", "rapide"), .4),
                 passage(1, "Méthode de montage rapide et claire.", ("méthode", "montage", "rapide", "claire"), .9)]
        found = decisions(items, SmartEditConfig(semantic_similarity_threshold=.7))
        self.assertEqual({item["kind"] for item in found}, {"SEMANTIC_REPETITION", "WEAKER_FORMULATION"})
        self.assertTrue(all(item["disposition"] == "REVIEW" for item in found))

    def test_unrelated_passages_are_not_cut(self):
        found = decisions([passage(0, "caméra", ("caméra",)), passage(1, "musique", ("musique",))], SmartEditConfig())
        self.assertEqual(found, [])

    def test_invalid_config(self):
        for case in ({"semantic_similarity_threshold": True}, {"topic_similarity_threshold": -1},
                     {"semantic_similarity_threshold": .1, "topic_similarity_threshold": .2},
                     {"max_section_sentences": 0}, {"auto_remove_exact_duplicates": 1}):
            with self.subTest(case=case), self.assertRaises(ValueError): SmartEditConfig(**case)
