from enum import Enum
from typing import List

from pydantic import BaseModel, constr, validator, Field


class TextType(Enum):
    PlainText = 'plain_text'
    MarkdownText = 'mrkdwn'


class Text(BaseModel):
    type: TextType
    text: str
    # Indicates whether emojis in a text field should be escaped into the colon emoji format.
    emoji: bool | None = None  # only plain_text

    # When set to false (as is default) URLs will be auto-converted into links,
    # conversation names will be link-ified, and certain mentions will be automatically parsed.
    verbatim: bool | None = None  # only mrkdwn

    class Config:
        use_enum_values = True

    @classmethod
    @validator('emoji')
    def use_emoji_only_for_plain_limited_text(cls, v: bool, values):
        if v is not None and 'type' in values and values['type'] != TextType.PlainText:
            raise ValueError(f'emoji field can only used with {TextType.PlainText} type text')

    @classmethod
    @validator('verbatim')
    def use_verbatim_only_for_markdown_limited_text(cls, v: bool, values):
        if v is not None and 'type' in values and values['type'] != TextType.MarkdownText:
            raise ValueError(f'verbatim field can only used with {TextType.MarkdownText} type text')


def limited_text(max_text_length: int = 3000, restrict_type: TextType | None = None):
    class LimitedText(Text):
        text: constr(max_length=max_text_length)

        @classmethod
        @validator('type', allow_reuse=True)
        def restrict_text_type(cls, v: TextType):
            if restrict_type and v != restrict_type:
                raise ValueError(f'text must be a {restrict_type.name} type text')

    return LimitedText


class ButtonStyle(Enum):
    danger = 'danger'
    primary = 'primary'


class ConfirmationDialog(BaseModel):
    title: limited_text(max_text_length=100, restrict_type=TextType.PlainText)
    text: limited_text(max_text_length=300)
    confirm: limited_text(max_text_length=30, restrict_type=TextType.PlainText)
    deny: limited_text(max_text_length=30, restrict_type=TextType.PlainText)
    style: ButtonStyle | None = None

    class Config:
        use_enum_values = True


class Option(BaseModel):
    text: limited_text(75)

    # A unique string value that will be passed to your app when this option is chosen.
    value: constr(max_length=75)

    # defines a line of descriptive text shown below the text field beside the radio button.
    description: limited_text(max_text_length=75, restrict_type=TextType.PlainText) | None = None

    # A URL to load in the user's browser when the option is clicked.
    # The url attribute is only available in overflow menus.
    # Maximum length for this field is 3000 characters.
    # If you're using url, you'll still receive an interaction payload and will need to send an
    # acknowledgement response.
    url: constr(max_length=3000) | None = None


class OptionGroup(BaseModel):
    label: limited_text(max_text_length=75, restrict_type=TextType.PlainText)
    options: List[Option] = []

    @classmethod
    @validator('options')
    def options_validate(cls, v: List[Option]):
        if len(v) > 100:
            raise ValueError('Maximum number of options is 100')

        if not len(v):
            raise ValueError('options must have at least 1 option')


class BlockElementType(Enum):
    StaticSelect = 'static_select'
    MultiStaticSelect = 'multi_static_select'
    Checkboxes = 'checkboxes'
    RadioButtons = 'radio_buttons'
    Button = 'button'
    PlainTextInput = 'plain_text_input'


class BaseElement(BaseModel):
    @property
    def element_options(self):
        return [element_type.name for element_type in BlockElementType]

    type: BlockElementType

    # An identifier for the action triggered when a menu option is selected.
    # You can use this when you receive an interaction payload to identify the source of the action.
    # Should be unique among all other action_ids in the containing block.
    action_id: constr(max_length=255)

    class Config:
        use_enum_values = True

    @classmethod
    @validator('type')
    def type_validate(cls, v: BlockElementType):
        if v not in [BlockElementType.StaticSelect]:
            raise ValueError(f'Element is not one of {cls.element_options} options')


class ConfirmableElement(BaseElement):
    confirm: ConfirmationDialog | None = None


class SelectElement(ConfirmableElement):
    # Indicates whether the element will be set to auto focus within the view object.
    # Only one element can be set to true. Defaults to false.
    focus_on_load: bool | None = None


class BlockType(Enum):
    actions = 'actions'
    input = 'input'
    divider = 'divider'
    header = 'header'
    context = 'context'
    section = 'section'


class Block(BaseModel):
    type: BlockType

    # A string acting as a unique identifier for a block. If not specified,a block_id will be generated.
    # You can use this block_id when you receive an interaction payload to identify the source of the action.
    # block_id should be unique for each message and each iteration of a message.
    # If a message is updated, use a new block_id.
    block_id: constr(max_length=255) | None = None

    class Config:
        use_enum_values = True


class ActionsBlock(Block):
    type: BlockType = BlockType.actions
    elements: List[BaseElement] = Field(max_items=25)


class InputBlock(Block):
    type: BlockType = BlockType.input
    label: limited_text(max_text_length=2000, restrict_type=TextType.PlainText)
    element: BaseElement

    # A boolean that indicates whether or not the use of elements in this block should dispatch a block_actions payload.
    dispatch_action: bool | None = None

    # An optional hint that appears below an input element in a lighter grey.
    hint: limited_text(max_text_length=2000, restrict_type=TextType.PlainText) | None = None

    # A boolean that indicates whether the input element may be empty when a user submits the modal.
    optional: bool | None = None


