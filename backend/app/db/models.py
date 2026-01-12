"""
SQLAlchemy ORM models for patient health records.
Includes EHR-style tables: Encounter, Vital, Lab, Medication.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, Boolean, Date
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

    # Relationships
    history = relationship("PatientHistory", back_populates="patient", cascade="all, delete-orphan")
    summary = relationship("PatientSummary", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient(id={self.patient_id}, name='{self.name}')>"


class PatientHistory(Base):
    """
    Individual visit/encounter records for a patient (legacy table).
    """
    __tablename__ = "patient_history"

    record_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    visit_date = Column(String)
    notes = Column(Text)
    treatment = Column(Text)
    clinician = Column(String)

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

    patient = relationship("Patient", back_populates="summary")

    def __repr__(self):
        return f"<PatientSummary(patient_id={self.patient_id})>"


# ============================================
# EHR-STYLE TABLES (New)
# ============================================

class Encounter(Base):
    """
    Clinical encounter/visit record.
    Each encounter represents a single patient visit.
    """
    __tablename__ = "encounters"

    encounter_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    encounter_date = Column(String, nullable=False)  # ISO date string
    encounter_type = Column(String)  # e.g., "office_visit", "emergency", "telehealth", "inpatient"
    chief_complaint = Column(Text)
    diagnosis_code = Column(String)  # ICD-10 code
    diagnosis_description = Column(String)
    provider_name = Column(String)
    provider_specialty = Column(String)
    disposition = Column(String)  # e.g., "discharged", "admitted", "transferred"
    notes = Column(Text)

    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    vitals = relationship("Vital", back_populates="encounter", cascade="all, delete-orphan")
    labs = relationship("Lab", back_populates="encounter", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Encounter(id={self.encounter_id}, patient_id={self.patient_id}, date={self.encounter_date})>"


class Vital(Base):
    """
    Vital signs recorded during an encounter.
    """
    __tablename__ = "vitals"

    vital_id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.encounter_id"), nullable=False)
    recorded_at = Column(String)  # ISO datetime string
    
    # Vital measurements
    temperature_f = Column(Float)  # Fahrenheit
    heart_rate_bpm = Column(Integer)  # Beats per minute
    blood_pressure_systolic = Column(Integer)  # mmHg
    blood_pressure_diastolic = Column(Integer)  # mmHg
    respiratory_rate = Column(Integer)  # Breaths per minute
    oxygen_saturation = Column(Float)  # SpO2 percentage
    weight_kg = Column(Float)
    height_cm = Column(Float)
    bmi = Column(Float)
    pain_level = Column(Integer)  # 0-10 scale
    
    # Flags
    is_abnormal = Column(Boolean, default=False)

    encounter = relationship("Encounter", back_populates="vitals")

    def __repr__(self):
        return f"<Vital(id={self.vital_id}, encounter_id={self.encounter_id})>"


class Lab(Base):
    """
    Laboratory test results.
    """
    __tablename__ = "labs"

    lab_id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.encounter_id"), nullable=False)
    ordered_date = Column(String)  # ISO date
    result_date = Column(String)  # ISO date
    
    # Test details
    test_name = Column(String, nullable=False)  # e.g., "HbA1c", "CBC", "BMP"
    test_code = Column(String)  # LOINC code
    result_value = Column(String)  # String to handle numeric and text results
    result_unit = Column(String)  # e.g., "%", "mg/dL", "cells/uL"
    reference_range = Column(String)  # e.g., "4.0-5.6"
    
    # Interpretation
    is_abnormal = Column(Boolean, default=False)
    abnormal_flag = Column(String)  # e.g., "H" (high), "L" (low), "C" (critical)
    interpretation = Column(Text)  # Clinical interpretation notes

    encounter = relationship("Encounter", back_populates="labs")

    def __repr__(self):
        return f"<Lab(id={self.lab_id}, test={self.test_name}, value={self.result_value})>"


class Medication(Base):
    """
    Patient medication records (prescriptions and active medications).
    """
    __tablename__ = "medications"

    medication_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    
    # Medication details
    medication_name = Column(String, nullable=False)
    generic_name = Column(String)
    drug_class = Column(String)  # e.g., "antihypertensive", "antibiotic", "analgesic"
    dosage = Column(String)  # e.g., "10mg"
    frequency = Column(String)  # e.g., "twice daily", "as needed"
    route = Column(String)  # e.g., "oral", "IV", "topical"
    
    # Prescription dates
    start_date = Column(String)  # ISO date
    end_date = Column(String)  # ISO date, null if ongoing
    
    # Status
    is_active = Column(Boolean, default=True)
    prescribing_provider = Column(String)
    indication = Column(String)  # Reason for prescription
    notes = Column(Text)

    patient = relationship("Patient", back_populates="medications")

    def __repr__(self):
        return f"<Medication(id={self.medication_id}, name={self.medication_name}, patient_id={self.patient_id})>"
