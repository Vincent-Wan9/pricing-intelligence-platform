from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import AuthServiceDep
from app.schemas.user_schema import LoginSchema, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(service: AuthServiceDep, form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    return service.login(LoginSchema(email = form.username, password = form.password))
