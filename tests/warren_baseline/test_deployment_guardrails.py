"""Proofs for the public-service deployment boundary."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.check_public_tree import scan_paths


ROOT = Path(__file__).resolve().parents[2]


class DeploymentGuardrailTests(unittest.TestCase):
    def test_next_configuration_rejects_a_direct_browser_api_variable(self):
        configuration = (ROOT / "web" / "next.config.ts").read_text(encoding="utf-8")

        self.assertIn('const publicApiVariable = "NEXT_PUBLIC_BASELINE_API_URL"', configuration)
        self.assertIn("INTERNAL_BASELINE_API_URL", configuration)
        self.assertIn('source: "/api/baseline/:path*"', configuration)

    def test_api_and_web_images_copy_only_their_public_runtime_inputs(self):
        api_dockerfile = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
        web_dockerfile = (ROOT / "Dockerfile.web").read_text(encoding="utf-8")

        self.assertNotRegex(api_dockerfile, r"(?m)^COPY \\. \\.$")
        self.assertIn("COPY src ./src", api_dockerfile)
        self.assertIn("COPY releases ./releases", api_dockerfile)
        self.assertNotIn("warren/outputs", api_dockerfile)
        self.assertNotIn("warren/outputs", web_dockerfile)

    def test_compose_keeps_the_api_internal_and_waits_for_its_health_check(self):
        compose = (ROOT / "docker-compose.coolify.yml").read_text(encoding="utf-8")

        self.assertIn("condition: service_healthy", compose)
        self.assertIn("INTERNAL_BASELINE_API_URL: http://api:8998", compose)
        self.assertNotIn("ports:", compose)
        self.assertNotIn("networks:", compose)

    def test_public_tree_guard_rejects_private_paths_and_fields_without_values(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            release = root / "releases" / "warren"
            release.mkdir(parents=True)
            release.joinpath("summary.json").write_text(
                '{"town":"Warren","nested":{"mailing_state":"CA"}}', encoding="utf-8"
            )

            diagnostics = scan_paths(
                root,
                ["warren/outputs/private.jsonl", "releases/warren/summary.json"],
            )

        self.assertEqual(
            diagnostics,
            [
                "releases/warren/summary.json: invalid public artifact",
                "releases/warren/summary.json: restricted field nested.mailing_state",
                "warren/outputs/private.jsonl: tracked private-data path",
            ],
        )
        self.assertNotIn("CA", "\n".join(diagnostics))

    def test_compose_file_validates_when_docker_is_available(self):
        if not self._docker_compose_available():
            self.skipTest("Docker Compose is unavailable in this test environment")
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose.coolify.yml", "config", "--quiet"],
            cwd=ROOT,
            check=True,
        )

    @staticmethod
    def _docker_compose_available() -> bool:
        return (
            subprocess.run(
                ["docker", "compose", "version"], capture_output=True, check=False
            ).returncode
            == 0
        )
