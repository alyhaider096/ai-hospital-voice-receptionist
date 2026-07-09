from app.db.seed import seed_database
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        seed_database(db)
    print("Seed data created.")


if __name__ == "__main__":
    main()

