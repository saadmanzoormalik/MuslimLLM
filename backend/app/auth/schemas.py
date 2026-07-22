from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class OnboardingAnswer(BaseModel):
    key: Literal["primary_use", "response_preference", "privacy_preference", "context_transfer_preference"]
    value: str = Field(min_length=1, max_length=80)
    step: int = Field(ge=0, le=3)


class EmailStart(BaseModel):
    email: EmailStr


class EmailVerify(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class OAuthStart(BaseModel):
    return_to: str = "/"


class GuestCreate(BaseModel):
    claim_existing_workspace: bool = True


class DeleteAccount(BaseModel):
    confirmation: Literal["DELETE"]
