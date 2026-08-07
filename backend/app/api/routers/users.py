from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import AdminUser, CurrentUser, UserServiceDep, require_roles
from app.models.user import User
from app.schemas.user_schema import CreateUserSchema, UpdateUserSchema, UserPublic

router = APIRouter(prefix="/users", tags=["users"])
admin = require_roles("admin")


@router.get("/me", response_model = UserPublic)
def me(user: CurrentUser) -> User:
    return user


@router.get("", response_model = list[UserPublic], dependencies = [Depends(admin)])
def list_users(service: UserServiceDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    return service.list(skip = skip, limit = limit)


@router.get("/{user_id}", response_model = UserPublic, dependencies = [Depends(admin)])
def get_user(user_id: UUID, service: UserServiceDep):
    return service.get(user_id)


@router.post("", response_model = UserPublic, status_code = status.HTTP_201_CREATED)
def create_user(data: CreateUserSchema, service: UserServiceDep, actor: AdminUser):
    return service.create(data, actor = actor)


@router.patch("/{user_id}", response_model = UserPublic)
def update_user(user_id: UUID, data: UpdateUserSchema, service: UserServiceDep, actor: AdminUser):
    return service.update(user_id, data, actor = actor)


@router.delete("/{user_id}", status_code = status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: UUID, service: UserServiceDep, actor: AdminUser) -> Response:
    service.deactivate(user_id, actor = actor)
    return Response(status_code = 204)
