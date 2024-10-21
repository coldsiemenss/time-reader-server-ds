import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime
import asyncio  # Импортируем asyncio

# Устанавливаем интенты
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.messages = True

# Создаем объект бота
bot = commands.Bot(command_prefix="!", intents=intents)

# Подключаемся к базе данных SQLite
conn = sqlite3.connect('voice_times.db')
c = conn.cursor()

# Создаем таблицу для хранения времени
c.execute('''CREATE TABLE IF NOT EXISTS voice_times (
             user_id INTEGER PRIMARY KEY,
             total_time INTEGER)''')
conn.commit()

# Функция для сохранения времени в базу данных
def log_user_time(user_id, time_spent):
    c.execute('SELECT total_time FROM voice_times WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        total_time = result[0] + time_spent
        c.execute('UPDATE voice_times SET total_time = ? WHERE user_id = ?', (total_time, user_id))
    else:
        c.execute('INSERT INTO voice_times (user_id, total_time) VALUES (?, ?)', (user_id, time_spent))
    conn.commit()

user_voice_times = {}
user_tasks = {}

async def update_user_time(member_id):
    while True:
        await asyncio.sleep(5)  # Используем асинхронное ожидание
        if member_id in user_voice_times:
            print(f"Обновление времени для пользователя ID: {member_id}")

@bot.event
async def on_voice_state_update(member, before, after):
    # Пользователь заходит в голосовой канал
    if before.channel is None and after.channel is not None:
        user_voice_times[member.id] = datetime.now()
        print(f"{member.name} подключился к каналу {after.channel.name}")

        # Запускаем задачу обновления времени
        if member.id not in user_tasks:
            user_tasks[member.id] = bot.loop.create_task(update_user_time(member.id))

    # Пользователь выходит из голосового канала
    elif before.channel is not None and after.channel is None:
        join_time = user_voice_times.pop(member.id, None)
        if join_time:
            time_spent = (datetime.now() - join_time).total_seconds()
            log_user_time(member.id, int(time_spent))
            print(f"{member.name} провел в канале {before.channel.name} {time_spent // 60} минут.")

        # Останавливаем задачу
        if member.id in user_tasks:
            user_tasks[member.id].cancel()
            del user_tasks[member.id]

@bot.event
async def on_message(message):
    # Игнорируем сообщения от бота
    if message.author == bot.user:
        return

    # Проверяем, если сообщение пришло в личные сообщения
    if isinstance(message.channel, discord.DMChannel):
        await message.channel.send("Бро, ты чуть-чуть не туда пишешь, иди в текстовый канал сервера.")
    else:
        await bot.process_commands(message)  # Обрабатываем команды, если это текстовый канал

@bot.tree.command(name="time", description="Узнать, сколько времени вы провели в голосовых каналах или укажите пользователя.")
async def time_command(interaction: discord.Interaction, member: discord.Member = None):
    if isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message("Эта команда работает только в текстовых каналах на сервере.", ephemeral=True)
        return

    if member is None:
        member = interaction.user

    c.execute('SELECT total_time FROM voice_times WHERE user_id = ?', (member.id,))
    result = c.fetchone()
    total_time = result[0] if result else 0

    if member.id in user_voice_times:
        total_time += int((datetime.now() - user_voice_times[member.id]).total_seconds())

    total_time_in_minutes = total_time // 60
    total_time_in_seconds = total_time % 60

    # Создаем красивое сообщение с использованием Embed
    embed = discord.Embed(title="⏱️ Время в голосовых каналах", color=0x00ff00)
    embed.add_field(name="Пользователь:", value=member.mention, inline=True)
    embed.add_field(name="🕒 Всего времени:", value=f"{total_time_in_minutes} минут и {total_time_in_seconds} секунд", inline=True)
    embed.set_thumbnail(url=member.avatar.url)  # Добавляем аватар пользователя
    embed.set_footer(text=f"Запрос от: {interaction.user.name}", icon_url=interaction.user.avatar.url)  # Подпись с инициатором запроса

    await interaction.response.send_message(embed=embed)

async def check_current_voice_channels():
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            for member in channel.members:
                if member.id not in user_voice_times:
                    user_voice_times[member.id] = datetime.now()
                    print(f"{member.name} уже находился в {channel.name}, запись времени начата.")

                    # Запускаем задачу обновления времени
                    if member.id not in user_tasks:
                        user_tasks[member.id] = bot.loop.create_task(update_user_time(member.id))

@bot.event
async def on_ready():
    await bot.tree.sync()
    await check_current_voice_channels()
    print(f'Бот запущен как {bot.user}')
# Запуск бота
bot.run('your token')
