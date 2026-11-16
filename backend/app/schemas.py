from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, computed_field, model_validator


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    role: str = Field(..., pattern="^(owner|station|admin)$")
    phone: Optional[str] = None
    real_name: Optional[str] = None
    station_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)

    @model_validator(mode="after")
    def check_station_user(self):
        if self.role == "station" and not self.station_id:
            raise ValueError("station role user must have station_id")
        return self


class UserRegister(BaseModel):
    username: str
    password: str = Field(min_length=8)
    phone: Optional[str] = None
    real_name: Optional[str] = None


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(owner|station|admin)$")
    phone: Optional[str] = None
    real_name: Optional[str] = None
    station_id: Optional[int] = None

    @model_validator(mode="after")
    def check_station_user(self):
        target_role = self.role
        if self.station_id is not None and target_role != "station":
            raise ValueError("only station role users can have station_id")
        if self.station_id is None and target_role == "station":
            raise ValueError("station role user must have station_id")
        return self


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StationBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    allowed_vehicle_types: Optional[str] = None
    daily_capacity: int = Field(50, ge=1)


class StationCreate(StationBase):
    pass


class StationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    allowed_vehicle_types: Optional[str] = None
    daily_capacity: Optional[int] = Field(None, ge=1)


class StationResponse(StationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleBase(BaseModel):
    plate_number: str = Field(min_length=5, max_length=12)
    vehicle_type: str = Field(min_length=1, max_length=50)
    register_date: Optional[date] = None
    usage_nature: Optional[str] = Field(default="non_operational", pattern="^(non_operational|commercial|operational)$")
    next_inspection_date: Optional[date] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = Field(None, min_length=1, max_length=50)
    register_date: Optional[date] = None
    usage_nature: Optional[str] = Field(None, pattern="^(non_operational|commercial|operational)$")
    next_inspection_date: Optional[date] = None


class VehicleResponse(VehicleBase):
    id: int
    owner_id: int
    created_at: datetime

    @computed_field
    @property
    def days_until_inspection(self) -> Optional[int]:
        if self.next_inspection_date:
            return (self.next_inspection_date - date.today()).days
        return None

    class Config:
        from_attributes = True


class TimeSlotAvailability(BaseModel):
    time_slot: str
    remaining: int


class StationBrief(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class VehicleBrief(BaseModel):
    id: int
    plate_number: str
    vehicle_type: str

    class Config:
        from_attributes = True


class StationAvailabilityResponse(BaseModel):
    station: StationResponse
    time_slots: List[TimeSlotAvailability]


class AppointmentBase(BaseModel):
    vehicle_id: int
    station_id: int
    appointment_date: date
    time_slot: str
    status: str = Field(default="booked", pattern="^(booked|checking|completed|cancelled)$")


class AppointmentCreate(BaseModel):
    vehicle_id: int
    station_id: int
    appointment_date: date
    time_slot: str


class AppointmentUpdate(BaseModel):
    station_id: Optional[int] = None
    appointment_date: Optional[date] = None
    time_slot: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(booked|checking|completed|cancelled)$")


class AppointmentResponse(AppointmentBase):
    id: int
    created_at: datetime
    vehicle: VehicleBrief
    station: StationBrief

    class Config:
        from_attributes = True


class InspectionItemBase(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    result: str = Field(..., pattern="^(pass|fail|retest)$")
    comment: Optional[str] = Field(None, max_length=500)


class InspectionItemCreate(InspectionItemBase):
    pass


class InspectionItemResponse(InspectionItemBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class InspectionReportBase(BaseModel):
    appointment_id: int
    result: str = Field(..., pattern="^(pass|fail|retest)$")
    overall_comment: Optional[str] = Field(None, max_length=1000)


class InspectionReportCreate(BaseModel):
    appointment_id: int
    result: str = Field(..., pattern="^(pass|fail|retest)$")
    overall_comment: Optional[str] = Field(None, max_length=1000)
    items: Optional[List[InspectionItemCreate]] = Field(default_factory=list)


class InspectionReportBriefAppointment(BaseModel):
    id: int
    appointment_date: date
    time_slot: str
    status: str
    vehicle: VehicleBrief
    station: StationBrief

    class Config:
        from_attributes = True


class InspectionReportResponse(InspectionReportBase):
    id: int
    created_at: datetime
    items: List[InspectionItemResponse] = []
    sticker_code: Optional[str] = None
    appointment: InspectionReportBriefAppointment

    class Config:
        from_attributes = True


class InspectionStatisticsResponse(BaseModel):
    total_count: int
    pass_count: int
    fail_count: int
    retest_count: int
    pass_rate: float
    fail_reasons: Dict[str, int]
