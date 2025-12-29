"""
SQLAlchemy ORM models for patient health records.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Patient(Base):
    """
    Patient demographic and summary information.
    """
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    primary_condition = Column(String)
    risk_level = Column(String)

    # Relationship to patient history records
    history = relationship("PatientHistory", back_populates="patient", cascade="all, delete-orphan")
    # Relationship to cached summary
    summary = relationship("PatientSummary", back_populates="patient", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient(id={self.patient_id}, name='{self.name}')>"


class PatientHistory(Base):
    """
    Individual visit/encounter records for a patient.
    """
    __tablename__ = "patient_history"

    record_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    visit_date = Column(String)
    notes = Column(Text)
    treatment = Column(Text)
    clinician = Column(String)

    # Relationship back to patient
    patient = relationship("Patient", back_populates="history")

    def __repr__(self):
        return f"<PatientHistory(id={self.record_id}, patient_id={self.patient_id})>"


class PatientSummary(Base):
    """
    Cached LLM-generated patient summary to reduce LLM calls.
    """
    __tablename__ = "patient_summary"

    patient_id = Column(Integer, ForeignKey("patients.patient_id"), primary_key=True)
    summary_text = Column(Text, nullable=False)
    last_updated = Column(String)  # ISO timestamp

    # Relationship back to patient
    patient = relationship("Patient", back_populates="summary")

    def __repr__(self):
        return f"<PatientSummary(patient_id={self.patient_id})>"

