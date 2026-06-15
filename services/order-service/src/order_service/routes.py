import http
import uuid
from broker import get_broker
from db.session import get_session
from events.events import OrderInitiated
from fastapi import Depends
from fastapi.routing import APIRouter
from order_service.models import Order, OrderStatus
from order_service.schemas import OrderResponse, PlaceOrderRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select
from starlette.exceptions import HTTPException


router = APIRouter()

def _generate_order_id() -> str:
    return f"ORD-{uuid.uuid4().hex[:6].upper()}"

@router.post("/place-order", response_model=OrderResponse)
async def place_order(
    request: PlaceOrderRequest,
    session: AsyncSession = Depends(get_session)
):
    order_id = _generate_order_id()

    order = Order(
        order_id=order_id,
        status=OrderStatus.STOCK_RESERVING,
        item_id=request.item_id,
        quantity=request.quantity,
        card_token=request.card_token,
        customer_id=request.customer_id
    )

    session.add(order)
    await session.commit()

    event = OrderInitiated(
        order_id=order_id,
        item_id=order.item_id,
        quantity=order.quantity,
        customer_id=order.customer_id,
        card_token=order.card_token
    )

    await get_broker().publish("saga:events", event)

    return OrderResponse(
        order_id=order_id,
        status=order.status,
        customer_id=order.status
    )

@router.get("/order/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Order)
        .where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail="Order not found!"
        )

    return OrderResponse(
        order_id=order.order_id,
        status=order.status,
        customer_id=order.customer_id,
        failed_at_step=order.failed_at_step
    )