# referral_service.py
from typing import Dict
from config import (
    INTEGRATOR_DEV_FEE_BPS, REF_TIER1_BPS, REF_TIER2_BPS, REF_TIER3_BPS
)

# простое in-memory хранилище уровней: user_id -> 1|2|3
_USER_TIERS: Dict[int, int] = {}

def set_user_ref_tier(user_id: int, tier: int) -> None:
    """Установить уровень рефералки для пользователя (1, 2 или 3)."""
    if tier not in (1, 2, 3):
        tier = 1
    _USER_TIERS[user_id] = tier

def get_user_ref_tier(user_id: int) -> int:
    """Получить уровень рефералки пользователя (по умолчанию 1)."""
    return int(_USER_TIERS.get(user_id, 1))

def get_user_ref_bps(user_id: int) -> int:
    """Получить комиссию рефералки в BPS (0.25% / 0.10% / 0.01%)."""
    t = get_user_ref_tier(user_id)
    return REF_TIER1_BPS if t == 1 else (REF_TIER2_BPS if t == 2 else REF_TIER3_BPS)

def get_total_integrator_fee_bps(user_id: int) -> int:
    """
    Получить ИТОГОВУЮ комиссию интегратора:
    = 1% нам (100 bps) + реф-уровень пользователя (0.25/0.10/0.01)
    """
    return int(INTEGRATOR_DEV_FEE_BPS) + int(get_user_ref_bps(user_id))
