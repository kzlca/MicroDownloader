"""Static guardrails for CI-specific Qt layout regressions.

These are deliberately additional to the real Qt headless smoke test; they do
not replace it. They can run without PySide6 in local source-only environments.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class GuiLayoutRegression(unittest.TestCase):
    def test_intercept_dialog_is_real_qdialog(self):
        tree = ast.parse((ROOT / 'scripts/smoke_ui.py').read_text(encoding='utf-8'))
        classes = [node for node in ast.walk(tree)
                   if isinstance(node, ast.ClassDef) and node.name == 'InterceptDialog']
        self.assertEqual(len(classes), 1)
        self.assertTrue(any(isinstance(base, ast.Name) and base.id == 'QDialog'
                            for base in classes[0].bases))

    def test_action_buttons_allow_narrow_layout(self):
        source = (ROOT / 'micro_downloader/widgets.py').read_text(encoding='utf-8')
        self.assertIn('btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)', source)
        self.assertIn('btn.setMinimumWidth(0)', source)
        self.assertIn('cols = 4 if width >= 770 else 3 if width >= 560 else 2 if width >= 330 else 1', source)

    def test_header_action_layout_is_only_inserted_once(self):
        source = (ROOT / 'micro_downloader/ui.py').read_text(encoding='utf-8')
        self.assertEqual(source.count('header.addLayout(self.header_actions)'), 1)


if __name__ == '__main__':
    unittest.main()
