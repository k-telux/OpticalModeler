"""Check the release scan against real byte/name leaks, without private fixtures."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_validator", ROOT / "scripts/validate_repository.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PublicPrivacyTest(unittest.TestCase):
    def test_identifier_leaks_fail_without_mutation_or_term_disclosure(self):
        secret = "Private-Model-42"
        terms = (VALIDATOR.normalize_identifier(secret),)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for encoding in ("utf-8", "utf-16le", "utf-16be"):
                with self.subTest(encoding=encoding):
                    path = root / f"payload-{encoding}.bin"
                    path.write_bytes(b"\x00\xff" + "private_model / 42".encode(encoding))
                    before = path.read_bytes()
                    with self.assertRaises(AssertionError) as failure:
                        VALIDATOR.check_private_terms(path, terms)
                    self.assertNotIn(secret, str(failure.exception))
                    self.assertEqual(path.read_bytes(), before)
            named = root / "PRIVATE_MODEL_42.txt"
            named.write_text("innocent contents", encoding="utf-8")
            with self.assertRaises(AssertionError) as failure:
                VALIDATOR.check_private_terms(named, terms)
            self.assertNotIn(VALIDATOR.normalize_identifier(secret), VALIDATOR.normalize_identifier(str(failure.exception)))
            clean = root / "public.txt"
            clean.write_text("SPECTROGRAPH: proposed interface; identity withheld", encoding="utf-8")
            VALIDATOR.check_private_terms(clean, terms)


if __name__ == "__main__":
    unittest.main()
