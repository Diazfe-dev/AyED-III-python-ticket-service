"""In-memory test doubles for the user service: no Flask, no database."""

from app.domain.errors import DuplicateUserError
from app.domain.users import User, normalize_email


class FakeUserRepository:
    """Dictionary-backed repository that assigns ids like the database would."""

    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.add_calls = 0

    def add(self, user: User) -> None:
        self.add_calls += 1
        owner = self.find_by_email(user.email)
        if owner is not None and owner is not user:
            raise DuplicateUserError()
        if user.id is None:
            user.id = len(self.users) + 1
        self.users[user.id] = user

    def get(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    def find_by_email(self, email: str) -> User | None:
        wanted = normalize_email(email)
        return next((user for user in self.users.values() if user.email == wanted), None)

    def list_by_role(self, role: str) -> list[User]:
        return [user for _, user in sorted(self.users.items()) if user.role == role]


class FakePasswordHasher:
    """Readable, instant hash: `hashed:<password>`. Records every `verify` call."""

    def __init__(self) -> None:
        self.verify_calls: list[tuple[str, str]] = []

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        self.verify_calls.append((password_hash, password))
        return password_hash == self.hash(password)

    def dummy_hash(self) -> str:
        return self.hash("dummy-password")


class CommitSpy:
    """Stands in for `session.commit` and counts the calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
