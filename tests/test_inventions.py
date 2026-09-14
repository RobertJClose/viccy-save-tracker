"""
Tests for the future inventions module (inventions.py stub).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from domains import inventions


class TestStubs(unittest.TestCase):
    """Future tracking modules exist but are not implemented yet."""

    def test_invention_extraction_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            inventions.extract_invention_ids("JAP=\n{\n}\n")


# A synthetic game install: two invention files exercising comments,
# nested blocks, cross-references and unusual-but-valid names.


if __name__ == "__main__":
    unittest.main()
