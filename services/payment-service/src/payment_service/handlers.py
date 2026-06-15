from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from broker.redis_client import Broker, get_broker
from db.session import get_engine
from events import  PaymentCharged, StockReserved, PaymentFailed 
from payment_service.models import Payment, PaymentStatus
from payment_service.paypal_client import get_paypal_client


def register_handlers(broker: Broker) -> None:
    @broker.on_event(StockReserved)
    async def on_stock_reserved(event: StockReserved) -> None:
        await _on_stock_reserved(event)

    
async def _on_stock_reserved(event: StockReserved) -> None:
    engine = get_engine()

    async with AsyncSession(engine) as db:
        try:
            stmt = await db.execute(
                select(Payment)
                .where(Payment.order_id == event.order_id)
                .limit(1)
            )

            existing_payment = stmt.scalar_one_or_none()

            if existing_payment is not None:
                if existing_payment.status == PaymentStatus.CHARGED:
                    payment_charged_event = PaymentCharged(
                        order_id=existing_payment.order_id,
                        auth_code=existing_payment.auth_code,
                        amount=existing_payment.amount 
                    )
        
                    await get_broker().publish("saga:events", payment_charged_event)
                    return
                elif existing_payment.status == PaymentStatus.FAILED:
                    payment_failed_event = PaymentFailed(
                        order_id=existing_payment.order_id,
                        reason="Payment previously failed"
                    )

                    await get_broker().publish("saga:events", payment_failed_event)
                    return
                    
            paypal_client = get_paypal_client()
            result = paypal_client.authorise(
                card_token=event.card_token,
                amount=event.total_amount
            )
           
            if result.success:
                payment = Payment(
                    order_id=event.order_id,
                    auth_code=result.auth_code,
                    amount=event.total_amount,
                    status=PaymentStatus.CHARGED
                )

                db.add(payment)
                await db.commit()

                payment_charged_event = PaymentCharged(
                    order_id = event.order_id,
                    auth_code=result.auth_code,
                    amount=event.total_amount
                )

                await get_broker().publish("saga:events", payment_charged_event)
            else:
                payment = Payment(
                    order_id= event.order_id,
                    auth_code= None,
                    amount=event.total_amount,
                    status=PaymentStatus.FAILED
                )

                db.add(payment)
                await db.commit()

                payment_failed_event = PaymentFailed(
                    order_id=event.order_id,
                    reason=result.decline_reason,
                )

                await get_broker().publish("saga:events", payment_failed_event)
            
        except Exception as e:
            await db.rollback()
            print(f"Error charging payment for {event.order_id}: {e}")
            
