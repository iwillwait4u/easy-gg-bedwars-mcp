from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creative_scripting_mcp import server


class DocsAndValidationTests(unittest.TestCase):
    def test_full_object_and_type_readers(self) -> None:
        entity = server.read_object("entity")
        ability_type = server.read_type("AbilityType")

        self.assertTrue(entity["found"])
        self.assertIn("getCFrame", entity["method_names"])
        self.assertTrue(ability_type["found"])
        self.assertEqual(ability_type["enum_values"]["RECALL"], "recall")
        self.assertIn("recall", ability_type["string_values"])

        projectile_type = server.read_type("ProjectileType")
        self.assertFalse(projectile_type["enum_keys_documented"])
        self.assertEqual(projectile_type["enum_values"], {})
        self.assertIn("arrow", projectile_type["string_values"])

    def test_exact_doc_search_includes_full_record(self) -> None:
        result = server.search_docs("Entity", limit=1)

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["results"][0]["name"], "Entity")
        self.assertIn("record", result["results"][0])
        self.assertIn("methods", result["results"][0]["record"])

    def test_event_reader_reports_mutability(self) -> None:
        event = server.read_event("EntityDamage")

        self.assertEqual(event["modifiable_fields"], ["damage", "knockback", "cancelled"])
        self.assertIn("entity", event["read_only_fields"])
        self.assertIn("fromEntity", event["read_only_fields"])

    def test_external_validation_checks_fields_methods_enums_and_logic(self) -> None:
        code = """Events.ProjectileHit(function(event)
    print(event.fakeField)
    event.position = Vector3.new(0, 0, 0)
    local target = event.hitEntity
    if target then
        target:fakeMethod()
    end
end)

local alignment = direction:Dot(targetDirection)
if alignment > offset.Magnitude then
    print(AbilityType.NOT_REAL)
end
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "check.lua").write_text(code, encoding="utf-8")

            result = server.validate_directory_script(str(root), "check.lua")

        warnings = "\n".join(result["warnings"])
        self.assertTrue(result["valid"])
        self.assertIn("fakeField is not documented", warnings)
        self.assertIn("position is assigned", warnings)
        self.assertIn("Entity:fakeMethod()", warnings)
        self.assertIn("AbilityType.NOT_REAL", warnings)
        self.assertIn("dot product", warnings)
        self.assertEqual(result["used_event_fields"]["ProjectileHit"], ["fakeField", "hitEntity", "position"])

    def test_validation_reports_unclosed_lua_blocks(self) -> None:
        result = server._validate_lua_code(
            "if true then\n    print(\"missing end\")\n",
            "broken.lua",
        )

        self.assertFalse(result["valid"])
        self.assertIn("expected 'end'", "\n".join(result["syntax_check"]["errors"]))

    def test_event_trace_generation_and_runtime_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = server.create_event_trace(
                str(root),
                ["ProjectileLaunched", "ProjectileHit"],
            )
            trace_path = root / "scripts" / "event_trace.lua"

            self.assertTrue(trace_path.exists())
            self.assertIn("eventTraceSequence", trace_path.read_text(encoding="utf-8"))
            self.assertTrue(result["validation"]["valid"])

        capabilities = server.runtime_capabilities()
        self.assertTrue(capabilities["creative_api"]["projectile_velocity"]["observe"])
        self.assertFalse(capabilities["creative_api"]["projectile_velocity"]["modify"])
        self.assertFalse(capabilities["code_sync_transport"]["read_runtime_console"])

    def test_external_script_edit_returns_diff_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()
            script = scripts / "main.lua"
            script.write_text('ChatService.sendMessage("before")\n', encoding="utf-8")

            result = server.edit_directory_script(
                str(root),
                "main.lua",
                "replace `before` with `after`",
            )

            self.assertEqual(script.read_text(encoding="utf-8"), 'ChatService.sendMessage("after")\n')
            self.assertTrue((scripts / "main.lua.bak").exists())
            self.assertIn("-ChatService.sendMessage(\"before\")", result["diff"])
            self.assertIn("+ChatService.sendMessage(\"after\")", result["diff"])
            self.assertTrue(result["validation"]["valid"])


if __name__ == "__main__":
    unittest.main()
