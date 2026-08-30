import discord
from discord import app_commands
from discord.ext import commands

RULE_TEXT = """新過去問DBのルール:
1. 他人への転載・販売は禁止
2. 個人情報が写り込んだ画像は投稿しない
3. 荒らし・誹謗中傷は禁止
"""

INVITE_LINK = "https://discord.gg/xxxxxxx"  # 実際のリンクに差し替え

WELCOME_TEXT = """ようこそ新過去問DBへ!
過去問を検索するには `/search` を使ってください。
詳しい使い方は `/help` で確認できます。
"""

USAGE_TEXT = """【使い方】
/search <科目> [年度] [試験区分] [学科] - 過去問を検索
/latest - 最近登録された過去問を表示
/add - 過去問を登録(Admin/Contributorのみ)
/report - 削除依頼
"""


def build_help_embed() -> discord.Embed:
    embed = discord.Embed(title="コマンド一覧", color=discord.Color.blurple())
    embed.add_field(name="/search", value="科目・年度・試験区分・学科で過去問を検索します。", inline=False)
    embed.add_field(name="/latest", value="最近登録された過去問を表示します。", inline=False)
    embed.add_field(name="/add", value="過去問を登録します。(Admin または Contributor)", inline=False)
    embed.add_field(name="/edit", value="登録済み過去問の情報を修正します。(Admin)", inline=False)
    embed.add_field(name="/remove", value="過去問を削除します。(Admin)", inline=False)
    embed.add_field(name="/report", value="著作権等の理由で削除を依頼します。", inline=False)
    embed.add_field(name="---", value="以下はレガシーコマンド(旧BOT互換、$から始まる形式)", inline=False)
    embed.add_field(name="$rule", value="新過去問DBのルールを表示します。", inline=False)
    embed.add_field(name="$invite", value="新過去問DBの招待リンクを表示します。", inline=False)
    embed.add_field(name="$usage", value="新過去問DBの使い方を表示します。", inline=False)
    embed.add_field(name="$welcome", value="参加時のメッセージを再表示します。", inline=False)
    return embed


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="使用可能なコマンド一覧を表示します")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=build_help_embed(), ephemeral=True)

    @commands.command(name="cmd")
    async def cmd_list(self, ctx: commands.Context):
        await ctx.send(embed=build_help_embed())

    @commands.command(name="rule")
    async def rule(self, ctx: commands.Context):
        await ctx.send(RULE_TEXT)

    @commands.command(name="invite")
    async def invite(self, ctx: commands.Context):
        await ctx.send(INVITE_LINK)

    @commands.command(name="usage")
    async def usage(self, ctx: commands.Context):
        await ctx.send(USAGE_TEXT)

    @commands.command(name="welcome")
    async def welcome(self, ctx: commands.Context):
        await ctx.send(WELCOME_TEXT)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            await member.send(WELCOME_TEXT)
        except discord.Forbidden:
            pass  # DM拒否設定のユーザーには送れない


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))