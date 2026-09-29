from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentFieldExtraction(Base):
    __tablename__ = "document_field_extractions"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)

    supplier_name_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_name_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_name_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    document_number_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_number_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_number_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    document_date_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_date_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_date_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    currency_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    total_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
