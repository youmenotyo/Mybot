import os
import math
import random

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ------------------ إعدادات اللعبة ------------------
G = 9.8  # الجاذبية m/s^2

POWER_MIN, POWER_MAX, POWER_STEP = 20, 80, 5
ANGLE_MIN, ANGLE_MAX, ANGLE_STEP = 5, 85, 5

TARGET_MIN_DIST, TARGET_MAX_DIST = 50, 400
CHALLENGE_MIN_DIST, CHALLENGE_MAX_DIST = 100, 300

HEIGHT_MIN, HEIGHT_MAX = 0, 40         # ارتفاعك عن سطح الهدف بالمتر
WIND_MIN, WIND_MAX = -15, 15           # سرعة الرياح بالمتر/ثانية (سالب = معاكسة، موجب = مع اتجاه السهم)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def calc_distance(power: float, angle_deg: float, height: float = 0, wind: float = 0) -> float:
    """يحسب مدى إطلاق السهم بالأمتار مع مراعاة الارتفاع الابتدائي وسرعة الرياح."""
    angle_rad = math.radians(angle_deg)
    vx = power * math.cos(angle_rad)
    vy = power * math.sin(angle_rad)

    # وقت الطيران حتى يصل السهم لمستوى الهدف (h + vy*t - 0.5*g*t^2 = 0)
    discriminant = vy ** 2 + 2 * G * height
    t = (vy + math.sqrt(discriminant)) / G

    # الرياح تدفع/تعيق السهم أفقيًا طوال مدة الطيران
    distance = vx * t + wind * t
    return round(max(distance, 0.0), 1)


def practice_feedback(diff: float) -> str:
    if diff <= 5:
        return "🎯 إصابة شبه مثالية! رامي محترف!"
    elif diff <= 15:
        return "👍 قريب جدًا من الهدف!"
    elif diff <= 30:
        return "😐 لا بأس، بس تقدر أحسن من كذا."
    else:
        return "❌ بعيد عن الهدف، حاول مرة ثانية!"


