from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.competitor import competitor_crud
from app.models.competitor import Competitor
from app.schemas.competitor_schema import (
    CompetitorPublic,
    CreateCompetitorSchema,
    UpdateCompetitorSchema,
)


class CompetitorServiceError(Exception):
    pass


class CompetitorNotFoundError(CompetitorServiceError):
    pass


class CompetitorConflictError(CompetitorServiceError):
    pass


class CompetitorValidationError(CompetitorServiceError):
    pass


class CompetitorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = competitor_crud

    def get(self, competitor_id: UUID) -> CompetitorPublic:
        return CompetitorPublic.model_validate(self._get_model(competitor_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[CompetitorPublic]:
        self._validate_pagination(skip, limit)
        competitors = self.crud.get_all(self.db, skip=skip, limit=limit)
        return [CompetitorPublic.model_validate(item) for item in competitors]

    def create(self, competitor_in: CreateCompetitorSchema) -> CompetitorPublic:
        data = competitor_in.model_dump()
        self._normalize_urls(data)
        self._ensure_unique_name(data["competitor_name"])

        competitor = Competitor(**data)
        try:
            self.db.add(competitor)
            self.db.commit()
            self.db.refresh(competitor)
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorConflictError(
                "Competitor could not be created because its data conflicts with an existing record") from exc
        return CompetitorPublic.model_validate(competitor)

    def update(self, competitor_id: UUID, competitor_in: UpdateCompetitorSchema) -> CompetitorPublic:
        competitor = self._get_model(competitor_id)
        data = competitor_in.model_dump(exclude_unset=True)
        self._normalize_urls(data)

        new_name = data.get("competitor_name")
        if new_name and new_name != competitor.competitor_name:
            self._ensure_unique_name(new_name, exclude_id=competitor_id)

        try:
            for field, value in data.items():
                setattr(competitor, field, value)
            self.db.add(competitor)
            self.db.commit()
            self.db.refresh(competitor)
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorConflictError("Competitor could not be updated") from exc
        return CompetitorPublic.model_validate(competitor)

    def deactivate(self, competitor_id: UUID) -> CompetitorPublic:
        return self._set_active(competitor_id, is_active=False)

    def reactivate(self, competitor_id: UUID) -> CompetitorPublic:
        return self._set_active(competitor_id, is_active=True)

    def _set_active(self, competitor_id: UUID, *, is_active: bool) -> CompetitorPublic:
        competitor = self._get_model(competitor_id)
        try:
            competitor.is_active = is_active
            self.db.add(competitor)
            self.db.commit()
            self.db.refresh(competitor)
        except IntegrityError as exc:
            self.db.rollback()
            action = "reactivated" if is_active else "deactivated"
            raise CompetitorConflictError(
                f"Competitor could not be {action}"
            ) from exc
        return CompetitorPublic.model_validate(competitor)

    def delete(self, competitor_id: UUID) -> None:
        competitor = self._get_model(competitor_id)
        if getattr(competitor, "is_active", False):
            raise CompetitorValidationError(
                "Active competitors must be deactivated before deletion"
            )
        try:
            self.db.delete(competitor)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorConflictError(
                "Competitor cannot be deleted while related data references it"
            ) from exc

    def _get_model(self, competitor_id: UUID) -> Competitor:
        competitor = self.crud.get(self.db, competitor_id)
        if competitor is None:
            raise CompetitorNotFoundError(
                f"Competitor {competitor_id} was not found"
            )
        return competitor

    def _ensure_unique_name(self, name: str, *, exclude_id: UUID | None = None) -> None:
        stmt = select(Competitor).where(
            Competitor.competitor_name.ilike(name.strip())
        )
        existing = self.db.scalar(stmt)
        if existing is not None and existing.competitor_id != exclude_id:
            raise CompetitorConflictError(
                f"Competitor '{name}' already exists"
            )

    @staticmethod
    def _normalize_urls(data: dict) -> None:
        for field in ("base_url", "website_url"):
            if field in data and data[field] is not None:
                data[field] = str(data[field]).rstrip("/")

    @staticmethod
    def _validate_pagination(skip: int, limit: int) -> None:
        if skip < 0:
            raise CompetitorValidationError("skip cannot be negative")
        if not 1 <= limit <= 1000:
            raise CompetitorValidationError("limit must be between 1 and 1000")
