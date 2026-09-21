from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass


CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
MAX_CREDENTIAL_BLOB_BYTES = 5120
MAX_CREDENTIAL_TARGET_LENGTH = 256
AEGIS_CREDENTIAL_PREFIX = "Aegis-9/"


class CredentialBrokerError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProtectedCredential:
    username: str
    password: str


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", wintypes.LPVOID), ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
    ]


def read_windows_credential(target: str) -> ProtectedCredential | None:
    """Read a Generic Credential for the current Windows user without logging its secret."""
    target = _validate_target(target)
    if sys.platform != "win32":
        raise CredentialBrokerError("Windows Credential Manager is unavailable on this platform.")
    pointer = ctypes.POINTER(_CREDENTIALW)()
    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]
    if not advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        error = ctypes.get_last_error()
        if error == 1168:
            return None
        raise CredentialBrokerError(f"Windows Credential Manager lookup failed with error {error}.")
    try:
        value = pointer.contents
        blob = ctypes.string_at(value.CredentialBlob, value.CredentialBlobSize)
        return ProtectedCredential(value.UserName or "", blob.decode("utf-16-le"))
    finally:
        advapi32.CredFree(pointer)


def write_windows_credential(target: str, username: str, password: str) -> None:
    """Create or replace a current-user Generic Credential."""
    target = _validate_values(target, username, password)
    username = username.strip()
    if sys.platform != "win32":
        raise CredentialBrokerError("Windows Credential Manager is unavailable on this platform.")
    blob = password.encode("utf-16-le")
    if len(blob) > MAX_CREDENTIAL_BLOB_BYTES:
        raise CredentialBrokerError("Credential secret exceeds the Windows Credential Manager limit.")
    buffer = ctypes.create_string_buffer(blob)
    credential = _CREDENTIALW()
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = username
    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi32.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
    advapi32.CredWriteW.restype = wintypes.BOOL
    if not advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise CredentialBrokerError(f"Windows Credential Manager write failed with error {ctypes.get_last_error()}.")


def delete_windows_credential(target: str) -> bool:
    target = _validate_target(target)
    if sys.platform != "win32":
        raise CredentialBrokerError("Windows Credential Manager is unavailable on this platform.")
    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi32.CredDeleteW.restype = wintypes.BOOL
    if advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0):
        return True
    error = ctypes.get_last_error()
    if error == 1168:
        return False
    raise CredentialBrokerError(f"Windows Credential Manager delete failed with error {error}.")


def _validate_values(target: str, username: str, password: str) -> str:
    target = _validate_target(target)
    if not isinstance(username, str) or not username.strip():
        raise CredentialBrokerError("Credential username must be non-empty.")
    if not isinstance(password, str) or not password:
        raise CredentialBrokerError("Credential password must be non-empty.")
    return target


def _validate_target(target: str) -> str:
    if not isinstance(target, str) or not target.strip():
        raise CredentialBrokerError("Credential target must be a non-empty reference.")
    target = target.strip()
    if len(target) > MAX_CREDENTIAL_TARGET_LENGTH or any(ord(character) < 32 for character in target):
        raise CredentialBrokerError("Credential target contains invalid characters or exceeds the supported length.")
    if not target.startswith(AEGIS_CREDENTIAL_PREFIX) or target == AEGIS_CREDENTIAL_PREFIX:
        raise CredentialBrokerError(f"Credential target must use the {AEGIS_CREDENTIAL_PREFIX} namespace.")
    return target


def resolve_credential(target: str, username: str | None = None, password: str | None = None) -> ProtectedCredential | None:
    """Prefer a complete protected credential, retaining complete legacy values only as fallback."""
    try:
        protected = read_windows_credential(target)
        if protected:
            return protected
    except CredentialBrokerError:
        if sys.platform == "win32":
            raise
    return ProtectedCredential(username, password) if username and password else None
