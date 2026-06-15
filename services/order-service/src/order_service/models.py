import enum
from db.base import Base, TimestampMixin
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Enum, String

class SagaStep(enum.IntEnum):
    """Saga steps in execution order"""

    ORDER = 1
    INVENTORY = 2
    PAYMENT = 3

class OrderStatus(str, enum.Enum):
    PLACED = "placed"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    STOCK_RESERVING = "stock_reserving"
    PAYMENT_AUTHORISING = "payment_authorising"
    COMPENSATING = "compensating"

class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.PLACED
    )
    item_id: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column()
    card_token: Mapped[str] = mapped_column(String(50))
    failed_at_step: Mapped[SagaStep | None] = mapped_column(
        Enum(SagaStep),
        nullable=True
    )
    