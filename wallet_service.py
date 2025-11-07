"""
Wallet service that provides user-scoped instances of ``SparkWalletManager``.

This abstraction ensures that each Telegram user operates on their own
wallet storage directory, preventing accidental data leakage between users.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, Optional

from spark_wallet import SparkWalletManager

# Root directory where all user-specific wallet data is stored. Can be
# overridden via the ``SPARK_WALLET_ROOT`` environment variable.
_DEFAULT_ROOT = Path(os.getenv("SPARK_WALLET_ROOT", "./spark_wallets"))

# In-memory cache of wallet managers keyed by user identifier.
_user_wallet_managers: Dict[int, SparkWalletManager] = {}

# Optional mapping from Telegram user ids to custom storage aliases.
_user_storage_aliases: Dict[int, str] = {}

# Optional factory override (primarily for tests) that allows injecting a
# custom ``SparkWalletManager`` constructor.
_wallet_manager_factory: Optional[Callable[[int], SparkWalletManager]] = None


def _sanitize_alias(alias: str) -> str:
    sanitized = alias.strip().replace("..", "").replace("/", "_").replace("\\", "_")
    return sanitized or "anonymous"


def _storage_path_for(user_id: int, root: Path) -> Path:
    """Return the storage path for a specific user."""

    alias = _user_storage_aliases.get(user_id)
    if alias is None:
        alias = str(user_id)
    safe_alias = _sanitize_alias(alias)
    return root / safe_alias


def configure_wallet_manager_factory(factory: Optional[Callable[[int], SparkWalletManager]]) -> None:
    """Configure a custom factory used to create wallet managers.

    Passing ``None`` resets the factory to the default implementation.
    Intended for unit tests where an isolated storage path is desirable.
    """

    global _wallet_manager_factory
    _wallet_manager_factory = factory
    clear_cached_managers()


def clear_cached_managers() -> None:
    """Drop all cached wallet manager instances.

    Useful for tests that need a clean state between runs.
    """

    _user_wallet_managers.clear()
    _user_storage_aliases.clear()


def get_wallet_manager(user_id: int, *, root: Optional[Path] = None) -> SparkWalletManager:
    """Return a user-scoped ``SparkWalletManager`` instance."""

    if _wallet_manager_factory is not None:
        return _wallet_manager_factory(user_id)

    root_path = root or _DEFAULT_ROOT
    root_path.mkdir(parents=True, exist_ok=True)

    manager = _user_wallet_managers.get(user_id)
    if manager is None:
        storage_path = _storage_path_for(user_id, root_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        manager = SparkWalletManager(str(storage_path))
        _user_wallet_managers[user_id] = manager
    return manager


def set_user_storage_alias(user_id: int, alias: str) -> None:
    """Assign a persistent storage alias for a Telegram user."""

    sanitized = _sanitize_alias(alias)
    current = _user_storage_aliases.get(user_id)
    if current == sanitized:
        return
    _user_storage_aliases[user_id] = sanitized
    # Reset cached manager so a new one is created with updated path.
    _user_wallet_managers.pop(user_id, None)


def get_user_storage_alias(user_id: int) -> Optional[str]:
    """Return the configured storage alias for the telegram user."""

    return _user_storage_aliases.get(user_id)


