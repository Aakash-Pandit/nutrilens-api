from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def _normalize_password(password: str) -> str:
    raw = password.encode("utf-8")[:72]
    return raw.decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("$2"):
        password = _normalize_password(password)
    return pwd_context.verify(password, hashed_password)
