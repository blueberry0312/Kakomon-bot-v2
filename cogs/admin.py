import os
import discord
from discord import app_commands
from discord.ext import commands
from db import (
    init_db, add_exam, find_duplicate, soft_delete_exam, edit_exam, get_exam,
    EXAM_TYPES, DEPARTMENTS,
)

# 「Admin」ロール: 削除・編集などサーバー運営に関わる操作ができる
# 「Contributor」ロール: 登録(/add)だけできる、有志に配りやすい弱い権限
ADMIN_ROLE_NAME = "Admin"
REGISTRAR_ROLE_NAME = "Contributor"

# /report の通知先チャンネルID(Railwayの環境変数 REPORT_CHANNEL_ID で設定)
REPORT_CHANNEL_ID = os.getenv("REPORT_CHANNEL_ID")


def _has_role(interaction: discord.Interaction, role_name: str) -> bool:
    return any(r.name == role_name for r in getattr(interaction.user, "roles", []))


def is_admin():
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False  # DMでは判定できないので不許可にする
        if interaction.user.guild_permissions.manage_guild:
            return True
        return _has_role(interaction, ADMIN_ROLE_NAME)
    return app_commands.check(predicate)


def can_register():
    """/add は「Admin」だけでなく「Contributor」ロールでも実行可能にする"""
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False  # DMでは判定できないので不許可にする
        if interaction.user.guild_permissions.manage_guild:
            return True
        return _has_role(interaction, ADMIN_ROLE_NAME) or _has_role(interaction, REGISTRAR_ROLE_NAME)
    return app_commands.check(predicate)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()

    @app_commands.command(name="add", description="過去問を登録します(添付ファイル必須)")
    @app_commands.describe(
        file="過去問の画像/PDFファイル",
        year="年度(例: 2026)",
        subject="科目名",
        exam_type="試験区分",
        department="学科",
        grade="学年(例: 2年)",
    )
    @app_commands.choices(
        exam_type=[app_commands.Choice(name=t, value=t) for t in EXAM_TYPES],
        department=[app_commands.Choice(name=d, value=d) for d in DEPARTMENTS],
    )
    @can_register()
    async def add(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        year: str,
        subject: str,
        exam_type: app_commands.Choice[str],
        department: app_commands.Choice[str] = None,
        grade: str = None,
    ):
        dup = await find_duplicate(
            year=year, subject=subject, exam_type=exam_type.value,
            department=department.value if department else None,
        )
        if dup:
            await interaction.response.send_message(
                f"⚠️ 既に登録されています: {year}年度 {subject} {exam_type.value}", ephemeral=True
            )
            return

        await add_exam(
            year=year,
            grade=grade,
            department=department.value if department else None,
            subject=subject,
            exam_type=exam_type.value,
            file_url=file.url,
            message_link=None,
            submitted_by=str(interaction.user),
        )
        await interaction.response.send_message(
            f"登録しました: {year}年度 {subject} {exam_type.value}"
        )

    @app_commands.command(name="remove", description="過去問を削除します(著作権上の削除依頼対応など)")
    @app_commands.describe(exam_id="削除する過去問のID(/search や /latest の結果に表示されるID)")
    @is_admin()
    async def remove(self, interaction: discord.Interaction, exam_id: int):
        ok = await soft_delete_exam(exam_id)
        if ok:
            await interaction.response.send_message(f"ID {exam_id} を削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message(f"ID {exam_id} は見つかりませんでした。", ephemeral=True)

    @app_commands.command(name="edit", description="登録済み過去問の情報を修正します")
    @app_commands.describe(
        exam_id="修正する過去問のID",
        subject="新しい科目名",
        year="新しい年度",
        exam_type="新しい試験区分",
        department="新しい学科",
    )
    @app_commands.choices(
        exam_type=[app_commands.Choice(name=t, value=t) for t in EXAM_TYPES],
        department=[app_commands.Choice(name=d, value=d) for d in DEPARTMENTS],
    )
    @is_admin()
    async def edit(
        self,
        interaction: discord.Interaction,
        exam_id: int,
        subject: str = None,
        year: str = None,
        exam_type: app_commands.Choice[str] = None,
        department: app_commands.Choice[str] = None,
    ):
        ok = await edit_exam(
            exam_id,
            subject=subject,
            year=year,
            exam_type=exam_type.value if exam_type else None,
            department=department.value if department else None,
        )
        if ok:
            await interaction.response.send_message(f"ID {exam_id} を更新しました。", ephemeral=True)
        else:
            await interaction.response.send_message("更新する項目がないか、IDが見つかりません。", ephemeral=True)

    @app_commands.command(name="report", description="著作権等の理由で過去問の削除を依頼します")
    @app_commands.describe(exam_id="削除依頼したい過去問のID", reason="削除理由")
    async def report(self, interaction: discord.Interaction, exam_id: int, reason: str):
        await interaction.response.send_message(
            "削除依頼を受け付けました。管理者が確認します。ご協力ありがとうございます。",
            ephemeral=True,
        )

        exam = await get_exam(exam_id)

        embed = discord.Embed(title="🚩 削除依頼が届きました", color=discord.Color.red())
        embed.add_field(name="対象ID", value=str(exam_id), inline=True)
        if exam:
            _, year, grade, department, subject, exam_type, file_url, submitted_by = exam
            embed.add_field(name="内容", value=f"{year}年度 {subject} {exam_type}", inline=True)
            embed.add_field(name="登録者", value=submitted_by or "不明", inline=True)
            embed.add_field(name="ファイル", value=f"[リンク]({file_url})", inline=False)
        else:
            embed.add_field(name="内容", value="⚠️ 該当IDが見つかりませんでした(既に削除済みの可能性)", inline=False)
        embed.add_field(name="理由", value=reason, inline=False)
        embed.add_field(name="依頼者", value=str(interaction.user), inline=False)
        embed.add_field(
            name="対応方法",
            value=f"問題があれば `/remove exam_id:{exam_id}` で削除してください。",
            inline=False,
        )

        if REPORT_CHANNEL_ID:
            channel = self.bot.get_channel(int(REPORT_CHANNEL_ID))
            if channel:
                await channel.send(embed=embed)
            else:
                print(f"[削除依頼] 通知先チャンネル(ID: {REPORT_CHANNEL_ID})が見つかりませんでした")
                print(f"[削除依頼] exam_id={exam_id} reason={reason} by={interaction.user}")
        else:
            print("[削除依頼] REPORT_CHANNEL_IDが未設定のためコンソールにのみ出力します")
            print(f"[削除依頼] exam_id={exam_id} reason={reason} by={interaction.user}")

async def setup(bot: commands.Bot):
    cog = Admin(bot)
    await bot.add_cog(cog)

    async def on_register_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            if interaction.guild is None:
                msg = "このコマンドはDMでは使えません。サーバー内のチャンネルで実行してください。"
            else:
                msg = f"このコマンドは「{ADMIN_ROLE_NAME}」または「{REGISTRAR_ROLE_NAME}」ロールを持つ人のみ使用できます。"
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            raise error

    async def on_admin_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            if interaction.guild is None:
                msg = "このコマンドはDMでは使えません。サーバー内のチャンネルで実行してください。"
            else:
                msg = f"このコマンドは「{ADMIN_ROLE_NAME}」ロールを持つ人のみ使用できます。"
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            raise error

    cog.add.error(on_register_error)
    cog.remove.error(on_admin_error)
    cog.edit.error(on_admin_error)