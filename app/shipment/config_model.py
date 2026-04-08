"""
app/shipment/config_model.py
────────────────────────────
SQLAlchemy model for shipment.ShipmentConfigurations.
Credentials & API URLs are stored here in the DB — NOT in .env.
"""
from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class ShipmentConfigurations(Base):
    """Maps to shipment.ShipmentConfigurations"""
    __tablename__ = "ShipmentConfigurations"
    __table_args__ = {"schema": "shipment", "extend_existing": True}

    shipmentConfigurationId = Column("ShipmentConfigurationId", BigInteger, primary_key=True, autoincrement=True)
    clientId                = Column("ClientId",                String,  nullable=False)
    accessTokenURL          = Column("AccessTokenURL",          Text,    nullable=True)
    createShipmentURL       = Column("CreateShipmentURL",       Text,    nullable=True)
    cancelShipmentURL       = Column("CancelShipmentURL",       Text,    nullable=True)
    trackShipmentURL        = Column("TrackShipmentURL",        Text,    nullable=True)
    wayBillURL              = Column("WayBillURL",              Text,    nullable=True)
    updateShipmentURL       = Column("UpdateShipmentURL",       Text,    nullable=True)
    deliveryAgent           = Column("DeliveryAgent",           String,  nullable=True)
    userName                = Column("UserName",                String,  nullable=True)
    password                = Column("Password",                String,  nullable=True)
    # Warehouse return address
    returnName              = Column("ReturnName",              String,  nullable=True)
    returnPhone             = Column("ReturnPhone",             String,  nullable=True)
    returnAddressLine1      = Column("ReturnAddressLine1",      Text,    nullable=True)
    returnAddressLine2      = Column("ReturnAddressLine2",      Text,    nullable=True)
    returnCity              = Column("ReturnCity",              String,  nullable=True)
    returnState             = Column("ReturnState",             String,  nullable=True)
    returnPinCode           = Column("ReturnPinCode",           String,  nullable=True)
    returnCountry           = Column("ReturnCountry",           String,  default="India")
    # Audit
    createdDate             = Column("CreatedDate",             DateTime(timezone=True), server_default=func.now())
    modifiedDate            = Column("ModifiedDate",            DateTime(timezone=True), nullable=True)
    createdBy               = Column("CreatedBy",               String,  nullable=True)
    modifiedBy              = Column("ModifiedBy",              String,  nullable=True)
    organizationId          = Column("OrganizationId",          Integer, nullable=True)
    deletedInd              = Column("DeletedInd",              Boolean, default=False)
    tenantId                = Column("TenantId",                Integer, nullable=True)
    stateId                 = Column("StateId",                 String,  nullable=True)