# ------------------ الواجهة التفاعلية (الأزرار) ------------------
class ArcheryView(discord.ui.View):
    def __init__(self, author_id: int, mode: str, target: float | None = None):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.mode = mode  # "practice" أو "challenge"
        self.target = target
        self.power = 50
        self.angle = 45
        self.height = random.choice(range(HEIGHT_MIN, HEIGHT_MAX + 1, 5))
        self.wind = random.choice(range(WIND_MIN, WIND_MAX + 1, 1))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "هذي مو رميتك! ابدأ لعبة جديدة لنفسك 🏹", ephemeral=True
            )
            return False
        return True

    def build_embed(self) -> discord.Embed:
        if self.mode == "practice":
            title = "🎯 وضع التدريب"
            desc = f"الهدف على بعد **{self.target} متر**\nعدّل القوة والزاوية ثم اضغط إطلاق!"
        else:
            title = "🏹 وضع تجاوز المسافة"
            desc = (
                f"لازم يوصل السهم لأبعد من **{self.target} متر** (ولو بمتر وحد)\n"
                f"عدّل القوة والزاوية ثم اضغط إطلاق!"
            )

        embed = discord.Embed(title=title, description=desc, color=discord.Color.gold())
        embed.add_field(name="💪 القوة", value=f"{self.power}", inline=True)
        embed.add_field(name="📐 الزاوية", value=f"{self.angle}°", inline=True)
        embed.add_field(name="🏔️ ارتفاعك", value=f"{self.height} متر", inline=True)

        if self.wind > 0:
            wind_text = f"+{self.wind} م/ث (مع اتجاه السهم 💨➡️)"
        elif self.wind < 0:
            wind_text = f"{self.wind} م/ث (معاكسة للسهم 💨⬅️)"
        else:
            wind_text = "0 م/ث (هدوء تام 🍃)"
        embed.add_field(name="🌬️ الرياح", value=wind_text, inline=True)

        embed.set_footer(text="⚠️ الارتفاع والرياح يتغيرون كل جولة، لا تعتمد على نفس القوة والزاوية دايمًا!")
        return embed

    async def refresh(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    # ---------- أزرار القوة ----------
    @discord.ui.button(label="➖ قوة", style=discord.ButtonStyle.secondary, row=0)
    async def power_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.power = max(POWER_MIN, self.power - POWER_STEP)
        await self.refresh(interaction)

    @discord.ui.button(label="➕ قوة", style=discord.ButtonStyle.secondary, row=0)
    async def power_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.power = min(POWER_MAX, self.power + POWER_STEP)
        await self.refresh(interaction)

    # ---------- أزرار الزاوية ----------
    @discord.ui.button(label="➖ زاوية", style=discord.ButtonStyle.secondary, row=1)
    async def angle_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.angle = max(ANGLE_MIN, self.angle - ANGLE_STEP)
        await self.refresh(interaction)

    @discord.ui.button(label="➕ زاوية", style=discord.ButtonStyle.secondary, row=1)
    async def angle_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.angle = min(ANGLE_MAX, self.angle + ANGLE_STEP)
        await self.refresh(interaction)

    # ---------- زر الإطلاق ----------
    @discord.ui.button(label="🏹 إطلاق السهم", style=discord.ButtonStyle.success, row=2)
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):
        distance = calc_distance(self.power, self.angle, height=self.height, wind=self.wind)

        for child in self.children:
            child.disabled = True

        conditions_text = f"(الارتفاع: {self.height}م، الرياح: {self.wind:+d} م/ث)"

        if self.mode == "practice":
            diff = round(abs(distance - self.target), 1)
            result_text = (
                f"السهم طار **{distance} متر** {conditions_text}\n"
                f"الهدف كان على **{self.target} متر**\n"
                f"الفرق: **{diff} متر**\n\n"
                f"{practice_feedback(diff)}"
            )
            color = discord.Color.green() if diff <= 15 else discord.Color.red()
        else:
            won = distance > self.target
            result_text = (
                f"السهم طار **{distance} متر** {conditions_text}\n"
                f"الحد المطلوب تجاوزه: **{self.target} متر**\n\n"
                + (
                    "✅ فزت! تجاوزت المسافة المطلوبة!"
                    if won
                    else "❌ خسرت! السهم ما وصل للمسافة المطلوبة."
                )
            )
            color = discord.Color.green() if won else discord.Color.red()

        embed = discord.Embed(title="نتيجة الرمية", description=result_text, color=color)
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


# ------------------ أوامر السلاش ------------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"تم تسجيل {len(synced)} أمر. البوت شغال باسم {bot.user}")
    except Exception as e:
        print(f"خطأ أثناء المزامنة: {e}")


@bot.tree.command(name="رماية_تدريب", description="ابدأ لعبة رمي سهم على هدف بمسافة عشوائية")
async def practice_game(interaction: discord.Interaction):
    target = random.choice(range(TARGET_MIN_DIST, TARGET_MAX_DIST + 1, 5))
    view = ArcheryView(author_id=interaction.user.id, mode="practice", target=target)
    await interaction.response.send_message(embed=view.build_embed(), view=view)


@bot.tree.command(name="رماية_تحدي", description="حاول تطلق السهم لمسافة أبعد من الحد المطلوب")
@app_commands.describe(المسافة="الحد الأدنى المطلوب تجاوزه بالمتر (اختياري)")
async def challenge_game(interaction: discord.Interaction, المسافة: int | None = None):
    min_distance = المسافة if المسافة else random.choice(
        range(CHALLENGE_MIN_DIST, CHALLENGE_MAX_DIST + 1, 5)
    )
    view = ArcheryView(author_id=interaction.user.id, mode="challenge", target=min_distance)
    await interaction.response.send_message(embed=view.build_embed(), view=view)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ ما لقيت DISCORD_TOKEN، حط التوكن في ملف .env")
    bot.run(TOKEN)
