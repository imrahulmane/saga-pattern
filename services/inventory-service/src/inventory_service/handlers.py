from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import update
from broker.redis_client import Broker, get_broker
from db.session import get_engine
from events.events import OrderInitiated, ReleaseStock, StockReserved, StockUnavailable
from inventory_service.models import Reservation, ReservationStatus, Stock


def register_handlers(broker: Broker) -> None:
    @broker.on_event(OrderInitiated)
    async def on_order_initiated(event: OrderInitiated) -> None:
        await _on_order_initiated(event)

    @broker.on_event(ReleaseStock, channel="saga:compensations")
    async def on_release_stock(event: ReleaseStock) -> None:
        await _on_release_stock(event)
    
    
async def _on_order_initiated(event: OrderInitiated) -> None:
    engine = get_engine()

    async with AsyncSession(engine) as db:
        try:
            already_reserved = await db.execute(
                select(Reservation)
                .where(Reservation.order_id == event.order_id)
                .where(Reservation.status == ReservationStatus.RESERVED)
                .limit(1)
            )

            reserved = already_reserved.scalar_one_or_none()

            if reserved:
                stock_reserved_event = StockReserved(
                    item_id=event.item_id,
                    customer_id=event.customer_id,
                    order_id=event.order_id,
                    card_token=event.card_token,
                    quantity=event.quantity,
                    total_amount=reserved.total_price
                )
    
                await get_broker().publish("saga:events", stock_reserved_event)
                return

            stock = await db.execute(
                select(Stock)
                .where(Stock.item_id == event.item_id)
                .where(Stock.available_qnty >= event.quantity)
                .with_for_update()
            )

            stock = stock.scalar_one_or_none()

            if stock is None:
                stock_unavailable_event = StockUnavailable(
                    order_id=event.order_id,
                    reason="stock unavailable"
                )
 
                await get_broker().publish("saga:events", stock_unavailable_event)
                return

            stock.available_qnty -= event.quantity
            total_price: int = stock.unit_price * event.quantity
            
            reservation = Reservation(
                item_id=event.item_id,
                quantity=event.quantity,
                order_id=event.order_id,
                unit_price=stock.unit_price,
                total_price=total_price
            )
            
            db.add(reservation)
            await db.commit()
            
            stock_reserved_event = StockReserved(
                item_id=event.item_id,
                customer_id=event.customer_id,
                order_id=event.order_id,
                card_token=event.card_token,
                quantity=event.quantity,
                total_amount=total_price
            )

            await get_broker().publish("saga:events", stock_reserved_event)
        except Exception as e:
            await db.rollback()
            print(f"Error reserving stocks for {event.order_id}: {e}")
            

async def _on_release_stock(event: ReleaseStock) -> None:
    engine = get_engine()

    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(Reservation)
            .where(Reservation.order_id == event.order_id)
            .where(Reservation.status == ReservationStatus.RESERVED)
            .with_for_update()
        )

        reservation = result.scalar_one_or_none()
        
        if reservation is None:
            return

        reservation.status = ReservationStatus.RELEASED
        
        _ = await db.execute(
            update(Stock)
            .where(Stock.item_id == reservation.item_id)
            .values(available_qnty = Stock.available_qnty + reservation.quantity)
        )

        await db.commit()
        
        