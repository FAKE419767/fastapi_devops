from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_account_service
from app.bll.account_service import AccountConflict, AccountService, InvalidCredentials

router = APIRouter(prefix="/account", tags=["account"])
Service = Annotated[AccountService, Depends(get_account_service)]


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, service: Service):
    try:
        return await service.register(body.username, body.password)
    except AccountConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/token", response_model=TokenResponse)
async def token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: Service
):
    if len(form.username) > 50 or not 1 <= len(form.password) <= 128:
        raise HTTPException(status_code=422, detail="Invalid credentials length")
    try:
        return await service.login(form.username, form.password)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}
        ) from exc
