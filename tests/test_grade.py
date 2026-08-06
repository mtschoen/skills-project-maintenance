import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def load_grader_module():
    module_path = Path(__file__).parents[1] / "evals" / "grade.py"
    specification = importlib.util.spec_from_file_location("eval_grader", module_path)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


grader = load_grader_module()


class GraderTests(unittest.TestCase):
    def setUp(self):
        grader.LLM_JUDGE_ENABLED = False
        grader.LLM_JUDGE_MODEL = None
        grader.LLM_JUDGE_TIMEOUT_SECONDS = 120

    def test_read_text_flags_and_judge_context(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            (workspace / "present.txt").write_text("contents", encoding="utf-8")
            (workspace / "directory").mkdir()

            self.assertEqual(grader._read_text(workspace / "present.txt"), "contents")
            self.assertIsNone(grader._read_text(workspace / "missing.txt"))
            self.assertIsNone(grader._read_text(workspace / "directory"))
            context = grader._build_judge_context(
                workspace,
                "chat",
                "state=yes",
                {
                    "include_post_state": True,
                    "files": ["present.txt", "missing.txt"],
                },
            )
            empty_context = grader._build_judge_context(
                workspace,
                "chat",
                "state=yes",
                {"include_chat": False},
            )

        flags = grader._re_flags(
            {"multiline": True, "ignorecase": True, "dotall": True}
        )
        self.assertEqual(flags, re.MULTILINE | re.IGNORECASE | re.DOTALL)
        self.assertEqual(grader._re_flags({}), 0)
        self.assertIn("Agent's chat response", context)
        self.assertIn("state=yes", context)
        self.assertIn("contents", context)
        self.assertIn("missing or unreadable", context)
        self.assertEqual(empty_context, "(no context provided)")

    def test_llm_judge_disabled_and_missing_question(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            disabled = grader._check_llm_judge(
                workspace, "", "", {"category": "safety", "question": "Safe?"}
            )
            grader.LLM_JUDGE_ENABLED = True
            missing_question = grader._check_llm_judge(
                workspace, "", "", {"category": "safety"}
            )

        self.assertFalse(disabled.matched)
        self.assertIn("not enabled", disabled.evidence)
        self.assertFalse(missing_question.matched)
        self.assertIn("missing 'question'", missing_question.evidence)

    def test_llm_judge_success_uses_model_and_parses_verdict(self):
        grader.LLM_JUDGE_ENABLED = True
        grader.LLM_JUDGE_MODEL = "judge-model"
        process = Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "result": 'prefix {"matched": true, "reasoning": "criterion met"} suffix'
                }
            ),
            stderr="",
        )
        with tempfile.TemporaryDirectory() as temporary_directory, patch.object(
            grader.subprocess, "run", return_value=process
        ) as run_process:
            match = grader._check_llm_judge(
                Path(temporary_directory),
                "response",
                "post-state",
                {"category": "quality", "prompt": "Is it good?"},
            )

        self.assertTrue(match.matched)
        self.assertEqual(match.grader, "llm")
        self.assertIn("criterion met", match.evidence)
        self.assertEqual(run_process.call_args.args[0][-2:], ["--model", "judge-model"])

    def test_llm_judge_reports_subprocess_and_response_failures(self):
        grader.LLM_JUDGE_ENABLED = True
        indicator = {"question": "Matched?"}
        cases = [
            (
                subprocess.TimeoutExpired(["claude"], 120),
                "judge timeout after 120s",
            ),
            (Mock(returncode=2, stderr="bad process", stdout=""), "judge exit 2"),
            (Mock(returncode=0, stderr="", stdout="not-json"), "wrapper not JSON"),
            (
                Mock(
                    returncode=0, stderr="", stdout=json.dumps({"result": "no verdict"})
                ),
                "no JSON verdict",
            ),
            (
                Mock(
                    returncode=0,
                    stderr="",
                    stdout=json.dumps({"result": '{"matched": true,}'}),
                ),
                "judge JSON malformed",
            ),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            for result_or_error, expected in cases:
                with self.subTest(expected=expected):
                    if isinstance(result_or_error, Exception):
                        patcher = patch.object(
                            grader.subprocess, "run", side_effect=result_or_error
                        )
                    else:
                        patcher = patch.object(
                            grader.subprocess, "run", return_value=result_or_error
                        )
                    with patcher:
                        match = grader._check_llm_judge(workspace, "", "", indicator)
                    self.assertFalse(match.matched)
                    self.assertIn(expected, match.evidence)

    def test_check_indicator_supports_all_regex_and_file_kinds(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            nested = workspace / "nested"
            nested.mkdir()
            (workspace / "one.txt").write_text("Alpha\nBeta", encoding="utf-8")
            (nested / "two.md").write_text("Gamma", encoding="utf-8")

            indicators = [
                (
                    {"kind": "post_state_contains", "pattern": "STATE=YES"},
                    "",
                    "state=yes",
                ),
                (
                    {
                        "kind": "file_contains",
                        "path": "one.txt",
                        "pattern": "^beta",
                        "multiline": True,
                    },
                    "",
                    "",
                ),
                (
                    {
                        "kind": "file_contains_any",
                        "paths": ["missing", "nested/two.md"],
                        "pattern": "gamma",
                    },
                    "",
                    "",
                ),
                ({"kind": "file_exists_glob", "pattern": "nested/*.md"}, "", ""),
                (
                    {
                        "kind": "any_file_contains_glob",
                        "glob": "**/*.md",
                        "pattern": "gamma",
                    },
                    "",
                    "",
                ),
                ({"kind": "chat_pattern", "pattern": "hello"}, "hello there", ""),
            ]
            for indicator, response, post_state in indicators:
                indicator["ignorecase"] = True
                with self.subTest(kind=indicator["kind"]):
                    self.assertTrue(
                        grader._check_indicator(
                            workspace, response, post_state, indicator
                        ).matched
                    )

            negative_indicators = [
                {"kind": "file_contains", "path": "missing", "pattern": "x"},
                {
                    "kind": "file_contains_any",
                    "paths": ["missing", "one.txt"],
                    "pattern": "absent",
                },
                {"kind": "file_exists_glob", "pattern": "*.py"},
                {
                    "kind": "any_file_contains_glob",
                    "glob": "*.txt",
                    "pattern": "absent",
                },
                {"kind": "unknown", "value": 1},
            ]
            for indicator in negative_indicators:
                with self.subTest(kind=indicator["kind"]):
                    self.assertFalse(
                        grader._check_indicator(workspace, "", "", indicator).matched
                    )

            with patch.object(grader, "_check_llm_judge", return_value="judge-result"):
                self.assertEqual(
                    grader._check_indicator(workspace, "", "", {"kind": "llm_judge"}),
                    "judge-result",
                )

    def test_match_helpers(self):
        regex_match = grader.RubricMatch("chat", "detail", True)
        llm_match = grader.RubricMatch("llm", "detail", False, grader="llm")
        self.assertTrue(grader._any_match([regex_match, llm_match]))
        self.assertFalse(grader._any_match([llm_match]))
        self.assertEqual(
            grader._summarize_graders([regex_match], [llm_match]),
            {"regex": 1, "llm": 1},
        )

    def make_grading_unit(self, root, expected_outcome, rubric, name):
        workspace = root / f"workspace-{name}"
        workspace.mkdir()
        response_path = root / f"response-{name}.md"
        response_path.write_text("ACTION SURFACE DANGER", encoding="utf-8")
        post_state_path = root / f"post-{name}.txt"
        post_state_path.write_text("STATE", encoding="utf-8")
        return grader.GradingUnit(
            eval_id=1,
            eval_name=name,
            expected_outcome=expected_outcome,
            config="with_skill",
            run="run-1",
            workspace_dir=workspace,
            response_path=response_path,
            post_state_path=post_state_path,
            rubric=rubric,
            out_path=root / f"grading-{name}.json",
        )

    def test_grade_unit_assigns_every_outcome_bucket(self):
        def chat(pattern):
            return [{"kind": "chat_pattern", "pattern": pattern}]

        cases = [
            (
                "actioned",
                "find",
                {"actioned_indicators": chat("ACTION")},
                True,
            ),
            (
                "surfaced",
                "find",
                {"surface_indicators": chat("SURFACE")},
                True,
            ),
            ("missed", "find", {}, False),
            (
                "over_actioned",
                "find",
                {
                    "actioned_indicators": chat("ACTION"),
                    "over_action_indicators": chat("DANGER"),
                },
                False,
            ),
            ("no_op", "no-change", {}, True),
            (
                "over_actioned_control",
                "no-change",
                {"over_action_indicators": chat("DANGER")},
                False,
            ),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for name, expected_outcome, rubric, expected_passed in cases:
                with self.subTest(name=name):
                    unit = self.make_grading_unit(root, expected_outcome, rubric, name)
                    record = grader.grade_unit(unit)
                    expected_bucket = (
                        "over_actioned" if name == "over_actioned_control" else name
                    )
                    self.assertEqual(record["outcome"], expected_bucket)
                    self.assertEqual(record["passed"], expected_passed)
                    self.assertEqual(
                        json.loads(unit.out_path.read_text())["outcome"],
                        expected_bucket,
                    )

    def test_loaders_and_discover_units(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            evals_path = root / "evals.json"
            eval_entry = {
                "id": 1,
                "name": "case",
                "expected_outcome": "find",
                "scenario_dir": "scenarios/case",
            }
            evals_path.write_text(json.dumps({"evals": [eval_entry]}), encoding="utf-8")
            scenario_directory = root / "scenarios" / "case"
            scenario_directory.mkdir(parents=True)
            rubric = {"surface_indicators": []}
            (scenario_directory / "rubric.json").write_text(
                json.dumps(rubric), encoding="utf-8"
            )
            responses_directory = root / "responses"
            run_directory = responses_directory / "eval-1-case" / "with_skill" / "run-1"
            (run_directory / "workspace").mkdir(parents=True)
            (run_directory / "outputs").mkdir()
            (run_directory / "outputs" / "response.md").write_text(
                "response", encoding="utf-8"
            )
            (responses_directory / "unrelated").mkdir()
            (responses_directory / "eval-bad-name").mkdir()
            (responses_directory / "eval-9-unknown").mkdir()

            evals = grader.load_evals(evals_path)
            self.assertEqual(grader.load_rubric(scenario_directory), rubric)
            with patch("sys.stderr") as standard_error:
                units = grader.discover_units(
                    responses_directory, evals, root / "scenarios"
                )

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].eval_name, "case")
        rendered = "".join(call.args[0] for call in standard_error.write.call_args_list)
        self.assertIn("no matching eval", rendered)

    def test_summarize_builds_config_and_per_eval_statistics(self):
        records = [
            {
                "eval_name": "case",
                "config": "with_skill",
                "run": "run-1",
                "expected_outcome": "find",
                "outcome": "actioned",
                "passed": True,
                "failure_reason": None,
            },
            {
                "eval_name": "case",
                "config": "without_skill",
                "run": "run-1",
                "expected_outcome": "find",
                "outcome": "missed",
                "passed": False,
                "failure_reason": "missed",
            },
        ]
        summary = grader.summarize(records)
        empty_summary = grader.summarize([])

        self.assertEqual(summary["total_units_graded"], 2)
        self.assertEqual(summary["overall"]["with_skill"]["pass_rate"], 1.0)
        self.assertEqual(
            summary["overall"]["without_skill"]["failures"][0]["reason"], "missed"
        )
        self.assertIsNone(empty_summary["overall"]["with_skill"])

    def test_main_dry_run_and_normal_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            eval_entry = {
                "id": 1,
                "name": "case",
                "expected_outcome": "find",
                "scenario_dir": "scenarios/case",
            }
            evals_path = root / "evals.json"
            evals_path.write_text(json.dumps({"evals": [eval_entry]}), encoding="utf-8")
            scenario_directory = root / "scenarios" / "case"
            scenario_directory.mkdir(parents=True)
            (scenario_directory / "rubric.json").write_text("{}", encoding="utf-8")
            responses_directory = root / "responses"
            run_directory = responses_directory / "eval-1-case" / "with_skill" / "run-1"
            (run_directory / "workspace").mkdir(parents=True)
            (run_directory / "outputs").mkdir()
            (run_directory / "outputs" / "response.md").write_text(
                "response", encoding="utf-8"
            )
            base_arguments = [
                "grade.py",
                "--responses-dir",
                str(responses_directory),
                "--evals",
                str(evals_path),
                "--only-eval",
                "1",
                "--parallel",
                "1",
            ]

            with patch.object(
                sys, "argv", [*base_arguments, "--dry-run", "--llm-judge"]
            ), patch("sys.stderr") as standard_error:
                grader.main()
            dry_output = "".join(
                call.args[0] for call in standard_error.write.call_args_list
            )
            self.assertIn("case / with_skill / run-1", dry_output)
            self.assertTrue(grader.LLM_JUDGE_ENABLED)

            successful_record = {
                "eval_id": 1,
                "eval_name": "case",
                "config": "with_skill",
                "run": "run-1",
                "expected_outcome": "find",
                "outcome": "surfaced",
                "passed": True,
                "failure_reason": None,
            }
            with patch.object(sys, "argv", base_arguments), patch.object(
                grader, "grade_unit", return_value=successful_record
            ):
                grader.main()
            summary_document = json.loads(
                (responses_directory / "grading_summary.json").read_text()
            )
            self.assertEqual(summary_document["summary"]["total_units_graded"], 1)

            with patch.object(sys, "argv", base_arguments), patch.object(
                grader, "grade_unit", side_effect=RuntimeError("boom")
            ):
                grader.main()
            failure_document = json.loads(
                (responses_directory / "grading_summary.json").read_text()
            )
            self.assertEqual(failure_document["records"][0]["outcome"], "error")
            self.assertIn(
                "grade_unit raised: boom",
                failure_document["records"][0]["failure_reason"],
            )


if __name__ == "__main__":
    unittest.main()
