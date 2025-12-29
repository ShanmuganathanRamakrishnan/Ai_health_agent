"""
Text Normalization Utilities.
Provides query normalization for patient identification.
"""
import re
from typing import Optional


# Pronouns that indicate reference to previous patient
PRONOUNS_MALE = {"he", "him", "his"}
PRONOUNS_FEMALE = {"she", "her", "hers"}
ALL_PRONOUNS = PRONOUNS_MALE | PRONOUNS_FEMALE


def normalize_query(query: str) -> str:
    """
    Normalize query for better patient name matching.
    
    Transformations:
    - Lowercase
    - Normalize possessives: "sarah's" → "sarah"
    - Strip extra whitespace
    """
    if not query:
        return ""
    
    # Lowercase
    normalized = query.lower()
    
    # Normalize possessives: "sarah's" → "sarah"
    # Match word followed by 's or 's
    normalized = re.sub(r"(\w+)'s\b", r"\1", normalized)
    normalized = re.sub(r"(\w+)'s\b", r"\1", normalized)  # Curly apostrophe
    
    # Strip extra whitespace
    normalized = " ".join(normalized.split())
    
    return normalized


def extract_possessive_name(query: str) -> Optional[str]:
    """
    Extract the base name from a possessive form.
    
    Examples:
        "sarah's condition" → "sarah"
        "John's history" → "john"
    """
    # Match possessive patterns
    patterns = [
        r"(\w+)'s\b",  # Standard apostrophe
        r"(\w+)'s\b",  # Curly apostrophe
    ]
    
    query_text = query.lower()
    
    for pattern in patterns:
        match = re.search(pattern, query_text)
        if match:
            return match.group(1)
    
    return None


def contains_pronoun(query: str) -> Optional[str]:
    """
    Check if query contains pronouns referring to a person.
    Returns the gender hint if found: 'male', 'female', or None.
    """
    words = set(re.findall(r'\b\w+\b', query.lower()))
    
    if words & PRONOUNS_MALE:
        return "male"
    if words & PRONOUNS_FEMALE:
        return "female"
    
    return None


def remove_pronouns(query: str) -> str:
    """
    Remove pronouns from query for cleaner processing.
    """
    words = query.split()
    cleaned = [w for w in words if w.lower() not in ALL_PRONOUNS]
    return " ".join(cleaned)
