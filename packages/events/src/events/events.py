


from datetime import datetime, timezone
from statistics import quantiles
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, computed_field


class BaseEvent(BaseModel):
    event_id : UUID = Field(default_factory=uuid4)
    order_id: str
    timestamp:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {"frozen" : True}

    @computed_field()
    @property
    def type(self) -> str:
        return self.__class__.__name__

class OrderInitiated(BaseEvent):
    """Emiited when order successfully initiated from order-service"""
    item_id : str
    quantity: int
    customer_id: str
    card_token: str

class OrderConfirmed(BaseEvent):
    """Command when saga successfully completed"""
    pass

class StockReserved(BaseEvent):
    """Emitted to the payment service"""
    item_id: str
    quantity: int
    customer_id: str
    card_token:  str
    total_amount: int

class StockUnavailable(BaseEvent):
    """Emitted when inventory service cannot reserve seats"""
    reason: str

class ReleaseStock(BaseEvent):
    """Command to release previously reserved seats"""

class PaymentCharged(BaseEvent):
    """Emitted when payment-service successfully authorises payment"""

    auth_code: str
    amount: int

class PaymentFailed(BaseEvent):
    """Emmited when payment-service declines payment"""

    reason: str

class VoidPayment(BaseEvent):
    """Command to void previously authorised payment"""
    pass

class SagaRolledBack(BaseEvent):
    """Emitted when the saga has fully compenseted and rolled back"""
    failed_at_step: str
