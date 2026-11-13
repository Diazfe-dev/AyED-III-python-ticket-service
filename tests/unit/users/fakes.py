"""In-memory test doubles for the user service: no Flask, no database."""

from app.domain.errors import DuplicateUserError
from app.domain.paging import Page, PageRequest
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

    def search(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        search_email: bool = True,
        window: PageRequest | None = None,
    ) -> list[User] | Page[User]:
        """Same contract as the real repository: filters, then `(name.casefold(), id)` order."""
        users = [
            user
            for user in self.users.values()
            if (role is None or user.role == role)
            and (is_active is None or user.is_active == is_active)
            and (q is None or _matches(user, q.casefold(), search_email))
        ]
        users.sort(key=lambda user: (user.name.casefold(), user.id))
        if window is None:
            return users
        start = window.offset
        return Page(
            items=users[start : start + window.limit],
            page=window.page,
            page_size=window.page_size,
            total=len(users),
        )


def _matches(user: User, text: str, search_email: bool) -> bool:
    return text in user.name.casefold() or (search_email and text in user.email.casefold())


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
