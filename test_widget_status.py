"""Run the v1.0.7 status contract through the combined widget entry point."""
from pathlib import Path
import runpy
from unittest.mock import patch
import test_status_speech


class CombinedWidgetStatusTests(test_status_speech.StatusVoiceTests):
    def setUp(self):
        widget_build = runpy.run_path(str(Path(__file__).parent / 'widget/build_skill.py'))['build']
        with patch.object(test_status_speech, 'build', widget_build):
            super().setUp()
