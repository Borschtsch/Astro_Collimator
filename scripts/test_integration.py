"""Explicit app-workflow validation; never discovers or runs unit test classes."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.integration.test_app import GuiTests
from tests.integration.test_workflows import WorkflowTests


def suite():
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(GuiTests)
    # WorkflowTests inherits the existing Tk/camera harness, not a second run of
    # every inherited scenario. Select only its own integration workflows.
    tests.addTests(WorkflowTests(name) for name in sorted(WorkflowTests.__dict__)
                   if name.startswith("test_"))
    return tests


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(suite())
    raise SystemExit(not result.wasSuccessful())
