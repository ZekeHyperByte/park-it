"""SiteConfig Pydantic schemas."""

from pydantic import BaseModel, ConfigDict


class SiteConfigBase(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None


class SiteConfigResponse(SiteConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SiteConfigUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None
