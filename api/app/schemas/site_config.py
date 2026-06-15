"""SiteConfig Pydantic schemas."""

from pydantic import BaseModel, ConfigDict


class SiteConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None


class SiteConfigUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None
