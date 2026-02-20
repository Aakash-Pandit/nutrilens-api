from enum import Enum


class UserType(str, Enum):
    ADMIN = "ADMIN"
    REGULAR = "REGULAR"