import uuid
from typing import Tuple, Optional, List, Union, Dict

from disnake import Interaction, MessageInteraction, ButtonStyle, Event, SelectOption, Member, User, TextInputStyle, \
    ModalInteraction, ChannelType
from disnake.abc import GuildChannel
from disnake.ui import Button, StringSelect, UserSelect, Modal, TextInput, ChannelSelect

from src.embeds import WarningEmbed


async def confirm_button(
        interaction: Interaction,
        message: str,
        timeout: int = 30
) -> Tuple[Optional[MessageInteraction], bool]:
    """
    Send a confirmation message with a button.
    :param interaction: The interaction object.
    :param message: The message to send.
    :param timeout: The timeout of the button.
    :return: The interaction object and a boolean indicating if the user confirmed the action.
    """
    custom_id = uuid.uuid1().hex

    await interaction.response.send_message(
        embed=WarningEmbed(
            title="你確定嗎？",
            description=message
        ),
        components=[
            Button(
                style=ButtonStyle.green,
                label="確定",
                custom_id=f"{custom_id}.confirm"
            ),
            Button(
                style=ButtonStyle.red,
                label="取消",
                custom_id=f"{custom_id}.cancel"
            )
        ],
        ephemeral=True
    )

    message_interaction = await interaction.bot.wait_for(
        Event.button_click,
        check=lambda i: i.data.custom_id.startswith(custom_id),
        timeout=timeout
    )

    if message_interaction.data.custom_id.endswith(".confirm"):
        return message_interaction, True

    return message_interaction, False


async def string_select(
        interaction: Interaction,
        placeholder: str,
        options: List[SelectOption],
        min_values: int = 1,
        max_values: int = 1,
        timeout=60
) -> Tuple[MessageInteraction, List[str]]:
    """
    Prompt the user to select a string.
    :param interaction: The interaction object.
    :param placeholder: The placeholder of the string select.
    :param options: The options of the string select.
    :param min_values: The minimum number of strings that can be selected.
    :param max_values: The maximum number of strings that can be selected.
    :param timeout: The timeout of the string select.
    :raise asyncio.TimeoutError: If the string select interaction times out.
    :return: The interaction object and the selected string.
    """
    custom_id = uuid.uuid1().hex

    await interaction.response.send_message(
        components=[StringSelect(
            custom_id=custom_id,
            placeholder=placeholder,
            options=options,
            min_values=min_values,
            max_values=max_values
        )],
        ephemeral=True
    )

    string_select_interaction: MessageInteraction = await interaction.bot.wait_for(
        Event.message_interaction,
        check=lambda i: i.data.custom_id == custom_id,
        timeout=timeout
    )

    return string_select_interaction, string_select_interaction.values


async def user_select(
        interaction: Interaction,
        placeholder: str,
        min_values: int = 1,
        max_values: int = 1,
        timeout=60
) -> Tuple[MessageInteraction, List[Union[Member, User]]]:
    """
    Prompt the user to select a user.
    :param interaction: The interaction object.
    :param placeholder: The placeholder of the user select.
    :param min_values: The minimum number of users that can be selected.
    :param max_values: The maximum number of users that can be selected.
    :param timeout: The timeout of the user select.
    :raise asyncio.TimeoutError: If the user select interaction times out.
    :return: The interaction object and the selected user.
    """
    custom_id = uuid.uuid1().hex

    await interaction.response.send_message(
        components=[UserSelect(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values
        )],
        ephemeral=True
    )

    user_select_interaction: MessageInteraction = await interaction.bot.wait_for(
        Event.message_interaction,
        check=lambda i: i.data.custom_id == custom_id,
        timeout=timeout
    )

    return user_select_interaction, user_select_interaction.resolved_values


