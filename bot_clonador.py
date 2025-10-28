import discord
from discord.ext import commands
import json
import asyncio
import os
from datetime import datetime
import logging
from flask import Flask
from threading import Thread

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Servidor web para manter o bot vivo
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Clonador está rodando!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Iniciar Flask em thread separada
Thread(target=run_flask).start()

# Configurações do bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Arquivo para salvar templates (usando variável de ambiente para path)
TEMPLATES_FILE = os.path.join('/tmp', 'server_templates.json')

def load_templates():
    """Carrega os templates salvos"""
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar templates: {e}")
    return {}

def save_templates(templates):
    """Salva os templates no arquivo"""
    try:
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar templates: {e}")
        return False

@bot.event
async def on_ready():
    logger.info(f'✅ Bot Clonador conectado como {bot.user.name}')
    logger.info(f'📊 Conectado em {len(bot.guilds)} servidores')
    
    # Status personalizado
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="!ajuda para clonar servidores"
    )
    await bot.change_presence(activity=activity)

@bot.command()
@commands.has_permissions(administrator=True)
async def clonar_server(ctx, server_id: int = None):
    """Clona a estrutura de outro servidor"""
    
    if server_id is None:
        embed = discord.Embed(
            title="❌ Erro",
            description="Use: `!clonar_server ID_DO_SERVER`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        # Verificar se é servidor atual
        if server_id == ctx.guild.id:
            await ctx.send("❌ Use `!clonar_atual nome_template` para clonar este servidor")
            return

        # Encontrar o servidor alvo
        target_guild = bot.get_guild(server_id)
        if not target_guild:
            await ctx.send("❌ Servidor não encontrado. O bot precisa estar no servidor alvo.")
            return

        # Verificar se está no servidor alvo
        if target_guild.get_member(bot.user.id) is None:
            await ctx.send("❌ O bot não está no servidor alvo. Adicione-o primeiro.")
            return

        await ctx.send(f"🔄 Clonando **{target_guild.name}**... Isso pode levar alguns minutos.")

        # Coletar dados do servidor
        template_data = await coletar_dados_servidor(target_guild)
        
        if not template_data:
            await ctx.send("❌ Erro ao coletar dados do servidor.")
            return

        # Salvar template
        template_name = f"clone_{target_guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        templates = load_templates()
        templates[template_name] = template_data
        
        if save_templates(templates):
            embed = discord.Embed(
                title="✅ Clone Concluído",
                description=f"Estrutura salva como `{template_name}`",
                color=0x00ff00
            )
            embed.add_field(
                name="📊 Estatísticas", 
                value=f"**Cargos:** {len(template_data['roles'])}\n**Categorias:** {len(template_data['categories'])}\n**Canais:** {sum(len(cat['channels']) for cat in template_data['categories'])}",
                inline=True
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Erro ao salvar template.")

    except Exception as e:
        logger.error(f"Erro em clonar_server: {e}")
        await ctx.send(f"❌ Erro: {str(e)}")

async def coletar_dados_servidor(guild):
    """Coleta dados estruturais do servidor"""
    try:
        template_data = {
            'name': guild.name,
            'icon_url': str(guild.icon.url) if guild.icon else None,
            'cloned_at': datetime.now().isoformat(),
            'roles': [],
            'categories': [],
            'channels': []
        }

        # Coletar cargos
        for role in guild.roles:
            if role.name != "@everyone" and not role.managed:
                role_data = {
                    'name': role.name,
                    'color': role.color.value,
                    'hoist': role.hoist,
                    'mentionable': role.mentionable,
                    'permissions': role.permissions.value,
                    'position': role.position
                }
                template_data['roles'].append(role_data)

        # Coletar categorias e canais
        for category in guild.categories:
            category_data = {
                'name': category.name,
                'position': category.position,
                'channels': []
            }

            for channel in category.channels:
                channel_data = {
                    'name': channel.name,
                    'type': str(channel.type),
                    'position': channel.position,
                    'nsfw': getattr(channel, 'nsfw', False)
                }

                if isinstance(channel, discord.TextChannel):
                    channel_data['slowmode_delay'] = channel.slowmode_delay
                    channel_data['topic'] = getattr(channel, 'topic', '')
                elif isinstance(channel, discord.VoiceChannel):
                    channel_data['bitrate'] = channel.bitrate
                    channel_data['user_limit'] = channel.user_limit

                # Permissões simplificadas
                channel_data['overwrites'] = []
                for target, overwrite in channel.overwrites.items():
                    if isinstance(target, discord.Role) and target.name != "@everyone":
                        overwrite_data = {
                            'role_name': target.name,
                            'allow': overwrite.pair()[0].value,
                            'deny': overwrite.pair()[1].value
                        }
                        channel_data['overwrites'].append(overwrite_data)

                category_data['channels'].append(channel_data)

            template_data['categories'].append(category_data)

        return template_data

    except Exception as e:
        logger.error(f"Erro ao coletar dados: {e}")
        return None

@bot.command()
@commands.has_permissions(administrator=True)
async def clonar_atual(ctx, nome_template: str = None):
    """Clona o servidor atual"""
    
    if not nome_template:
        await ctx.send("❌ Use: `!clonar_atual nome_do_template`")
        return
    
    try:
        await ctx.send(f"🔄 Clonando **{ctx.guild.name}**...")
        
        template_data = await coletar_dados_servidor(ctx.guild)
        if not template_data:
            await ctx.send("❌ Erro ao coletar dados.")
            return

        templates = load_templates()
        templates[nome_template] = template_data
        
        if save_templates(templates):
            await ctx.send(f"✅ Servidor clonado como `{nome_template}`")
        else:
            await ctx.send("❌ Erro ao salvar template.")

    except Exception as e:
        await ctx.send(f"❌ Erro: {str(e)}")

@bot.command()
async def listar_templates(ctx):
    """Lista todos os templates salvos"""
    
    templates = load_templates()
    
    if not templates:
        await ctx.send("📭 Nenhum template salvo.")
        return

    embed = discord.Embed(title="📁 Templates Salvos", color=0x9b59b6)
    
    for name, template in list(templates.items())[:8]:  # Limitar para não exceder limite
        total_channels = sum(len(cat['channels']) for cat in template['categories'])
        
        embed.add_field(
            name=f"📋 {name[:20]}...",
            value=f"**Servidor:** {template['name']}\n**Cargos:** {len(template['roles'])} | **Canais:** {total_channels}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def aplicar_template(ctx, template_name: str = None):
    """Aplica um template salvo"""
    
    if not template_name:
        await ctx.send("❌ Use: `!aplicar_template nome_do_template`")
        return

    templates = load_templates()
    if template_name not in templates:
        await ctx.send("❌ Template não encontrado.")
        return

    # Confirmação rápida (sem reactions por simplicidade)
    embed = discord.Embed(
        title="⚠️ Confirmar",
        description=f"Aplicar template **{template_name}**?\nDigite `sim` para confirmar.",
        color=0xff9900
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'sim'

    try:
        await bot.wait_for('message', timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("❌ Tempo esgotado.")
        return

    await ctx.send("🔄 Aplicando template...")

    try:
        template = templates[template_name]
        created = await aplicar_estrutura(ctx.guild, template)
        
        embed = discord.Embed(
            title="✅ Template Aplicado",
            color=0x00ff00
        )
        embed.add_field(name="📊 Criados", 
                      value=f"**Cargos:** {created['roles']}\n**Categorias:** {created['categories']}\n**Canais:** {created['channels']}")
        
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro: {str(e)}")

async def aplicar_estrutura(guild, template):
    """Aplica a estrutura do template"""
    created = {'roles': 0, 'categories': 0, 'channels': 0}
    
    # Criar cargos
    for role_data in template['roles'][:20]:  # Limitar cargos
        try:
            await guild.create_role(
                name=role_data['name'],
                color=discord.Color(role_data['color']),
                hoist=role_data['hoist'],
                mentionable=role_data['mentionable'],
                permissions=discord.Permissions(role_data['permissions'])
            )
            created['roles'] += 1
            await asyncio.sleep(0.5)
        except:
            pass

    # Criar categorias e canais
    for category_data in template['categories'][:10]:  # Limitar categorias
        try:
            category = await guild.create_category_channel(
                name=category_data['name']
            )
            created['categories'] += 1

            for channel_data in category_data['channels'][:5]:  # Limitar canais
                try:
                    if channel_data['type'] == 'text':
                        await category.create_text_channel(
                            name=channel_data['name'],
                            nsfw=channel_data.get('nsfw', False)
                        )
                    elif channel_data['type'] == 'voice':
                        await category.create_voice_channel(
                            name=channel_data['name'],
                            bitrate=min(channel_data.get('bitrate', 64000), guild.bitrate_limit)
                        )
                    created['channels'] += 1
                    await asyncio.sleep(0.5)
                except:
                    pass
                    
            await asyncio.sleep(0.5)
        except:
            pass

    return created

@bot.command()
async def servidores_bot(ctx):
    """Lista servidores onde o bot está"""
    
    embed = discord.Embed(title="🏠 Servidores do Bot", color=0xe74c3c)
    
    for guild in list(bot.guilds)[:10]:
        embed.add_field(
            name=f"🛡️ {guild.name}",
            value=f"ID: `{guild.id}`",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def ajuda(ctx):
    """Mostra ajuda do bot"""
    
    embed = discord.Embed(
        title="🤖 Bot Clonador - Comandos",
        color=0x3498db
    )
    
    embed.add_field(
        name="📥 Clonagem",
        value="`!clonar_server ID`\n`!clonar_atual NOME`\n`!servidores_bot`",
        inline=True
    )
    
    embed.add_field(
        name="📤 Templates", 
        value="`!listar_templates`\n`!aplicar_template NOME`",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Tratamento simplificado de erros"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Precisa de permissão de Administrador")
    else:
        await ctx.send("❌ Erro no comando. Use `!ajuda`")

# Iniciar bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("❌ Token não encontrado!")
    else:
        logger.info("🚀 Iniciando bot no Render...")
        bot.run(token)
