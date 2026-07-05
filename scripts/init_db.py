from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.startup import run_startup_checks


if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings)
    result = run_startup_checks(settings)
    print("Database initialized")
    print(result)