class DividerBlock(Block):
    type: BlockType = BlockType.divider


class ContextBlock(Block):
    type: BlockType = BlockType.context
    elements: List[Text] = Field(max_items=10)


class HeaderBlock(Block):
    type: BlockType = BlockType.header
    text: limited_text(max_text_length=150, restrict_type=TextType.PlainText)


class SectionBlock(Block):
    type: BlockType = BlockType.section
    text: limited_text(max_text_length=3000) | None = None
    # TODO: add 'fields' and validate text/field -> https://api.slack.com/reference/block-kit/blocks#section
    fields: List[Text] | None = None
    accessory: BaseElement | None = None


class SelectMenu(SelectElement):
    @property
    def element_options(self):
        return [BlockElementType.StaticSelect]

    options: List[Option] = Field(default=None, max_items=100)
    # defines the placeholder text shown on the menu.g
    placeholder: limited_text(max_text_length=150, restrict_type=TextType.PlainText)
    initial_option: Option | OptionGroup | None = None
    option_groups: List[OptionGroup] | None = Field(default=None, max_items=100)

    @classmethod
    @validator('options')
    def options_validate(cls, v: List[Option], values):
        if v and 'option_groups' in values and values['option_groups']:
            raise ValueError('If `option_groups` is specified, `options` field should not be.')

        if len(v) > 100:
            raise ValueError('Maximum number of options is 100')

        if not len(v):
            raise ValueError('options must have at least 1 option')

    @classmethod
    @validator('option_groups')
    def option_groups_validate(cls, v: List[OptionGroup], values):
        if v and 'options' in values and values['options']:
            raise ValueError('If `options` is specified, `option_groups` field should not be.')

        if not len(v):
            raise ValueError('option_groups must have at least 1 group')

    @classmethod
    @validator('initial_option')
    def initial_option_validate(cls, v: OptionGroup | Option, values):
        options = values.get('options')
        option_groups = values('option_groups')

        if v and options and v.value not in [option.value for option in options]:
            raise ValueError('initial_option should exactly match one of the options within options or option_groups')

        if v and option_groups:
            option_group_values = sorted(option.value for option in v.options)
            option_groups_values = [sorted(option.value for option in group.options) for group in option_groups]
            if option_group_values not in option_groups_values:
                raise ValueError(
                    'initial_option should exactly match one of the options within options or option_groups')


class MultiSelectMenu(SelectMenu):
    @property
    def element_options(self):
        return [BlockElementType.MultiStaticSelect]

    max_selected_items: int | None = Field(None, mt=1)



class Selector(SelectElement):
    @property
    def element_options(self):
        return [BlockElementType.Checkboxes, BlockElementType.RadioButtons]

    options: List[Option] = Field(min_items=1, max_items=10)
    initial_option: List[Option] | None = None

    @classmethod
    @validator('initial_option')
    def initial_option_validate(cls, v: List[Option], values):
        options_values = [option.value for option in values.get('options', [])]

        for option in v:
            if option.value not in options_values:
                raise ValueError('initial_option should exactly match one or many of the options')


class Button(ConfirmableElement):
    @property
    def element_options(self):
        return [BlockElementType.Button]

    text: limited_text(max_text_length=75, restrict_type=TextType.PlainText)

    # A URL to load in the user's browser when the button is clicked.
    # If you're using url, you'll still receive an interaction payload and will need to send an acknowledgement response
    url: constr(max_length=3000) | None = None

    # The value to send along with the interaction payload.
    value: constr(max_length=2000) | None = None
    style: ButtonStyle | None = None

    # t a button element. This label will be read out by screen readers instead of the button text object
    accessibility_label: constr(max_length=75) | None = None


class TriggerActions(Enum):
    #  payload is dispatched when user presses the enter key while the input is in focus.
    #  Hint text will appear underneath the input explaining to the user to press enter to submit.
    onEnterPressed = 'on_enter_pressed'
    # payload is dispatched when a character is entered (or removed) in the input.
    onCharacterEntered = 'on_character_entered'


class DispatchActionConfiguration(BaseElement):
    trigger_actions_on: List[TriggerActions] | None = None


class Input(BaseElement):
    @property
    def element_options(self):
        return [BlockElementType.PlainTextInput]

    # Defines the placeholder text shown in the plain-text input
    placeholder: limited_text(max_text_length=150, restrict_type=TextType.PlainText) | None = None
    initial_value: str | None = None

    # Indicates whether the input will be a single line (false) or a larger textarea (true). Defaults to false.
    multiline: bool | None = None

    # The minimum length of input that the user must provide. If the user provides less, they will receive an error.
    min_length: int | None = Field(None, lt=3000)

    # The maximum length of input that the user can provide. If the user provides more, they will receive an error.
    max_length: int | None = None
    dispatch_action_config: DispatchActionConfiguration | None = None

    # Indicates whether the element will be set to auto focus within the view object.
    # Only one element can be set to true. Defaults to false.
    focus_on_load: bool | None = None


def serialize_blocks(blocks: List[Block]):
    return [block.dict(exclude_none=True, by_alias=True) for block in blocks]
