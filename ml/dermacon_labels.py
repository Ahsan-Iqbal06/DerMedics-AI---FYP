"""DermaCon-IN (Harvard Dataverse doi:10.7910/DVN/W7OUZM) diagnosis -> DerMedics app label.

Grouping follows the DermNet categories the app was first trained on (e.g. DermNet's fungal class also holds
candidiasis and pityriasis versicolor), so both datasets agree on what each label means.
Anything not listed becomes "unsupported", except labels in EXCLUDE, which are dropped (ambiguous or not a
skin-condition photo).
"""

DERMACON_MAP = {
    # acne
    "Acne": "acne", "Acne Conglobata": "acne", "Truncal Acne": "acne",
    # eczema (atopic, nummular, infected eczema)
    "Eczema": "eczema", "Infected Eczema": "eczema", "Atopic Dermatitis": "eczema", "Ear Eczema": "eczema",
    "Disseminated Eczema": "eczema", "Dry Discoid Eczema": "eczema", "Crusted eczematous dermatitis": "eczema",
    "Chronic eczema with secondary infection": "eczema",
    # contact dermatitis
    "Contact Dermatitis": "contact_dermatitis", "Allergic Contact Dermatitis": "contact_dermatitis",
    "Textile Dermatitis": "contact_dermatitis", "Kumkum Dermatitis": "contact_dermatitis",
    "Contact Dermatitis with secondary infection": "contact_dermatitis",
    # psoriasis
    "Psoriasis": "psoriasis", "Chronic plaque psoriasis": "psoriasis", "Guttate Psoriasis": "psoriasis",
    "Psoriasis Vulgaris": "psoriasis", "Palmar psoriasis": "psoriasis", "Inverse psoriasis": "psoriasis",
    "Pustular psoriasis": "psoriasis",
    # fungal (tinea, candida, versicolor) — same grouping as DermNet's fungal category
    "Tinea Cruris": "tinea", "Tinea Corporis": "tinea", "Tinea Faciei": "tinea", "Steroid Modified Tinea": "tinea",
    "Candidal Intertrigo": "tinea", "Tinea Versicolor": "tinea", "Tinea Capitis": "tinea", "Tinea": "tinea",
    "Tinea Manuum": "tinea", "Tinea pedis": "tinea", "Infected Tinea": "tinea",
    "Tinea Infected with secondary bacterial Infection": "tinea", "Eczemated Tinea": "tinea",
    # scabies
    "Scabies": "scabies", "Nodular Scabies": "scabies", "Scabies Infected": "scabies", "Pustular Scabies": "scabies",
    # bacterial (impetigo, pyoderma, furuncle, folliculitis, cellulitis) — DermNet's bacterial category
    "Impetigo": "impetigo", "Pyoderma": "impetigo", "Furuncle": "impetigo", "Folliculitis": "impetigo",
    "Cellulitis": "impetigo",
    # pigmentation
    "Vitiligo": "pigmentation_disorder", "Melasma": "pigmentation_disorder",
    "Post-Inflammatory hyperpigmentation": "pigmentation_disorder",
    "Post-Inflammatory hypopigmentation": "pigmentation_disorder", "Hyperpigmentation disorder": "pigmentation_disorder",
    "Nevus Depigmentosis": "pigmentation_disorder",
    # urticaria
    "Urticaria": "urticaria",
    # warts / viral papules
    "Wart": "warts", "Verruca Vulgaris": "warts", "Molluscum Contagiosum": "warts",
}

# Dropped entirely: no definite diagnosis, normal-looking skin, or conditions whose look overlaps an app label
# without being it (would teach the model the wrong thing).
EXCLUDE = {
    "No Definite Diagnosis", "Acne Scars", "Acne Keloidalis", "Pruritic Urticarial Papules", "Urticarial vasculitis",
    "Candidal Balanoposthitis", "Candidal Vulvovaginitis", "Oral Candidiasis", "Folliculitis Decalvans",
    "Pyoderma gangrenosum", "Pseudofolliculitis barbae", "Epidermodysplasia Verruciformis",
    "Inflammatory Linear Verrucous Epidermal Nevus", "Lichen Planus pigmentosus", "Reticulate acropigmentation of Dohi",
}


def dermacon_target(disease: str, quality: str) -> str | None:
    disease = disease.strip()
    if disease in EXCLUDE or "NO DISCERNIBLE PATHOLOGY" in quality or quality.startswith("No,"):
        return None
    return DERMACON_MAP.get(disease, "unsupported")
