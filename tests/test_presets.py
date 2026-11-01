"""Tests for composing a vault's folders from packs, roles, and choices.

Stdlib unittest only — the repo has no runtime dependencies and the test
suite keeps it that way. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import unittest

from llm_wiki.layout import Layout, validate
from llm_wiki.presets import ADDONS, DEFAULT_PACK, DEMO_PAGES, PACKS, ROLES, PresetError, catalog, compose


class CatalogTests(unittest.TestCase):
    def test_default_pack_is_standard(self):
        self.assertEqual(DEFAULT_PACK, "standard")

    def test_standard_is_the_four_page_types_of_the_gist(self):
        self.assertEqual(
            [folder.folder for folder in PACKS["standard"].folders],
            ["references", "entities", "synthesis", "concepts"],
        )

    def test_minimal_is_one_wiki_folder(self):
        self.assertEqual([folder.folder for folder in PACKS["minimal"].folders], ["wiki"])
        self.assertFalse(PACKS["minimal"].takes_roles)

    def test_roles_add_the_agreed_folders(self):
        adds = {name: [ADDONS[a].folder for a in role.adds] for name, role in ROLES.items()}
        self.assertEqual(
            adds,
            {
                "learner": ["courses"],
                "researcher": ["questions"],
                "indie-hacker": ["projects"],
                "creator": ["ideas", "outputs"],
                "team": ["meetings", "decisions"],
                "personal": ["journal"],
            },
        )

    def test_every_pack_and_addon_is_a_valid_layout_on_its_own(self):
        for pack in PACKS.values():
            with self.subTest(pack=pack.name):
                self.assertEqual(validate(compose(pack.name).categories), [])
        everything = compose("standard", roles=ROLES)
        self.assertEqual(validate(everything.categories), [])

    def test_demo_pages_cover_the_four_page_types(self):
        self.assertEqual(set(DEMO_PAGES.values()), {"reference", "entity", "synthesis", "concept"})

    def test_catalog_is_plain_data(self):
        data = catalog()
        self.assertEqual(data["default_pack"], "standard")
        self.assertEqual([pack["name"] for pack in data["packs"]], list(PACKS))
        team = next(role for role in data["roles"] if role["name"] == "team")
        self.assertEqual(team["adds"], ["meetings", "decisions"])
        self.assertTrue(team["suggests"]["staged_writes"])


class ComposeTests(unittest.TestCase):
    def test_standard_alone(self):
        plan = compose()
        self.assertEqual(plan.folders, ("references", "entities", "synthesis", "concepts"))
        self.assertEqual(Layout(plan.categories, "AGENTS.md").catch_all.folder, "concepts")

    def test_role_folders_come_before_the_pack_rows(self):
        plan = compose(roles=["creator", "indie-hacker"])
        self.assertEqual(
            plan.folders,
            ("projects", "ideas", "outputs", "references", "entities", "synthesis", "concepts"),
        )

    def test_overlapping_roles_add_a_folder_once(self):
        plan = compose(roles=["team"], addons=["decisions"])
        self.assertEqual(plan.folders.count("decisions"), 1)
        self.assertEqual(plan.addons, ())

    def test_explicit_addon_is_recorded(self):
        self.assertEqual(compose(addons=["journal"]).addons, ("journal",))

    def test_own_folder_sits_just_above_the_pack_rows(self):
        plan = compose(roles=["learner"], folders=[("recipes", "Cooking recipes")])
        self.assertEqual(plan.folders, ("courses", "recipes", "references", "entities", "synthesis", "concepts"))
        recipes = plan.rows[1]
        self.assertEqual((recipes.role, recipes.template, recipes.template_as), (None, "page", "recipes"))
        self.assertEqual(plan.custom, ("recipes",))

    def test_rename_keeps_the_role(self):
        plan = compose(renames=[("concepts", "notes")])
        self.assertEqual(plan.folders[-1], "notes")
        self.assertEqual(Layout(plan.categories, "AGENTS.md").folder_for("concept"), "notes")
        self.assertEqual(plan.rows[-1].template_as, "concept")

    def test_rename_of_own_folder_renames_its_template(self):
        plan = compose(folders=[("recipes", "x")], renames=[("recipes", "cooking")])
        self.assertEqual(plan.rows[0].template_as, "cooking")

    def test_minimal_can_rename_its_folder(self):
        self.assertEqual(compose("minimal", renames=[("wiki", "notes")]).folders, ("notes",))

    def test_category_value_is_the_folder_or_the_kind(self):
        standard = compose()
        self.assertEqual(standard.category_value(standard.rows[0], "reference"), "references")
        minimal = compose("minimal")
        self.assertEqual(minimal.category_value(minimal.rows[0], "entity"), "entities")
        self.assertEqual(minimal.category_value(minimal.rows[0]), "concepts")

    def test_suggestions_follow_the_roles(self):
        self.assertTrue(compose(roles=["team"]).suggests_staged_writes())
        self.assertFalse(compose(roles=["creator"]).suggests_staged_writes())
        self.assertTrue(compose(roles=["indie-hacker"]).suggests_history_import())


class ComposeProblemTests(unittest.TestCase):
    def assertProblem(self, fragment: str, **kwargs) -> None:
        with self.assertRaises(PresetError) as caught:
            compose(**kwargs)
        self.assertTrue(
            any(fragment in problem for problem in caught.exception.problems),
            f"{fragment!r} not in {caught.exception.problems}",
        )

    def test_unknown_pack(self):
        self.assertProblem("unknown pack", pack="zettelkasten")

    def test_minimal_takes_no_additions(self):
        self.assertProblem("single folder", pack="minimal", roles=["learner"])
        self.assertProblem("single folder", pack="minimal", folders=[("recipes", "x")])

    def test_unknown_role_and_addon(self):
        self.assertProblem("unknown role", roles=["wizard"])
        self.assertProblem("unknown add-on", addons=["wizards"])

    def test_own_folder_needs_a_description(self):
        self.assertProblem("needs a description", folders=[("recipes", "  ")])

    def test_own_folder_with_a_bad_name(self):
        self.assertProblem("lowercase", folders=[("My Recipes", "x")])
        self.assertProblem("system folders", folders=[("_recipes", "x")])

    def test_own_folder_clashing_with_an_existing_folder(self):
        self.assertProblem("more than once", roles=["creator"], folders=[("ideas", "x")])

    def test_own_folder_named_like_a_vault_page(self):
        self.assertProblem("already the name of a vault page", folders=[("index", "x")])
        self.assertProblem("already the name of a vault page", folders=[("llm-wiki-pattern", "x")])

    def test_own_folder_clashing_with_a_page_template(self):
        self.assertProblem("page template", folders=[("concept", "x")])

    def test_rename_of_a_missing_folder(self):
        self.assertProblem("no such folder", renames=[("skills", "how-to")])

    def test_rename_onto_an_existing_folder(self):
        self.assertProblem("more than once", renames=[("concepts", "entities")])


if __name__ == "__main__":
    unittest.main()
