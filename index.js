const { Client, GatewayIntentBits, SlashCommandBuilder, REST, Routes, PermissionFlagsBits, ActivityType } = require('discord.js');
const express = require('express');
const http = require('http');

// Configuração do cliente Discord
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildVoiceStates
    ]
});

// Configuração do servidor web para manter o bot online
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.get('/', (req, res) => {
    res.json({ 
        status: 'Bot online', 
        uptime: Math.floor(process.uptime()),
        guilds: client.guilds.cache.size 
    });
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ 
        status: 'healthy',
        timestamp: new Date().toISOString(),
        ping: client.ws.ping
    });
});

// Comandos Slash
const commands = [
    new SlashCommandBuilder()
        .setName('clonar')
        .setDescription('🔄 Clona a estrutura completa de um servidor')
        .addStringOption(option =>
            option.setName('servidor')
                .setDescription('ID do servidor de destino')
                .setRequired(true))
        .addBooleanOption(option =>
            option.setName('cargos')
                .setDescription('Clonar cargos? (Padrão: true)'))
        .addBooleanOption(option =>
            option.setName('canais')
                .setDescription('Clonar canais? (Padrão: true)'))
        .addBooleanOption(option =>
            option.setName('permissoes')
                .setDescription('Clonar permissões? (Padrão: true)')),
    
    new SlashCommandBuilder()
        .setName('status')
        .setDescription('📊 Ver status do bot e servidores'),
    
    new SlashCommandBuilder()
        .setName('limpar')
        .setDescription('🗑️ Limpar todos os canais e cargos do servidor (CUIDADO!)')
        .addStringOption(option =>
            option.setName('servidor')
                .setDescription('ID do servidor para limpar')
                .setRequired(true))
];

// Registrar comandos
async function registerCommands() {
    try {
        const rest = new REST({ version: '10' }).setToken(process.env.TOKEN);
        console.log('🔄 Registrando comandos slash...');
        
        await rest.put(
            Routes.applicationCommands(client.user.id),
            { body: commands }
        );
        console.log('✅ Comandos slash registrados com sucesso!');
    } catch (error) {
        console.error('❌ Erro ao registrar comandos:', error);
    }
}

// Sistema de clonagem
async function cloneServer(interaction, targetGuildId, options = {}) {
    const {
        cloneRoles = true,
        cloneChannels = true,
        clonePermissions = true
    } = options;

    const sourceGuild = interaction.guild;
    let targetGuild;

    try {
        targetGuild = client.guilds.cache.get(targetGuildId);
        if (!targetGuild) {
            throw new Error('Servidor destino não encontrado. Verifique se o ID está correto e o bot está no servidor.');
        }

        // Verificar permissões
        const botMember = targetGuild.members.me;
        if (!botMember.permissions.has(PermissionFlagsBits.Administrator)) {
            throw new Error('O bot precisa de permissão de Administrador no servidor destino.');
        }

        await interaction.editReply('🔄 Iniciando processo de clonagem...');

        const roleMap = new Map();
        const categoryMap = new Map();

        // Clonar cargos
        if (cloneRoles) {
            await interaction.editReply('🎭 Clonando cargos...');
            const roles = sourceGuild.roles.cache
                .filter(role => !role.managed && role.id !== sourceGuild.id)
                .sort((a, b) => b.position - a.position);

            roleMap.set(sourceGuild.id, targetGuild.id);

            for (const role of roles.values()) {
                try {
                    const newRole = await targetGuild.roles.create({
                        name: role.name,
                        color: role.color,
                        hoist: role.hoist,
                        permissions: clonePermissions ? role.permissions : 0n,
                        mentionable: role.mentionable,
                        position: role.position
                    });
                    roleMap.set(role.id, newRole.id);
                } catch (error) {
                    console.error(`Erro ao criar cargo ${role.name}:`, error);
                }
            }
        }

        // Limpar canais existentes se for clonar canais
        if (cloneChannels) {
            await interaction.editReply('🗑️ Limpando canais existentes...');
            const channels = targetGuild.channels.cache;
            for (const channel of channels.values()) {
                try {
                    await channel.delete();
                } catch (error) {
                    console.error(`Erro ao deletar canal ${channel.name}:`, error);
                }
            }

            // Clonar categorias
            await interaction.editReply('📁 Clonando categorias...');
            const categories = sourceGuild.channels.cache.filter(ch => ch.type === 4);
            
            for (const category of categories.values()) {
                try {
                    const newCategory = await targetGuild.channels.create({
                        name: category.name,
                        type: 4,
                        position: category.position,
                        permissionOverwrites: clonePermissions ? 
                            updatePermissionOverwrites(category.permissionOverwrites.cache, roleMap) : []
                    });
                    categoryMap.set(category.id, newCategory.id);
                } catch (error) {
                    console.error(`Erro ao criar categoria ${category.name}:`, error);
                }
            }

            // Clonar canais de texto
            await interaction.editReply('💬 Clonando canais de texto...');
            const textChannels = sourceGuild.channels.cache.filter(ch => 
                ch.type === 0 && ch.parent
            );
            
            for (const channel of textChannels.values()) {
                try {
                    const parentId = categoryMap.get(channel.parentId);
                    await targetGuild.channels.create({
                        name: channel.name,
                        type: 0,
                        parent: parentId,
                        topic: channel.topic,
                        position: channel.position,
                        nsfw: channel.nsfw,
                        rateLimitPerUser: channel.rateLimitPerUser,
                        permissionOverwrites: clonePermissions ? 
                            updatePermissionOverwrites(channel.permissionOverwrites.cache, roleMap) : []
                    });
                } catch (error) {
                    console.error(`Erro ao criar canal de texto ${channel.name}:`, error);
                }
            }

            // Clonar canais de voz
            await interaction.editReply('🔊 Clonando canais de voz...');
            const voiceChannels = sourceGuild.channels.cache.filter(ch => 
                ch.type === 2 && ch.parent
            );
            
            for (const channel of voiceChannels.values()) {
                try {
                    const parentId = categoryMap.get(channel.parentId);
                    await targetGuild.channels.create({
                        name: channel.name,
                        type: 2,
                        parent: parentId,
                        position: channel.position,
                        bitrate: Math.min(channel.bitrate, targetGuild.maximumBitrate),
                        userLimit: channel.userLimit,
                        permissionOverwrites: clonePermissions ? 
                            updatePermissionOverwrites(channel.permissionOverwrites.cache, roleMap) : []
                    });
                } catch (error) {
                    console.error(`Erro ao criar canal de voz ${channel.name}:`, error);
                }
            }
        }

        await interaction.editReply(`✅ Clonagem concluída com sucesso!\n**Servidor:** ${targetGuild.name}`);

    } catch (error) {
        console.error('Erro na clonagem:', error);
        await interaction.editReply(`❌ Erro: ${error.message}`);
    }
}

