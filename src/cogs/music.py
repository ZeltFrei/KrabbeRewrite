import random
from typing import TYPE_CHECKING, Tuple, Optional

from disnake import ApplicationCommandInteraction, Option, OptionType, OptionChoice, ButtonStyle
from disnake.ext.commands import Cog, slash_command
from disnake.ui import Button
from disnake_ext_paginator import Paginator

from src.classes.voice_channel import VoiceChannel
from src.embeds import SuccessEmbed, ErrorEmbed, InfoEmbed
from src.kava.utils import ensure_music_client, ensure_music_permissions, get_active_client_in, get_idle_clients_in
from src.utils import split_list

if TYPE_CHECKING:
    from src.bot import Krabbe
    from src.kava.server import KavaServer, ServerSideClient


async def music_check(
        server: "KavaServer",
        interaction: ApplicationCommandInteraction
) -> Tuple[bool, Optional["ServerSideClient"], Optional[VoiceChannel]]:
    if not (client := await ensure_music_client(server, interaction)):
        return False, None, None

    if not (channel := await ensure_music_permissions(interaction)):
        return False, client, None

    return True, client, channel


class Music(Cog):
    def __init__(self, bot: "Krabbe"):
        self.bot: "Krabbe" = bot
        self.server: Optional["KavaServer"] = None

    @Cog.listener(name="on_ready")
    async def on_ready(self):
        self.server = self.bot.kava_server

    @slash_command(
        name="nowplaying",
        description="顯示目前正在播放的歌曲"
    )
    async def nowplaying(self, interaction: ApplicationCommandInteraction):
        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request("nowplaying", channel_id=channel.channel_id)

        if response["status"] == "success":
            await interaction.response.send_message(
                embed=SuccessEmbed(response["message"]),
                ephemeral=True
            )
        elif response["status"] == "error":
            await interaction.response.send_message(
                embed=ErrorEmbed(response["message"]),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=ErrorEmbed("未知的錯誤"),
                ephemeral=True
            )

    @slash_command(
        name="py",
        description="播放音樂",
        options=[
            Option(
                name="query",
                description="歌曲名稱或網址，支援 YouTube, YouTube Music, SoundCloud, Spotify",
                type=OptionType.string,
                autocomplete=True,
                required=True
            ),
            Option(
                name="index",
                description="要將歌曲放置於當前播放序列的位置",
                type=OptionType.integer,
                required=False
            )
        ]
    )
    async def play(self, interaction: ApplicationCommandInteraction, query: str, index: int = None):
        if not (channel := await ensure_music_permissions(interaction)):
            return

        await interaction.response.defer(ephemeral=True)

        if not (client := get_active_client_in(self.bot.kava_server, channel)):
            idle_clients = get_idle_clients_in(self.bot.kava_server, channel.channel.guild)

            if not idle_clients:
                await interaction.response.send_message(
                    embed=ErrorEmbed("目前沒有可用的音樂機器人，請稍後再試"),
                    ephemeral=True
                )
                return

            client = idle_clients[0]

            response = await client.request(
                'connect', owner_id=channel.owner_id, channel_id=channel.channel_id
            )

            if not response["status"] == "success":
                await interaction.response.send_message(
                    embed=ErrorEmbed(response["message"]),
                    ephemeral=True
                )
                return

        response = await client.request(
            "play", channel_id=channel.channel_id, author_id=interaction.author.id, query=query, index=index
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤"),
            )

    @play.autocomplete("query")
    async def play_autocomplete(self, interaction: ApplicationCommandInteraction, query: str):
        channel = VoiceChannel.get_active_channel_from_interaction(interaction)

        if not channel:
            return [OptionChoice(name="請先加入一個語音頻道！", value="")]

        response = await random.choice(list(self.server.clients.values())).request("search", query=query)

        return [OptionChoice.from_dict(choice) for choice in response['results']]

    @slash_command(
        name="sk",
        description="跳過當前播放的歌曲",
        options=[
            Option(
                name="target",
                description="要跳到的歌曲編號",
                type=OptionType.integer,
                required=False
            ),
            Option(
                name="move",
                description="是否移除目標以前的所有歌曲，如果沒有提供 target，這個參數會被忽略",
                type=OptionType.boolean,
                required=False
            )
        ]
    )
    async def skip(self, interaction: ApplicationCommandInteraction, target: int = None, move: bool = False):
        await interaction.response.defer(ephemeral=True)

        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "skip", channel_id=channel.channel_id, target=target, move=move
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤"),
            )

    @slash_command(
        name="rm",
        description="移除歌曲",
        options=[
            Option(
                name="target",
                description="要移除的歌曲編號",
                type=OptionType.integer,
                required=True
            )
        ]
    )
    async def remove(self, interaction: ApplicationCommandInteraction, target: int):
        await interaction.response.defer(ephemeral=True)

        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "remove", channel_id=channel.channel_id, target=target
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤"),
            )

    @slash_command(
        name="cl",
        description="清除播放序列",
    )
    async def clean(self, interaction: ApplicationCommandInteraction):
        await interaction.response.defer(ephemeral=True)

        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "clean", channel_id=channel.channel_id
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤")
            )

    @slash_command(
        name="ps",
        description="暫停當前播放的歌曲"
    )
    async def pause(self, interaction: ApplicationCommandInteraction):
        await interaction.response.defer(ephemeral=True)

        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "pause", channel_id=channel.channel_id
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤"),
            )

    @slash_command(
        name="ct",
        description="恢復當前播放的歌曲"
    )
    async def resume(self, interaction: ApplicationCommandInteraction):
        await interaction.response.defer(ephemeral=True)

        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "resume", channel_id=channel.channel_id
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤"),
            )

    @slash_command(
        name="sp",
        description="停止播放並清空播放序列",
    )
    async def stop(self, interaction: ApplicationCommandInteraction):
        await interaction.response.defer(ephemeral=True)

        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "stop", channel_id=channel.channel_id
        )

        if response["status"] == "success":
            await interaction.edit_original_response(
                embed=SuccessEmbed(response["message"]),
            )
        elif response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
        else:
            await interaction.edit_original_response(
                embed=ErrorEmbed("未知的錯誤"),
            )

    @slash_command(
        name="qe",
        description="顯示播放序列",
    )
    async def queue(self, interaction: ApplicationCommandInteraction):
        check_passed, client, channel = await music_check(self.server, interaction)

        if not check_passed:
            return

        response = await client.request(
            "queue", channel_id=channel.channel_id
        )

        if response["status"] == "error":
            await interaction.edit_original_response(
                embed=ErrorEmbed(response["message"]),
            )
            return

        pages: list[InfoEmbed] = []

        for iteration, songs_in_page in enumerate(split_list(response["queue"], 10)):
            pages.append(
                InfoEmbed(
                    title="播放序列",
                    description='\n'.join(
                        [
                            f"**[{index + 1 + (iteration * 10)}]** {track['title']}"
                            for index, track in enumerate(songs_in_page)
                        ]
                    )
                )
            )

        paginator = Paginator(
            timeout=60,
            previous_button=Button(
                style=ButtonStyle.blurple, emoji='⏪'
            ),
            next_button=Button(
                style=ButtonStyle.blurple,
                emoji='⏩'
            ),
            trash_button=Button(
                style=ButtonStyle.red,
                emoji='⏹️'
            ),
            page_counter_style=ButtonStyle.green,
            interaction_check_message=ErrorEmbed("沒事戳這顆幹嘛？")
        )

        await paginator.start(interaction, pages)


def setup(bot: "Krabbe"):
    bot.add_cog(Music(bot))
