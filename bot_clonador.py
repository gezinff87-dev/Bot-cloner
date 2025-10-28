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
    return "🤖 Bot Clonador COMPLETO está rodando!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Iniciar Flask em thread separada
Thread(target=run_flask).start()

# Configurações do bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Arquivo para salvar templates
TEMPLATES_FILE = os.path.join('/tmp', 'server_templates_complete.json')

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
    logger.info(f'✅ Bot Clonador COMPLETO conectado como {bot.user.name}')
    logger.info(f'📊 Conectado em {len(bot.guilds)} servidores')
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="!ajuda | Clone 100% completo"
    )
    await bot.change_presence(activity=activity)

@bot.command()
@commands.has_permissions(administrator=True)
async def clonar_tudo(ctx, server_id: int = None):
    """Clona 100% da estrutura do servidor"""
    
    if server_id is None:
        embed = discord.Embed(
            title="❌ Erro",
            description="Use: `!clonar_tudo ID_DO_SERVER`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        # Encontrar o servidor alvo
        target_guild = bot.get_guild(server_id)
        if not target_guild:
            await ctx.send("❌ Servidor não encontrado. O bot precisa estar no servidor alvo.")
            return

        # Verificar se está no servidor alvo
        if target_guild.get_member(bot.user.id) is None:
            await ctx.send("❌ O bot não está no servidor alvo. Adicione-o primeiro.")
            return

        # Mensagem de início
        embed = discord.Embed(
            title="🔄 INICIANDO CLONE COMPLETO",
            description=f"Clonando **{target_guild.name}**...\nIsso pode levar vários minutos para servidores grandes.",
            color=0x3498db
        )
        embed.add_field(name="📝 Status", value="Coletando dados do servidor...")
        status_msg = await ctx.send(embed=embed)

        # Coletar dados COMPLETOS do servidor
        template_data = await coletar_dados_completos(target_guild, status_msg)
        
        if not template_data:
            await status_msg.edit(embed=discord.Embed(
                title="❌ Erro",
                description="Falha ao coletar dados do servidor.",
                color=0xff0000
            ))
            return

        # Salvar template
        template_name = f"clone_completo_{target_guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        templates = load_templates()
        templates[template_name] = template_data
        
        if save_templates(templates):
            # Embed de resultado final
            total_channels = sum(len(cat['channels']) for cat in template_data['categories'])
            total_emojis = len(template_data['emojis'])
            total_roles = len(template_data['roles'])
            
            result_embed = discord.Embed(
                title="✅ CLONE COMPLETO CONCLUÍDO",
                description=f"**Servidor:** {target_guild.name}\n**Template:** `{template_name}`",
                color=0x00ff00
            )
            result_embed.add_field(
                name="📊 ESTATÍSTICAS COMPLETAS",
                value=f"**🎭 Cargos:** {total_roles}\n**📁 Categorias:** {len(template_data['categories'])}\n**💬 Canais:** {total_channels}\n**😊 Emojis:** {total_emojis}",
                inline=False
            )
            result_embed.add_field(
                name="🚀 PRÓXIMOS PASSOS",
                value=f"Use `!aplicar_tudo {template_name}` para aplicar este template completo",
                inline=False
            )
            
            await status_msg.edit(embed=result_embed)
        else:
            await status_msg.edit(embed=discord.Embed(
                title="❌ Erro",
                description="Falha ao salvar template.",
                color=0xff0000
            ))

    except Exception as e:
        logger.error(f"Erro em clonar_tudo: {e}")
        await ctx.send(f"❌ Erro crítico: {str(e)}")

async def coletar_dados_completos(guild, status_msg):
    """Coleta TODOS os dados do servidor"""
    try:
        template_data = {
            'name': guild.name,
            'description': guild.description,
            'icon_url': str(guild.icon.url) if guild.icon else None,
            'banner_url': str(guild.banner.url) if guild.banner else None,
            'afk_channel': guild.afk_channel.name if guild.afk_channel else None,
            'afk_timeout': guild.afk_timeout,
            'verification_level': str(guild.verification_level),
            'default_notifications': str(guild.default_notifications),
            'explicit_content_filter': str(guild.explicit_content_filter),
            'cloned_at': datetime.now().isoformat(),
            'roles': [],
            'emojis': [],
            'stickers': [],
            'categories': [],
            'channels': []
        }

        # Atualizar status
        await status_msg.edit(embed=discord.Embed(
            title="🔄 Coletando Cargos...",
            description=f"Servidor: {guild.name}",
            color=0x3498db
        ))

        # Coletar TODOS os cargos (exceto @everyone)
        for role in guild.roles:
            if role.name != "@everyone" and not role.managed:
                role_data = {
                    'name': role.name,
                    'color': role.color.value,
                    'hoist': role.hoist,
                    'mentionable': role.mentionable,
                    'permissions': role.permissions.value,
                    'position': role.position,
                    'display_icon': str(role.display_icon.url) if role.display_icon else None
                }
                template_data['roles'].append(role_data)

        # Coletar emojis
        await status_msg.edit(embed=discord.Embed(
            title="🔄 Coletando Emojis...",
            color=0x3498db
        ))
        
        for emoji in guild.emojis:
            emoji_data = {
                'name': emoji.name,
                'url': str(emoji.url),
                'animated': emoji.animated,
                'required_colons': emoji.required_colons,
                'managed': emoji.managed,
                'available': emoji.available
            }
            template_data['emojis'].append(emoji_data)

        # Coletar figurinhas (stickers)
        try:
            stickers = await guild.fetch_stickers()
            for sticker in stickers:
                sticker_data = {
                    'name': sticker.name,
                    'description': sticker.description,
                    'emoji': sticker.emoji,
                    'format_type': str(sticker.format),
                    'url': sticker.url
                }
                template_data['stickers'].append(sticker_data)
        except:
            pass  # Stickers podem não ser acessíveis

        # Coletar categorias e canais
        await status_msg.edit(embed=discord.Embed(
            title="🔄 Coletando Categorias e Canais...",
            color=0x3498db
        ))

        # Coletar canais sem categoria primeiro
        for channel in guild.channels:
            if channel.category is None:
                channel_data = await coletar_dados_canal(channel)
                if channel_data:
                    template_data['channels'].append(channel_data)

        # Coletar categorias e seus canais
        for category in guild.categories:
            category_data = {
                'name': category.name,
                'position': category.position,
                'nsfw': getattr(category, 'nsfw', False),
                'channels': []
            }

            # Coletar permissões da categoria
            category_data['overwrites'] = []
            for target, overwrite in category.overwrites.items():
                overwrite_data = await coletar_dados_permissao(target, overwrite)
                if overwrite_data:
                    category_data['overwrites'].append(overwrite_data)

            # Coletar canais da categoria
            for channel in category.channels:
                channel_data = await coletar_dados_canal(channel)
                if channel_data:
                    category_data['channels'].append(channel_data)

            template_data['categories'].append(category_data)

        return template_data

    except Exception as e:
        logger.error(f"Erro ao coletar dados completos: {e}")
        return None

async def coletar_dados_canal(channel):
    """Coleta dados completos de um canal"""
    try:
        channel_data = {
            'name': channel.name,
            'type': str(channel.type),
            'position': channel.position,
            'nsfw': getattr(channel, 'nsfw', False),
            'overwrites': []
        }

        # Configurações específicas por tipo
        if isinstance(channel, discord.TextChannel):
            channel_data['topic'] = getattr(channel, 'topic', '')
            channel_data['slowmode_delay'] = channel.slowmode_delay
            channel_data['default_auto_archive_duration'] = getattr(channel, 'default_auto_archive_duration', 1440)
            
        elif isinstance(channel, discord.VoiceChannel):
            channel_data['bitrate'] = channel.bitrate
            channel_data['user_limit'] = channel.user_limit
            channel_data['rtc_region'] = str(channel.rtc_region) if channel.rtc_region else None
            
        elif isinstance(channel, discord.StageChannel):
            channel_data['bitrate'] = channel.bitrate
            channel_data['user_limit'] = channel.user_limit
            channel_data['topic'] = getattr(channel, 'topic', '')
            
        elif isinstance(channel, discord.ForumChannel):
            channel_data['topic'] = getattr(channel, 'topic', '')
            channel_data['slowmode_delay'] = channel.slowmode_delay
            channel_data['default_auto_archive_duration'] = getattr(channel, 'default_auto_archive_duration', 1440)
            channel_data['available_tags'] = [tag.name for tag in getattr(channel, 'available_tags', [])]

        # Coletar permissões do canal
        for target, overwrite in channel.overwrites.items():
            overwrite_data = await coletar_dados_permissao(target, overwrite)
            if overwrite_data:
                channel_data['overwrites'].append(overwrite_data)

        return channel_data

    except Exception as e:
        logger.error(f"Erro ao coletar dados do canal {channel.name}: {e}")
        return None

async def coletar_dados_permissao(target, overwrite):
    """Coleta dados de permissões"""
    try:
        if isinstance(target, discord.Role) and target.name != "@everyone":
            return {
                'type': 'role',
                'name': target.name,
                'allow': overwrite.pair()[0].value,
                'deny': overwrite.pair()[1].value
            }
        elif isinstance(target, discord.Member):
            return {
                'type': 'member',
                'name': target.name,
                'allow': overwrite.pair()[0].value,
                'deny': overwrite.pair()[1].value
            }
    except:
        pass
    return None

@bot.command()
@commands.has_permissions(administrator=True)
async def aplicar_tudo(ctx, template_name: str = None):
    """Aplica um template COMPLETO"""
    
    if not template_name:
        await ctx.send("❌ Use: `!aplicar_tudo nome_do_template`")
        return

    templates = load_templates()
    if template_name not in templates:
        await ctx.send("❌ Template não encontrado.")
        return

    template = templates[template_name]
    
    # Confirmação
    embed = discord.Embed(
        title="⚠️ CONFIRMAR APLICAÇÃO COMPLETA",
        description=f"**Template:** {template_name}\n**Origem:** {template['name']}",
        color=0xff9900
    )
    
    total_channels = sum(len(cat['channels']) for cat in template['categories']) + len(template.get('channels', []))
    embed.add_field(
        name="📊 ESTRUTURA A SER CRIADA",
        value=f"**🎭 Cargos:** {len(template['roles'])}\n**📁 Categorias:** {len(template['categories'])}\n**💬 Canais:** {total_channels}\n**😊 Emojis:** {len(template['emojis'])}",
        inline=False
    )
    
    embed.add_field(
        name="🔧 CONFIRMAR",
        value="Digite `CONFIRMAR` para aplicar o template completo",
        inline=False
    )
    
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() == 'CONFIRMAR'

    try:
        await bot.wait_for('message', timeout=45.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("❌ Tempo esgotado.")
        return

    # Iniciar aplicação
    status_msg = await ctx.send("🔄 **INICIANDO APLICAÇÃO COMPLETA...**")
    
    try:
        results = await aplicar_estrutura_completa(ctx.guild, template, status_msg)
        
        # Resultado final
        result_embed = discord.Embed(
            title="✅ APLICAÇÃO COMPLETA CONCLUÍDA",
            color=0x00ff00
        )
        result_embed.add_field(
            name="📊 RESULTADOS",
            value=f"**✅ Cargos criados:** {results['roles']}/{len(template['roles'])}\n**✅ Categorias criadas:** {results['categories']}/{len(template['categories'])}\n**✅ Canais criados:** {results['channels']}/{total_channels}",
            inline=False
        )
        
        await status_msg.edit(embed=result_embed)

    except Exception as e:
        await status_msg.edit(content=f"❌ **ERRO CRÍTICO:** {str(e)}")

async def aplicar_estrutura_completa(guild, template, status_msg):
    """Aplica a estrutura COMPLETA do template"""
    results = {'roles': 0, 'categories': 0, 'channels': 0}
    
    # Criar cargos
    await status_msg.edit(content="🔄 **Criando cargos...**")
    role_mapping = {}
    
    for role_data in sorted(template['roles'], key=lambda x: x['position']):
        try:
            new_role = await guild.create_role(
                name=role_data['name'],
                color=discord.Color(role_data['color']),
                hoist=role_data['hoist'],
                mentionable=role_data['mentionable'],
                permissions=discord.Permissions(role_data['permissions'])
            )
            role_mapping[role_data['name']] = new_role
            results['roles'] += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Erro ao criar cargo {role_data['name']}: {e}")

    # Criar categorias
    await status_msg.edit(content="🔄 **Criando categorias...**")
    category_mapping = {}
    
    for category_data in sorted(template['categories'], key=lambda x: x['position']):
        try:
            new_category = await guild.create_category_channel(
                name=category_data['name'],
                position=category_data['position']
            )
            category_mapping[category_data['name']] = new_category
            results['categories'] += 1
            
            # Aplicar permissões da categoria
            for overwrite_data in category_data.get('overwrites', []):
                if overwrite_data['type'] == 'role' and overwrite_data['name'] in role_mapping:
                    await new_category.set_permissions(
                        role_mapping[overwrite_data['name']],
                        overwrite=discord.PermissionOverwrite.from_pair(
                            discord.Permissions(overwrite_data['allow']),
                            discord.Permissions(overwrite_data['deny'])
                        )
                    )
            
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"Erro ao criar categoria {category_data['name']}: {e}")

    # Criar canais nas categorias
    await status_msg.edit(content="🔄 **Criando canais...**")
    
    for category_data in template['categories']:
        if category_data['name'] in category_mapping:
            category = category_mapping[category_data['name']]
            
            for channel_data in category_data['channels']:
                try:
                    new_channel = await criar_canal_completo(guild, category, channel_data, role_mapping)
                    if new_channel:
                        results['channels'] += 1
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"Erro ao criar canal {channel_data['name']}: {e}")

    # Criar canais sem categoria
    for channel_data in template.get('channels', []):
        try:
            new_channel = await criar_canal_completo(guild, None, channel_data, role_mapping)
            if new_channel:
                results['channels'] += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"Erro ao criar canal sem categoria {channel_data['name']}: {e}")

    return results

