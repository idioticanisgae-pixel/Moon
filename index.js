const { Client, GatewayIntentBits, AttachmentBuilder } = require("discord.js")
const { execFile } = require("child_process")
const fs = require("fs")
const path = require("path")
const os = require("os")
const https = require("https")
require("dotenv").config()

// ── Config ────────────────────────────────────────────────────────────────
const LUA_EXE = path.join(__dirname, "obfuscator", "lua.exe")
const CLI_LUA = path.join(__dirname, "obfuscator", "cli.lua")
const OBF_DIR = path.join(__dirname, "obfuscator")
const LOG_FILE = path.join(__dirname, "zuka.log")

// ── Logger ────────────────────────────────────────────────────────────────
function timestamp() {
    return new Date().toISOString()
}

function log(level, msg) {
    const line = `[${timestamp()}] [${level}] ${msg}`
    console.log(line)
    fs.appendFileSync(LOG_FILE, line + "\n", "utf8")
}

const logger = {
    info:  (msg) => log("INFO ", msg),
    warn:  (msg) => log("WARN ", msg),
    error: (msg) => log("ERROR", msg),
    cmd:   (msg) => log("CMD  ", msg),
}

const VALID_PRESETS = ["Default", "Luraph", "Luarmor", "HttpGet", "Fast", "Light", "Strings", "Byte", "Heavy", "Medium"]

// ── Obfuscate function ────────────────────────────────────────────────────
function obfuscate(code, preset, luau) {
    return new Promise((resolve, reject) => {
        const tmpInput = path.join(os.tmpdir(), `zuka_${Date.now()}.lua`)
        const tmpOutput = tmpInput.replace(".lua", ".obfuscated.lua")

        fs.writeFileSync(tmpInput, code, "utf8")

        const args = [CLI_LUA, "--preset", preset, "--out", tmpOutput]
        if (luau) args.push("--LuaU")
        args.push(tmpInput)

        execFile(LUA_EXE, args, { cwd: OBF_DIR }, (err, stdout, stderr) => {
            if (fs.existsSync(tmpInput)) fs.unlinkSync(tmpInput)

            if (err) {
                if (fs.existsSync(tmpOutput)) fs.unlinkSync(tmpOutput)
                return reject(stderr || err.message)
            }

            if (fs.existsSync(tmpOutput)) {
                const result = fs.readFileSync(tmpOutput, "utf8")
                fs.unlinkSync(tmpOutput)
                resolve(result)
            } else {
                reject("Obfuscator ran but produced no output file.")
            }
        })
    })
}

// ── Download helper ───────────────────────────────────────────────────────
function downloadText(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            let data = ""
            res.on("data", (chunk) => (data += chunk))
            res.on("end", () => resolve(data))
            res.on("error", reject)
        })
    })
}

// ── Safe delete helper ────────────────────────────────────────────────────
async function tryDelete(message) {
    try {
        await message.delete()
        logger.info(`Deleted original message ${message.id} from ${message.author.tag} in #${message.channel.name}`)
    } catch (err) {
        logger.warn(`Could not delete message ${message.id}: ${err.message}`)
    }
}

// ── Bot setup ─────────────────────────────────────────────────────────────
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
    ],
})

client.once("ready", () => {
    logger.info(`Logged in as ${client.user.tag}`)
    logger.info(`Zuka Bot is online!`)
})

