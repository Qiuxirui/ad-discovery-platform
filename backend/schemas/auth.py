"""商家与管理员的认证请求/响应模型（邮箱/手机号不用 EmailStr，改正则校验）。"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from ..constants import CITIES
from .common import BaseORMModel

__all__ = [
    "AdminLoginIn",
    "AdminOut",
    "MerchantLoginIn",
    "MerchantEnvelope",
    "MerchantOut",
    "MerchantSignupIn",
    "MerchantUpdateIn",
    "PasswordChangeIn",
]

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PASSWORD_MIN = 8
PASSWORD_MAX = 64


class MerchantSignupIn(BaseModel):
    """商家注册即入驻（P0-M-01）。"""

    name: str = Field(min_length=1, max_length=60)
    contact_name: str = Field(min_length=1, max_length=30)
    phone: str = Field(min_length=11, max_length=11)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    city: str = Field(min_length=1, max_length=20)
    main_category_id: int | None = None
    agree_policy: bool = False

    @field_validator("name", "contact_name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("该字段不能为空")
        return text

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str) -> str:
        phone = value.strip()
        if not PHONE_RE.match(phone):
            raise ValueError("手机号格式不正确，请填写 11 位大陆手机号")
        return phone

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_RE.match(email):
            raise ValueError("邮箱格式不正确")
        return email

    @field_validator("city")
    @classmethod
    def _check_city(cls, value: str) -> str:
        city = value.strip()
        if city not in CITIES:
            raise ValueError("请选择列表中的城市")
        return city

    @field_validator("agree_policy")
    @classmethod
    def _check_policy(cls, value: bool) -> bool:
        if not value:
            raise ValueError("请先阅读并同意《广告政策》与《信息真实承诺》")
        return value


class MerchantLoginIn(BaseModel):
    """账号 = 邮箱或手机号。"""

    account: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)

    @field_validator("account")
    @classmethod
    def _strip_account(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("请输入邮箱或手机号")
        return text


class MerchantUpdateIn(BaseModel):
    """商家资料修改。"""

    contact_name: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=11)
    city: str | None = Field(default=None, max_length=20)
    main_category_id: int | None = None

    @field_validator("phone")
    @classmethod
    def _check_optional_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        phone = value.strip()
        if not PHONE_RE.match(phone):
            raise ValueError("手机号格式不正确，请填写 11 位大陆手机号")
        return phone

    @field_validator("city")
    @classmethod
    def _check_optional_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        city = value.strip()
        if city not in CITIES:
            raise ValueError("请选择列表中的城市")
        return city


class PasswordChangeIn(BaseModel):
    """修改密码。"""

    old_password: str = Field(min_length=1, max_length=PASSWORD_MAX)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class MerchantOut(BaseORMModel):
    """商家信息（不含密码哈希）。"""

    id: int
    name: str
    contact_name: str
    phone: str
    email: str
    city: str
    main_category_id: int | None = None
    main_category_name: str | None = None
    verified: bool = False
    status: str = "active"
    created_at: str | None = None


class AdminLoginIn(BaseModel):
    """后台登录。"""

    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class AdminOut(BaseORMModel):
    """管理员信息。"""

    id: int
    username: str
    display_name: str
    role: str = "admin"


class MerchantEnvelope(BaseModel):
    """``{merchant}`` 包装（登录/注册响应 + Set-Cookie）。"""

    merchant: MerchantOut
