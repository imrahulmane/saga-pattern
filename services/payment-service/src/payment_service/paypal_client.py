


from dataclasses import dataclass
from functools import lru_cache
import random
import uuid

from payment_service.settings import get_settings


@dataclass
class AuthorisationResult:
    success : bool
    auth_code: str | None = None
    decline_reason: str | None = None

class MockPaypalClient:
    def __init__(self, fail_rate: float |  None = None) -> None:
        if fail_rate is not None:
            self.fail_rate = fail_rate
        else:
            self.fail_rate = get_settings().payment_fail_rate
            
    def authorise(self, card_token: str, amount: int) -> AuthorisationResult:
        if card_token == "declined":
            return AuthorisationResult(
                success=False,
                decline_reason="Card Declined!!"
            )

        if random.random() < self.fail_rate:
            return AuthorisationResult(
                success=False,
                decline_reason=random.choice([
                    "Insuffecient funds!",
                    "Wrong card info",
                    "Fraud!!",
                    "Expired card"
                ]
            ),
            )

        auth_code = f"AUTH-{uuid.uuid4().hex[:12].upper()}"
        return AuthorisationResult(
            success=True,
            auth_code=auth_code
        )


@lru_cache(1)
def get_paypal_client() -> MockPaypalClient:
    return MockPaypalClient()