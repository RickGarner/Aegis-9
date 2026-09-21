import unittest
from unittest.mock import patch

from app.credential_broker import CredentialBrokerError, ProtectedCredential, delete_windows_credential, read_windows_credential, resolve_credential, write_windows_credential


class CredentialBrokerTests(unittest.TestCase):
    def test_rejects_empty_reference(self):
        with self.assertRaises(CredentialBrokerError):
            read_windows_credential("")

    @patch("app.credential_broker.sys.platform", "linux")
    def test_fails_closed_off_windows(self):
        with self.assertRaisesRegex(CredentialBrokerError, "unavailable"):
            read_windows_credential("Aegis-9/Test")

    def test_write_rejects_empty_values_before_platform_access(self):
        for username, password in (("", "secret"), ("reader", "")):
            with self.assertRaises(CredentialBrokerError):
                write_windows_credential("Aegis-9/Test", username, password)

    def test_rejects_targets_outside_aegis_namespace(self):
        for target in ("OtherApp/Test", "Aegis-9/", "Aegis-9/Test\nInjected"):
            with self.assertRaises(CredentialBrokerError):
                read_windows_credential(target)

    @patch("app.credential_broker.sys.platform", "linux")
    def test_delete_fails_closed_off_windows(self):
        with self.assertRaisesRegex(CredentialBrokerError, "unavailable"):
            delete_windows_credential("Aegis-9/Test")

    @patch("app.credential_broker.read_windows_credential")
    def test_protected_credential_precedes_legacy_values(self, read):
        read.return_value = ProtectedCredential("protected-reader", "protected-secret")
        value = resolve_credential("Aegis-9/Test", "legacy", "legacy-secret")
        self.assertEqual("protected-reader", value.username)

    @patch("app.credential_broker.read_windows_credential", return_value=None)
    def test_complete_legacy_pair_is_compatibility_fallback(self, _read):
        value = resolve_credential("Aegis-9/Test", "legacy", "legacy-secret")
        self.assertEqual(ProtectedCredential("legacy", "legacy-secret"), value)

    @patch("app.credential_broker.sys.platform", "win32")
    @patch("app.credential_broker.read_windows_credential", side_effect=CredentialBrokerError("access denied"))
    def test_windows_broker_error_does_not_fall_back_to_plaintext(self, _read):
        with self.assertRaisesRegex(CredentialBrokerError, "access denied"):
            resolve_credential("Aegis-9/Test", "legacy", "legacy-secret")