// ── Message handler ───────────────────────────────────────────────────────
client.on("messageCreate", async (message) => {
    if (message.author.bot) return

    const content = message.content.trim()

    // ── !help ──────────────────────────────────────────────────────────────
    if (content === "!help") {
        logger.cmd(`!help used by ${message.author.tag} (${message.author.id}) in #${message.channel.name} [${message.guild?.name}]`)
        return message.reply([
            "**Zuka's Obfuscator**",
            "",
            "**Commands:**",
            "`!ob <code>` — Obfuscate code directly",
            "`!ob` + attach a `.lua` file — Obfuscate a file",
            "",
            "**Options (add to command):**",
            "`--preset <name>` — Choose preset (default: Default)",
            "`--luau` — Enable LuaU mode",
            "",
            "**Presets:**",
            "`Default` — Default Obfuscation, encryption, anti-tamper & more",
            "`Luraph` — Luraph Replication, without the external bullshit.",
            "`Luarmor` — Same as Luraph without any external bullshit.",
            "`HttpGet` — Mainly for loadstrings.",
            "`Byte` —  Bytecode Vmify it's slightly buggy I wouldnt use it for protection.",
            "`Medium` — Less beefy than Default.",
            "`Fast` —  Small Vmified output.",
            "`Strings` —  Strings only obfuscation, Dynamic fake roblox service names to make the output look like it wasn't obfuscated.",
            "",
            "**Examples:**",
            "`!ob print('hi')`",
            "`!ob --preset Executor print('hi')`",
            "`!ob --preset Luraph --luau` (with attached .lua file)",
            "",
            "⚠️ Your original script will be deleted from chat after obfuscation.",
        ].join("\n"))
    }

    // ── !ob ────────────────────────────────────────────────────────────────
    if (!content.startsWith("!ob")) return

    // Parse args from message
    let raw = content.replace("!ob", "").trim()

    let preset = "Default"
    let luau = false

    // Extract --preset
    const presetMatch = raw.match(/--preset\s+(\S+)/i)
    if (presetMatch) {
        const requested = presetMatch[1]
        if (!VALID_PRESETS.includes(requested)) {
            logger.warn(`Invalid preset "${requested}" requested by ${message.author.tag} (${message.author.id})`)
            return message.reply(`Unknown preset \`${requested}\`.\nValid presets: ${VALID_PRESETS.join(", ")}`)
        }
        preset = requested
        raw = raw.replace(presetMatch[0], "").trim()
    }

    // Extract --luau
    if (/--luau/i.test(raw)) {
        luau = true
        raw = raw.replace(/--luau/i, "").trim()
    }

    // Strip code block fences
    let code = raw.replace(/^```(?:lua)?\n?/, "").replace(/```$/, "").trim()

    // Check for file attachment
    const attachment = message.attachments.find((a) => a.name.endsWith(".lua"))
    if (attachment) {
        try {
            code = await downloadText(attachment.url)
        } catch {
            return message.reply("Failed to download your file.")
        }
    }

    if (!code) {
        logger.warn(`!ob used with no code by ${message.author.tag} (${message.author.id}) in #${message.channel.name}`)
        return message.reply([
            "❌ No code provided!",
            "Usage: `!ob <code>` or attach a `.lua` file.",
            "Type `!help` for more info.",
        ].join("\n"))
    }

    logger.cmd(`!ob by ${message.author.tag} (${message.author.id}) | Guild: ${message.guild?.name} | #${message.channel.name} | Preset: ${preset} | LuaU: ${luau} | File: ${attachment ? attachment.name : "none"} | Size: ${code.length} chars`)

    // Delete the original message BEFORE sending the obfuscated result
    await tryDelete(message)

    // Send a temporary "working" notice to the channel (not a reply, since original is gone)
    const statusMsg = await message.channel.send(
        `<@${message.author.id}> Obfuscating with preset \`${preset}\`${luau ? " (LuaU mode)" : ""}...`
    )

    try {
        const result = await obfuscate(code, preset, luau)
        logger.info(`Obfuscation SUCCESS | User: ${message.author.tag} | Preset: ${preset} | Input: ${code.length} chars → Output: ${result.length} chars`)

        if (result.length < 1800) {
            await statusMsg.edit(
                `<@${message.author.id}> Preset: \`${preset}\`\n\`\`\`lua\n${result}\n\`\`\``
            )
        } else {
            const outName = attachment ? `obf_${attachment.name}` : `obfuscated.lua`
            const tmpOut = path.join(os.tmpdir(), outName)
            fs.writeFileSync(tmpOut, result, "utf8")

            const file = new AttachmentBuilder(tmpOut, { name: outName })
            await statusMsg.edit({
                content: `<@${message.author.id}> Preset: \`${preset}\``,
                files: [file],
            })
            fs.unlinkSync(tmpOut)
        }
    } catch (err) {
        logger.error(`Obfuscation FAILED | User: ${message.author.tag} | Preset: ${preset} | Reason: ${err}`)
        await statusMsg.edit(
            `<@${message.author.id}> Obfuscation failed. Please check your code and try again.`
        )
    }
})

// ── Start ─────────────────────────────────────────────────────────────────
if (!process.env.TOKEN) {
    logger.error("No TOKEN found in .env file!")
    process.exit(1)
}

// Catch unhandled errors so they go to the log file too
process.on("unhandledRejection", (err) => {
    logger.error(`Unhandled rejection: ${err}`)
})
process.on("uncaughtException", (err) => {
    logger.error(`Uncaught exception: ${err}`)
})

logger.info("Starting Zuka Bot...")
client.login(process.env.TOKEN)