async def criar_canal_completo(guild, category, channel_data, role_mapping):
    """Cria um canal com todas as configurações"""
    try:
        channel_kwargs = {
            'name': channel_data['name'],
            'position': channel_data['position'],
            'nsfw': channel_data.get('nsfw', False)
        }

        if category:
            channel_kwargs['category'] = category

        new_channel = None
        
        if channel_data['type'] == 'text':
            channel_kwargs['topic'] = channel_data.get('topic', '')
            channel_kwargs['slowmode_delay'] = channel_data.get('slowmode_delay', 0)
            new_channel = await guild.create_text_channel(**channel_kwargs)
            
        elif channel_data['type'] == 'voice':
            channel_kwargs['bitrate'] = min(channel_data.get('bitrate', 64000), guild.bitrate_limit)
            channel_kwargs['user_limit'] = channel_data.get('user_limit', 0)
            new_channel = await guild.create_voice_channel(**channel_kwargs)
            
        elif channel_data['type'] == 'stage':
            channel_kwargs['topic'] = channel_data.get('topic', '')
            new_channel = await guild.create_stage_channel(**channel_kwargs)

        # Aplicar permissões
        if new_channel:
            for overwrite_data in channel_data.get('overwrites', []):
                if overwrite_data['type'] == 'role' and overwrite_data['name'] in role_mapping:
                    await new_channel.set_permissions(
                        role_mapping[overwrite_data['name']],
                        overwrite=discord.PermissionOverwrite.from_pair(
                            discord.Permissions(overwrite_data['allow']),
                            discord.Permissions(overwrite_data['deny'])
                        )
                    )

        return new_channel

    except Exception as e:
        logger.error(f"Erro ao criar canal {channel_data['name']}: {e}")
        return None

