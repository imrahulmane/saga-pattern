
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import update
from broker.redis_client import Broker, get_broker
from db.session import get_engine
from events import  PaymentCharged, ReleaseStock, SagaRolledBack, StockReserved, PaymentFailed, StockUnavailable
from order_service.models import Order, OrderStatus, SagaStep 


def register_handlers(broker: Broker) -> None:
    @broker.on_event(StockReserved)
    async def on_stock_reserved(event: StockReserved) -> None:
        await _on_stock_reserved(event)
   
    @broker.on_event(PaymentCharged)
    async def on_payment_charged(event: PaymentCharged) -> None:
        await _on_payment_charged(event)
    
    @broker.on_event(PaymentFailed)
    async def on_payment_failed(event: PaymentFailed) -> None:
           await _on_payment_failed(event)
   
    @broker.on_event(StockUnavailable)
    async def on_stock_unavailable(event: StockUnavailable) -> None:
            await _on_stock_unavailable(event)
    

async def _on_stock_reserved(event: StockReserved) -> None:
    engine = get_engine()
    try:
        async with AsyncSession(engine) as db:
            _ = await db.execute(
                update(Order)
                .where(Order.order_id == event.order_id)
                .where(Order.status == OrderStatus.STOCK_RESERVING)
                .values(status=OrderStatus.PAYMENT_AUTHORISING)
            )

            await db.commit()
    except Exception as e:
        print(f"Error order {event.order_id} -- {e}")
        
async def _on_payment_charged(event: PaymentCharged) -> None:
    engine = get_engine()
    try:
        async with AsyncSession(engine) as db:
            _ = await db.execute(
                update(Order)
                .where(Order.order_id == event.order_id)
                .where(Order.status == OrderStatus.PAYMENT_AUTHORISING)
                .values(status=OrderStatus.CONFIRMED)
            )

            await db.commit()
    except Exception as e:
        print(f"Error order {event.order_id} -- {e}")

async def _on_payment_failed(event: PaymentFailed) -> None:
    engine = get_engine()
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(
                select(Order)
                .where(Order.order_id == event.order_id)
                .where(Order.status == OrderStatus.PAYMENT_AUTHORISING)
                .with_for_update()
            )

            order: Order | None = result.scalar_one_or_none()

            if order is None:
                return

            order.status = OrderStatus.CANCELLED
            order.failed_at_step = SagaStep.PAYMENT.name_lower
            await db.commit()
           
            release_stock_event = ReleaseStock(
                order_id=event.order_id
            )
            await get_broker().publish("saga:compensations", release_stock_event)
           
            rollback = SagaRolledBack(
                order_id=event.order_id,
                failed_at_step=SagaStep.PAYMENT.name_lower
            )
            await get_broker().publish("saga:events", rollback)
    except Exception as e:
        print(f"Error order {event.order_id} -- {e}")


async def _on_stock_unavailable(event: StockUnavailable) -> None:
    engine = get_engine()
    try:
        async with AsyncSession(engine) as db:
            _ = await db.execute(
                update(Order)
                .where(Order.order_id == event.order_id)
                .where(Order.status == OrderStatus.STOCK_RESERVING)
                .values(status=OrderStatus.CANCELLED)
                .values(failed_at_step=SagaStep.INVENTORY.name_lower)
            )

            await db.commit()
    except Exception as e:
        print(f"Error order {event.order_id} -- {e}")