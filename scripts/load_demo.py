from __future__ import annotations

from app.core.config import get_settings
from app.database.session import get_engine
from app.services.data_loader import DemoDataLoader


def main() -> None:
    settings = get_settings()
    loader = DemoDataLoader(settings.resolved_raw_data_dir, get_engine())
    result = loader.load_demo(reset_existing=True)
    print(result)


if __name__ == "__main__":
    main()

