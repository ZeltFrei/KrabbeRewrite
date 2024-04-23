import uuid
from typing import Union, Dict, Tuple, TYPE_CHECKING, List

from disnake import PermissionOverwrite, Member, Role, Interaction, ModalInteraction, TextInputStyle, Event, User, \
    MessageInteraction
from disnake.ui import Modal, TextInput, UserSelect

if TYPE_CHECKING:
    from src.classes.guild_settings import GuildSettings
    from src.classes.channel_settings import ChannelSettings


def generate_permission_overwrites(
        channel_settings: "ChannelSettings",
        guild_settings: "GuildSettings"
) -> Dict[Union[Role, Member], PermissionOverwrite]:
    """
    Generate
    :return:
    """
    return {}


async def user_select(
        interaction: Interaction,
        placeholder: str,
        min_values: int = 1,
        max_values: int = 1
) -> Tuple[MessageInteraction, List[Union[Member, User]]]:
    """
    Prompt the user to select a user.
    :param interaction: The interaction object.
    :param placeholder: The placeholder of the user select.
    :param min_values: The minimum number of users that can be selected.
    :param max_values: The maximum number of users that can be selected.
    :return: The interaction object and the selected user.
    """
    custom_id = uuid.uuid1().hex

    await interaction.response.send_message(
        components=[UserSelect(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values
        )]
    )

    user_select_interaction: MessageInteraction = await interaction.bot.wait_for(
        Event.message_interaction, check=lambda i: i.data.custom_id == custom_id
    )

    return user_select_interaction, user_select_interaction.resolved_values


async def quick_modal(
        interaction: Interaction,
        title: str,
        field_name: str,
        placeholder: str,
        value: str = "",
        max_length: int = 256,
        min_length: int = 2,
        style: TextInputStyle = TextInputStyle.short,
        timeout: int = 180
) -> Tuple[ModalInteraction, str]:
    """
    Quickly create a modal interaction with a single text field.
    :param interaction: The interaction object.
    :param title: The title of the modal.
    :param field_name: The name of the field.
    :param placeholder: The placeholder of the field.
    :param value: The value of the field.
    :param max_length: The maximum length of the field.
    :param min_length: The minimum length of the field.
    :param style: The style of the text input.
    :param timeout: The timeout of the modal.
    :raise TimeoutError: If the modal interaction times out.
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
                    required=True
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
