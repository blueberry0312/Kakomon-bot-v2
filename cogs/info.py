import discord
from discord.ext import commands

RULE_TEXT = """新過去問DBのルール:
1. 他人への転載・販売は禁止
2. 個人情報が写り込んだ画像は投稿しない
3. 荒らし・誹謗中傷は禁止
"""

INVITE_LINK = "https://discord.gg/kChZWPMQ8a"  

WELCOME_TEXT = """ようこそ新過去問DBへ!
過去問を検索するには `$search 科目名` を使ってください。
詳しい使い方は `$usage` で確認できます。
"""

USAGE_TEXT = """【使い方】
$search <科目> [先生名] [年度] - 過去問を検索
$upload - 過去問を投稿するフローを開始(DMで案内)
$cmd - コマンド一覧
"""


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="cmd")
    async def cmd_list(self, ctx: commands.Context):
        embed = discord.Embed(title="コマンド一覧 (beta)", color=discord.Color.blurple())
        embed.add_field(name="$cmd", value="使用可能なコマンド一覧を表示します。", inline=False)
        embed.add_field(name="$rule", value="新過去問DBのルールを表示します。", inline=False)
        embed.add_field(name="$invite", value="新過去問DBの招待リンクを表示します。", inline=False)
        embed.add_field(name="$usage", value="新過去問DBの使い方を表示します。", inline=False)
        embed.add_field(name="$welcome", value="参加時のメッセージを再表示します。", inline=False)
        embed.add_field(name="$search", value="過去問をタグ検索します。", inline=False)
        await ctx.send(embed=embed)

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
