from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creative_scripting_mcp import server


class ReferenceAnalysisTests(unittest.TestCase):
    def test_reference_audit_returns_aggregates_without_source_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "mcp-data"
            data_dir.mkdir()
            (data_dir / "confirmed-script-evidence.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "title": "Persistent interaction",
                                "status": "script_embedded_in_thread",
                                "content": "private source wording",
                                "codeBlocks": [
                                    'DataStoreService.setAsync("key", 1)\n'
                                    'ButtonService.create("Open")\n'
                                    "Events.PlayerChatted(function(event) end)"
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8-sig",
            )
            (data_dir / "needs-review.json").write_text(
                json.dumps({"records": [{"status": "not_confirmed"}]}),
                encoding="utf-8",
            )

            result = server.audit_reference_export(str(root))

        serialized = json.dumps(result)
        self.assertEqual(result["confirmed_record_count"], 1)
        self.assertEqual(result["needs_review_count"], 1)
        self.assertEqual(result["official_service_calls"][0]["service"], "DataStoreService")
        self.assertEqual(result["community_only_services"][0]["service"], "ButtonService")
        self.assertIn("persistence", result["mechanic_theme_counts"])
        self.assertFalse(result["content_returned"])
        self.assertNotIn("private source wording", serialized)
        self.assertNotIn("DataStoreService.setAsync", serialized)

    def test_mechanic_recommendations_use_official_docs(self) -> None:
        result = server.recommend_mechanic_apis("save player positions with persistent data")

        self.assertEqual(result["matches"][0]["mechanic"], "persistence")
        services = result["matches"][0]["services"]
        self.assertEqual(services[0]["name"], "DataStoreService")
        self.assertTrue(services[0]["officially_documented"])

    def test_combined_dataset_fallback_only_analyzes_confirmed_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "mcp-data"
            data_dir.mkdir()
            (data_dir / "bedwars-scripts-mcp-dataset.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "status": "script_embedded_in_thread",
                                "codeBlocks": ['DataStoreService.setAsync("key", 1)'],
                            },
                            {
                                "status": "not_confirmed_needs_thread_open",
                                "codeBlocks": ['FakeService.run("untrusted")'],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = server.audit_reference_export(str(root))

        self.assertTrue(result["used_combined_dataset_fallback"])
        self.assertEqual(result["confirmed_record_count"], 1)
        self.assertEqual(result["needs_review_count"], 1)
        self.assertEqual(result["community_only_services"], [])

    def test_mechanic_recipes_only_link_cached_official_records(self) -> None:
        docs = server._load_docs_cache()

        for mechanic, recipe in server.MECHANIC_API_RECIPES.items():
            for category in ("services", "events", "objects", "types"):
                for name in recipe[category]:
                    with self.subTest(mechanic=mechanic, category=category, name=name):
                        self.assertIsNotNone(server._casefold_lookup(docs[category], name))

    def test_algorithm_guides_are_original_and_use_cached_official_records(self) -> None:
        result = server.recommend_algorithm("target selection with line of sight")
        serialized = json.dumps(result)

        algorithms = {match["algorithm"] for match in result["matches"]}
        self.assertIn("target_selection", algorithms)
        self.assertIn("segment_visibility", algorithms)
        self.assertFalse(result["source_content_included"])
        self.assertNotIn("realistic aimbot", serialized.casefold())

        docs = server._load_docs_cache()
        for algorithm, guide in server.ALGORITHM_GUIDES.items():
            for category in ("services", "events", "objects", "types"):
                for name in guide[category]:
                    with self.subTest(algorithm=algorithm, category=category, name=name):
                        self.assertIsNotNone(server._casefold_lookup(docs[category], name))

    def test_aimbot_label_resolves_as_creative_target_assist(self) -> None:
        result = server.resolve_creative_mechanic("host-only aimbot with wall checks")

        self.assertTrue(result["recognized"])
        self.assertTrue(result["creative_host_panel_scope"])
        self.assertEqual(
            result["matched_aliases"][0]["canonical_mechanic"],
            "projectile_target_assist",
        )
        algorithms = {
            match["algorithm"]
            for match in result["algorithm_guidance"]["matches"]
        }
        self.assertIn("target_selection", algorithms)
        self.assertIn("segment_visibility", algorithms)
        self.assertIn("not documented as modifiable", "\n".join(result["capability_limits"]))

    def test_movement_labels_resolve_without_blacklisting(self) -> None:
        for prompt in ("fly ability", "host speed mechanic"):
            with self.subTest(prompt=prompt):
                result = server.resolve_creative_mechanic(prompt)
                algorithms = {
                    match["algorithm"]
                    for match in result["algorithm_guidance"]["matches"]
                }
                self.assertTrue(result["recognized"])
                self.assertIn("creative_movement", algorithms)

    def test_mechanic_words_are_not_prompt_blacklisted(self) -> None:
        for prompt in (
            "aimbot",
            "KA for my private creative match",
            "connect my sync token and session",
        ):
            with self.subTest(prompt=prompt):
                try:
                    server._generate_script_from_prompt(prompt)
                except server.BedWarsMcpError as exc:
                    message = str(exc)
                    self.assertNotIn("Blocked unsafe", message)
                    self.assertNotIn("out-of-scope terms", message)

        with self.assertRaisesRegex(
            server.BedWarsMcpError,
            "Recognized this as a custom Creative mechanic",
        ):
            server._generate_script_from_prompt("aimbot")

    def test_button_service_gets_specific_validation_guidance(self) -> None:
        result = server._validate_lua_code(
            'ButtonService.create("Open")\n',
            "button.lua",
        )

        warning_text = "\n".join(result["warnings"])
        self.assertIn("community reference material", warning_text)
        self.assertIn("PromptService", warning_text)
        self.assertIn("InputService", warning_text)

    def test_validate_directory_project_summarizes_all_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "good.lua").write_text(
                'MessageService.broadcast("ok")\n',
                encoding="utf-8",
            )
            (scripts / "warning.lua").write_text(
                'ButtonService.create("Open")\n',
                encoding="utf-8",
            )

            result = server.validate_directory_project(str(root))

        self.assertEqual(result["file_count"], 2)
        self.assertTrue(result["valid"])
        self.assertEqual(result["warning_count"], 1)
        self.assertEqual(result["files_with_warnings"], ["scripts/warning.lua"])


if __name__ == "__main__":
    unittest.main()