async def channel_select(
        interaction: Interaction,
        placeholder: str,
        min_values: int = 1,
        max_values: int = 1,
        channel_types: List[ChannelType] = ChannelType.text,
        timeout=60
) -> Tuple[MessageInteraction, List[Union[GuildChannel]]]:
    """
    Prompt the user to select a channel.

    :param interaction: The interaction object.
    :param placeholder: The placeholder of the channel select.
    :param min_values: The minimum number of channels that can be selected.
    :param max_values: The maximum number of channels that can be selected.
    :param channel_types: The types of channels that can be selected.
    :param timeout: The timeout of the channel select.
    :raise asyncio.TimeoutError: If the channel select interaction times out.
    :return: The interaction object and the selected channel.
    """
    custom_id = uuid.uuid1().hex

    await interaction.response.send_message(
        components=[ChannelSelect(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            channel_types=channel_types
        )],
        ephemeral=True
    )

    user_select_interaction: MessageInteraction = await interaction.bot.wait_for(
        Event.message_interaction,
        check=lambda i: i.data.custom_id == custom_id,
        timeout=timeout
    )

    return user_select_interaction, user_select_interaction.resolved_values


async def quick_modal(
        interaction: Interaction,
        title: str,
        field_name: str,
        placeholder: str,
        value: Optional[str] = None,
        max_length: int = 256,
        min_length: int = 2,
        required: bool = True,
        style: TextInputStyle = TextInputStyle.short,
        timeout: int = 180
) -> Tuple[ModalInteraction, Optional[str]]:
    """
    Quickly create a modal interaction with a single text field.
    :param interaction: The interaction object.
    :param title: The title of the modal.
    :param field_name: The name of the field.
    :param placeholder: The placeholder of the field.
    :param value: The value of the field.
    :param max_length: The maximum length of the field.
    :param min_length: The minimum length of the field.
    :param required: If the field is required.
    :param style: The style of the text input.
    :param timeout: The timeout of the modal.
    :raise asyncio.TimeoutError: If the modal interaction times out.
    :return: The modal interaction object and the value of the field.
    """
    custom_id = uuid.uuid1().hex

    await interaction.response.send_modal(
        modal=Modal(
            title=title,
            components=[
                TextInput(
                    label=field_name,
                    placeholder=placeholder,
                    value=value,
                    style=style,
                    custom_id="text_field",
                    max_length=max_length,
                    min_length=min_length,
                    required=required
                )
            ],
            custom_id=custom_id
        )
    )

    modal_interaction = await interaction.bot.wait_for(
        Event.modal_submit, check=lambda i: i.data.custom_id == custom_id,
        timeout=timeout
    )

    return modal_interaction, modal_interaction.text_values.get("text_field")


async def quick_long_modal(
        interaction: Interaction,
        modal: Modal,
        timeout=180
) -> Tuple[ModalInteraction, Dict[str, str]]:
    """
    Quickly create a long modal interaction.
    :param interaction: The interaction object.
    :param modal: The modal object.
    :param timeout: The timeout of the modal.
    :return: The modal interaction object and the values of the fields.
    """
    custom_id = uuid.uuid1().hex

    modal.custom_id = custom_id

    await interaction.response.send_modal(
        modal=modal
    )

    modal_interaction: ModalInteraction = await interaction.bot.wait_for(
        Event.modal_submit, check=lambda i: i.data.custom_id == custom_id,
        timeout=timeout
    )

    return modal_interaction, modal_interaction.text_values


async def confirm_modal(
        interaction: Interaction,
        text: str,
        confirmation_message: str = "我確定",
        timeout: int = 180
) -> Tuple[ModalInteraction, bool]:
    """
    Quickly create a modal interaction with a confirmation message.
    :param interaction: The interaction object.
    :param text: The text of the confirmation message.
    :param confirmation_message: The message user need to type before confirming.
    :param timeout: The timeout of the modal.
    :return: The modal interaction object and a boolean indicating if the user confirmed the action.
    """
    interaction, response = await quick_modal(
        interaction,
        title=text,
        field_name=f"請輸入 {confirmation_message} 來確認操作",
        placeholder=confirmation_message,
        max_length=100,
        min_length=1,
        timeout=timeout
    )

    if response == confirmation_message:
        return interaction, True

    return interaction, False
