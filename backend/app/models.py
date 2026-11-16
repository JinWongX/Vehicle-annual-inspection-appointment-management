from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="owner")
    phone = Column(String, nullable=True)
    real_name = Column(String, nullable=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    station = relationship("Station", back_populates="staff")
    vehicles = relationship("Vehicle", back_populates="owner")


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    allowed_vehicle_types = Column(String, nullable=True)
    daily_capacity = Column(Integer, nullable=False, default=50)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    staff = relationship("User", back_populates="station")
    appointments = relationship("Appointment", back_populates="station")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plate_number = Column(String, unique=True, index=True, nullable=False)
    vehicle_type = Column(String, nullable=False)
    register_date = Column(Date, nullable=True)
    usage_nature = Column(String, nullable=True, default="non_operational")
    next_inspection_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="vehicles")
    appointments = relationship("Appointment", back_populates="vehicle")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    time_slot = Column(String, nullable=False)
    status = Column(String, nullable=False, default="booked")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    vehicle = relationship("Vehicle", back_populates="appointments")
    station = relationship("Station", back_populates="appointments")
    inspection_report = relationship("InspectionReport", back_populates="appointment", uselist=False)


class InspectionReport(Base):
    __tablename__ = "inspection_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, unique=True)
    result = Column(String, nullable=False)
    overall_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="inspection_report")
    items = relationship("InspectionItem", back_populates="report")


class InspectionItem(Base):
    __tablename__ = "inspection_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("inspection_reports.id"), nullable=False)
    item_name = Column(String, nullable=False)
    result = Column(String, nullable=False)
    comment = Column(Text, nullable=True)

    report = relationship("InspectionReport", back_populates="items")
