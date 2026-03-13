"""Tests for create-stateweave-agent template."""

import shutil
import tempfile
import unittest
from pathlib import Path

from stateweave.templates.create_agent import create_project


class TestCreateProject(unittest.TestCase):
    """Test project scaffolding."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_project_directory(self):
        result = create_project("my-agent", output_dir=self.tmpdir)
        self.assertTrue(Path(result["project_dir"]).exists())

    def test_creates_agent_file(self):
        result = create_project("my-agent", output_dir=self.tmpdir)
        agent_path = Path(result["files"]["agent"])
        self.assertTrue(agent_path.exists())
        content = agent_path.read_text()
        self.assertIn("auto_checkpoint", content)
        self.assertIn("my-agent", content)

    def test_creates_export_script(self):
        result = create_project("my-agent", framework="crewai", output_dir=self.tmpdir)
        export_path = Path(result["files"]["export"])
        self.assertTrue(export_path.exists())
        content = export_path.read_text()
        self.assertIn("crewai", content)

    def test_creates_requirements(self):
        result = create_project("my-agent", output_dir=self.tmpdir)
        req_path = Path(result["files"]["requirements"])
        self.assertTrue(req_path.exists())
        content = req_path.read_text()
        self.assertIn("stateweave", content)

    def test_creates_ci_workflow(self):
        result = create_project("my-agent", output_dir=self.tmpdir)
        ci_path = Path(result["files"]["ci"])
        self.assertTrue(ci_path.exists())
        content = ci_path.read_text()
        self.assertIn("stateweave doctor", content)
        self.assertIn("GDWN-BLDR/stateweave-action", content)

    def test_creates_readme(self):
        result = create_project("my-agent", output_dir=self.tmpdir)
        readme_path = Path(result["files"]["readme"])
        self.assertTrue(readme_path.exists())
        content = readme_path.read_text()
        self.assertIn("my-agent", content)
        self.assertIn("StateWeave", content)

    def test_custom_framework(self):
        result = create_project("test-bot", framework="dspy", output_dir=self.tmpdir)
        agent_content = Path(result["files"]["agent"]).read_text()
        self.assertIn("dspy", agent_content)

    def test_agent_id_normalized(self):
        result = create_project("My Cool Agent", output_dir=self.tmpdir)
        agent_content = Path(result["files"]["agent"]).read_text()
        self.assertIn("my-cool-agent", agent_content)


if __name__ == "__main__":
    unittest.main()
