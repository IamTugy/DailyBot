from abc import ABC
from enum import Enum
from functools import lru_cache
from typing import List

from pydantic import BaseModel, constr, validator


class TextType(Enum):
    PlainText = 'plain_text'
    MarkdownText = 'mrkdwn'


class TextWithoutMaxSize(BaseModel):
    type: TextType
    text: str
    # Indicates whether emojis in a text field should be escaped into the colon emoji format.
    emoji: bool | None = None  # only plain_text

    # When set to false (as is default) URLs will be auto-converted into links,
    # conversation names will be link-ified, and certain mentions will be automatically parsed.
    verbatim: bool | None = None  # only mrkdwn

    @validator('emoji')
    def use_emoji_only_for_plain_text(self, v, values):
        if v is not None and values['type'] != TextType.PlainText:
            raise ValueError(f'emoji field can only used with {TextType.PlainText} type text')

    @validator('verbatim')
    def use_verbatim_only_for_markdown_text(self, v, values):
        if v is not None and values['type'] != TextType.MarkdownText:
            raise ValueError(f'verbatim field can only used with {TextType.MarkdownText} type text')

    def as_dict(self):
        obj = {
            "type": self.type.value,
            "text": self.text
        }

        if self.emoji is not None:
            obj['emoji'] = self.emoji

        if self.verbatim is not None:
            obj['verbatim'] = self.verbatim

        return obj


class Text:
    def __init__(self, text_max_length: int = 3000):
        class TextWithMaxSize(TextWithoutMaxSize):
            @validator('text')
            def validate_text_less_then_max_length(self, v):
                if v > text_max_length:
                    raise ValueError(f'text is longer then {text_max_length} max size')

        self.return_class = TextWithMaxSize

    def __call__(self, *args, **kwargs):
        return self.return_class


class SelectType(Enum):
    StaticSelect = 'static_select'


class Option(BaseModel):
    text: Text(75)()

    # A unique string value that will be passed to your app when this option is chosen.
    value: constr(max_length=75)

    # defines a line of descriptive text shown below the text field beside the radio button.
    description: Text(75)() | None = None

    # A URL to load in the user's browser when the option is clicked.
    # The url attribute is only available in overflow menus.
    # Maximum length for this field is 3000 characters.
    # If you're using url, you'll still receive an interaction payload and will need to send an
    # acknowledgement response.
    url: constr(max_length=3000) | None = None

    @validator('description')
    def description_use_plain_text_only(self, v):
        if v is not None and v['text'].type != TextType.PlainText:
            raise ValueError(f'description must be a {TextType.PlainText} type text')

    def as_dict(self):
        obj = {
            "text": self.text.as_dict(),
            "value": self.value
        }

        if self.url is not None:
            obj['url'] = self.url

        if self.description is not None:
            obj['description'] = self.description

        return obj


class OptionGroup(BaseModel):
    label: Text(75)()
    options: List[Option] = []

    @validator('label')
    def label_use_plain_text_only(self, v):
        if v is not None and v['text'].type != TextType.PlainText:
            raise ValueError(f'label must be a {TextType.PlainText} type text')

    @validator('options')
    def options_validate(self, v: List[Option]):
        if len(v) > 100:
            raise ValueError('Maximum number of options is 100')

        if not len(v):
            raise ValueError('options must have at least 1 option')


class Select(BaseModel):
    type: SelectType

    # defines the placeholder text shown on the menu.
    placeholder: Text(150)()

    # An identifier for the action triggered when a menu option is selected.
    # You can use this when you receive an interaction payload to identify the source of the action.
    # Should be unique among all other action_ids in the containing block.
    action_id: constr(max_length=255)

    options: List[Option] = []
    option_groups: List[OptionGroup] | None = None
    initial_option: Option | OptionGroup | None = None # --------> validate me!

    @validator('placeholder')
    def placeholder_use_plain_text_only(self, v: Text(150)()):
        if v is not None and v.type != TextType.PlainText:
            raise ValueError(f'placeholder must be a {TextType.PlainText} type text')

    @validator('options')
    def options_validate(self, v: List[Option], values):
        if v and 'option_groups' in values and values['option_groups']:
            raise ValueError('If `option_groups` is specified, `options` field should not be.')

        if len(v) > 100:
            raise ValueError('Maximum number of options is 100')

        if not len(v):
            raise ValueError('options must have at least 1 option')

    @validator('option_groups')
    def option_groups_validate(self, v: List[OptionGroup], values):
        if v and 'options' in values and values['options']:
            raise ValueError('If `options` is specified, `option_groups` field should not be.')

        if len(v) > 100:
            raise ValueError('Maximum number of option_groups is 100')

        if not len(v):
            raise ValueError('option_groups must have at least 1 group')

