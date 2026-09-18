def greet(name: str) -> str:
    if not name or not name.strip():
        raise ValueError("name must not be empty")
    return f"Hello, {name}!"
