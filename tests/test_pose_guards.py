"""Exercise refusal paths with a fake Robot; no hardware modules or connections."""
import importlib.util
from pathlib import Path
import sys
import types
import numpy  # Load before patch.dict restores sys.modules.
import unittest
from unittest.mock import Mock, patch


class PoseGuards(unittest.TestCase):
    def load_pose(self):
        robot_module = types.ModuleType("dexcontrol.robot")
        robot_module.Robot = Mock(side_effect=AssertionError("Robot must not be constructed"))
        spec = importlib.util.spec_from_file_location("pose_under_test",
            Path(__file__).resolve().parents[1] / "software/poses/goto_pose.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"dexcontrol": types.ModuleType("dexcontrol"), "dexcontrol.robot": robot_module}):
            spec.loader.exec_module(module)
        return module, robot_module.Robot

    def test_banned_pose_refused_before_robot_construction(self):
        module, robot = self.load_pose()
        with patch.object(sys, "argv", ["goto_pose.py", "folded"]):
            with self.assertRaises(SystemExit):
                module.main()
        robot.assert_not_called()

    def test_invalid_step_wait_or_clearance_refused_before_robot(self):
        for option, value in [("--step", "0"), ("--step", "nan"), ("--wait", "-1"), ("--min-sep", "inf")]:
            module, robot = self.load_pose()
            with patch.object(sys, "argv", ["goto_pose.py", "pre_move", option, value]):
                with self.assertRaises(SystemExit):
                    module.main()
            robot.assert_not_called()

    def test_missing_fk_does_not_silently_allow_motion(self):
        module, robot = self.load_pose()
        with patch.object(module, "_fk_setup", side_effect=ImportError("missing pinocchio")):
            with self.assertRaises(SystemExit):
                module.check_path({}, {}, 0.04)
        robot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
