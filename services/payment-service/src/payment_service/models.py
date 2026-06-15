import enum
from db.base import Base, TimestampMixin
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Enum, String

class PaymentStatus(str, enum.Enum):
    CHARGED = "charged"
    FAILED = "failed"
    
class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = {"schema" : "payment"}
    
    order_id: Mapped[str] = mapped_column(String(20),  primary_key=True)
    amount: Mapped[int] = mapped_column()
    auth_code: Mapped[str | None] = mapped_column()
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
    )