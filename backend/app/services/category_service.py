from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.category import category_crud
from app.models.category import Category
from app.models.product import Product
from app.schemas.category_schema import (
    CategoryPublic,
    CreateCategorySchema,
    UpdateCategorySchema,
)
from app.utils.generate_slug import generate_slug


class CategoryServiceError(Exception):
    pass


class CategoryNotFoundError(CategoryServiceError):
    pass


class CategoryConflictError(CategoryServiceError):
    pass


class CategoryValidationError(CategoryServiceError):
    pass


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = category_crud

    def get(self, category_id: UUID) -> CategoryPublic:
        return CategoryPublic.model_validate(self._get_model(category_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[CategoryPublic]:
        if skip < 0 or not 1 <= limit <= 1000:
            raise CategoryValidationError("Invalid pagination values")
        categories = self.crud.get_all(self.db, skip=skip, limit=limit)
        return [CategoryPublic.model_validate(item) for item in categories]

    def create(self, category_in: CreateCategorySchema) -> CategoryPublic:
        self._validate_parent(category_in.parent_id)
        self._ensure_unique_name(category_in.category_name)

        data = category_in.model_dump()
        category = Category(
            **data,
            slug=generate_slug(
                self.db,
                category_in.category_name,
                "category",
            ),
        )
        try:
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
        except IntegrityError as exc:
            self.db.rollback()
            raise CategoryConflictError("Category could not be created") from exc
        return CategoryPublic.model_validate(category)

    def update(
        self,
        category_id: UUID,
        category_in: UpdateCategorySchema,
    ) -> CategoryPublic:
        category = self._get_model(category_id)
        data = category_in.model_dump(exclude_unset=True)

        parent_id = data.get("parent_id", category.parent_id)
        self._validate_parent(parent_id, category_id=category_id)

        if (
            "category_name" in data
            and data["category_name"] != category.category_name
        ):
            self._ensure_unique_name(
                data["category_name"],
                exclude_id=category_id,
            )
            data["slug"] = generate_slug(
                self.db,
                data["category_name"],
                "category",
            )

        try:
            for field, value in data.items():
                setattr(category, field, value)
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
        except IntegrityError as exc:
            self.db.rollback()
            raise CategoryConflictError("Category could not be updated") from exc

        return CategoryPublic.model_validate(category)

    def delete(self, category_id: UUID) -> None:
        category = self._get_model(category_id)

        child_exists = self.db.scalar(
            select(Category.category_id).where(
                Category.parent_id == category_id
            )
        )
        product_exists = self.db.scalar(
            select(Product.product_id).where(
                Product.category_id == category_id
            )
        )
        if child_exists is not None:
            raise CategoryConflictError(
                "Category cannot be deleted while child categories reference it"
            )
        if product_exists is not None:
            raise CategoryConflictError(
                "Category cannot be deleted while products reference it"
            )

        try:
            self.db.delete(category)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise CategoryConflictError("Category could not be deleted") from exc

    def _get_model(self, category_id: UUID) -> Category:
        category = self.crud.get(self.db, category_id)
        if category is None:
            raise CategoryNotFoundError(
                f"Category {category_id} was not found"
            )
        return category

    def _validate_parent(
        self,
        parent_id: UUID | None,
        *,
        category_id: UUID | None = None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == category_id:
            raise CategoryValidationError(
                "A category cannot be its own parent"
            )
        parent = self.db.get(Category, parent_id)
        if parent is None:
            raise CategoryValidationError(
                f"Parent category {parent_id} does not exist"
            )

        current = parent
        visited: set[UUID] = set()
        while current is not None and current.parent_id is not None:
            if current.category_id in visited:
                raise CategoryValidationError(
                    "Existing category hierarchy contains a cycle"
                )
            visited.add(current.category_id)
            if current.parent_id == category_id:
                raise CategoryValidationError(
                    "Parent assignment would create a category cycle"
                )
            current = self.db.get(Category, current.parent_id)

    def _ensure_unique_name(
        self,
        name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        stmt = select(Category).where(
            Category.category_name.ilike(name.strip())
        )
        existing = self.db.scalar(stmt)
        if existing is not None and existing.category_id != exclude_id:
            raise CategoryConflictError(
                f"Category '{name}' already exists"
            )
