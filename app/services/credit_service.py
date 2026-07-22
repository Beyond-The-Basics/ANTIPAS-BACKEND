"""Credit charging — STUB.

`SPEC.md`: publishing a RosterSearch/OpponentSearch charges the publishing captain's *personal*
credits (GuestSearch/PlayerAvailability are free). The real `CreditTransaction` ledger, balance
checks, and non-engagement refund are a separate PR. For now `charge_publish` is a no-op seam so
callers are wired correctly and only the ledger implementation is missing.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SearchType
from app.models.user import User


async def charge_publish(db: AsyncSession, user: User, search_type: SearchType, search_id: uuid.UUID) -> None:
    """Charge one credit to `user` for publishing a listing. STUB: no ledger write, no balance check.

    TODO(credits PR): insert a CreditTransaction(amount=-1, reason=publish_charge), reject on
    insufficient balance, and wire the non-engagement refund.
    """
    return None
