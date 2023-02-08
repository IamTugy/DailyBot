from pydantic import BaseModel, Field


class TruncatedBase(str):
    DOTS_AMOUNT = 3
    limit: int

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def truncate(cls, value: str):
        size = cls.limit - cls.DOTS_AMOUNT
        return value[:size] + "..." if len(value) > cls.limit else value

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')
        if not v:
            raise TypeError('empty string is not allowed')
        return cls(cls.truncate(v))


def truncated_text(limit=10):
    return type('TruncatedText', (TruncatedBase,), {'limit': limit})