function updatePermissionOverwrites(overwrites, roleMap) {
    return overwrites.map(overwrite => {
        const newId = roleMap.get(overwrite.id) || overwrite.id;
        return {
            id: newId,
            allow: overwrite.allow,
            deny: overwrite.deny,
            type: overwrite.type
        };
    });
}

// Eventos do cliente
client.once('ready', async () => {
    console.log(`✅ Bot logado como ${client.user.tag}`);
    console.log(`📊 Conectado em ${client.guilds.cache.size} servidores`);
    
    // Atualizar status
    client.user.setPresence({
        activities: [{ name: '/clonar para clonar servidores', type: ActivityType.Watching }],
        status: 'online'
    });

    await registerCommands();
});

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isCommand()) return;

    await interaction.deferReply({ ephemeral: true });

    try {
        switch (interaction.commandName) {
            case 'clonar':
                if (!interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
                    return interaction.editReply('❌ Você precisa de permissão de Administrador para usar este comando.');
                }

                const targetGuildId = interaction.options.getString('servidor');
                const cloneRoles = interaction.options.getBoolean('cargos') ?? true;
                const cloneChannels = interaction.options.getBoolean('canais') ?? true;
                const clonePermissions = interaction.options.getBoolean('permissoes') ?? true;

                await cloneServer(interaction, targetGuildId, {
                    cloneRoles,
                    cloneChannels,
                    clonePermissions
                });
                break;

            case 'status':
                const guilds = client.guilds.cache;
                const statusMessage = `
📊 **Status do Bot**
🟢 Online há: ${Math.floor(process.uptime() / 60)} minutos
📡 Ping: ${client.ws.ping}ms
🏠 Servidores: ${guilds.size}
👥 Usuários: ${guilds.reduce((acc, guild) => acc + guild.memberCount, 0)}
                `.trim();
                await interaction.editReply(statusMessage);
                break;

            case 'limpar':
                if (!interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
                    return interaction.editReply('❌ Você precisa de permissão de Administrador para usar este comando.');
                }

                const guildIdToClean = interaction.options.getString('servidor');
                const guildToClean = client.guilds.cache.get(guildIdToClean);
                
                if (!guildToClean) {
                    return interaction.editReply('❌ Servidor não encontrado.');
                }

                await interaction.editReply('🗑️ Iniciando limpeza...');
                
                // Limpar canais
                const channels = guildToClean.channels.cache;
                for (const channel of channels.values()) {
                    try {
                        await channel.delete();
                    } catch (error) {
                        console.error(`Erro ao deletar canal:`, error);
                    }
                }

                // Limpar cargos
                const roles = guildToClean.roles.cache.filter(role => 
                    !role.managed && role.id !== guildToClean.id && role.editable
                );
                for (const role of roles.values()) {
                    try {
                        await role.delete();
                    } catch (error) {
                        console.error(`Erro ao deletar cargo:`, error);
                    }
                }

                await interaction.editReply('✅ Limpeza concluída!');
                break;
        }
    } catch (error) {
        console.error('Erro no comando:', error);
        await interaction.editReply('❌ Ocorreu um erro ao executar o comando.');
    }
});

// Sistema anti-queda
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
    console.log('Reiniciando bot...');
    process.exit(1);
});

// Reconexão automática
client.on('disconnect', () => {
    console.log('Bot desconectado. Tentando reconectar...');
});

client.on('reconnecting', () => {
    console.log('Reconectando...');
});

// Inicialização
async function startBot() {
    try {
        // Iniciar servidor web primeiro
        const server = app.listen(PORT, () => {
            console.log(`🌐 Servidor web rodando na porta ${PORT}`);
        });

        // Manter a porta aberta
        server.keepAliveTimeout = 0;
        
        // Conectar o bot ao Discord
        await client.login(process.env.TOKEN);
        
    } catch (error) {
        console.error('Erro ao iniciar bot:', error);
        setTimeout(startBot, 10000); // Tentar novamente em 10 segundos
    }
}

// Iniciar o bot
startBot();
