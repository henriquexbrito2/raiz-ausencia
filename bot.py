import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- SISTEMA WEB PARA MANTER O BOT ATIVO NO RAILWAY ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Online"

def run():
    # O Railway define a porta automaticamente através da variável PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -------------------------------------------------------------

load_dotenv()
TOKEN = os.getenv("TOKEN")
ID_CANAL_ADM = os.getenv("ID_CANAL_ADM")

class AbsenceBot(commands.Bot):
    def __init__(self):
        # Utiliza todas as intents necessárias para gerenciamento de membros e mensagens
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        
    async def setup_hook(self):
        # Mantém o botão persistente ativo mesmo se o bot reiniciar
        self.add_view(InitialView())

bot = AbsenceBot()

# --- 3. BOTÕES DE APROVAÇÃO (CHAT DA ADMINISTRAÇÃO) ---
class AdminApprovalView(discord.ui.View):
    def __init__(self, user_id: int, reason: str, duration: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.reason = reason
        self.duration = duration

    async def notify_user(self, status: str, color: discord.Color):
        try:
            user = await bot.fetch_user(self.user_id)
            embed = discord.Embed(title=f"Sua ausência foi {status}!", color=color)
            embed.add_field(name="Período", value=self.duration, inline=False)
            embed.add_field(name="Motivo", value=self.reason, inline=False)
            await user.send(embed=embed)
        except Exception:
            pass # Ignora se a DM do moderador estiver fechada

    @discord.ui.button(label="Aprovar ✅", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.notify_user("APROVADA", discord.Color.green())
        
        for item in self.children: 
            item.disabled = True
        await interaction.message.edit(content="🟢 **Ausência Aprovada!** Mod avisado na DM.", view=self)

    @discord.ui.button(label="Recusar ❌", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.notify_user("RECUSADA", discord.Color.red())
        
        for item in self.children: 
            item.disabled = True
        await interaction.message.edit(content="🔴 **Ausência Recusada!** Mod avisado na DM.", view=self)

# --- 2. FORMULÁRIO (MODAL FLUTUANTE) ---
class AbsenceModal(discord.ui.Modal, title="Formulário de Ausência"):
    duration = discord.ui.TextInput(label="Período da Ausência", placeholder="Ex: 10/07 a 15/07", style=discord.TextStyle.short)
    reason = discord.ui.TextInput(label="Motivo real", placeholder="Explique detalhadamente aqui...", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Seu pedido foi enviado para análise da administração!", ephemeral=True)
        
        if ID_CANAL_ADM:
            adm_channel = bot.get_channel(int(ID_CANAL_ADM))
            if adm_channel:
                embed = discord.Embed(title="🚨 Novo Pedido de Ausência", color=discord.Color.orange())
                embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
                embed.add_field(name="Período", value=self.duration.value, inline=True)
                embed.add_field(name="Motivo", value=self.reason.value, inline=False)
                
                view = AdminApprovalView(user_id=interaction.user.id, reason=self.reason.value, duration=self.duration.value)
                await adm_channel.send(embed=embed, view=view)

# --- 1. BOTÃO INICIAL (CHAT PÚBLICO DA STAFF) ---
class InitialView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Solicitar Ausência 📅", style=discord.ButtonStyle.primary, custom_id="btn_request_absence")
    async def request_absence(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AbsenceModal())

# --- FUNÇÃO AUXILIAR PARA GERAR O EMBED DO PAINEL ---
def gerar_embed_painel():
    return discord.Embed(
        title="Formulário de Ausência da Staff",
        description="Se você precisa se ausentar das suas funções, clique no botão abaixo para justificar.",
        color=discord.Color.blue()
    )

# --- COMANDO TRADICIONAL TEXTUAL (!criar_painel) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def criar_painel(ctx):
    await ctx.send(embed=gerar_embed_painel(), view=InitialView())

# --- COMANDO DE BARRA SLASH (/criar_painel) ---
@bot.tree.command(name="criar_painel", description="Envia o painel com o botão de formulário de ausência no canal.")
@app_commands.checks.has_permissions(administrator=True)
async def criar_painel_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Painel criado com sucesso!", ephemeral=True)
    await interaction.channel.send(embed=gerar_embed_painel(), view=InitialView())

@bot.event
async def on_ready():
    print(f"Bot logado com sucesso como {bot.user}")
    try:
        # Sincroniza os comandos Slash globalmente com o Discord
        sincronizados = await bot.tree.sync()
        print(f"Sincronizados {len(sincronizados)} comandos slash com sucesso.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos slash: {e}")

# Inicia a API web do Railway e executa o bot do Discord
keep_alive()
bot.run(TOKEN)
