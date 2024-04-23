import uuid
from typing import Union, Dict, Tuple, TYPE_CHECKING

from disnake import PermissionOverwrite, Member, Role, Interaction, ModalInteraction, TextInputStyle, Event
from disnake.ui import Modal, TextInput

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


async def quick_modal(
        interaction: Interaction,
        title: str,
        field_name: str,
        placeholder: str,
        value: str,
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
            custom_id=uuid.uuid1().hex
        )
    )

    modal_interaction = await interaction.bot.wait_for(
        Event.modal_submit, check=lambda i: i.data.custom_id == custom_id,
        timeout=timeout
    )

    return modal_interaction, modal_interaction.text_values.get("text_field")