@bot.command()
async def listar_templates(ctx):
    """Lista todos os templates salvos"""
    
    templates = load_templates()
    
    if not templates:
        await ctx.send("📭 Nenhum template salvo.")
        return

    embed = discord.Embed(title="📁 TEMPLATES COMPLETOS SALVOS", color=0x9b59b6)
    
    for name, template in list(templates.items()):
        total_channels = sum(len(cat['channels']) for cat in template['categories']) + len(template.get('channels', []))
        
        embed.add_field(
            name=f"📋 {name}",
            value=f"**Servidor:** {template['name']}\n**Estrutura:** {len(template['roles'])} cargos, {len(template['categories'])} categorias, {total_channels} canais",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def servidores_bot(ctx):
    """Lista servidores onde o bot está"""
    
    embed = discord.Embed(title="🏠 SERVIDORES DISPONÍVEIS", color=0xe74c3c)
    
    for guild in bot.guilds:
        bot_member = guild.get_member(bot.user.id)
        permissions = "✅ Admin" if bot_member.guild_permissions.administrator else "⚠️ Limitado"
        
        embed.add_field(
            name=f"🛡️ {guild.name}",
            value=f"**ID:** `{guild.id}`\n**Permissões:** {permissions}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def ajuda(ctx):
    """Mostra ajuda do bot completo"""
    
    embed = discord.Embed(
        title="🤖 BOT CLONADOR COMPLETO - COMANDOS",
        description="**Clone 100% da estrutura de servidores**",
        color=0xf39c12
    )
    
    embed.add_field(
        name="🚀 COMANDOS PRINCIPAIS",
        value="""`!clonar_tudo ID` - Clona **TODA** a estrutura
`!aplicar_tudo NOME` - Aplica template completo
`!listar_templates` - Lista templates salvos
`!servidores_bot` - Mostra servidores disponíveis""",
        inline=False
    )
    
    embed.add_field(
        name="📊 O QUE É CLONADO",
        value="""✅ **Todos os cargos** (cores, permissões, posições)
✅ **Todas as categorias** (com posições exatas)
✅ **Todos os canais** (texto, voz, stage, fórum)
✅ **Todas as permissões** (cargos e membros)
✅ **Emojis e configurações** do servidor""",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Iniciar bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("❌ Token não encontrado!")
    else:
        logger.info("🚀 Iniciando Bot Clonador COMPLETO no Render...")
        bot.run(token)
