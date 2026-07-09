from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.admin_user import AdminUser
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.doctor_routing_keyword import DoctorRoutingKeyword
from app.models.doctor_schedule import DoctorSchedule
from app.models.hospital import Hospital


DOCTOR_SEEDS = [
    {
        "department": "Ophthalmology",
        "name": "Dr. Ayesha Khan",
        "specialty": "Ophthalmology",
        "keywords": ["eye pain", "blurry vision", "red eye", "vision problem"],
    },
    {
        "department": "Cardiology",
        "name": "Dr. Hamza Ali",
        "specialty": "Cardiology",
        "keywords": ["chest discomfort", "palpitations", "heart pain", "blood pressure"],
    },
    {
        "department": "Dermatology",
        "name": "Dr. Sana Malik",
        "specialty": "Dermatology",
        "keywords": ["skin rash", "itching", "acne", "skin allergy"],
    },
    {
        "department": "Dentistry",
        "name": "Dr. Bilal Ahmed",
        "specialty": "Dentistry",
        "keywords": ["tooth pain", "gum pain", "dental pain", "toothache"],
    },
    {
        "department": "General Medicine",
        "name": "Dr. Sara Ahmed",
        "specialty": "General Physician",
        "keywords": ["fever", "cough", "flu", "body pain", "headache"],
    },
]

EMERGENCY_KEYWORDS = [
    "severe chest pain",
    "difficulty breathing",
    "heavy bleeding",
    "loss of consciousness",
    "stroke symptoms",
    "seizure",
    "serious injury",
]


def seed_database(db: Session) -> None:
    hospital = db.scalar(select(Hospital).where(Hospital.name == "Demo General Hospital"))
    if hospital is None:
        hospital = Hospital(
            name="Demo General Hospital",
            timezone=settings.hospital_timezone,
            phone="+920000000000",
            address="Demo hospital address",
        )
        db.add(hospital)
        db.flush()

    departments_by_name: dict[str, Department] = {}
    for doctor_seed in DOCTOR_SEEDS:
        department_name = doctor_seed["department"]
        department = db.scalar(
            select(Department).where(
                Department.hospital_id == hospital.id,
                Department.name == department_name,
            )
        )
        if department is None:
            department = Department(hospital_id=hospital.id, name=department_name)
            db.add(department)
            db.flush()
        departments_by_name[department_name] = department

    general_doctor: Doctor | None = None
    for doctor_seed in DOCTOR_SEEDS:
        doctor = db.scalar(select(Doctor).where(Doctor.name == doctor_seed["name"]))
        if doctor is None:
            doctor = Doctor(
                department_id=departments_by_name[doctor_seed["department"]].id,
                name=doctor_seed["name"],
                specialty=doctor_seed["specialty"],
            )
            db.add(doctor)
            db.flush()

        if doctor.specialty == "General Physician":
            general_doctor = doctor

        for priority, keyword in enumerate(doctor_seed["keywords"], start=10):
            existing_keyword = db.scalar(
                select(DoctorRoutingKeyword).where(
                    DoctorRoutingKeyword.doctor_id == doctor.id,
                    DoctorRoutingKeyword.keyword == keyword,
                )
            )
            if existing_keyword is None:
                db.add(
                    DoctorRoutingKeyword(
                        doctor_id=doctor.id,
                        keyword=keyword,
                        priority=priority,
                        emergency_flag=False,
                    )
                )

        for day_of_week in range(1, 7):
            existing_schedule = db.scalar(
                select(DoctorSchedule).where(
                    DoctorSchedule.doctor_id == doctor.id,
                    DoctorSchedule.day_of_week == day_of_week,
                )
            )
            if existing_schedule is None:
                db.add(
                    DoctorSchedule(
                        doctor_id=doctor.id,
                        day_of_week=day_of_week,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                        slot_duration_minutes=30,
                    )
                )

    if general_doctor is not None:
        for keyword in EMERGENCY_KEYWORDS:
            existing_keyword = db.scalar(
                select(DoctorRoutingKeyword).where(
                    DoctorRoutingKeyword.doctor_id == general_doctor.id,
                    DoctorRoutingKeyword.keyword == keyword,
                )
            )
            if existing_keyword is None:
                db.add(
                    DoctorRoutingKeyword(
                        doctor_id=general_doctor.id,
                        keyword=keyword,
                        priority=1,
                        emergency_flag=True,
                    )
                )

    admin = db.scalar(select(AdminUser).where(AdminUser.email == settings.admin_bootstrap_email))
    if admin is None:
        db.add(
            AdminUser(
                email=settings.admin_bootstrap_email,
                password_hash=hash_password(settings.admin_bootstrap_password),
                role="admin",
            )
        )

    db.commit()

