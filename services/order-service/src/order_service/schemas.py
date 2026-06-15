from order_service.models import OrderStatus, SagaStep
from pydantic.main import BaseModel

class PlaceOrderRequest(BaseModel):
    item_id: str
    quantity: int
    customer_id: str
    card_token: str

class OrderResponse(BaseModel):
    order_id: str
    status: OrderStatus
    customer_id: str
    failed_at_step: SagaStep | None = None

    model_config = {"from_attributes": True}