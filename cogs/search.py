import discord
from discord import app_commands
from discord.ext import commands
from db import init_db, search_exams, latest_exams, EXAM_TYPES, DEPARTMENTS


class Search(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()

    @app_commands.command(name="search", description="過去問を検索します")
    @app_commands.describe(
        subject="科目名(部分一致)",
        year="年度(例: 2026)",
        exam_type="試験区分",
        department="学科",
    )
    @app_commands.choices(
        exam_type=[app_commands.Choice(name=t, value=t) for t in EXAM_TYPES],
        department=[app_commands.Choice(name=d, value=d) for d in DEPARTMENTS],
    )
    async def search(
        self,
        interaction: discord.Interaction,
        subject: str = None,
        year: str = None,
        exam_type: app_commands.Choice[str] = None,
        department: app_commands.Choice[str] = None,
    ):
        results = await search_exams(
            subject=subject,
            year=year,
            exam_type=exam_type.value if exam_type else None,
            department=department.value if department else None,
        )
        if not results:
            await interaction.response.send_message("該当する過去問が見つかりませんでした。", ephemeral=True)
            return

        embed = discord.Embed(title="検索結果", color=discord.Color.green())
        for eid, yr, grade, dept, subj, etype, link in results:
            label = f"[{eid}] {subj} ({yr}年度 {etype})"
            value = f"学科: {dept or '不明'} / 学年: {grade or '不明'}"
            if link:
                value += f"\n[投稿へ移動]({link})"
            embed.add_field(name=label, value=value, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="latest", description="最近登録された過去問を表示します")
    async def latest(self, interaction: discord.Interaction):
        results = await latest_exams()
        if not results:
            await interaction.response.send_message("まだ過去問が登録されていません。", ephemeral=True)
            return

        embed = discord.Embed(title="最新の過去問", color=discord.Color.blurple())
        for eid, yr, grade, dept, subj, etype, link in results:
            label = f"[{eid}] {subj} ({yr}年度 {etype})"
            value = f"学科: {dept or '不明'} / 学年: {grade or '不明'}"
            if link:
                value += f"\n[投稿へ移動]({link})"
            embed.add_field(name=label, value=value, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Search(bot))
