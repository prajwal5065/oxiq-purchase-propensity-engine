import asyncio

from app.db.session import Base, engine
import app.models  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
