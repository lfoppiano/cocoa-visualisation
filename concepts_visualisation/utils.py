import inflect

_inflect_engine = inflect.engine()


def process_key(keyword):
    """Normalize keyword to lowercase singular form."""
    keyl = keyword.lower().replace("-", " ").replace("_", " ")
    singular = _inflect_engine.singular_noun(keyl)
    return singular if singular else keyl
