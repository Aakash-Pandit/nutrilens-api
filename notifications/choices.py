import enum


class NotificationStatus(str, enum.Enum):
    SUCCESS = "success"
    FAIL = "fail"