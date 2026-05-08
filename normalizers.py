import re
try:
    from logging_utils import log_warning
except ImportError:
    pass  # Allow running independently if needed

NORMALIZATION_MAPPINGS = {
    "region": {
        "apac": "APAC",
        "asia pacific": "APAC",
        "na": "North America",
        "north america": "North America",
        "eu": "Europe",
        "europe": "Europe",
        "latam": "LATAM",
        "latin america": "LATAM"
    },
    "genre": {
        "scifi": "Sci-Fi",
        "sci-fi": "Sci-Fi",
        "science fiction": "Sci-Fi",
        "drama": "Drama",
        "thriller": "Thriller",
        "fantasy": "Fantasy",
        "action": "Action"
    },
    "device_type": {
        "smarttv": "Smart TV",
        "smart tv": "Smart TV",
        "mobile": "Mobile",
        "iphone": "Mobile",
        "android": "Mobile",
        "desktop": "Desktop",
        "web": "Desktop",
        "tablet": "Tablet"
    },
    "subscription_type": {
        "basic": "Basic",
        "standard": "Standard",
        "premium": "Premium"
    }
}

def normalize_text_field(value):
    """
    Trims whitespace and reduces repeated spaces.
    Does not hide malformed strings or impossible values.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)
        
    cleaned = re.sub(r'\s+', ' ', value).strip()
    return cleaned

def _apply_mapping(value, mapping_dict, field_name, dataset_type="startup"):
    """
    Applies dictionary mapping and handles capitalization drift.
    Returns structured normalization result.
    """
    if value is None:
        return {"value": None, "changed": False, "message": None}
        
    cleaned_value = normalize_text_field(value)
    
    # Enterprise dataset: mostly pass-through, minimal normalization (whitespace only)
    if dataset_type == "enterprise":
        if cleaned_value != value:
            return {
                "value": cleaned_value,
                "changed": True,
                "message": f"Trimmed whitespace in {field_name}: '{value}' -> '{cleaned_value}'"
            }
        return {"value": value, "changed": False, "message": None}

    # Startup dataset: actively apply normalization mapping
    lower_value = cleaned_value.lower()
    
    if lower_value in mapping_dict:
        normalized = mapping_dict[lower_value]
        if normalized != value:
            return {
                "value": normalized,
                "changed": True,
                "message": f"Normalized {field_name} from '{value}' to '{normalized}'"
            }
            
    # If no specific mapping matched, but whitespace was trimmed
    if cleaned_value != value:
        return {
            "value": cleaned_value,
            "changed": True,
            "message": f"Cleaned {field_name} text spacing: '{value}' -> '{cleaned_value}'"
        }
        
    return {"value": value, "changed": False, "message": None}

def normalize_region(value, dataset_type="startup"):
    return _apply_mapping(value, NORMALIZATION_MAPPINGS["region"], "region", dataset_type)

def normalize_genre(value, dataset_type="startup"):
    return _apply_mapping(value, NORMALIZATION_MAPPINGS["genre"], "genre", dataset_type)

def normalize_device_type(value, dataset_type="startup"):
    return _apply_mapping(value, NORMALIZATION_MAPPINGS["device_type"], "device_type", dataset_type)

def normalize_subscription_type(value, dataset_type="startup"):
    return _apply_mapping(value, NORMALIZATION_MAPPINGS["subscription_type"], "subscription_type", dataset_type)

def process_and_log_normalization(conn, dataset, source_file, table_name, row_reference, field_name, value, normalizer_func):
    """
    Executes the normalization and logs a WARNING if the data was modified.
    Automatically detects enterprise vs startup dataset.
    """
    dataset_type = "enterprise" if "vistastream" in dataset.lower() else "startup"
    result = normalizer_func(value, dataset_type=dataset_type)
    
    if result["changed"]:
        try:
            log_warning(conn, dataset, source_file, table_name, row_reference, "normalized", result["message"])
        except NameError:
            # Fallback if logging_utils is not imported
            print(f"[WARNING] {result['message']}")
            
    return result["value"]
