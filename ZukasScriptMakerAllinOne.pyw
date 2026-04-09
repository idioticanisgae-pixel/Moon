import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re
import json
import os
import pyperclip

# ── Theme ────────────────────────────────────────────────────────────────────
BG       = "#0e0e12"
BG2      = "#16161c"
BG3      = "#1e1e26"
ACCENT   = "#c32123"
ACCENT2  = "#ff4444"
CYAN     = "#00e5ff"
GREEN    = "#50c850"
YELLOW   = "#ffc832"
SUBTEXT  = "#888899"
TEXT     = "#e8e8f0"
BORDER   = "#2a2a38"
FONT_UI  = ("Consolas", 10)
FONT_SM  = ("Consolas", 9)
FONT_LG  = ("Consolas", 13, "bold")
FONT_TITLE = ("Consolas", 11, "bold")

# ── Converter Logic ──────────────────────────────────────────────────────────

def convert_to_addcmd(source: str) -> str:
    """Convert RegisterCommand / Modules.X:Initialize patterns to addcmd style."""
    output_lines = []
    source = source.strip()

    # Pattern 1: RegisterCommand({Name=..., Aliases={...}, ...}, function(args) ... end)
    reg_pattern = re.compile(
        r'RegisterCommand\s*\(\s*\{[^}]*Name\s*=\s*"([^"]+)"[^}]*(?:Aliases\s*=\s*\{([^}]*)\})?[^}]*\}\s*,\s*function\s*\((.*?)\)(.*?)end\s*\)',
        re.DOTALL
    )

    # Pattern 2: Modules.X:Initialize() wrapper — extract inner RegisterCommand calls
    init_pattern = re.compile(
        r'function\s+Modules\.(\w+):Initialize\(\)(.*?)end',
        re.DOTALL
    )

    converted = source
    found_any = False

    # Handle Modules.X:Initialize blocks first — unwrap them
    for init_match in init_pattern.finditer(source):
        mod_name = init_match.group(1)
        body = init_match.group(2)
        output_lines.append(f"-- ── Module: {mod_name} ──────────────────────────────────────")
        inner = convert_to_addcmd(body)
        output_lines.append(inner)
        found_any = True

    if found_any:
        return "\n".join(output_lines)

    # Handle RegisterCommand calls
    for m in reg_pattern.finditer(source):
        found_any = True
        name = m.group(1)
        aliases_raw = m.group(2) or ""
        params = m.group(3).strip()
        body = m.group(4).strip()

        # Parse aliases
        aliases = [a.strip().strip('"').strip("'")
                   for a in aliases_raw.split(",") if a.strip().strip('"').strip("'")]
        alias_str = "{" + ", ".join(f'"{a}"' for a in aliases) + "}"

        # Normalise params — addcmd always passes (args, speaker)
        if not params or params == "":
            params = "args, speaker"
        elif "args" not in params:
            params = "args, speaker"

        # Re-indent body
        body_lines = body.split("\n")
        indented = "\n".join("    " + l if l.strip() else "" for l in body_lines)

        output_lines.append(
            f'addcmd("{name}", {alias_str}, function({params})\n{indented}\nend)'
        )

    if not found_any:
        # Nothing to convert — wrap raw function body as a template
        output_lines.append(build_template_from_raw(source))

    return "\n\n".join(output_lines)


def build_template_from_raw(body: str) -> str:
    """Wrap raw Lua code into an addcmd template."""
    lines = body.strip().split("\n")
    indented = "\n".join("    " + l if l.strip() else "" for l in lines)
    return (
        'addcmd("commandname", {"alias1"}, function(args, speaker)\n'
        + indented
        + "\nend)"
    )


def generate_addcmd(name: str, aliases: list, body: str,
                    use_getplayer: bool, use_donotif: bool,
                    use_speaker: bool, use_runservice: bool) -> str:
    alias_str = "{" + ", ".join(f'"{a.strip()}"' for a in aliases if a.strip()) + "}"
    lines = []
    lines.append(f'addcmd("{name}", {alias_str}, function(args, speaker)')

    if use_getplayer:
        lines.append('    local targets = getPlayer(args[1], speaker)')
        lines.append('    if #targets == 0 then')
        lines.append(f'        DoNotif("No players found.", 2)')
        lines.append('        return')
        lines.append('    end')
        lines.append('    for _, plr in ipairs(targets) do')
        lines.append('        -- your code here')
        lines.append('    end')
    elif use_speaker:
        lines.append('    local char = speaker.Character')
        lines.append('    local hum = char and char:FindFirstChildOfClass("Humanoid")')
        lines.append('    local root = char and char:FindFirstChild("HumanoidRootPart")')
        lines.append('    if not (hum and root) then return end')
        lines.append('    -- your code here')
    else:
        if body.strip():
            for l in body.strip().split("\n"):
                lines.append("    " + l if l.strip() else "")
        else:
            lines.append('    -- your code here')

    if use_runservice:
        lines.append('')
        lines.append('    local conn')
        lines.append('    conn = RunService.Heartbeat:Connect(function()')
        lines.append('        -- loop body')
        lines.append('    end)')

    if use_donotif:
        lines.append(f'    DoNotif("{name}: DONE", 2)')

    lines.append('end)')
    return "\n".join(lines)


def generate_toggle_cmd(name: str, aliases: list, on_body: str, off_body: str) -> str:
    alias_str = "{" + ", ".join(f'"{a.strip()}"' for a in aliases if a.strip()) + "}"
    on_ind  = "\n".join("        " + l if l.strip() else "" for l in on_body.strip().split("\n"))
    off_ind = "\n".join("        " + l if l.strip() else "" for l in off_body.strip().split("\n"))
    return (
        f"do\n"
        f"    local {name}Enabled = false\n"
        f"    local {name}Conn\n\n"
        f'    addcmd("{name}", {alias_str}, function(args, speaker)\n'
        f"        {name}Enabled = not {name}Enabled\n"
        f"        if {name}Enabled then\n"
        f"{on_ind}\n"
        f'            DoNotif("{name}: ENABLED", 2)\n'
        f"        else\n"
        f"            if {name}Conn then {name}Conn:Disconnect() {name}Conn = nil end\n"
        f"{off_ind}\n"
        f'            DoNotif("{name}: DISABLED", 2)\n'
        f"        end\n"
        f"    end)\n"
        f"end"
    )


def generate_module(mod_name: str, cmds: list) -> str:
    lines = []
    lines.append(f"Modules.{mod_name} = {{")
    lines.append("    State = { IsEnabled = false, Connection = nil },")
    lines.append("    Config = {}")
    lines.append("}")
    lines.append(f"function Modules.{mod_name}:Initialize()")
    for cmd in cmds:
        alias_str = "{" + ", ".join(f'"{a.strip()}"' for a in cmd["aliases"] if a.strip()) + "}"
        lines.append(f'    addcmd("{cmd["name"]}", {alias_str}, function(args, speaker)')
        lines.append(f'        -- {cmd["name"]} logic')
        lines.append(f'        DoNotif("{cmd["name"]}: called", 2)')
        lines.append('    end)')
    lines.append("end")
    return "\n".join(lines)


def generate_module_register(mod_name: str, cmds: list) -> str:
    """Generate standalone RegisterCommand style — no Modules wrapper, just bare RegisterCommand calls."""
    lines = []
    lines.append(f"-- ── {mod_name} ──────────────────────────────────────────")
    lines.append(f"-- RegisterCommand style for ZukaPanel")
    lines.append("")

    for cmd in cmds:
        name       = cmd["name"]
        alias_list = [a.strip() for a in cmd["aliases"] if a.strip()]
        alias_str  = "{" + ", ".join(f'"{a}"' for a in alias_list) + "}"
        lines.append(f'RegisterCommand({{')
        lines.append(f'    Name        = "{name}",')
        lines.append(f'    Aliases     = {alias_str},')
        lines.append(f'    Description = "{name} command",')
        lines.append(f'    ArgsDesc    = {{}},')
        lines.append(f'    Permissions = {{}},')
        lines.append(f'}}, function(args, speaker)')
        lines.append(f'    -- {name} logic here')
        lines.append(f'    DoNotif("{name}: called by " .. speaker.Name, 2)')
        lines.append(f'end)')
        lines.append("")

    return "\n".join(lines).rstrip()


def generate_module_dual(mod_name: str, cmds: list) -> str:
    """Generate RegisterCommandDual style — registers in both ZukaPanel and addcmd systems."""
    lines = []
    lines.append(f"-- ── {mod_name} ──────────────────────────────────────────")
    lines.append(f"-- RegisterCommandDual style — works with both ZukaPanel and addcmd")
    lines.append("")

    for cmd in cmds:
        name       = cmd["name"]
        alias_list = [a.strip() for a in cmd["aliases"] if a.strip()]
        alias_str  = "{" + ", ".join(f'"{a}"' for a in alias_list) + "}"
        lines.append(f'RegisterCommandDual({{')
        lines.append(f'    Name        = "{name}",')
        lines.append(f'    Aliases     = {alias_str},')
        lines.append(f'    Description = "{name} command",')
        lines.append(f'}}, function(args, speaker)')
        lines.append(f'    -- {name} logic here')
        lines.append(f'    DoNotif("{name}: called by " .. speaker.Name, 2)')
        lines.append(f'end)')
        lines.append("")

    return "\n".join(lines).rstrip()


# ── IY-Style GUI Template Generator ─────────────────────────────────────────

def generate_iy_gui(title: str, prefix: str, cmds: list, theme: dict) -> str:
    c1 = theme.get("shade1", "36, 36, 37")
    c2 = theme.get("shade2", "46, 46, 47")
    c3 = theme.get("shade3", "78, 78, 79")
    ct = theme.get("text",   "255, 255, 255")

    lines = []
    def w(s=""): lines.append(s)

    w("-- ════════════════════════════════════════════════════════")
    w(f"-- {title} — IY-Style Command Framework")
    w("-- Generated by Zuka Panel Command Builder")
    w("-- ════════════════════════════════════════════════════════")
    w()
    w("local Players          = game:GetService('Players')")
    w("local UserInputService = game:GetService('UserInputService')")
    w("local RunService       = game:GetService('RunService')")
    w("local TweenService     = game:GetService('TweenService')")
    w("local TextChatService  = game:GetService('TextChatService')")
    w("local LocalPlayer      = Players.LocalPlayer")
    w("local speaker          = LocalPlayer")
    w()
    w(f'local PREFIX = "{prefix}"')
    w(f'local TITLE  = "{title}"')
    w()
    w("-- ── Command Registry ──────────────────────────────────────────────")
    w("local cmds = {}")
    w()
    w("local function addcmd(name, aliases, func)")
    w("    cmds[#cmds + 1] = { NAME = name, ALIAS = aliases or {}, FUNC = func }")
    w("end")
    w()
    w("local function findCmd(str)")
    w("    str = str:lower()")
    w("    for _, cmd in ipairs(cmds) do")
    w("        if cmd.NAME:lower() == str then return cmd end")
    w("        for _, a in ipairs(cmd.ALIAS) do")
    w("            if a:lower() == str then return cmd end")
    w("        end")
    w("    end")
    w("end")
    w()
    w("local function execCmd(str, plr)")
    w("    plr = plr or speaker")
    w("    local parts = str:split(' ')")
    w("    local name  = table.remove(parts, 1):lower()")
    w("    local cmd   = findCmd(name)")
    w("    if cmd then task.spawn(function() pcall(cmd.FUNC, parts, plr) end) end")
    w("end")
    w()
    w("-- ── getPlayer (IY-style special keywords) ─────────────────────────")
    w("local function getPlayersByName(name)")
    w("    local found = {}")
    w("    name = name:lower()")
    w("    for _, p in ipairs(Players:GetPlayers()) do")
    w("        if p.Name:lower():find(name, 1, true) or")
    w("           p.DisplayName:lower():find(name, 1, true) then")
    w("            table.insert(found, p)")
    w("        end")
    w("    end")
    w("    return found")
    w("end")
    w()
    w("local function getPlayer(arg, plr)")
    w("    if not arg or arg == '' then return {plr} end")
    w("    local low = arg:lower()")
    w("    if low == 'me'     then return {plr} end")
    w("    if low == 'all'    then return Players:GetPlayers() end")
    w("    if low == 'others' then")
    w("        local t = {}")
    w("        for _, p in ipairs(Players:GetPlayers()) do")
    w("            if p ~= plr then table.insert(t, p) end")
    w("        end")
    w("        return t")
    w("    end")
    w("    if low == 'random' then")
    w("        local all = Players:GetPlayers()")
    w("        return #all > 0 and {all[math.random(#all)]} or {}")
    w("    end")
    w("    if low == 'friends' then")
    w("        local t = {}")
    w("        for _, p in ipairs(Players:GetPlayers()) do")
    w("            if p ~= plr and plr:IsFriendsWith(p.UserId) then")
    w("                table.insert(t, p)")
    w("            end")
    w("        end")
    w("        return t")
    w("    end")
    w("    if low == 'team' then")
    w("        local t = {}")
    w("        for _, p in ipairs(Players:GetPlayers()) do")
    w("            if p.Team == plr.Team then table.insert(t, p) end")
    w("        end")
    w("        return t")
    w("    end")
    w("    return getPlayersByName(arg)")
    w("end")
    w()
    w("-- ── DoNotif ────────────────────────────────────────────────────────")
    w("local _notifGui")
    w("local function DoNotif(msg, duration)")
    w("    duration = duration or 3")
    w("    if _notifGui then _notifGui:Destroy() end")
    w("    local ok, sg = pcall(function()")
    w("        local s = Instance.new('ScreenGui')")
    w("        s.Name = 'ZukaNotif'")
    w("        s.ResetOnSpawn = false")
    w("        s.Parent = game:GetService('CoreGui')")
    w("        return s")
    w("    end)")
    w("    if not ok then")
    w("        sg = Instance.new('ScreenGui')")
    w("        sg.ResetOnSpawn = false")
    w("        sg.Parent = LocalPlayer:WaitForChild('PlayerGui')")
    w("    end")
    w("    _notifGui = sg")
    w("    local f = Instance.new('Frame', sg)")
    w(f"    f.BackgroundColor3 = Color3.fromRGB({c1})")
    w("    f.BorderSizePixel = 0")
    w("    f.Position = UDim2.new(0.5, -150, 0, -50)")
    w("    f.Size = UDim2.new(0, 300, 0, 40)")
    w("    Instance.new('UICorner', f).CornerRadius = UDim.new(0, 6)")
    w("    local lbl = Instance.new('TextLabel', f)")
    w("    lbl.Size = UDim2.fromScale(1, 1)")
    w("    lbl.BackgroundTransparency = 1")
    w(f"    lbl.TextColor3 = Color3.fromRGB({ct})")
    w("    lbl.Font = Enum.Font.GothamBold")
    w("    lbl.TextSize = 13")
    w("    lbl.Text = msg")
    w("    TweenService:Create(f, TweenInfo.new(0.3), {")
    w("        Position = UDim2.new(0.5, -150, 0, 12)")
    w("    }):Play()")
    w("    task.delay(duration, function()")
    w("        if sg.Parent then")
    w("            TweenService:Create(f, TweenInfo.new(0.3), {")
    w("                Position = UDim2.new(0.5, -150, 0, -50)")
    w("            }):Play()")
    w("            task.wait(0.35) sg:Destroy()")
    w("        end")
    w("    end)")
    w("end")
    w()
    w("-- ── ScreenGui parent ────────────────────────────────────────────────")
    w("local PARENT do")
    w("    local ok, sg = pcall(function()")
    w("        local s = Instance.new('ScreenGui')")
    w(f"        s.Name = '{title.replace(' ','_')}'")
    w("        s.ResetOnSpawn = false")
    w("        s.DisplayOrder = 999")
    w("        s.Parent = game:GetService('CoreGui')")
    w("        return s")
    w("    end)")
    w("    if ok then PARENT = sg else")
    w("        local s = Instance.new('ScreenGui')")
    w(f"        s.Name = '{title.replace(' ','_')}'")
    w("        s.ResetOnSpawn = false")
    w("        s.Parent = LocalPlayer:WaitForChild('PlayerGui')")
    w("        PARENT = s")
    w("    end")
    w("end")
    w()
    w("-- ── Main Holder ─────────────────────────────────────────────────────")
    w("local Holder = Instance.new('Frame', PARENT)")
    w(f"Holder.BackgroundColor3 = Color3.fromRGB({c2})")
    w("Holder.BorderSizePixel = 0")
    w("Holder.Position = UDim2.new(1, -265, 1, -235)")
    w("Holder.Size = UDim2.new(0, 255, 0, 225)")
    w("Holder.Active = true")
    w("Holder.ZIndex = 10")
    w()
    w("local TitleBar = Instance.new('TextLabel', Holder)")
    w(f"TitleBar.BackgroundColor3 = Color3.fromRGB({c1})")
    w("TitleBar.BorderSizePixel = 0")
    w("TitleBar.Size = UDim2.new(0, 255, 0, 20)")
    w(f"TitleBar.TextColor3 = Color3.fromRGB({ct})")
    w("TitleBar.Font = Enum.Font.GothamBold")
    w("TitleBar.TextSize = 13")
    w("TitleBar.Text = TITLE")
    w("TitleBar.ZIndex = 10")
    w()
    w("local Dark = Instance.new('Frame', Holder)")
    w(f"Dark.BackgroundColor3 = Color3.fromRGB({c1})")
    w("Dark.BorderSizePixel = 0")
    w("Dark.Position = UDim2.new(0, 0, 0, 45)")
    w("Dark.Size = UDim2.new(0, 255, 0, 180)")
    w("Dark.ZIndex = 10")
    w()
    w("local Cmdbar = Instance.new('TextBox', Holder)")
    w("Cmdbar.BackgroundTransparency = 1")
    w("Cmdbar.BorderSizePixel = 0")
    w("Cmdbar.Position = UDim2.new(0, 5, 0, 20)")
    w("Cmdbar.Size = UDim2.new(0, 245, 0, 25)")
    w("Cmdbar.Font = Enum.Font.Gotham")
    w("Cmdbar.TextSize = 13")
    w("Cmdbar.TextXAlignment = Enum.TextXAlignment.Left")
    w(f"Cmdbar.TextColor3 = Color3.fromRGB({ct})")
    w("Cmdbar.Text = ''")
    w(f"Cmdbar.PlaceholderText = 'Command... (prefix: {prefix})'")
    w("Cmdbar.ZIndex = 10")
    w()
    w("local CMDsF = Instance.new('ScrollingFrame', Holder)")
    w("CMDsF.BackgroundTransparency = 1")
    w("CMDsF.BorderSizePixel = 0")
    w("CMDsF.Position = UDim2.new(0, 5, 0, 48)")
    w("CMDsF.Size = UDim2.new(0, 240, 0, 170)")
    w("CMDsF.ScrollBarThickness = 6")
    w(f"CMDsF.ScrollBarImageColor3 = Color3.fromRGB({c3})")
    w("CMDsF.CanvasSize = UDim2.new(0, 0, 0, 0)")
    w("CMDsF.ZIndex = 10")
    w("local cmdLayout = Instance.new('UIListLayout', CMDsF)")
    w("cmdLayout.SortOrder = Enum.SortOrder.LayoutOrder")
    w("cmdLayout.Padding = UDim.new(0, 1)")
    w()
    w("local MinBtn = Instance.new('TextButton', Holder)")
    w(f"MinBtn.BackgroundColor3 = Color3.fromRGB({c3})")
    w("MinBtn.BorderSizePixel = 0")
    w("MinBtn.Position = UDim2.new(1, -20, 0, 0)")
    w("MinBtn.Size = UDim2.new(0, 20, 0, 20)")
    w(f"MinBtn.TextColor3 = Color3.fromRGB({ct})")
    w("MinBtn.Font = Enum.Font.GothamBold")
    w("MinBtn.TextSize = 12")
    w("MinBtn.Text = '-'")
    w("MinBtn.ZIndex = 11")
    w()
    w("-- ── Drag ────────────────────────────────────────────────────────────")
    w("do")
    w("    local dragging, dragStart, startPos")
    w("    TitleBar.InputBegan:Connect(function(inp)")
    w("        if inp.UserInputType == Enum.UserInputType.MouseButton1 then")
    w("            dragging = true dragStart = inp.Position startPos = Holder.Position")
    w("        end")
    w("    end)")
    w("    TitleBar.InputEnded:Connect(function(inp)")
    w("        if inp.UserInputType == Enum.UserInputType.MouseButton1 then dragging = false end")
    w("    end)")
    w("    UserInputService.InputChanged:Connect(function(inp)")
    w("        if dragging and inp.UserInputType == Enum.UserInputType.MouseMovement then")
    w("            local d = inp.Position - dragStart")
    w("            Holder.Position = UDim2.new(startPos.X.Scale, startPos.X.Offset + d.X,")
    w("                                        startPos.Y.Scale, startPos.Y.Offset + d.Y)")
    w("        end")
    w("    end)")
    w("end")
    w()
    w("-- ── Minimize ─────────────────────────────────────────────────────────")
    w("local minimized = false")
    w("MinBtn.MouseButton1Click:Connect(function()")
    w("    minimized = not minimized")
    w("    Dark.Visible   = not minimized")
    w("    Cmdbar.Visible = not minimized")
    w("    CMDsF.Visible  = not minimized")
    w("    Holder.Size = minimized and UDim2.new(0,255,0,20) or UDim2.new(0,255,0,225)")
    w("    MinBtn.Text = minimized and '+' or '-'")
    w("end)")
    w()
    w("-- ── Cmd list entry builder ───────────────────────────────────────────")
    w("local function addCmdEntry(name, desc)")
    w("    local btn = Instance.new('TextButton', CMDsF)")
    w(f"    btn.BackgroundColor3 = Color3.fromRGB({c2})")
    w("    btn.BorderSizePixel = 0")
    w("    btn.Size = UDim2.new(1, -8, 0, 20)")
    w(f"    btn.TextColor3 = Color3.fromRGB({ct})")
    w("    btn.Font = Enum.Font.Gotham")
    w("    btn.TextSize = 11")
    w("    btn.TextXAlignment = Enum.TextXAlignment.Left")
    w("    btn.Text = '  ' .. name .. (desc ~= '' and '  —  ' .. desc or '')")
    w("    btn.ZIndex = 10")
    w("    btn.MouseButton1Click:Connect(function()")
    w("        Cmdbar.Text = name .. ' '")
    w("        Cmdbar:CaptureFocus()")
    w("    end)")
    w("    task.defer(function()")
    w("        CMDsF.CanvasSize = UDim2.new(0,0,0, cmdLayout.AbsoluteContentSize.Y + 4)")
    w("    end)")
    w("end")
    w()
    w("-- ── Cmdbar execution ─────────────────────────────────────────────────")
    w("Cmdbar.FocusLost:Connect(function(enter)")
    w("    if not enter then return end")
    w("    local text = Cmdbar.Text:gsub('^%s*(.-)%s*$', '%1')")
    w("    if text:sub(1, #PREFIX):lower() == PREFIX:lower() then text = text:sub(#PREFIX+1) end")
    w("    if text ~= '' then execCmd(text, speaker) end")
    w("    Cmdbar.Text = ''")
    w("end)")
    w()
    w("-- ── Chat listener ────────────────────────────────────────────────────")
    w("local function onChat(msg)")
    w("    if msg:sub(1,#PREFIX):lower() ~= PREFIX:lower() then return end")
    w("    execCmd(msg:sub(#PREFIX+1), speaker)")
    w("end")
    w("pcall(function()")
    w("    TextChatService.MessageReceived:Connect(function(m)")
    w("        if m.TextSource and m.TextSource.UserId == LocalPlayer.UserId then onChat(m.Text) end")
    w("    end)")
    w("end)")
    w("LocalPlayer.Chatted:Connect(onChat)")
    w()
    w("-- ── Commands ─────────────────────────────────────────────────────────")
    w()

    for cmd in cmds:
        name      = cmd["name"]
        aliases   = cmd.get("aliases", [])
        body      = cmd.get("body", "").strip()
        desc      = cmd.get("desc", "")
        alias_lua = "{" + ", ".join(f'"{a}"' for a in aliases if a) + "}"
        w(f'addcmd("{name}", {alias_lua}, function(args, speaker)')
        if body:
            for line in body.split("\n"):
                w("    " + line)
        else:
            w(f'    DoNotif("{name} called", 2)')
        w("end)")
        w(f'addCmdEntry("{name}", "{desc}")')
        w()

    w("task.defer(function()")
    w("    CMDsF.CanvasSize = UDim2.new(0,0,0, cmdLayout.AbsoluteContentSize.Y + 4)")
    w("end)")
    w()
    w(f'DoNotif("{title} loaded!", 3)')
    return "\n".join(lines)


RAINBOW_UTIL = '''
-- ── Rainbow / Animated Outline Utility ───────────────────────────────────────
-- Usage:
--   RainbowOutline(frame)                     -- default rainbow, thickness 2
--   RainbowOutline(frame, 3, 0.5)             -- thickness 3, half speed
--   RainbowOutline(frame, 2, 1, true)         -- also recolors the title bar text
--   PulseOutline(frame, Color3.fromRGB(0,200,255))  -- single color pulse
--   GlowOutline(frame, Color3.fromRGB(200,0,255))   -- neon glow effect
-- All functions return the UIStroke so you can :Destroy() it to stop.

local TweenService = game:GetService("TweenService")
local RunService   = game:GetService("RunService")

local function RainbowOutline(frame, thickness, speed, recolorText)
    thickness = thickness or 2
    speed     = speed     or 1

    local stroke = Instance.new("UIStroke", frame)
    stroke.Thickness     = thickness
    stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border

    local hue = 0
    local conn = RunService.Heartbeat:Connect(function(dt)
        hue = (hue + dt * speed * 0.2) % 1
        local color = Color3.fromHSV(hue, 1, 1)
        stroke.Color = color
        if recolorText then
            for _, v in ipairs(frame:GetDescendants()) do
                if v:IsA("TextLabel") or v:IsA("TextButton") or v:IsA("TextBox") then
                    v.TextColor3 = color
                end
            end
        end
    end)

    -- Store disconnect on stroke so caller can stop it
    stroke.AncestryChanged:Connect(function()
        if not stroke.Parent then conn:Disconnect() end
    end)

    return stroke, conn
end

local function PulseOutline(frame, color, thickness, speed)
    color     = color     or Color3.fromRGB(0, 200, 255)
    thickness = thickness or 2
    speed     = speed     or 1.5

    local stroke = Instance.new("UIStroke", frame)
    stroke.Color     = color
    stroke.Thickness = thickness
    stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border

    local function pulse()
        TweenService:Create(stroke, TweenInfo.new(speed * 0.5, Enum.EasingStyle.Sine), {
            Thickness = thickness * 3,
            Transparency = 0.6,
        }):Play()
        task.wait(speed * 0.5)
        TweenService:Create(stroke, TweenInfo.new(speed * 0.5, Enum.EasingStyle.Sine), {
            Thickness = thickness,
            Transparency = 0,
        }):Play()
        task.wait(speed * 0.5)
    end

    local running = true
    local thread  = task.spawn(function()
        while running do pulse() end
    end)

    stroke.AncestryChanged:Connect(function()
        if not stroke.Parent then running = false end
    end)

    return stroke
end

local function GlowOutline(frame, color, thickness)
    color     = color     or Color3.fromRGB(200, 0, 255)
    thickness = thickness or 3

    -- Outer glow (thick, semi-transparent)
    local glow = Instance.new("UIStroke", frame)
    glow.Color        = color
    glow.Thickness    = thickness * 3
    glow.Transparency = 0.7
    glow.ApplyStrokeMode = Enum.ApplyStrokeMode.Border

    -- Inner sharp stroke
    local inner = Instance.new("UIStroke", frame)
    inner.Color        = color
    inner.Thickness    = thickness
    inner.Transparency = 0
    inner.ApplyStrokeMode = Enum.ApplyStrokeMode.Border

    -- Subtle pulse on the glow layer
    local function glowPulse()
        TweenService:Create(glow, TweenInfo.new(1.2, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
            Transparency = 0.4,
        }):Play()
        task.wait(1.2)
        TweenService:Create(glow, TweenInfo.new(1.2, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
            Transparency = 0.8,
        }):Play()
        task.wait(1.2)
    end

    local running = true
    task.spawn(function() while running do glowPulse() end end)
    glow.AncestryChanged:Connect(function()
        if not glow.Parent then running = false end
    end)

    return inner, glow
end
'''


# ── Loop Command Generator ────────────────────────────────────────────────────

def generate_loop_cmd(name: str, aliases: list, loop_body: str,
                      stop_body: str, delay: float, use_getplayer: bool) -> str:
    alias_str = "{" + ", ".join(f'"{a.strip()}"' for a in aliases if a.strip()) + "}"
    on_ind  = "\n".join("                    " + l if l.strip() else "" for l in loop_body.strip().split("\n"))
    off_ind = "\n".join("            " + l if l.strip() else "" for l in stop_body.strip().split("\n"))
    plr_pre = ""
    if use_getplayer:
        plr_pre = (
            f"        local targets = getPlayer(args[1], speaker)\n"
            f"        if #targets == 0 then DoNotif(\"No players found.\", 2)"
            f" {name}Active = false return end\n"
        )
    lines = [
        "do",
        f"    local {name}Active = false",
        f"    local {name}Thread",
        "",
        f'    addcmd("{name}", {alias_str}, function(args, speaker)',
        f"        {name}Active = not {name}Active",
        f"        if {name}Active then",
        plr_pre.rstrip("\n") if plr_pre else "",
        f"            {name}Thread = task.spawn(function()",
        f"                while {name}Active do",
        on_ind,
        f"                    task.wait({delay})",
        f"                end",
        f"            end)",
        f'            DoNotif("{name}: RUNNING", 2)',
        f"        else",
        f"            if {name}Thread then task.cancel({name}Thread) {name}Thread = nil end",
        off_ind,
        f'            DoNotif("{name}: STOPPED", 2)',
        f"        end",
        f"    end)",
        f"end",
    ]
    return "\n".join(l for l in lines if l is not None)


# ── Utilities Generator ──────────────────────────────────────────────────────

LEVENSHTEIN_SNIPPET = '''-- ── Levenshtein Distance (fuzzy command suggestions) ────────────────────────
local function calculateLevenshteinDistance(s, t)
    local m, n = #s, #t
    local d = {}
    for i = 0, m do d[i] = {[0] = i} end
    for j = 0, n do d[0][j] = j end
    for j = 1, n do
        for i = 1, m do
            if s:sub(i,i) == t:sub(j,j) then
                d[i][j] = d[i-1][j-1]
            else
                d[i][j] = 1 + math.min(d[i-1][j], d[i][j-1], d[i-1][j-1])
            end
        end
    end
    return d[m][n]
end

-- Usage in your command processor:
-- local SUGGESTION_THRESHOLD = 2
-- local lowestDistance = math.huge
-- local closestMatch = nil
-- for command, _ in pairs(Commands) do
--     local distance = calculateLevenshteinDistance(cmdName, command)
--     if distance < lowestDistance then
--         lowestDistance = distance
--         closestMatch = command
--     end
-- end
-- if closestMatch and lowestDistance <= SUGGESTION_THRESHOLD then
--     DoNotif(("Unknown command: %s. Did you mean ;%s?"):format(cmdName, closestMatch), 4)
-- else
--     DoNotif("Unknown command: " .. cmdName, 3)
-- end
'''

DETECT_ENV_SNIPPET = '''-- ── detectEnvironment() ─────────────────────────────────────────────────────
-- Checks which executor functions are available and rates the executor.
-- Returns a table with: executor name, available functions, count, rating.

local function detectEnvironment()
    local env = {
        executor  = identifyexecutor and identifyexecutor() or "Unknown",
        functions = {},
        level     = 0
    }
    local testFunctions = {
        "getgenv", "getrenv", "getrawmetatable", "setreadonly",
        "hookmetamethod", "hookfunction", "newcclosure",
        "getnamecallmethod", "checkcaller", "getconnections",
        "firesignal", "Drawing", "WebSocket", "request",
        "http_request", "readfile", "writefile",
        "isfile", "isfolder", "makefolder", "delfile"
    }
    for _, funcName in ipairs(testFunctions) do
        local func = getfenv()[funcName]
        if func then
            env.functions[funcName] = type(func)
            env.level = env.level + 1
        end
    end
    env.rating = env.level >= 20 and "Peak Executor"
        or env.level >= 10 and "Decent"
        or "Dog shit"
    return env
end

-- Usage:
-- local env = detectEnvironment()
-- print("Executor:", env.executor)
-- print("Rating:", env.rating)
-- print("Functions available:", env.level)
'''

FIND_PLAYER_SNIPPET = '''-- ── Utilities.findPlayer() ───────────────────────────────────────────────────
-- Resolves a player by exact name, display name, or partial match.
-- Supports "me" as a shortcut for LocalPlayer.

local Utilities = Utilities or {}

function Utilities.findPlayer(inputName)
    local input = tostring(inputName):lower()
    if input == "" then return nil end
    if input == "me" then return game:GetService("Players").LocalPlayer end

    local exactMatch   = nil
    local partialMatch = nil

    for _, player in ipairs(game:GetService("Players"):GetPlayers()) do
        local username    = player.Name:lower()
        local displayName = player.DisplayName:lower()

        if username == input or displayName == input then
            exactMatch = player
            break
        end

        if not partialMatch then
            if username:sub(1, #input) == input or
               displayName:sub(1, #input) == input then
                partialMatch = player
            end
        end
    end

    return exactMatch or partialMatch
end

-- Usage:
-- local target = Utilities.findPlayer(args[1])
-- if not target then DoNotif("Player not found.", 2) return end
'''

def generate_args_boilerplate(args_config: list) -> str:
    """Generate arg parsing boilerplate from a list of arg configs."""
    lines = []
    for i, arg in enumerate(args_config):
        idx    = i + 1
        name   = arg["name"] or f"arg{idx}"
        kind   = arg["type"]
        req    = arg["required"]
        defval = arg.get("default", "")

        if kind == "number":
            lines.append(f'local {name} = tonumber(args[{idx}])')
            if req:
                lines.append(f'if not {name} then DoNotif("Usage: <{name}: number>", 3) return end')
            elif defval:
                lines.append(f'if not {name} then {name} = {defval} end')

        elif kind == "player":
            lines.append(f'local {name}Targets = getPlayer(args[{idx}], speaker)')
            lines.append(f'if #{{name}}Targets == 0 then DoNotif("Player not found.", 2) return end')
            lines.append(f'for _, {name} in ipairs({name}Targets) do')
            lines.append(f'    -- your code using {name}')
            lines.append(f'end')

        elif kind == "string":
            lines.append(f'local {name} = args[{idx}]')
            if req:
                lines.append(f'if not {name} or {name} == "" then DoNotif("Usage: <{name}: string>", 3) return end')
            elif defval:
                lines.append(f'if not {name} then {name} = "{defval}" end')

        elif kind == "boolean":
            lines.append(f'local {name}Raw = args[{idx}] and args[{idx}]:lower()')
            lines.append(f'local {name} = ({name}Raw == "true" or {name}Raw == "on" or {name}Raw == "1")')
            if defval:
                lines.append(f'if not {name}Raw then {name} = {defval} end')

    return "\n".join("    " + l for l in lines)


# ── GUI ──────────────────────────────────────────────────────────────────────

class ZukaCmdBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Zuka Panel — Command Builder v2 + Dex")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        # try pyperclip silently
        self._clip_ok = True
        try:
            pyperclip.copy("")
        except Exception:
            self._clip_ok = False

        self._build_ui()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_titlebar()
        self._build_tabs()

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=BG2, height=44)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        accent_line = tk.Frame(bar, bg=ACCENT, width=4)
        accent_line.pack(side="left", fill="y", padx=(0, 12))

        tk.Label(bar, text="ZUKA", font=("Consolas", 15, "bold"),
                 fg=ACCENT, bg=BG2).pack(side="left")
        tk.Label(bar, text=" PANEL", font=("Consolas", 15, "bold"),
                 fg=CYAN, bg=BG2).pack(side="left")
        tk.Label(bar, text="  //  Command Builder",
                 font=FONT_UI, fg=SUBTEXT, bg=BG2).pack(side="left")

        tk.Label(bar, text="v2.0  addcmd + dex",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="right", padx=12)

    def _build_tabs(self):
        # ── Scrollable tab bar ───────────────────────────────────────────────
        tab_bar_outer = tk.Frame(self, bg=BG2, height=36)
        tab_bar_outer.pack(fill="x")
        tab_bar_outer.pack_propagate(False)

        # Left/right scroll arrow buttons
        btn_left = tk.Button(
            tab_bar_outer, text="◀", font=FONT_SM,
            bg=BG2, fg=SUBTEXT, bd=0, padx=6,
            activebackground=BG3, activeforeground=TEXT,
            cursor="hand2", relief="flat"
        )
        btn_left.pack(side="left", fill="y")

        btn_right = tk.Button(
            tab_bar_outer, text="▶", font=FONT_SM,
            bg=BG2, fg=SUBTEXT, bd=0, padx=6,
            activebackground=BG3, activeforeground=TEXT,
            cursor="hand2", relief="flat"
        )
        btn_right.pack(side="right", fill="y")

        # Canvas acts as the scrollable viewport for tab buttons
        tab_canvas = tk.Canvas(
            tab_bar_outer, bg=BG2, height=36,
            highlightthickness=0, bd=0
        )
        tab_canvas.pack(side="left", fill="both", expand=True)

        # Inner frame holds the actual buttons
        tab_inner = tk.Frame(tab_canvas, bg=BG2)
        tab_canvas_window = tab_canvas.create_window(
            (0, 0), window=tab_inner, anchor="nw"
        )

        def _on_tab_inner_configure(event):
            tab_canvas.configure(scrollregion=tab_canvas.bbox("all"))

        tab_inner.bind("<Configure>", _on_tab_inner_configure)

        # Keep inner frame height in sync with canvas
        def _on_canvas_configure(event):
            tab_canvas.itemconfig(tab_canvas_window, height=event.height)

        tab_canvas.bind("<Configure>", _on_canvas_configure)

        # Scroll by fixed pixel amount
        SCROLL_STEP = 120

        def scroll_left():
            x = tab_canvas.canvasx(0)
            tab_canvas.xview_moveto(
                max(0.0, (x - SCROLL_STEP) / max(tab_inner.winfo_reqwidth(), 1))
            )

        def scroll_right():
            x = tab_canvas.canvasx(0)
            tab_canvas.xview_moveto(
                min(1.0, (x + SCROLL_STEP) / max(tab_inner.winfo_reqwidth(), 1))
            )

        btn_left.configure(command=scroll_left)
        btn_right.configure(command=scroll_right)

        # Mouse-wheel scrolling on the tab bar
        def _tab_mousewheel(event):
            delta = -1 if (event.delta > 0 or event.num == 4) else 1
            x = tab_canvas.canvasx(0)
            tab_canvas.xview_moveto(
                max(0.0, min(1.0,
                    (x + delta * SCROLL_STEP) / max(tab_inner.winfo_reqwidth(), 1)
                ))
            )

        tab_canvas.bind("<MouseWheel>", _tab_mousewheel)
        tab_canvas.bind("<Button-4>",   _tab_mousewheel)
        tab_canvas.bind("<Button-5>",   _tab_mousewheel)
        tab_inner.bind("<MouseWheel>",  _tab_mousewheel)
        tab_inner.bind("<Button-4>",    _tab_mousewheel)
        tab_inner.bind("<Button-5>",    _tab_mousewheel)

        # ── Content area ─────────────────────────────────────────────────────
        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True)

        self._pages = {}
        self._tab_btns = {}
        self._active_tab = tk.StringVar(value="")

        tabs = [
            ("🧙  Wizard",       self._build_wizard_page),
            ("⚡  Builder",      self._build_builder_page),
            ("🔄  Converter",    self._build_converter_page),
            ("🔀  Toggle",       self._build_toggle_page),
            ("🔁  Loop",         self._build_loop_page),
            ("📦  Module",       self._build_module_page),
            ("📋  Templates",    self._build_templates_page),
            ("🎯  Presets",      self._build_presets_page),
            ("🔬  Dex",          self._build_dex_page),
            ("🏠  Hub",          self._build_hub_page),
            ("📥  Import",       self._build_import_page),
            ("🎨  GUI Maker",    self._build_guimaker_page),
            ("🖥  IY Frame",     self._build_iyframe_page),
            ("🌈  FX",           self._build_fx_page),
            ("🔧  Args",         self._build_args_page),
            ("🛠  Utilities",    self._build_utilities_page),
            ("📊  Bulk",         self._build_bulk_page),
            ("🔩  Assembler",    self._build_assembler_page),
            ("⚙️  Config",       self._build_config_page),
            ("📄  ZukaTemplate", self._build_zukaplate_page),
        ]

        for name, builder in tabs:
            page = tk.Frame(content, bg=BG)
            self._pages[name] = page
            builder(page)

        def switch(name):
            for n, p in self._pages.items():
                p.pack_forget()
            self._pages[name].pack(fill="both", expand=True)
            self._active_tab.set(name)
            for n, b in self._tab_btns.items():
                b.configure(
                    fg=TEXT if n == name else SUBTEXT,
                    bg=BG3 if n == name else BG2,
                )
            # Auto-scroll the tab bar so the active tab is visible
            self.after(10, lambda: _scroll_to_active(name))

        def _scroll_to_active(name):
            btn = self._tab_btns.get(name)
            if not btn:
                return
            try:
                btn.update_idletasks()
                bx = btn.winfo_x()
                bw = btn.winfo_width()
                total = tab_inner.winfo_reqwidth()
                vw = tab_canvas.winfo_width()
                if total <= vw:
                    tab_canvas.xview_moveto(0.0)
                    return
                # centre the button in the viewport
                target = bx + bw / 2 - vw / 2
                tab_canvas.xview_moveto(
                    max(0.0, min(1.0, target / total))
                )
            except Exception:
                pass

        for name, _ in tabs:
            btn = tk.Button(
                tab_inner, text=name, font=FONT_SM,
                bg=BG2, fg=SUBTEXT, bd=0,
                activebackground=BG3, activeforeground=TEXT,
                cursor="hand2", padx=12,
                command=lambda n=name: switch(n)
            )
            btn.pack(side="left", fill="y", ipady=2)
            # Forward mouse-wheel events from buttons too
            btn.bind("<MouseWheel>", _tab_mousewheel)
            btn.bind("<Button-4>",   _tab_mousewheel)
            btn.bind("<Button-5>",   _tab_mousewheel)
            self._tab_btns[name] = btn

        switch("🧙  Wizard")

    # ── Page: Builder ────────────────────────────────────────────────────────

    def _build_builder_page(self, parent):
        # Left: form
        left = tk.Frame(parent, bg=BG, width=380)
        left.pack(side="left", fill="y", padx=(14, 0), pady=14)
        left.pack_propagate(False)

        # Right: output
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(left, "COMMAND NAME")
        self._name_var = tk.StringVar()
        self._entry(left, self._name_var)

        self._label(left, "ALIASES  (comma separated)")
        self._alias_var = tk.StringVar()
        self._entry(left, self._alias_var, placeholder="alias1, alias2")

        self._label(left, "BODY  (raw Lua, optional)")
        self._body_box = self._text_area(left, height=6)

        # Options
        self._label(left, "OPTIONS")
        opt_frame = tk.Frame(left, bg=BG)
        opt_frame.pack(fill="x", pady=(2, 8))

        self._opt_getplayer  = self._checkbox(opt_frame, "getPlayer() loop")
        self._opt_speaker    = self._checkbox(opt_frame, "speaker.Character")
        self._opt_donotif    = self._checkbox(opt_frame, "DoNotif on finish")
        self._opt_runservice = self._checkbox(opt_frame, "RunService.Heartbeat")

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(4, 0))
        self._btn(btn_row, "⚡  GENERATE", self._do_generate, ACCENT).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "🗑  CLEAR", self._clear_builder, BG3).pack(side="left")

        # Live preview label
        tk.Label(left, text="LIVE PREVIEW  (updates as you type)",
                 font=FONT_SM, fg=SUBTEXT, bg=BG, anchor="w").pack(fill="x", pady=(10,2))
        self._preview_box = self._text_area(left, height=8)
        self._preview_box.configure(state="disabled")

        # Wire live preview
        def _update_preview(*_):
            name = self._name_var.get().strip()
            if not name:
                self._set_output(self._preview_box, "-- enter a command name to preview")
                return
            aliases = [a.strip() for a in self._alias_var.get().split(",") if a.strip()]
            body    = self._body_box.get("1.0", "end-1c")
            try:
                result = generate_addcmd(
                    name, aliases, body,
                    self._opt_getplayer.get(),
                    self._opt_donotif.get(),
                    self._opt_speaker.get(),
                    self._opt_runservice.get(),
                )
                self._set_output(self._preview_box, result)
            except Exception:
                pass

        self._name_var.trace_add("write", _update_preview)
        self._alias_var.trace_add("write", _update_preview)
        self._body_box.bind("<KeyRelease>", _update_preview)
        self._opt_getplayer.trace_add("write", _update_preview)
        self._opt_donotif.trace_add("write", _update_preview)
        self._opt_speaker.trace_add("write", _update_preview)
        self._opt_runservice.trace_add("write", _update_preview)

        # Output
        self._label(right, "OUTPUT")
        self._builder_out = self._text_area(right, height=30, expand=True)
        self._builder_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6, 0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._builder_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._builder_out), BG3).pack(side="left")

    def _do_generate(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Command name is required.")
            return
        aliases = [a.strip() for a in self._alias_var.get().split(",") if a.strip()]
        body = self._body_box.get("1.0", "end-1c")
        result = generate_addcmd(
            name, aliases, body,
            self._opt_getplayer.get(),
            self._opt_donotif.get(),
            self._opt_speaker.get(),
            self._opt_runservice.get(),
        )
        self._set_output(self._builder_out, result)

    def _clear_builder(self):
        self._name_var.set("")
        self._alias_var.set("")
        self._body_box.delete("1.0", "end")
        self._set_output(self._builder_out, "")

    # ── Page: Converter ──────────────────────────────────────────────────────

    def _build_converter_page(self, parent):
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=14, pady=(14, 6))
        self._label(top, "PASTE EXISTING LUA  (RegisterCommand / Modules.X:Initialize)")

        self._conv_input = self._text_area(parent, height=14)
        self._conv_input.pack(fill="x", padx=14)

        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", padx=14, pady=6)
        self._btn(btn_row, "🔄  CONVERT", self._do_convert, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "📂  LOAD FILE", self._load_file, BG3).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR", lambda: (self._conv_input.delete("1.0","end"), self._set_output(self._conv_out, "")), BG3).pack(side="left")

        self._label_frame(parent, "CONVERTED OUTPUT")
        self._conv_out = self._text_area(parent, height=14, expand=True)

        out_btns = tk.Frame(parent, bg=BG)
        out_btns.pack(fill="x", padx=14, pady=(6, 14))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._conv_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._conv_out), BG3).pack(side="left")

    def _do_convert(self):
        src = self._conv_input.get("1.0", "end-1c").strip()
        if not src:
            messagebox.showwarning("Empty", "Paste some Lua first.")
            return
        result = convert_to_addcmd(src)
        self._set_output(self._conv_out, result)

    def _load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Lua files", "*.lua"), ("All files", "*.*")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self._conv_input.delete("1.0", "end")
                self._conv_input.insert("1.0", f.read())

    # ── Page: Toggle ─────────────────────────────────────────────────────────

    def _build_toggle_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=380)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(left, "COMMAND NAME")
        self._tog_name = tk.StringVar()
        self._entry(left, self._tog_name)

        self._label(left, "ALIASES")
        self._tog_alias = tk.StringVar()
        self._entry(left, self._tog_alias, placeholder="alias1, alias2")

        self._label(left, "ON BODY  (enabled branch)")
        self._tog_on = self._text_area(left, height=6)

        self._label(left, "OFF BODY  (disabled branch)")
        self._tog_off = self._text_area(left, height=6)

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(6,0))
        self._btn(btn_row, "⚡  GENERATE", self._do_toggle, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR", self._clear_toggle, BG3).pack(side="left")

        self._label(right, "OUTPUT")
        self._tog_out = self._text_area(right, height=30, expand=True)
        self._tog_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._tog_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._tog_out), BG3).pack(side="left")

    def _do_toggle(self):
        name = self._tog_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Command name required.")
            return
        aliases = [a.strip() for a in self._tog_alias.get().split(",") if a.strip()]
        on_body  = self._tog_on.get("1.0", "end-1c")
        off_body = self._tog_off.get("1.0", "end-1c")
        result = generate_toggle_cmd(name, aliases, on_body, off_body)
        self._set_output(self._tog_out, result)

    def _clear_toggle(self):
        self._tog_name.set("")
        self._tog_alias.set("")
        self._tog_on.delete("1.0", "end")
        self._tog_off.delete("1.0", "end")
        self._set_output(self._tog_out, "")

    # ── Page: Loop ───────────────────────────────────────────────────────────

    def _build_loop_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=380)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(left, "COMMAND NAME")
        self._loop_name = tk.StringVar()
        self._entry(left, self._loop_name)

        self._label(left, "ALIASES")
        self._loop_alias = tk.StringVar()
        self._entry(left, self._loop_alias, placeholder="alias1, alias2")

        self._label(left, "LOOP DELAY  (seconds)")
        self._loop_delay = tk.StringVar(value="0.1")
        self._entry(left, self._loop_delay)

        self._label(left, "LOOP BODY  (runs every tick)")
        self._loop_body = self._text_area(left, height=5)

        self._label(left, "STOP BODY  (runs on disable, optional)")
        self._loop_stop = self._text_area(left, height=3)

        self._label(left, "OPTIONS")
        opt_frame = tk.Frame(left, bg=BG)
        opt_frame.pack(fill="x", pady=(2,8))
        self._loop_getplayer = self._checkbox(opt_frame, "Use getPlayer() targeting  (all / me / others / friends / team / random)")

        # Info box showing IY special keywords
        info = tk.Frame(left, bg=BG2)
        info.pack(fill="x", pady=(0,8))
        tk.Label(info, text="IY Player Keywords", font=FONT_SM, fg=ACCENT, bg=BG2,
                 anchor="w").pack(fill="x", padx=6, pady=(4,2))
        keywords = [
            ("me",      "The speaker"),
            ("all",     "Every player"),
            ("others",  "Everyone except speaker"),
            ("random",  "One random player"),
            ("friends", "Speaker's friends"),
            ("team",    "Speaker's team"),
        ]
        for kw, desc in keywords:
            row = tk.Frame(info, bg=BG2)
            row.pack(fill="x", padx=6, pady=1)
            tk.Label(row, text=kw, font=(FONT_SM[0], FONT_SM[1], "bold"),
                     fg=CYAN, bg=BG2, width=10, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, anchor="w").pack(side="left")
        tk.Frame(info, bg=BG2, height=4).pack()

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(4,0))
        self._btn(btn_row, "⚡  GENERATE", self._do_loop, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR", self._clear_loop, BG3).pack(side="left")

        self._label(right, "OUTPUT")
        self._loop_out = self._text_area(right, height=30, expand=True)
        self._loop_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._loop_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._loop_out), BG3).pack(side="left")

    def _do_loop(self):
        name = self._loop_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Command name required.")
            return
        aliases   = [a.strip() for a in self._loop_alias.get().split(",") if a.strip()]
        loop_body = self._loop_body.get("1.0", "end-1c")
        stop_body = self._loop_stop.get("1.0", "end-1c")
        try:
            delay = float(self._loop_delay.get().strip())
        except Exception:
            delay = 0.1
        result = generate_loop_cmd(
            name, aliases, loop_body, stop_body,
            delay, self._loop_getplayer.get()
        )
        self._set_output(self._loop_out, result)

    def _clear_loop(self):
        self._loop_name.set("")
        self._loop_alias.set("")
        self._loop_delay.set("0.1")
        self._loop_body.delete("1.0", "end")
        self._loop_stop.delete("1.0", "end")
        self._set_output(self._loop_out, "")

    # ── Page: Module ─────────────────────────────────────────────────────────

    def _build_module_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=380)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(left, "MODULE NAME")
        self._mod_name = tk.StringVar()
        self._entry(left, self._mod_name, placeholder="e.g. Aimbot")

        # Style selector
        self._label(left, "OUTPUT STYLE")
        style_row = tk.Frame(left, bg=BG)
        style_row.pack(fill="x", pady=(0, 8))
        self._mod_style = tk.StringVar(value="Modules")

        tk.Radiobutton(
            style_row, text="Modules.X:Initialize()", variable=self._mod_style,
            value="Modules", font=FONT_SM, fg=CYAN, bg=BG, selectcolor=BG2,
            activebackground=BG, activeforeground=CYAN,
            highlightthickness=0, cursor="hand2"
        ).pack(side="left", padx=(0, 12))

        tk.Radiobutton(
            style_row, text="RegisterCommand", variable=self._mod_style,
            value="Register", font=FONT_SM, fg=YELLOW, bg=BG, selectcolor=BG2,
            activebackground=BG, activeforeground=YELLOW,
            highlightthickness=0, cursor="hand2"
        ).pack(side="left", padx=(0, 12))

        tk.Radiobutton(
            style_row, text="RegisterCommandDual", variable=self._mod_style,
            value="Dual", font=FONT_SM, fg=GREEN, bg=BG, selectcolor=BG2,
            activebackground=BG, activeforeground=GREEN,
            highlightthickness=0, cursor="hand2"
        ).pack(side="left")

        # Style hint label
        self._mod_style_hint = tk.Label(left, text="", font=("Consolas", 8),
                                        fg=SUBTEXT, bg=BG, anchor="w", wraplength=340, justify="left")
        self._mod_style_hint.pack(fill="x", pady=(0, 6))

        def _update_hint(*_):
            s = self._mod_style.get()
            if s == "Modules":
                self._mod_style_hint.configure(
                    text="Modules.Name = {} → :Initialize() → addcmd() wrappers",
                    fg=CYAN)
            elif s == "Register":
                self._mod_style_hint.configure(
                    text="RegisterCommand({Name,Aliases,Description,...}, func) — bare, no Modules table",
                    fg=YELLOW)
            else:
                self._mod_style_hint.configure(
                    text="RegisterCommandDual — registers in both ZukaPanel and addcmd systems simultaneously",
                    fg=GREEN)
        self._mod_style.trace_add("write", _update_hint)
        _update_hint()

        self._label(left, "COMMANDS  (one per line: name|alias1,alias2)")
        self._mod_cmds = self._text_area(left, height=10)
        self._mod_cmds.insert("1.0", "fly|noclip,f\nnofly|unfly")

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(6,0))
        self._btn(btn_row, "⚡  GENERATE", self._do_module, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR", self._clear_module, BG3).pack(side="left")

        self._label(right, "OUTPUT")
        self._mod_out = self._text_area(right, height=30, expand=True)
        self._mod_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._mod_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._mod_out), BG3).pack(side="left")

    def _do_module(self):
        mod_name = self._mod_name.get().strip()
        if not mod_name:
            messagebox.showwarning("Missing", "Module name required.")
            return
        raw_cmds = self._mod_cmds.get("1.0", "end-1c").strip().split("\n")
        cmds = []
        for line in raw_cmds:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            name = parts[0].strip()
            aliases = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
            cmds.append({"name": name, "aliases": aliases})

        style = self._mod_style.get()
        if style == "Register":
            result = generate_module_register(mod_name, cmds)
        elif style == "Dual":
            result = generate_module_dual(mod_name, cmds)
        else:
            result = generate_module(mod_name, cmds)

        self._set_output(self._mod_out, result)

    def _clear_module(self):
        self._mod_name.set("")
        self._mod_cmds.delete("1.0", "end")
        self._set_output(self._mod_out, "")

    # ── Page: Templates ──────────────────────────────────────────────────────

    TEMPLATES = {
        "Basic Command": (
            'addcmd("commandname", {"alias"}, function(args, speaker)\n'
            '    DoNotif("Command fired by " .. speaker.Name, 2)\n'
            'end)'
        ),
        "getPlayer Loop": (
            'addcmd("commandname", {"alias"}, function(args, speaker)\n'
            '    local targets = getPlayer(args[1], speaker)\n'
            '    if #targets == 0 then return DoNotif("No players found.", 2) end\n'
            '    for _, plr in ipairs(targets) do\n'
            '        -- do something with plr\n'
            '        DoNotif("Applied to: " .. plr.Name, 2)\n'
            '    end\n'
            'end)'
        ),
        "Toggle with Heartbeat": (
            'do\n'
            '    local cmdEnabled = false\n'
            '    local cmdConn\n\n'
            '    addcmd("commandname", {"alias"}, function(args, speaker)\n'
            '        cmdEnabled = not cmdEnabled\n'
            '        if cmdEnabled then\n'
            '            cmdConn = RunService.Heartbeat:Connect(function()\n'
            '                -- loop body\n'
            '            end)\n'
            '            DoNotif("commandname: ENABLED", 2)\n'
            '        else\n'
            '            if cmdConn then cmdConn:Disconnect() cmdConn = nil end\n'
            '            DoNotif("commandname: DISABLED", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Remote FireServer": (
            'do\n'
            '    local Remote = game:GetService("ReplicatedStorage"):WaitForChild("RemoteName")\n\n'
            '    addcmd("commandname", {"alias"}, function(args, speaker)\n'
            '        local targets = getPlayer(args[1], speaker)\n'
            '        for _, plr in ipairs(targets) do\n'
            '            pcall(function()\n'
            '                Remote:FireServer(plr)\n'
            '            end)\n'
            '        end\n'
            '        DoNotif("Fired remote for " .. #targets .. " players.", 2)\n'
            '    end)\n'
            'end'
        ),
        "Character Teleport": (
            'addcmd("tp", {"teleport"}, function(args, speaker)\n'
            '    local target = getPlayer(args[1], speaker)[1]\n'
            '    if not target or not target.Character then\n'
            '        return DoNotif("Target not found.", 2)\n'
            '    end\n'
            '    local myRoot = speaker.Character and speaker.Character:FindFirstChild("HumanoidRootPart")\n'
            '    local tRoot  = target.Character:FindFirstChild("HumanoidRootPart")\n'
            '    if myRoot and tRoot then\n'
            '        myRoot.CFrame = tRoot.CFrame * CFrame.new(0, 0, -3)\n'
            '        DoNotif("Teleported to " .. target.Name, 2)\n'
            '    end\n'
            'end)'
        ),
        "Keybind addbind": (
            '-- Toggle fly on G key\n'
            'addbind("fly", "Enum.KeyCode.G", false, "nofly")\n\n'
            '-- Fire command on Left click\n'
            'addbind("commandname", "LeftClick", false)\n\n'
            '-- Fire on key release\n'
            'addbind("commandname", "Enum.KeyCode.F", true)'
        ),
        # ── Character / Player ───────────────────────────────────────────────
        "Fly Toggle": (
            'do\n'
            '    local flyEnabled = false\n'
            '    local flyConn\n'
            '    local bodyVel, bodyGyro\n\n'
            '    local function enableFly(char)\n'
            '        local root = char:FindFirstChild("HumanoidRootPart")\n'
            '        if not root then return end\n'
            '        bodyVel = Instance.new("BodyVelocity", root)\n'
            '        bodyVel.MaxForce = Vector3.new(1e9,1e9,1e9)\n'
            '        bodyVel.Velocity = Vector3.zero\n'
            '        bodyGyro = Instance.new("BodyGyro", root)\n'
            '        bodyGyro.MaxTorque = Vector3.new(1e9,1e9,1e9)\n'
            '        bodyGyro.P = 1e6\n'
            '        local cam = workspace.CurrentCamera\n'
            '        local speed = 50\n'
            '        local UIS = game:GetService("UserInputService")\n'
            '        flyConn = game:GetService("RunService").Heartbeat:Connect(function()\n'
            '            local dir = Vector3.zero\n'
            '            if UIS:IsKeyDown(Enum.KeyCode.W) then dir = dir + cam.CFrame.LookVector end\n'
            '            if UIS:IsKeyDown(Enum.KeyCode.S) then dir = dir - cam.CFrame.LookVector end\n'
            '            if UIS:IsKeyDown(Enum.KeyCode.A) then dir = dir - cam.CFrame.RightVector end\n'
            '            if UIS:IsKeyDown(Enum.KeyCode.D) then dir = dir + cam.CFrame.RightVector end\n'
            '            if UIS:IsKeyDown(Enum.KeyCode.Space) then dir = dir + Vector3.yAxis end\n'
            '            if UIS:IsKeyDown(Enum.KeyCode.LeftShift) then dir = dir - Vector3.yAxis end\n'
            '            bodyVel.Velocity = dir.Magnitude > 0 and dir.Unit * speed or Vector3.zero\n'
            '            bodyGyro.CFrame = cam.CFrame\n'
            '        end)\n'
            '    end\n\n'
            '    local function disableFly(char)\n'
            '        if flyConn then flyConn:Disconnect() flyConn = nil end\n'
            '        if bodyVel then bodyVel:Destroy() bodyVel = nil end\n'
            '        if bodyGyro then bodyGyro:Destroy() bodyGyro = nil end\n'
            '        local hum = char and char:FindFirstChildOfClass("Humanoid")\n'
            '        if hum then hum.PlatformStand = false end\n'
            '    end\n\n'
            '    addcmd("fly", {"noclipfly", "ffly"}, function(args, speaker)\n'
            '        flyEnabled = not flyEnabled\n'
            '        local char = speaker.Character\n'
            '        if not char then return end\n'
            '        if flyEnabled then\n'
            '            local hum = char:FindFirstChildOfClass("Humanoid")\n'
            '            if hum then hum.PlatformStand = true end\n'
            '            enableFly(char)\n'
            '            DoNotif("Fly: ENABLED", 2)\n'
            '        else\n'
            '            disableFly(char)\n'
            '            DoNotif("Fly: DISABLED", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Noclip Toggle": (
            'do\n'
            '    local noclipEnabled = false\n'
            '    local noclipConn\n\n'
            '    addcmd("noclip", {"nc", "ghost"}, function(args, speaker)\n'
            '        noclipEnabled = not noclipEnabled\n'
            '        if noclipEnabled then\n'
            '            noclipConn = game:GetService("RunService").Stepped:Connect(function()\n'
            '                local char = speaker.Character\n'
            '                if not char then return end\n'
            '                for _, part in ipairs(char:GetDescendants()) do\n'
            '                    if part:IsA("BasePart") and part.CanCollide then\n'
            '                        part.CanCollide = false\n'
            '                    end\n'
            '                end\n'
            '            end)\n'
            '            DoNotif("Noclip: ON", 2)\n'
            '        else\n'
            '            if noclipConn then noclipConn:Disconnect() noclipConn = nil end\n'
            '            DoNotif("Noclip: OFF", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Speed Toggle": (
            'do\n'
            '    local origSpeed = 16\n'
            '    local speedEnabled = false\n\n'
            '    addcmd("speed", {"ws", "walkspeed"}, function(args, speaker)\n'
            '        local char = speaker.Character\n'
            '        local hum = char and char:FindFirstChildOfClass("Humanoid")\n'
            '        if not hum then return DoNotif("No humanoid.", 2) end\n\n'
            '        local newSpeed = tonumber(args[1])\n'
            '        if newSpeed then\n'
            '            origSpeed = hum.WalkSpeed\n'
            '            hum.WalkSpeed = newSpeed\n'
            '            DoNotif("Speed set to " .. newSpeed, 2)\n'
            '        else\n'
            '            speedEnabled = not speedEnabled\n'
            '            if speedEnabled then\n'
            '                origSpeed = hum.WalkSpeed\n'
            '                hum.WalkSpeed = 100\n'
            '                DoNotif("Speed: FAST (100)", 2)\n'
            '            else\n'
            '                hum.WalkSpeed = origSpeed\n'
            '                DoNotif("Speed: RESET (" .. origSpeed .. ")", 2)\n'
            '            end\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Infinite Jump": (
            'do\n'
            '    local ijEnabled = false\n'
            '    local ijConn\n\n'
            '    addcmd("ijump", {"infjump", "ij"}, function(args, speaker)\n'
            '        ijEnabled = not ijEnabled\n'
            '        if ijEnabled then\n'
            '            local UIS = game:GetService("UserInputService")\n'
            '            ijConn = UIS.JumpRequest:Connect(function()\n'
            '                local char = speaker.Character\n'
            '                local hum = char and char:FindFirstChildOfClass("Humanoid")\n'
            '                if hum and hum:GetState() ~= Enum.HumanoidStateType.Dead then\n'
            '                    hum:ChangeState(Enum.HumanoidStateType.Jumping)\n'
            '                end\n'
            '            end)\n'
            '            DoNotif("Infinite Jump: ON", 2)\n'
            '        else\n'
            '            if ijConn then ijConn:Disconnect() ijConn = nil end\n'
            '            DoNotif("Infinite Jump: OFF", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Goto / Bring Player": (
            '-- goto <player> teleports you to them; bring <player> brings them to you\n'
            'addcmd("goto", {"goto"}, function(args, speaker)\n'
            '    local target = getPlayer(args[1], speaker)[1]\n'
            '    if not (target and target.Character) then return DoNotif("Player not found.", 2) end\n'
            '    local myRoot = speaker.Character and speaker.Character:FindFirstChild("HumanoidRootPart")\n'
            '    local tRoot  = target.Character:FindFirstChild("HumanoidRootPart")\n'
            '    if myRoot and tRoot then\n'
            '        myRoot.CFrame = tRoot.CFrame * CFrame.new(2, 0, -3)\n'
            '        DoNotif("Went to " .. target.Name, 2)\n'
            '    end\n'
            'end)\n\n'
            'addcmd("bring", {"br"}, function(args, speaker)\n'
            '    local targets = getPlayer(args[1], speaker)\n'
            '    if #targets == 0 then return DoNotif("No players found.", 2) end\n'
            '    local myRoot = speaker.Character and speaker.Character:FindFirstChild("HumanoidRootPart")\n'
            '    if not myRoot then return end\n'
            '    for i, plr in ipairs(targets) do\n'
            '        local root = plr.Character and plr.Character:FindFirstChild("HumanoidRootPart")\n'
            '        if root then\n'
            '            root.CFrame = myRoot.CFrame * CFrame.new(i * 3, 0, -3)\n'
            '        end\n'
            '    end\n'
            '    DoNotif("Brought " .. #targets .. " player(s).", 2)\n'
            'end)'
        ),
        "Fake Lag / Ping Spike": (
            '-- Artificially delays RunService to simulate lag\n'
            'do\n'
            '    local lagEnabled = false\n'
            '    local lagConn\n\n'
            '    addcmd("fakelag", {"lag", "pingspike"}, function(args, speaker)\n'
            '        lagEnabled = not lagEnabled\n'
            '        local delay = tonumber(args[1]) or 0.3  -- seconds\n'
            '        if lagEnabled then\n'
            '            lagConn = game:GetService("RunService").Heartbeat:Connect(function()\n'
            '                local t = tick()\n'
            '                -- Busy-wait to block the thread\n'
            '                while tick() - t < delay do end\n'
            '            end)\n'
            '            DoNotif("Fake Lag: ON (" .. delay .. "s)", 2)\n'
            '        else\n'
            '            if lagConn then lagConn:Disconnect() lagConn = nil end\n'
            '            DoNotif("Fake Lag: OFF", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Keybind Toggle Alias Changer": (
            '-- Dynamically remap a command alias at runtime, or bind toggle to a key\n'
            'do\n'
            '    -- Change an existing command alias on the fly:\n'
            '    addcmd("setalias", {"remap", "alias"}, function(args, speaker)\n'
            '        local cmdName = args[1]\n'
            '        local newAlias = args[2]\n'
            '        if not (cmdName and newAlias) then\n'
            '            return DoNotif("Usage: setalias <cmd> <newalias>", 3)\n'
            '        end\n'
            '        -- addcmd re-registration with extra alias\n'
            '        -- This wraps the existing command under a new name:\n'
            '        addcmd(newAlias, {}, function(a, s)\n'
            '            execCmd(cmdName, s)\n'
            '        end)\n'
            '        DoNotif("Alias added: " .. newAlias .. " -> " .. cmdName, 2)\n'
            '    end)\n\n'
            '    -- Bind any command to a key toggle:\n'
            '    addcmd("bindkey", {"keybind", "kb"}, function(args, speaker)\n'
            '        local key = args[1]   -- e.g. "F", "G", "X"\n'
            '        local cmd = args[2]   -- e.g. "fly"\n'
            '        if not (key and cmd) then\n'
            '            return DoNotif("Usage: bindkey <Key> <cmd>", 3)\n'
            '        end\n'
            '        local keyCode = Enum.KeyCode[key]\n'
            '        if not keyCode then return DoNotif("Invalid key: " .. key, 2) end\n'
            '        addbind(cmd, "Enum.KeyCode." .. key, false)\n'
            '        DoNotif("Bound " .. key .. " -> " .. cmd, 2)\n'
            '    end)\n'
            'end'
        ),
        "Anti-Admin Hook": (
            'do\n'
            '    local conns = {}\n\n'
            '    addcmd("antiadmin", {"blockadmin"}, function(args, speaker)\n'
            '        -- Disconnect existing\n'
            '        for _, c in pairs(conns) do c:Disconnect() end\n'
            '        conns = {}\n\n'
            '        local hdc = game:GetService("ReplicatedStorage"):FindFirstChild("HDAdminHDClient")\n'
            '        if hdc and hdc:FindFirstChild("Signals") then\n'
            '            for _, sigName in ipairs({"ExecuteClientCommand", "ActivateClientCommand"}) do\n'
            '                local s = hdc.Signals:FindFirstChild(sigName)\n'
            '                if s then\n'
            '                    table.insert(conns, s.OnClientEvent:Connect(function(cmd)\n'
            '                        print("[AntiAdmin] Blocked:", tostring(cmd))\n'
            '                    end))\n'
            '                end\n'
            '            end\n'
            '        end\n'
            '        DoNotif("Anti-Admin: ACTIVE", 2)\n'
            '    end)\n'
            'end'
        ),
    }

    def _build_templates_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=220)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(left, "TEMPLATES")

        listbox = tk.Listbox(
            left, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            selectforeground=TEXT, font=FONT_SM, bd=0,
            highlightthickness=1, highlightcolor=BORDER,
            activestyle="none", cursor="hand2",
        )
        listbox.pack(fill="both", expand=True)
        for name in self.TEMPLATES:
            listbox.insert("end", "  " + name)

        self._label(right, "PREVIEW")
        self._tpl_out = self._text_area(right, height=28, expand=True)

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._tpl_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._tpl_out), BG3).pack(side="left")

        def on_select(event):
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0]).strip()
            code = self.TEMPLATES.get(name, "")
            self._tpl_out.configure(state="normal")
            self._tpl_out.delete("1.0", "end")
            self._tpl_out.insert("1.0", code)

        listbox.bind("<<ListboxSelect>>", on_select)

    # ── Widget Helpers ───────────────────────────────────────────────────────

    def _label(self, parent, text):
        tk.Label(parent, text=text, font=FONT_SM, fg=ACCENT,
                 bg=BG, anchor="w").pack(fill="x", pady=(8, 2))

    def _label_frame(self, parent, text):
        tk.Label(parent, text=text, font=FONT_SM, fg=ACCENT,
                 bg=BG, anchor="w").pack(fill="x", padx=14, pady=(8,2))

    def _entry(self, parent, var, placeholder=""):
        e = tk.Entry(parent, textvariable=var, font=FONT_UI,
                     bg=BG2, fg=TEXT, insertbackground=CYAN,
                     bd=0, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER)
        e.pack(fill="x", ipady=5)
        if placeholder and not var.get():
            e.insert(0, placeholder)
            e.configure(fg=SUBTEXT)
            def on_focus_in(ev):
                if e.get() == placeholder:
                    e.delete(0, "end")
                    e.configure(fg=TEXT)
            def on_focus_out(ev):
                if not e.get():
                    e.insert(0, placeholder)
                    e.configure(fg=SUBTEXT)
            e.bind("<FocusIn>", on_focus_in)
            e.bind("<FocusOut>", on_focus_out)
        return e

    def _text_area(self, parent, height=8, expand=False):
        frame = tk.Frame(parent, bg=BORDER, bd=1)
        if expand:
            frame.pack(fill="both", expand=True)
        else:
            frame.pack(fill="x")

        t = tk.Text(frame, font=("Consolas", 10), bg=BG2, fg=TEXT,
                    insertbackground=CYAN, bd=0, wrap="none",
                    height=height, selectbackground=ACCENT,
                    selectforeground=TEXT, padx=8, pady=6,
                    tabs=("1c",))

        vsb = tk.Scrollbar(frame, orient="vertical", command=t.yview,
                           bg=BG2, troughcolor=BG2, bd=0, width=8)
        hsb = tk.Scrollbar(frame, orient="horizontal", command=t.xview,
                           bg=BG2, troughcolor=BG2, bd=0, width=8)
        t.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        t.pack(fill="both", expand=True)

        # Syntax-ish highlighting (basic keywords)
        t.tag_configure("kw",    foreground="#cc99ff")
        t.tag_configure("str",   foreground="#99dd66")
        t.tag_configure("fn",    foreground=CYAN)
        t.tag_configure("zuka",    foreground=YELLOW)
        t.tag_configure("exploit", foreground="#ab54f7")  # purple for exploit APIs
        t.tag_configure("cmt",   foreground=SUBTEXT)
        t.tag_configure("num",   foreground="#ff9966")

        def highlight(event=None):
            t.tag_remove("kw", "1.0", "end")
            t.tag_remove("str", "1.0", "end")
            t.tag_remove("fn", "1.0", "end")
            t.tag_remove("zuka", "1.0", "end")
            t.tag_remove("cmt", "1.0", "end")
            t.tag_remove("num", "1.0", "end")
            content = t.get("1.0", "end")
            for match in re.finditer(r'\b(local|function|end|if|then|else|elseif|for|while|do|return|not|and|or|true|false|nil|in|pairs|ipairs|repeat|until|break)\b', content):
                s = f"1.0+{match.start()}c"
                e2 = f"1.0+{match.end()}c"
                t.tag_add("kw", s, e2)
            for match in re.finditer(r'"[^"]*"|\'[^\']*\'', content):
                t.tag_add("str", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
            # Zuka/Roblox APIs (yellow)
            for match in re.finditer(
                r'\b(addcmd|execCmd|DoNotif|getPlayer|addbind|removecmd|removebind|'
                r'RegisterCommand|RegisterCommandDual|NotificationManager|Utilities|'
                r'game|workspace|Workspace|math|string|table|task|Enum|Instance|CFrame|Vector3|Vector2|Color3|UDim|UDim2|'
                r'TweenService|LogService|UserInputService|ReplicatedStorage|HttpService|RunService|'
                r'Players|LocalPlayer|PlayerMouse|CurrentCamera|Lighting|Debris|CoreGui|StarterGui|'
                r'ContentProvider|TeleportService|TextChatService|MarketplaceService|PathfindingService|CollectionService|'
                r'pcall|xpcall|pairs|ipairs|setmetatable|getmetatable|rawget|rawset|rawequal|select|unpack|type|typeof|tostring|tonumber)\b',
                content):
                t.tag_add("zuka", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
            # Exploit-only APIs (purple)
            for match in re.finditer(
                r'\b(hookmetamethod|hookfunction|getnamecallmethod|getgc|filtergc|Drawing|'
                r'getgenv|getsenv|getrenv|getfenv|setfenv|setclipboard|getclipboard|'
                r'decompile|saveinstance|getrawmetatable|setrawmetatable|checkcaller|'
                r'cloneref|clonefunction|iscclosure|islclosure|isexecutorclosure|newcclosure|getfunctionhash|'
                r'writefile|appendfile|loadfile|readfile|listfiles|makefolder|isfolder|isfile|delfile|delfolder|'
                r'getcustomasset|fireclickdetector|firetouchinterest|fireproximityprompt|'
                r'setupvalue|getupvalues|get_gc_objects|identifyexecutor|getexecutorname|'
                r'set_ro|get_mt|hook_meta|new_ccl|check_caller|clone_func|'
                r'crypt|syn|rconsole|rconsoleclear)\b',
                content):
                t.tag_add("exploit", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
            for match in re.finditer(r'--[^\n]*', content):
                t.tag_add("cmt", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
            for match in re.finditer(r'\b\d+\.?\d*\b', content):
                t.tag_add("num", f"1.0+{match.start()}c", f"1.0+{match.end()}c")

        t.bind("<KeyRelease>", highlight)
        return t

    def _checkbox(self, parent, text):
        var = tk.BooleanVar()
        cb = tk.Checkbutton(parent, text=text, variable=var,
                            font=FONT_SM, fg=TEXT, bg=BG,
                            selectcolor=BG2, activebackground=BG,
                            activeforeground=TEXT,
                            highlightthickness=0, cursor="hand2")
        cb.pack(anchor="w")
        return var

    def _btn(self, parent, text, command, color=ACCENT):
        b = tk.Button(
            parent, text=text, font=FONT_SM,
            bg=color, fg=TEXT, bd=0,
            activebackground=ACCENT2, activeforeground=TEXT,
            cursor="hand2", padx=12, pady=5,
            command=command,
        )
        return b

    def _set_output(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _copy(self, widget):
        text = widget.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("Empty", "Nothing to copy.")
            return
        if self._clip_ok:
            try:
                pyperclip.copy(text)
                messagebox.showinfo("Copied", "Copied to clipboard!")
            except Exception:
                self._fallback_copy(text)
        else:
            self._fallback_copy(text)

    def _fallback_copy(self, text):
        win = tk.Toplevel(self)
        win.title("Copy this")
        win.configure(bg=BG)
        tk.Label(win, text="pyperclip not available — select all & copy:",
                 font=FONT_SM, fg=SUBTEXT, bg=BG).pack(padx=10, pady=(10,4))
        t = tk.Text(win, font=FONT_UI, bg=BG2, fg=TEXT, width=80, height=20)
        t.pack(padx=10, pady=(0,10))
        t.insert("1.0", text)
        t.focus()
        t.tag_add("sel", "1.0", "end")

    def _save(self, widget):
        text = widget.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("Empty", "Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".lua",
            filetypes=[("Lua files", "*.lua"), ("All files", "*.*")],
            initialfile="zuka_commands.lua"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")


    # ── Page: Dex Integration ────────────────────────────────────────────────

    DEX_SNIPPETS = {
        "Open Dex Explorer": (
            'addcmd("dex", {"explorer", "opendex"}, function(args, speaker)\n'
            '    -- Load and open Dex Explorer (Zex)\n'
            '    local ok, err = pcall(function()\n'
            '        loadstring(game:HttpGet("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Zex.lua"))()\n'
            '    end)\n'
            '    if not ok then\n'
            '        DoNotif("Dex failed: " .. tostring(err), 3)\n'
            '    else\n'
            '        DoNotif("Dex opened!", 2)\n'
            '    end\n'
            'end)'
        ),
        "Decompile Clicked Script": (
            '-- Right-click any LocalScript/ModuleScript in Explorer and run this\n'
            'addcmd("decompile", {"dc", "decomp"}, function(args, speaker)\n'
            '    local target = game:GetService("Selection"):Get()[1]\n'
            '    if not target or not (target:IsA("LocalScript") or target:IsA("ModuleScript") or target:IsA("Script")) then\n'
            '        return DoNotif("Select a script first.", 2)\n'
            '    end\n'
            '    local ok, src = pcall(decompile, target)\n'
            '    if ok and src and #src > 0 then\n'
            '        setclipboard(src)\n'
            '        DoNotif("Decompiled & copied: " .. target.Name, 2)\n'
            '    else\n'
            '        DoNotif("Decompile failed.", 2)\n'
            '    end\n'
            'end)'
        ),
        "Dump All RemoteEvents": (
            'addcmd("dumpremotes", {"remotes", "listremotes"}, function(args, speaker)\n'
            '    local results = {}\n'
            '    local function scan(obj, path)\n'
            '        for _, child in ipairs(obj:GetChildren()) do\n'
            '            local p = path .. "." .. child.Name\n'
            '            if child:IsA("RemoteEvent") or child:IsA("RemoteFunction") or child:IsA("BindableEvent") then\n'
            '                table.insert(results, child.ClassName .. ": " .. p)\n'
            '            end\n'
            '            scan(child, p)\n'
            '        end\n'
            '    end\n'
            '    scan(game:GetService("ReplicatedStorage"), "ReplicatedStorage")\n'
            '    scan(game:GetService("ReplicatedFirst"), "ReplicatedFirst")\n'
            '    local out = table.concat(results, "\\n")\n'
            '    setclipboard(out)\n'
            '    DoNotif("Dumped " .. #results .. " remotes — copied!", 2)\n'
            '    print(out)\n'
            'end)'
        ),
        "Hook Remote + Log Args": (
            'do\n'
            '    local hookedRemotes = {}\n\n'
            '    addcmd("hookremote", {"hr", "watchremote"}, function(args, speaker)\n'
            '        local remotePath = args[1]\n'
            '        if not remotePath then return DoNotif("Usage: hookremote <name>", 2) end\n\n'
            '        -- Search ReplicatedStorage for matching remote\n'
            '        local function findRemote(name, parent)\n'
            '            for _, v in ipairs(parent:GetDescendants()) do\n'
            '                if v.Name:lower() == name:lower() and\n'
            '                   (v:IsA("RemoteEvent") or v:IsA("RemoteFunction")) then\n'
            '                    return v\n'
            '                end\n'
            '            end\n'
            '        end\n\n'
            '        local remote = findRemote(remotePath, game:GetService("ReplicatedStorage"))\n'
            '        if not remote then return DoNotif("Remote not found: " .. remotePath, 2) end\n\n'
            '        -- Hook FireServer\n'
            '        local orig = hookmetamethod(game, "__namecall", function(self, ...)\n'
            '            local method = getnamecallmethod()\n'
            '            if self == remote and (method == "FireServer" or method == "InvokeServer") then\n'
            '                local argList = {...}\n'
            '                local strs = {}\n'
            '                for i, v in ipairs(argList) do\n'
            '                    strs[i] = tostring(v)\n'
            '                end\n'
            '                print("[HookRemote] " .. remote.Name .. " fired: " .. table.concat(strs, ", "))\n'
            '                DoNotif("[HR] " .. remote.Name .. " fired!", 1.5)\n'
            '            end\n'
            '            return orig(self, ...)\n'
            '        end)\n'
            '        table.insert(hookedRemotes, orig)\n'
            '        DoNotif("Now hooking: " .. remote.Name, 2)\n'
            '    end)\n'
            'end'
        ),
        "Module Poisoning Template": (
            '-- Poison a ModuleScript so any future require() returns your data\n'
            'addcmd("poison", {"poisonmod", "hookmodule"}, function(args, speaker)\n'
            '    local modName = args[1]\n'
            '    if not modName then return DoNotif("Usage: poison <ModuleName>", 2) end\n\n'
            '    local function findModule(name, root)\n'
            '        for _, v in ipairs(root:GetDescendants()) do\n'
            '            if v:IsA("ModuleScript") and v.Name:lower() == name:lower() then\n'
            '                return v\n'
            '            end\n'
            '        end\n'
            '    end\n\n'
            '    local mod = findModule(modName, game)\n'
            '    if not mod then return DoNotif("Module not found: " .. modName, 2) end\n\n'
            '    local orig = clonefunction(require)\n'
            '    hookfunction(require, newcclosure(function(m, ...)\n'
            '        local result = orig(m, ...)\n'
            '        if m == mod then\n'
            '            print("[Poison] Module " .. modName .. " required — intercepted!")\n'
            '            -- Modify result table here, or return a fake one:\n'
            '            -- return {}\n'
            '        end\n'
            '        return result\n'
            '    end))\n'
            '    DoNotif("Poisoned: " .. modName, 2)\n'
            'end)'
        ),
        "SaveInstance (Rip Game)": (
            'addcmd("rip", {"saveinstance", "ripgame"}, function(args, speaker)\n'
            '    DoNotif("Saving instance... check console.", 3)\n'
            '    task.spawn(function()\n'
            '        local opts = {\n'
            '            SavePlayers    = false,\n'
            '            SaveNonCreatable = true,\n'
            '            IsolateStarterPlayer = true,\n'
            '        }\n'
            '        local ok, err = pcall(saveinstance, game, opts)\n'
            '        if ok then\n'
            '            DoNotif("Save complete!", 2)\n'
            '        else\n'
            '            DoNotif("Save failed: " .. tostring(err), 3)\n'
            '        end\n'
            '    end)\n'
            'end)'
        ),
        "GetGC — Scan Closures": (
            '-- Scan garbage collector for hidden tables/functions matching a name\n'
            'addcmd("gcfind", {"getgc", "scanmem"}, function(args, speaker)\n'
            '    local needle = args[1] and args[1]:lower() or ""\n'
            '    if needle == "" then return DoNotif("Usage: gcfind <keyword>", 2) end\n\n'
            '    local found = 0\n'
            '    for _, v in ipairs(getgc(true)) do\n'
            '        if type(v) == "table" then\n'
            '            for k, _ in pairs(v) do\n'
            '                if tostring(k):lower():find(needle) then\n'
            '                    print("[GCFind] Table key match:", k, "->", tostring(v[k]):sub(1, 80))\n'
            '                    found = found + 1\n'
            '                    if found > 50 then\n'
            '                        DoNotif("50+ results — check console.", 2)\n'
            '                        return\n'
            '                    end\n'
            '                end\n'
            '            end\n'
            '        elseif type(v) == "function" then\n'
            '            local info = debug.getinfo and debug.getinfo(v) or {}\n'
            '            if tostring(info.name or ""):lower():find(needle) then\n'
            '                print("[GCFind] Function match:", tostring(v))\n'
            '                found = found + 1\n'
            '            end\n'
            '        end\n'
            '    end\n'
            '    DoNotif("GCFind done: " .. found .. " matches.", 2)\n'
            'end)'
        ),
        "Hook Metamethod __index": (
            'do\n'
            '    local orig\n'
            '    local logging = false\n\n'
            '    addcmd("hookmeta", {"hookindex", "spyindex"}, function(args, speaker)\n'
            '        logging = not logging\n'
            '        if logging then\n'
            '            orig = hookmetamethod(game, "__index", newcclosure(function(self, key)\n'
            '                -- Filter to interesting keys only:\n'
            '                if type(key) == "string" and key:find("Data") then\n'
            '                    print("[__index spy]", tostring(self), ".", key)\n'
            '                end\n'
            '                return orig(self, key)\n'
            '            end))\n'
            '            DoNotif("__index hook: ENABLED", 2)\n'
            '        else\n'
            '            if orig then\n'
            '                hookmetamethod(game, "__index", orig)\n'
            '                orig = nil\n'
            '            end\n'
            '            DoNotif("__index hook: DISABLED", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Spy on __newindex": (
            'do\n'
            '    local orig\n'
            '    local active = false\n\n'
            '    addcmd("spynew", {"newindex", "watchwrite"}, function(args, speaker)\n'
            '        active = not active\n'
            '        if active then\n'
            '            orig = hookmetamethod(game, "__newindex", newcclosure(function(self, key, value)\n'
            '                print("[__newindex]", tostring(self), key, "=", tostring(value))\n'
            '                return orig(self, key, value)\n'
            '            end))\n'
            '            DoNotif("__newindex spy: ON", 2)\n'
            '        else\n'
            '            if orig then hookmetamethod(game, "__newindex", orig) orig = nil end\n'
            '            DoNotif("__newindex spy: OFF", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "LogService Output Capture": (
            '-- Capture all game print/warn/error into a file\n'
            'do\n'
            '    local conn\n'
            '    local log = {}\n\n'
            '    addcmd("capturelog", {"logcap", "dumplog"}, function(args, speaker)\n'
            '        if conn then\n'
            '            conn:Disconnect() conn = nil\n'
            '            local out = table.concat(log, "\\n")\n'
            '            writefile("zuka_log_" .. os.time() .. ".txt", out)\n'
            '            DoNotif("Log saved! " .. #log .. " lines.", 2)\n'
            '            log = {}\n'
            '        else\n'
            '            local LogService = game:GetService("LogService")\n'
            '            conn = LogService.MessageOut:Connect(function(msg, msgType)\n'
            '                local prefix = ({[Enum.MessageType.MessageOutput]="[OUT]",[Enum.MessageType.MessageWarning]="[WRN]",[Enum.MessageType.MessageError]="[ERR]"})[msgType] or "[?]"\n'
            '                table.insert(log, prefix .. " " .. msg)\n'
            '            end)\n'
            '            DoNotif("Log capture: STARTED", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),

        # ── Memory & GC ──────────────────────────────────────────────────────
        "_G / shared Environment Monitor": (
            '-- Toggle monitoring _G and shared for unexpected writes\n'
            'do\n'
            '    local monitorConn\n'
            '    local snapshot = {}\n\n'
            '    local function takeSnapshot()\n'
            '        snapshot = {}\n'
            '        for k, v in pairs(_G) do snapshot[k] = v end\n'
            '        for k, v in pairs(shared) do snapshot["__shared_" .. tostring(k)] = v end\n'
            '    end\n\n'
            '    addcmd("gwatch", {"watchg", "envmonitor"}, function(args, speaker)\n'
            '        if monitorConn then\n'
            '            task.cancel(monitorConn)\n'
            '            monitorConn = nil\n'
            '            DoNotif("_G monitor: OFF", 2)\n'
            '            return\n'
            '        end\n\n'
            '        takeSnapshot()\n'
            '        monitorConn = task.spawn(function()\n'
            '            while task.wait(1) do\n'
            '                -- Check _G\n'
            '                for k, v in pairs(_G) do\n'
            '                    local key = tostring(k)\n'
            '                    if snapshot[key] ~= v then\n'
            '                        warn(("[_G CHANGE] \'%s\' %s -> %s"):format(key, tostring(snapshot[key]), tostring(v)))\n'
            '                        snapshot[key] = v\n'
            '                    end\n'
            '                end\n'
            '                for k in pairs(snapshot) do\n'
            '                    if not k:find("^__shared_") and _G[k] == nil then\n'
            '                        warn(("[_G DELETE] \'%s\' was removed"):format(tostring(k)))\n'
            '                        snapshot[k] = nil\n'
            '                    end\n'
            '                end\n'
            '                -- Check shared\n'
            '                for k, v in pairs(shared) do\n'
            '                    local key = "__shared_" .. tostring(k)\n'
            '                    if snapshot[key] ~= v then\n'
            '                        warn(("[shared CHANGE] \'%s\' %s -> %s"):format(tostring(k), tostring(snapshot[key]), tostring(v)))\n'
            '                        snapshot[key] = v\n'
            '                    end\n'
            '                end\n'
            '            end\n'
            '        end)\n'
            '        DoNotif("_G monitor: ON", 2)\n'
            '    end)\n'
            'end'
        ),
        "GC Table Crawler": (
            '-- Crawl GC for tables matching a field/value pattern\n'
            'addcmd("gctable", {"crawlgc", "gctrawl"}, function(args, speaker)\n'
            '    local needle = args[1] and args[1]:lower() or ""\n'
            '    if needle == "" then return DoNotif("Usage: gctable <fieldname>", 2) end\n\n'
            '    local results = {}\n'
            '    for _, obj in ipairs(getgc(true)) do\n'
            '        if type(obj) == "table" then\n'
            '            local ok, val = pcall(function() return rawget(obj, needle) end)\n'
            '            if ok and val ~= nil then\n'
            '                table.insert(results, {tbl=obj, val=val})\n'
            '            end\n'
            '            -- also fuzzy-search keys\n'
            '            for k, v in pairs(obj) do\n'
            '                if tostring(k):lower():find(needle, 1, true) then\n'
            '                    table.insert(results, {tbl=obj, key=k, val=v})\n'
            '                    break\n'
            '                end\n'
            '            end\n'
            '        end\n'
            '        if #results >= 30 then break end\n'
            '    end\n'
            '    for i, r in ipairs(results) do\n'
            '        print(("[GCTable #%d] key=%s val=%s"):format(i, tostring(r.key or needle), tostring(r.val):sub(1,60)))\n'
            '    end\n'
            '    DoNotif("GC crawl: " .. #results .. " hits", 2)\n'
            'end)'
        ),
        "Upvalue Scanner & Patcher": (
            '-- Read or patch an upvalue inside a target function from GC\n'
            'addcmd("upvalue", {"uv", "patchuv"}, function(args, speaker)\n'
            '    local fnName  = args[1]  -- function name to find in GC\n'
            '    local uvIndex = tonumber(args[2]) or 1\n'
            '    local newVal  = args[3]  -- if provided, patch it\n'
            '    if not fnName then return DoNotif("Usage: upvalue <fnName> [index] [newval]", 3) end\n\n'
            '    local found\n'
            '    for _, fn in ipairs(getgc()) do\n'
            '        if type(fn) == "function" then\n'
            '            local info = debug.getinfo and debug.getinfo(fn, "n")\n'
            '            if info and (info.name or ""):lower() == fnName:lower() then\n'
            '                found = fn\n'
            '                break\n'
            '            end\n'
            '        end\n'
            '    end\n'
            '    if not found then return DoNotif("Function not found: " .. fnName, 2) end\n\n'
            '    local ok, name, val = pcall(debug.getupvalue, found, uvIndex)\n'
            '    if not ok then return DoNotif("getupvalue failed", 2) end\n'
            '    print(("[UV] fn=%s idx=%d name=%s val=%s"):format(fnName, uvIndex, tostring(name), tostring(val)))\n\n'
            '    if newVal then\n'
            '        local patchVal = tonumber(newVal) or (newVal == "true") or (newVal ~= "false" and newVal)\n'
            '        pcall(debug.setupvalue, found, uvIndex, patchVal)\n'
            '        DoNotif("Patched upvalue " .. uvIndex .. " = " .. tostring(patchVal), 2)\n'
            '    else\n'
            '        DoNotif(("UV[%d] %s = %s"):format(uvIndex, tostring(name), tostring(val)), 3)\n'
            '    end\n'
            'end)'
        ),
        "Closure Integrity Check": (
            '-- Verify if a function is a native/C closure or has been hooked\n'
            'addcmd("checkfn", {"isfunc", "closurecheck"}, function(args, speaker)\n'
            '    local fnName = args[1]\n'
            '    if not fnName then return DoNotif("Usage: checkfn <globalFnName>", 2) end\n\n'
            '    local fn = getgenv()[fnName] or _G[fnName]\n'
            '    if type(fn) ~= "function" then\n'
            '        return DoNotif(fnName .. " is not a function in env.", 2)\n'
            '    end\n\n'
            '    local results = {}\n'
            '    table.insert(results, "fn: " .. tostring(fn))\n'
            '    table.insert(results, "isC: " .. tostring(iscclosure(fn)))\n'
            '    table.insert(results, "isL: " .. tostring(islclosure(fn)))\n'
            '    table.insert(results, "isExec: " .. tostring(isexecutorclosure(fn)))\n'
            '    local hash = pcall(getfunctionhash, fn) and getfunctionhash(fn) or "N/A"\n'
            '    table.insert(results, "hash: " .. tostring(hash))\n'
            '    print("[CheckFn] " .. fnName .. "\\n" .. table.concat(results, " | "))\n'
            '    DoNotif("CheckFn: " .. fnName .. " — see console", 2)\n'
            'end)'
        ),
        # ── Remote / Network ─────────────────────────────────────────────────
        "Remote Bruteforce Fuzzer": (
            '-- Fire every remote in the game with test args and log responses\n'
            'addcmd("fuzzremotes", {"fuzzer", "rfuzz"}, function(args, speaker)\n'
            '    local testArgs = {nil, true, false, 0, 1, "", "test",\n'
            '        speaker, speaker.Character,\n'
            '        Vector3.zero, CFrame.identity}\n\n'
            '    local remotes = {}\n'
            '    for _, v in ipairs(game:GetDescendants()) do\n'
            '        if v:IsA("RemoteEvent") or v:IsA("RemoteFunction") then\n'
            '            table.insert(remotes, v)\n'
            '        end\n'
            '    end\n\n'
            '    DoNotif("Fuzzing " .. #remotes .. " remotes...", 3)\n'
            '    task.spawn(function()\n'
            '        for _, remote in ipairs(remotes) do\n'
            '            for _, arg in ipairs(testArgs) do\n'
            '                pcall(function()\n'
            '                    if remote:IsA("RemoteEvent") then\n'
            '                        remote:FireServer(arg)\n'
            '                    else\n'
            '                        local res = remote:InvokeServer(arg)\n'
            '                        if res ~= nil then\n'
            '                            print(("[Fuzz] " .. remote:GetFullName() .. " responded: " .. tostring(res)))\n'
            '                        end\n'
            '                    end\n'
            '                end)\n'
            '                task.wait(0.05)\n'
            '            end\n'
            '        end\n'
            '        DoNotif("Fuzz complete!", 2)\n'
            '    end)\n'
            'end)'
        ),
        "Remote Spy (namecall hook)": (
            '-- Full remote spy via __namecall — logs every FireServer/InvokeServer\n'
            'do\n'
            '    local spyEnabled = false\n'
            '    local orig\n'
            '    local blacklist = {}  -- add remote names to mute: blacklist["noisyRemote"] = true\n\n'
            '    addcmd("rspy", {"remotespy", "spy"}, function(args, speaker)\n'
            '        spyEnabled = not spyEnabled\n'
            '        if spyEnabled then\n'
            '            orig = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)\n'
            '                local method = getnamecallmethod()\n'
            '                if (method == "FireServer" or method == "InvokeServer") and\n'
            '                   (self:IsA("RemoteEvent") or self:IsA("RemoteFunction")) and\n'
            '                   not blacklist[self.Name] then\n'
            '                    local argList = {...}\n'
            '                    local strs = {}\n'
            '                    for i, v in ipairs(argList) do\n'
            '                        strs[i] = typeof(v) .. "(" .. tostring(v) .. ")"\n'
            '                    end\n'
            '                    print(("[RemoteSpy] %s:%s(%s)"):format(\n'
            '                        self:GetFullName(), method, table.concat(strs, ", ")))\n'
            '                end\n'
            '                return orig(self, ...)\n'
            '            end))\n'
            '            DoNotif("Remote Spy: ON", 2)\n'
            '        else\n'
            '            if orig then hookmetamethod(game, "__namecall", orig) orig = nil end\n'
            '            DoNotif("Remote Spy: OFF", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Block Specific Remote": (
            '-- Intercept and block a named remote from firing to server\n'
            'do\n'
            '    local blocked = {}\n'
            '    local orig\n'
            '    local active = false\n\n'
            '    local function ensureHook()\n'
            '        if active then return end\n'
            '        active = true\n'
            '        orig = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)\n'
            '            local method = getnamecallmethod()\n'
            '            if blocked[self.Name] and\n'
            '               (method == "FireServer" or method == "InvokeServer") then\n'
            '                warn("[BlockRemote] Blocked: " .. self:GetFullName())\n'
            '                return  -- drop the call\n'
            '            end\n'
            '            return orig(self, ...)\n'
            '        end))\n'
            '    end\n\n'
            '    addcmd("blockremote", {"br", "silenceremote"}, function(args, speaker)\n'
            '        local name = args[1]\n'
            '        if not name then return DoNotif("Usage: blockremote <RemoteName>", 2) end\n'
            '        if blocked[name] then\n'
            '            blocked[name] = nil\n'
            '            DoNotif("Unblocked: " .. name, 2)\n'
            '        else\n'
            '            blocked[name] = true\n'
            '            ensureHook()\n'
            '            DoNotif("Blocking: " .. name, 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Replay Last Remote Call": (
            '-- Capture the last FireServer call and replay it on demand\n'
            'do\n'
            '    local lastCall = nil\n'
            '    local orig\n\n'
            '    orig = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)\n'
            '        local method = getnamecallmethod()\n'
            '        if method == "FireServer" and self:IsA("RemoteEvent") then\n'
            '            lastCall = {remote = self, args = {...}}\n'
            '        end\n'
            '        return orig(self, ...)\n'
            '    end))\n\n'
            '    addcmd("replay", {"refire", "repeatremote"}, function(args, speaker)\n'
            '        if not lastCall then return DoNotif("No call captured yet.", 2) end\n'
            '        local count = tonumber(args[1]) or 1\n'
            '        for i = 1, count do\n'
            '            pcall(function()\n'
            '                lastCall.remote:FireServer(table.unpack(lastCall.args))\n'
            '            end)\n'
            '            if count > 1 then task.wait(0.05) end\n'
            '        end\n'
            '        DoNotif("Replayed " .. count .. "x: " .. lastCall.remote.Name, 2)\n'
            '    end)\n'
            'end'
        ),
        # ── Identity / Metatable ─────────────────────────────────────────────
        "Identity Spoof (setidentity)": (
            '-- Temporarily elevate script identity level for privileged API access\n'
            'addcmd("setid", {"identity", "elevate"}, function(args, speaker)\n'
            '    local level = tonumber(args[1]) or 7\n'
            '    local ok, err = pcall(setidentity, level)\n'
            '    if ok then\n'
            '        DoNotif("Identity set to " .. level, 2)\n'
            '        print("[Identity] Current level:", identifyexecutor and identifyexecutor() or "unknown")\n'
            '    else\n'
            '        DoNotif("setidentity failed: " .. tostring(err), 3)\n'
            '    end\n'
            'end)'
        ),
        "Metatable Lock Bypass": (
            '-- Read a locked/protected table by bypassing __index restrictions\n'
            'addcmd("readmeta", {"metamread", "bypassmt"}, function(args, speaker)\n'
            '    local objName = args[1]\n'
            '    local propName = args[2]\n'
            '    if not (objName and propName) then\n'
            '        return DoNotif("Usage: readmeta <global> <prop>", 2)\n'
            '    end\n\n'
            '    local obj = getgenv()[objName] or _G[objName]\n'
            '    if not obj then return DoNotif("Object not found: " .. objName, 2) end\n\n'
            '    -- rawget bypasses __index metamethods\n'
            '    local rawVal = rawget(obj, propName)\n'
            '    -- Also try getrawmetatable to peek at hidden fields\n'
            '    local mt = getrawmetatable(obj)\n'
            '    local mtVal = mt and rawget(mt, propName)\n\n'
            '    print(("[ReadMeta] rawget:", tostring(rawVal)))\n'
            '    print(("[ReadMeta] metatable[" .. propName .. "]:", tostring(mtVal)))\n'
            '    DoNotif("ReadMeta: check console", 2)\n'
            'end)'
        ),
        "Freeze Metatable (__newindex block)": (
            '-- Freeze a table so writes to it are silently dropped\n'
            'addcmd("freezetable", {"freeze", "locktable"}, function(args, speaker)\n'
            '    local objName = args[1]\n'
            '    if not objName then return DoNotif("Usage: freezetable <globalName>", 2) end\n\n'
            '    local obj = getgenv()[objName] or _G[objName]\n'
            '    if type(obj) ~= "table" then return DoNotif("Not a table: " .. objName, 2) end\n\n'
            '    local mt = getrawmetatable(obj) or {}\n'
            '    -- setrawmetatable bypasses __metatable lock\n'
            '    mt.__newindex = newcclosure(function(t, k, v)\n'
            '        warn(("[Freeze] Write blocked: %s.%s = %s"):format(objName, tostring(k), tostring(v)))\n'
            '        -- do nothing — drop the write\n'
            '    end)\n'
            '    mt.__index = mt.__index or obj  -- preserve reads\n'
            '    setrawmetatable(obj, mt)\n'
            '    DoNotif("Frozen: " .. objName, 2)\n'
            'end)'
        ),
        "Spoof Instance ClassName": (
            '-- Make an instance report a fake ClassName via __index hook on its metatable\n'
            'addcmd("spoofinst", {"faketype", "classname"}  , function(args, speaker)\n'
            '    -- Usage: select an instance in Explorer, then run this\n'
            '    local fakeClass = args[1] or "Script"\n\n'
            '    -- Get the selected instance from Dex/Explorer selection\n'
            '    local target = game:GetService("Selection"):Get()[1]\n'
            '    if not target then return DoNotif("Select an instance first.", 2) end\n\n'
            '    local mt = getrawmetatable(target)\n'
            '    if not mt then return DoNotif("No metatable accessible.", 2) end\n\n'
            '    local origIndex = mt.__index\n'
            '    setrawmetatable(target, {\n'
            '        __index = newcclosure(function(self, key)\n'
            '            if key == "ClassName" then return fakeClass end\n'
            '            return origIndex(self, key)\n'
            '        end),\n'
            '        __newindex = mt.__newindex,\n'
            '        __namecall = mt.__namecall,\n'
            '    })\n'
            '    DoNotif("Spoofed " .. target.Name .. " as " .. fakeClass, 2)\n'
            'end)'
        ),
        "Infinite Yield Spam": (
            '-- Spam a task indefinitely with configurable delay — useful for stress testing\n'
            'do\n'
            '    local spamThreads = {}\n\n'
            '    addcmd("spam", {"taskspam", "iyspam"}, function(args, speaker)\n'
            '        local cmd    = args[1]  -- command to spam-exec, or leave nil for custom body\n'
            '        local delay  = tonumber(args[2]) or 0.1\n'
            '        local limit  = tonumber(args[3]) or 0   -- 0 = infinite\n\n'
            '        if cmd == "stop" then\n'
            '            for _, t in ipairs(spamThreads) do pcall(task.cancel, t) end\n'
            '            spamThreads = {}\n'
            '            return DoNotif("Spam: STOPPED", 2)\n'
            '        end\n\n'
            '        local count = 0\n'
            '        local thread\n'
            '        thread = task.spawn(function()\n'
            '            while true do\n'
            '                if cmd then\n'
            '                    pcall(execCmd, cmd, speaker)\n'
            '                else\n'
            '                    -- Replace with your own action:\n'
            '                    print("[spam] tick", count)\n'
            '                end\n'
            '                count = count + 1\n'
            '                if limit > 0 and count >= limit then break end\n'
            '                task.wait(delay)\n'
            '            end\n'
            '            DoNotif("Spam done: " .. count .. "x", 2)\n'
            '        end)\n'
            '        table.insert(spamThreads, thread)\n'
            '        DoNotif("Spam started (" .. (limit>0 and limit.."x" or "inf") .. ", " .. delay .. "s)", 2)\n'
            '    end)\n'
            'end'
        ),
        "Anti-Fling  (all players)": (
            '-- Prevents other players from flinging your character\n'
            '-- Zeros velocity/rotVelocity and disables collide on others every Stepped\n'
            'do\n'
            '    local antiFlingConn\n'
            '    local antiFlingOn = false\n\n'
            '    addcmd("antifling", {"af", "nofling"}, function(args, speaker)\n'
            '        antiFlingOn = not antiFlingOn\n'
            '        if antiFlingOn then\n'
            '            antiFlingConn = game:GetService("RunService").Stepped:Connect(function()\n'
            '                for _, plr in next, game:GetService("Players"):GetPlayers() do\n'
            '                    if plr ~= speaker and plr.Character then\n'
            '                        pcall(function()\n'
            '                            for _, v in next, plr.Character:GetChildren() do\n'
            '                                if v:IsA("BasePart") and v.CanCollide then\n'
            '                                    v.CanCollide = false\n'
            '                                    if v.Name == "Torso" then v.Massless = true end\n'
            '                                    v.Velocity    = Vector3.new()\n'
            '                                    v.RotVelocity = Vector3.new()\n'
            '                                end\n'
            '                            end\n'
            '                        end)\n'
            '                    end\n'
            '                end\n'
            '            end)\n'
            '            DoNotif("Anti-Fling: ON", 2)\n'
            '        else\n'
            '            if antiFlingConn then antiFlingConn:Disconnect() antiFlingConn = nil end\n'
            '            DoNotif("Anti-Fling: OFF", 2)\n'
            '        end\n'
            '    end)\n'
            'end'
        ),
        "Disable TouchInterests  (server replication)": (
            '-- Disables all serverside .Touched events — replicates to server\n'
            '-- Made by AnthonyIsntHere\n'
            'for _, x in next, workspace:GetDescendants() do\n'
            '    if x:IsA("TouchTransmitter") then\n'
            '        x:Destroy()\n'
            '    elseif x:IsA("BasePart") and (x.CanTouch or x.CanQuery) then\n'
            '        x.CanTouch, x.CanQuery = false, false\n'
            '    end\n'
            'end\n'
            'workspace.DescendantAdded:Connect(function(x)\n'
            '    if x:IsA("TouchTransmitter") then\n'
            '        repeat task.wait() until x:IsDescendantOf(workspace)\n'
            '        x:Destroy()\n'
            '    elseif x:IsA("BasePart") and (x.CanTouch or x.CanQuery) then\n'
            '        x.CanTouch, x.CanQuery = false, false\n'
            '    end\n'
            'end)\n'
            'DoNotif("TouchInterests: DISABLED", 2)'
        ),
        "CFrame Desync  (position spoofer)": (
            '-- CFrame Desync — spoof your visual position away from your real hitbox\n'
            '-- Full standalone module with GUI, pin control, position/rotation modes\n'
            '-- Credits: zuka (@OverZuka)\n'
            'addcmd("desync", {"cfd", "cfdesync"}, function(args, speaker)\n'
            '    local ok, err = pcall(function()\n'
            '        local CFrameDesync = loadstring(game:HttpGet(\n'
            '            "https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Cframe.lua"\n'
            '        ))()\n'
            '        if CFrameDesync then\n'
            '            CFrameDesync:Toggle()\n'
            '            DoNotif("CFrame Desync: TOGGLED", 2)\n'
            '        end\n'
            '    end)\n'
            '    if not ok then DoNotif("Desync load failed: " .. tostring(err):sub(1,50), 3) end\n'
            'end)'
        ),
        "DecalId → ImageId → Hash": (
            '-- Convert a DecalId to its underlying ImageId and content hash\n'
            '-- Credits: AnthonyIsntHere, ou1z\n'
            '-- Requires: syn.request (or http_request)\n'
            'addcmd("decalinfo", {"decal", "imageid"}, function(args, speaker)\n'
            '    local decalId = tonumber(args[1])\n'
            '    if not decalId then return DoNotif("Usage: decalinfo <DecalId>", 2) end\n\n'
            '    local request = syn and syn.request or http_request or request\n'
            '    if not request then return DoNotif("No http request function available.", 3) end\n\n'
            '    task.spawn(function()\n'
            '        DoNotif("Fetching decal info...", 2)\n'
            '        local r1 = request({ Url = "https://assetdelivery.roblox.com/v1/asset/?id=" .. decalId })\n'
            '        local imageId = r1.Body:match("?id=(%d+)")\n'
            '        if not imageId then return DoNotif("Could not resolve ImageId.", 3) end\n\n'
            '        local r2 = request({ Url = "https://assetdelivery.roblox.com/v1/assetId/" .. imageId })\n'
            '        local hash = r2.Body:match("com/(%w+)")\n\n'
            '        local result = "ImageId: " .. imageId .. "\\nHash: " .. (hash or "N/A")\n'
            '        setclipboard(result)\n'
            '        print("[DecalInfo]\\n" .. result)\n'
            '        DoNotif("Copied! ImageId: " .. imageId, 3)\n'
            '    end)\n'
            'end)'
        ),

    }

    def _build_dex_page(self, parent):
        # Split layout: left = snippet list, right = preview + info
        left = tk.Frame(parent, bg=BG, width=230)
        left.pack(side="left", fill="y", padx=(14, 0), pady=14)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        # Header info
        hdr = tk.Frame(left, bg=BG2)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="🔬 DEX INTEGRATION", font=FONT_TITLE,
                 fg=ACCENT, bg=BG2, anchor="w").pack(fill="x", padx=8, pady=(6,2))
        tk.Label(hdr, text="Snippets using exploit APIs:\nhookmetamethod · getgc · debug.getupvalue\nremote spy · metatable · identity spoof",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2, justify="left", anchor="w").pack(fill="x", padx=8, pady=(0,6))

        self._label(left, "SNIPPETS")

        listbox = tk.Listbox(
            left, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            selectforeground=TEXT, font=FONT_SM, bd=0,
            highlightthickness=1, highlightcolor=BORDER,
            activestyle="none", cursor="hand2",
        )
        listbox.pack(fill="both", expand=True)
        for name in self.DEX_SNIPPETS:
            listbox.insert("end", "  " + name)

        # Right side
        # Small info bar
        info_bar = tk.Frame(right, bg=BG3)
        info_bar.pack(fill="x", pady=(0, 8))
        tk.Label(info_bar,
                 text="⚠  These snippets use exploit-only APIs. Requires hookmetamethod, getgc, decompile, etc. to be available in your executor.",
                 font=FONT_SM, fg=YELLOW, bg=BG3, wraplength=620, justify="left").pack(anchor="w", padx=8, pady=6)

        self._label(right, "PREVIEW")
        self._dex_out = self._text_area(right, height=28, expand=True)

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6, 0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._dex_out), CYAN).pack(side="left", padx=(0, 6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._dex_out), BG3).pack(side="left", padx=(0, 6))
        self._btn(out_btns, "⚡  SEND TO BUILDER", self._dex_to_builder, ACCENT).pack(side="left")

        def on_select(event):
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0]).strip()
            code = self.DEX_SNIPPETS.get(name, "")
            self._dex_out.configure(state="normal")
            self._dex_out.delete("1.0", "end")
            self._dex_out.insert("1.0", code)

        listbox.bind("<<ListboxSelect>>", on_select)
        self._dex_listbox = listbox

    def _dex_to_builder(self):
        """Send Dex snippet to Converter tab for further editing."""
        code = self._dex_out.get("1.0", "end-1c").strip()
        if not code:
            messagebox.showinfo("Empty", "Select a snippet first.")
            return
        # Populate converter input and switch to converter tab
        self._conv_input.delete("1.0", "end")
        self._conv_input.insert("1.0", code)
        # Switch tab
        for name, btn in self._tab_btns.items():
            if "Converter" in name:
                btn.invoke()
                break

    # ── Page: Hub Creator ────────────────────────────────────────────────────

    # Verified loadstring URLs
    LIB_URLS = {
        "Luna":  "https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Luna.lua",
        "Orion": "https://raw.githubusercontent.com/shlexware/Orion/main/source",
    }

    # Official Luna addon tab structure from LUNA-UI-ADDON-MAIN.lua
    LUNA_ADDON_TABS = [
        "Player",      # Spectate, TP to Player, Avatar Morph
        "Teleport",    # Waypoints, Coordinate TP, Quick TPs
        "Anti+",       # Anti-Fling, Character Integrity, Session
        "Movement",    # Fly, Speed, Noclip, Infinite Jump
        "Visual",      # ESP, Fullbright, etc
        "Utility",     # Server info, Chat tools
        "Loadstrings", # Tool loaders by category
        "Aimbot",      # Aimbot controls/checks/visuals
        "Delete Tool", # Part deleter with keybind
        "Mod Poison",  # require() hooks, module patching
        "Scripts",     # Extra exploit scripts
        "Settings",    # Appearance, UI settings
        "Info",        # Game/player info panel
    ]

    def _build_hub_page(self, parent):
        self._hub_elements = []   # list of dicts: {kind, label, desc, cmd, args, options, flag}

        # ── Left: settings + element builder ─────────────────────────────────
        left = tk.Frame(parent, bg=BG, width=370)
        left.pack(side="left", fill="y", padx=(14, 0), pady=14)
        left.pack_propagate(False)

        # Library picker
        self._label(left, "UI LIBRARY")
        lib_row = tk.Frame(left, bg=BG)
        lib_row.pack(fill="x", pady=(0, 8))
        self._hub_lib = tk.StringVar(value="Luna")
        for lib in ("Luna", "Orion"):
            col = CYAN if lib == "Luna" else YELLOW
            tk.Radiobutton(lib_row, text=lib, variable=self._hub_lib, value=lib,
                           font=FONT_SM, fg=col, bg=BG, selectcolor=BG2,
                           activebackground=BG, activeforeground=col,
                           highlightthickness=0, cursor="hand2").pack(side="left", padx=(0, 16))

        # Window settings
        self._label(left, "WINDOW SETTINGS")
        ws = tk.Frame(left, bg=BG2)
        ws.pack(fill="x", pady=(0, 8))

        def wrow(label, var, placeholder=""):
            r = tk.Frame(ws, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=TEXT,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)
            if placeholder and not var.get():
                e.insert(0, placeholder)
                e.configure(fg=SUBTEXT)
                def _fi(ev, _e=e, _v=var, _p=placeholder):
                    if _e.get() == _p: _e.delete(0, "end"); _e.configure(fg=TEXT)
                def _fo(ev, _e=e, _v=var, _p=placeholder):
                    if not _e.get(): _e.insert(0, _p); _e.configure(fg=SUBTEXT)
                e.bind("<FocusIn>", _fi); e.bind("<FocusOut>", _fo)
            return var

        self._hub_title   = tk.StringVar(value="Zuka Hub")
        self._hub_intro   = tk.StringVar(value="Welcome!")
        self._hub_config  = tk.StringVar(value="ZukaHub")
        self._hub_intro_en = tk.BooleanVar(value=True)
        self._hub_save_cfg = tk.BooleanVar(value=True)

        wrow("Title:",   self._hub_title)
        wrow("Intro txt:", self._hub_intro)
        wrow("CfgFolder:", self._hub_config)

        flag_row = tk.Frame(ws, bg=BG2)
        flag_row.pack(fill="x", padx=6, pady=(2, 6))
        tk.Checkbutton(flag_row, text="Intro anim", variable=self._hub_intro_en,
                       font=FONT_SM, fg=TEXT, bg=BG2, selectcolor=BG3,
                       activebackground=BG2, highlightthickness=0).pack(side="left", padx=(0, 12))
        tk.Checkbutton(flag_row, text="Save config", variable=self._hub_save_cfg,
                       font=FONT_SM, fg=TEXT, bg=BG2, selectcolor=BG3,
                       activebackground=BG2, highlightthickness=0).pack(side="left")

        # Element kind selector
        self._label(left, "ADD ELEMENT")
        kind_row = tk.Frame(left, bg=BG)
        kind_row.pack(fill="x", pady=(0, 6))
        self._hub_kind = tk.StringVar(value="Button")
        KIND_COLORS = {"Button": CYAN, "Toggle": YELLOW, "Textbox": "#ab54f7", "Dropdown": GREEN}
        for k, col in KIND_COLORS.items():
            tk.Radiobutton(kind_row, text=k, variable=self._hub_kind, value=k,
                           font=FONT_SM, fg=col, bg=BG, selectcolor=BG2,
                           activebackground=BG, activeforeground=col,
                           highlightthickness=0, cursor="hand2",
                           command=self._hub_refresh_form).pack(side="left", padx=(0, 10))

        # Dynamic element form
        self._hub_form_frame = tk.Frame(left, bg=BG2)
        self._hub_form_frame.pack(fill="x", pady=(0, 6))
        self._hub_form_vars = {}
        self._hub_refresh_form()

        add_btn_row = tk.Frame(left, bg=BG)
        add_btn_row.pack(fill="x", pady=(4, 0))
        self._btn(add_btn_row, "➕  ADD ELEMENT", self._hub_add_element, ACCENT).pack(side="left", padx=(0, 6))
        self._btn(add_btn_row, "🗑  CLEAR ALL",
                  lambda: (self._hub_elements.clear(), self._hub_refresh_list()), BG3).pack(side="left")

        # ── Right: element list + output ──────────────────────────────────────
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(right, "ELEMENTS  (drag to reorder — use ↑↓ buttons)")

        list_frame = tk.Frame(right, bg=BORDER, bd=1)
        list_frame.pack(fill="x")
        self._hub_listbox = tk.Listbox(
            list_frame, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            font=FONT_SM, bd=0, highlightthickness=0, activestyle="none",
            height=8
        )
        self._hub_listbox.pack(side="left", fill="both", expand=True)
        lb_vsb = tk.Scrollbar(list_frame, orient="vertical", command=self._hub_listbox.yview,
                              bg=BG2, troughcolor=BG2, bd=0, width=8)
        lb_vsb.pack(side="right", fill="y")
        self._hub_listbox.configure(yscrollcommand=lb_vsb.set)

        lb_ctrl = tk.Frame(right, bg=BG)
        lb_ctrl.pack(fill="x", pady=(4, 8))
        self._btn(lb_ctrl, "↑", self._hub_move_up,   BG3).pack(side="left", padx=(0, 4))
        self._btn(lb_ctrl, "↓", self._hub_move_down, BG3).pack(side="left", padx=(0, 4))
        self._btn(lb_ctrl, "🗑 Remove", self._hub_remove_selected, "#aa2222").pack(side="left")

        self._label(right, "GENERATED OUTPUT")
        self._hub_out = self._text_area(right, height=16, expand=True)
        self._hub_out.configure(state="disabled")

        out_row = tk.Frame(right, bg=BG)
        out_row.pack(fill="x", pady=(6, 0))
        self._btn(out_row, "⚡  GENERATE", self._hub_generate, ACCENT).pack(side="left", padx=(0, 6))
        self._btn(out_row, "📋  COPY", lambda: self._copy(self._hub_out), CYAN).pack(side="left", padx=(0, 6))
        self._btn(out_row, "💾  SAVE", lambda: self._save(self._hub_out), BG3).pack(side="left")

    def _hub_refresh_form(self):
        """Rebuild the element input form based on selected kind."""
        for w in self._hub_form_frame.winfo_children():
            w.destroy()
        self._hub_form_vars = {}
        kind = self._hub_kind.get()
        f = self._hub_form_frame

        KIND_COLORS = {"Button": CYAN, "Toggle": YELLOW, "Textbox": "#ab54f7", "Dropdown": GREEN}
        col = KIND_COLORS.get(kind, TEXT)

        def frow(label, key, placeholder="", color=TEXT):
            r = tk.Frame(f, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            var = tk.StringVar()
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=color,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)
            if placeholder:
                e.insert(0, placeholder)
                e.configure(fg=SUBTEXT)
                def _fi(ev, _e=e, _p=placeholder):
                    if _e.get() == _p: _e.delete(0, "end"); _e.configure(fg=color)
                def _fo(ev, _e=e, _p=placeholder):
                    if not _e.get(): _e.insert(0, _p); _e.configure(fg=SUBTEXT)
                e.bind("<FocusIn>", _fi); e.bind("<FocusOut>", _fo)
            self._hub_form_vars[key] = var

        tk.Label(f, text=f"── {kind} settings ──", font=FONT_SM,
                 fg=col, bg=BG2).pack(anchor="w", padx=6, pady=(6, 2))

        frow("Label:",   "label",   "Button label",  col)
        frow("Desc:",    "desc",    "optional",       SUBTEXT)

        if kind == "Button":
            frow("Command:", "cmd",  "fly",            CYAN)
            frow("Args:",    "args", "optional args",  SUBTEXT)

        elif kind == "Toggle":
            frow("Command:", "cmd",  "fly",            YELLOW)
            frow("Flag:",    "flag", "toggle_fly",     SUBTEXT)

        elif kind == "Textbox":
            frow("Command:", "cmd",     "speed",           "#ab54f7")
            frow("Placeholder:", "placeholder", "Enter value...", SUBTEXT)
            frow("Flag:",    "flag",    "textbox_speed",   SUBTEXT)

        elif kind == "Dropdown":
            frow("Command:", "cmd",     "goto",           GREEN)
            frow("Options:", "options", "opt1, opt2, opt3", SUBTEXT)
            frow("Flag:",    "flag",    "dropdown_goto",   SUBTEXT)

    def _hub_get_form(self, key, default=""):
        var = self._hub_form_vars.get(key)
        if not var:
            return default
        v = var.get().strip()
        # Strip placeholder-colored ghost text (placeholders never have spaces at start)
        return v if v else default

    def _hub_add_element(self):
        kind  = self._hub_kind.get()
        label = self._hub_get_form("label")
        if not label or label in ("Button label", "optional"):
            messagebox.showwarning("Missing", "Enter a label for the element.")
            return
        elem = {
            "kind":        kind,
            "label":       label,
            "desc":        self._hub_get_form("desc", "nil"),
            "cmd":         self._hub_get_form("cmd", "commandname"),
            "args":        self._hub_get_form("args", ""),
            "placeholder": self._hub_get_form("placeholder", "Enter value..."),
            "options":     self._hub_get_form("options", "Option 1, Option 2"),
            "flag":        self._hub_get_form("flag", label.lower().replace(" ", "_")),
        }
        self._hub_elements.append(elem)
        self._hub_refresh_list()

    def _hub_refresh_list(self):
        self._hub_listbox.delete(0, "end")
        KIND_ICONS = {"Button": "🎯", "Toggle": "🔀", "Textbox": "✏️", "Dropdown": "📂"}
        for elem in self._hub_elements:
            icon = KIND_ICONS.get(elem["kind"], "?")
            cmd_info = f'→ execCmd("{elem["cmd"]}")' if elem["kind"] == "Button" else f'→ {elem["cmd"]}'
            self._hub_listbox.insert("end",
                f'  {icon} [{elem["kind"]}]  "{elem["label"]}"  {cmd_info}')

    def _hub_move_up(self):
        sel = self._hub_listbox.curselection()
        if not sel or sel[0] == 0: return
        i = sel[0]
        self._hub_elements[i-1], self._hub_elements[i] = self._hub_elements[i], self._hub_elements[i-1]
        self._hub_refresh_list()
        self._hub_listbox.selection_set(i-1)

    def _hub_move_down(self):
        sel = self._hub_listbox.curselection()
        if not sel or sel[0] >= len(self._hub_elements)-1: return
        i = sel[0]
        self._hub_elements[i], self._hub_elements[i+1] = self._hub_elements[i+1], self._hub_elements[i]
        self._hub_refresh_list()
        self._hub_listbox.selection_set(i+1)

    def _hub_remove_selected(self):
        sel = self._hub_listbox.curselection()
        if not sel: return
        self._hub_elements.pop(sel[0])
        self._hub_refresh_list()

    def _hub_generate(self):
        if not self._hub_elements:
            messagebox.showwarning("Empty", "Add at least one element first.")
            return

        lib   = self._hub_lib.get()
        title = self._hub_title.get().strip() or "Zuka Hub"
        intro = self._hub_intro.get().strip() or "Welcome!"
        cfg   = self._hub_config.get().strip() or "ZukaHub"
        use_intro = self._hub_intro_en.get()
        save_cfg  = self._hub_save_cfg.get()
        lp_name   = '" .. game.Players.LocalPlayer.Name .. "'

        lines = []
        def w(s=""): lines.append(s)

        w("-- ════════════════════════════════════════════════")
        w(f"-- Hub: {title}  |  Library: {lib}")
        w(f"-- Generated by Zuka Panel Hub Creator")
        w("-- ════════════════════════════════════════════════")
        w()
        w("local Players     = game:GetService('Players')")
        w("local speaker     = Players.LocalPlayer")
        w()

        # ── Library loadstring ─────────────────────────────────────────────
        url = self.LIB_URLS[lib]

        if lib == "Luna":
            w(f"local Luna = loadstring(game:HttpGet('{url}'))()")
            w()
            desc_str = f'"{intro}, " .. speaker.Name'
            w("local Window = Luna:CreateWindow({")
            w(f'    Name            = "{title}",')
            w(f'    Subtitle        = nil,')
            w(f'    LogoID          = nil,')
            w(f'    LoadingEnabled  = {str(use_intro).lower()},')
            w(f'    LoadingTitle    = "{title}",')
            w(f'    LoadingSubtitle = "by Zuka",')
            w(f'    ConfigSettings  = {{')
            w(f'        ConfigFolder = "{cfg}"')
            w(f'    }},')
            w(f'    KeySystem = false,')
            w("})")
            w()
            w("local Tab = Window:MakeTab({")
            w(f'    Name = "Main",')
            w(f'    Icon = nil,')
            w("})")
            w()

            for elem in self._hub_elements:
                cmd   = elem["cmd"]
                label = elem["label"]
                desc  = f'"{elem["desc"]}"' if elem["desc"] not in ("nil","optional","") else "nil"
                flag  = elem["flag"] or label.lower().replace(" ", "_")

                if elem["kind"] == "Button":
                    args = elem["args"].strip()
                    arg_str = f', "{args}"' if args else ""
                    w(f'Tab:CreateButton({{')
                    w(f'    Name        = "{label}",')
                    w(f'    Description = {desc},')
                    w(f'    Callback    = function()')
                    w(f'        pcall(execCmd, "{cmd}"{arg_str}, speaker)')
                    w(f'    end,')
                    w(f'}})')

                elif elem["kind"] == "Toggle":
                    w(f'Tab:CreateToggle({{')
                    w(f'    Name         = "{label}",')
                    w(f'    Description  = {desc},')
                    w(f'    CurrentValue = false,')
                    w(f'    Callback     = function(Value)')
                    w(f'        pcall(execCmd, "{cmd}", speaker)')
                    w(f'    end,')
                    w(f'}}, "{flag}")')

                elif elem["kind"] == "Textbox":
                    ph = elem["placeholder"] or "Enter value..."
                    w(f'Tab:CreateInput({{')
                    w(f'    Name                = "{label}",')
                    w(f'    Description         = {desc},')
                    w(f'    PlaceholderText     = "{ph}",')
                    w(f'    ClearTextAfterFocusLost = true,')
                    w(f'    Numeric             = false,')
                    w(f'    Enter               = true,')
                    w(f'    Callback            = function(Text)')
                    w(f'        if Text and Text ~= "" then')
                    w(f'            pcall(execCmd, "{cmd} " .. Text, speaker)')
                    w(f'        end')
                    w(f'    end,')
                    w(f'}}, "{flag}")')

                elif elem["kind"] == "Dropdown":
                    opts = [o.strip() for o in elem["options"].split(",") if o.strip()]
                    opt_lua = "{" + ", ".join(f'"{o}"' for o in opts) + "}"
                    first   = f'"{opts[0]}"' if opts else '"Option 1"'
                    w(f'Tab:CreateDropdown({{')
                    w(f'    Name            = "{label}",')
                    w(f'    Description     = {desc},')
                    w(f'    Options         = {opt_lua},')
                    w(f'    CurrentOption   = {{{first}}},')
                    w(f'    MultipleOptions = false,')
                    w(f'    Callback        = function(Option)')
                    w(f'        if Option and Option ~= "" then')
                    w(f'            pcall(execCmd, "{cmd} " .. Option, speaker)')
                    w(f'        end')
                    w(f'    end,')
                    w(f'}}, "{flag}")')

                w()

        else:  # Orion
            w(f"local OrionLib = loadstring(game:HttpGet('{url}'))()")
            w()
            w("local Window = OrionLib:MakeWindow({")
            w(f'    Name          = "{title}",')
            w(f'    HidePremium   = true,')
            w(f'    SaveConfig    = {str(save_cfg).lower()},')
            w(f'    ConfigFolder  = "{cfg}",')
            w(f'    IntroEnabled  = {str(use_intro).lower()},')
            w(f'    IntroText     = "{intro}, " .. speaker.Name,')
            w("})")
            w()
            w("local Tab = Window:MakeTab({")
            w(f'    Name        = "Main",')
            w(f'    Icon        = "rbxassetid://4483345998",')
            w(f'    PremiumOnly = false,')
            w("})")
            w()

            for elem in self._hub_elements:
                cmd   = elem["cmd"]
                label = elem["label"]
                flag  = elem["flag"] or label.lower().replace(" ", "_")

                if elem["kind"] == "Button":
                    args = elem["args"].strip()
                    arg_str = f', "{args}"' if args else ""
                    w(f'Tab:AddButton({{')
                    w(f'    Name     = "{label}",')
                    w(f'    Callback = function()')
                    w(f'        pcall(execCmd, "{cmd}"{arg_str}, speaker)')
                    w(f'    end,')
                    w(f'}})')

                elif elem["kind"] == "Toggle":
                    w(f'Tab:AddToggle({{')
                    w(f'    Name     = "{label}",')
                    w(f'    Default  = false,')
                    w(f'    Save     = {str(save_cfg).lower()},')
                    w(f'    Flag     = "{flag}",')
                    w(f'    Callback = function(Value)')
                    w(f'        pcall(execCmd, "{cmd}", speaker)')
                    w(f'    end,')
                    w(f'}})')

                elif elem["kind"] == "Textbox":
                    ph = elem["placeholder"] or "Enter value..."
                    w(f'Tab:AddTextbox({{')
                    w(f'    Name          = "{label}",')
                    w(f'    Default       = "{ph}",')
                    w(f'    TextDisappear = true,')
                    w(f'    Callback      = function(Value)')
                    w(f'        if Value and Value ~= "" then')
                    w(f'            pcall(execCmd, "{cmd} " .. Value, speaker)')
                    w(f'        end')
                    w(f'    end,')
                    w(f'}})')

                elif elem["kind"] == "Dropdown":
                    opts = [o.strip() for o in elem["options"].split(",") if o.strip()]
                    opt_lua = "{" + ", ".join(f'"{o}"' for o in opts) + "}"
                    first   = f'"{opts[0]}"' if opts else '"Option 1"'
                    w(f'Tab:AddDropdown({{')
                    w(f'    Name     = "{label}",')
                    w(f'    Default  = {first},')
                    w(f'    Options  = {opt_lua},')
                    w(f'    Save     = {str(save_cfg).lower()},')
                    w(f'    Flag     = "{flag}",')
                    w(f'    Callback = function(Value)')
                    w(f'        if Value and Value ~= "" then')
                    w(f'            pcall(execCmd, "{cmd} " .. Value, speaker)')
                    w(f'        end')
                    w(f'    end,')
                    w(f'}})')

                w()

            w("OrionLib:Init()")

        code = "\n".join(lines)
        self._set_output(self._hub_out, code)

    # ── Page: Script Importer ────────────────────────────────────────────────

    # Regex patterns for format detection
    _IMPORT_PATTERNS = {
        "loadstring": [
            r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(',
            r'loadstring\s*\(\s*game\.HttpGet\s*\(',
            r'loadstring\s*\(\s*HttpGet\s*\(',
            r'require\s*\(\s*\d+\s*\)',
        ],
        "modules": [
            r'Modules\s*\.\s*\w+\s*=\s*\{',
            r'function\s+Modules\s*\.\s*\w+\s*:\s*Initialize\s*\(',
        ],
        "register": [
            r'RegisterCommand\s*\(',
            r'RegisterCommandDual\s*\(',
        ],
    }

    def _build_import_page(self, parent):
        # ── Left: input + detection ───────────────────────────────────────────
        left = tk.Frame(parent, bg=BG, width=500)
        left.pack(side="left", fill="y", padx=(14, 0), pady=14)
        left.pack_propagate(False)

        self._label(left, "PASTE SCRIPT  (any format)")

        self._imp_input = self._text_area(left, height=16)
        self._imp_input.bind("<KeyRelease>", self._imp_auto_detect)
        self._imp_input.bind("<ButtonRelease>", self._imp_auto_detect)

        # Detection result bar
        det_row = tk.Frame(left, bg=BG2)
        det_row.pack(fill="x", pady=(4, 0))
        tk.Label(det_row, text="DETECTED:", font=FONT_SM, fg=SUBTEXT,
                 bg=BG2, padx=6).pack(side="left")
        self._imp_det_label = tk.Label(det_row, text="—  paste a script above",
                                       font=FONT_SM, fg=SUBTEXT, bg=BG2)
        self._imp_det_label.pack(side="left")

        # Command metadata
        sep = tk.Frame(left, bg=BORDER, height=1)
        sep.pack(fill="x", pady=10)

        self._label(left, "WRAP AS COMMAND")

        meta = tk.Frame(left, bg=BG2)
        meta.pack(fill="x")

        def mrow(label, var, col=TEXT, placeholder=""):
            r = tk.Frame(meta, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=col,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)
            if placeholder:
                e.insert(0, placeholder)
                e.configure(fg=SUBTEXT)
                def _fi(ev, _e=e, _c=col, _p=placeholder):
                    if _e.get() == _p: _e.delete(0,"end"); _e.configure(fg=_c)
                def _fo(ev, _e=e, _c=col, _p=placeholder):
                    if not _e.get(): _e.insert(0,_p); _e.configure(fg=SUBTEXT)
                e.bind("<FocusIn>",_fi); e.bind("<FocusOut>",_fo)
            return var

        self._imp_cmd      = tk.StringVar()
        self._imp_aliases  = tk.StringVar()
        self._imp_args_desc = tk.StringVar()

        mrow("Cmd name:",  self._imp_cmd,       CYAN,    "e.g. myscript")
        mrow("Aliases:",   self._imp_aliases,    YELLOW,  "a, ms  (comma sep)")
        mrow("Args desc:", self._imp_args_desc,  SUBTEXT, "optional description")

        # Output style
        self._label(left, "OUTPUT STYLE")
        style_row = tk.Frame(left, bg=BG)
        style_row.pack(fill="x", pady=(0, 8))
        self._imp_style = tk.StringVar(value="addcmd")
        tk.Radiobutton(style_row, text="addcmd()", variable=self._imp_style,
                       value="addcmd", font=FONT_SM, fg=CYAN, bg=BG,
                       selectcolor=BG2, activebackground=BG, activeforeground=CYAN,
                       highlightthickness=0, cursor="hand2").pack(side="left", padx=(0,14))
        tk.Radiobutton(style_row, text="RegisterCommand()", variable=self._imp_style,
                       value="register", font=FONT_SM, fg=YELLOW, bg=BG,
                       selectcolor=BG2, activebackground=BG, activeforeground=YELLOW,
                       highlightthickness=0, cursor="hand2").pack(side="left")

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(8, 0))
        self._btn(btn_row, "⚡  CONVERT & WRAP",   self._imp_do_convert, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "➡  SEND TO BUILDER",   self._imp_to_builder, CYAN).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR",             self._imp_clear,      BG3).pack(side="left")

        # ── Right: output ─────────────────────────────────────────────────────
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(right, "OUTPUT  —  ready to paste into your panel")
        self._imp_out = self._text_area(right, height=32, expand=True)
        self._imp_out.configure(state="disabled")

        out_row = tk.Frame(right, bg=BG)
        out_row.pack(fill="x", pady=(6, 0))
        self._btn(out_row, "📋  COPY", lambda: self._copy(self._imp_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_row, "💾  SAVE", lambda: self._save(self._imp_out), BG3).pack(side="left")

    # ── Import helpers ────────────────────────────────────────────────────────

    def _imp_detect_format(self, src: str) -> str:
        """Return 'loadstring' | 'modules' | 'register' | 'raw'."""
        import re
        for fmt, patterns in self._IMPORT_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, src, re.IGNORECASE):
                    return fmt
        return "raw"

    def _imp_auto_detect(self, event=None):
        src = self._imp_input.get("1.0", "end-1c").strip()
        if not src:
            self._imp_det_label.configure(text="—  paste a script above", fg=SUBTEXT)
            return
        fmt = self._imp_detect_format(src)
        FMT_LABELS = {
            "loadstring": ("🌐  loadstring / HttpGet",         CYAN),
            "modules":    ("📦  Modules.X:Initialize() style", YELLOW),
            "register":   ("📋  RegisterCommand style",        "#ab54f7"),
            "raw":        ("📝  Raw Lua",                      GREEN),
        }
        text, color = FMT_LABELS[fmt]
        self._imp_det_label.configure(text=text, fg=color)

    def _imp_extract_body(self, src: str, fmt: str) -> str:
        """
        Pull the executable core out of the detected format.
        For loadstring  → keep as-is (it IS the executable call).
        For modules     → extract the body of :Initialize().
        For register    → extract the function body of each RegisterCommand.
        For raw         → keep as-is.
        """
        import re

        if fmt in ("raw", "loadstring"):
            return src

        if fmt == "modules":
            # Extract everything inside :Initialize() ... end
            m = re.search(
                r'function\s+Modules\s*\.\s*\w+\s*:\s*Initialize\s*\(\s*\)(.*?)^end',
                src, re.DOTALL | re.MULTILINE
            )
            if m:
                body = m.group(1).strip()
                return body if body else src
            return src

        if fmt == "register":
            # Pull all RegisterCommand / RegisterCommandDual calls and keep them intact
            # (They already contain the function body)
            calls = re.findall(
                r'RegisterCommand(?:Dual)?\s*\(.*?\)\s*\)',
                src, re.DOTALL
            )
            if calls:
                return "\n\n".join(c.strip() for c in calls)
            return src

        return src

    def _imp_do_convert(self):
        import re
        src = self._imp_input.get("1.0", "end-1c").strip()
        if not src:
            messagebox.showwarning("Empty", "Paste a script first.")
            return

        cmd_raw = self._imp_cmd.get().strip()
        # strip placeholder text
        if cmd_raw in ("e.g. myscript", ""):
            cmd_raw = "myscript"
        cmd = cmd_raw.lower().replace(" ", "_")

        aliases_raw = self._imp_aliases.get().strip()
        if aliases_raw in ("a, ms  (comma sep)", ""):
            aliases_raw = ""
        aliases = [a.strip() for a in aliases_raw.split(",") if a.strip() and a.strip() not in ("a", "ms")]

        desc_raw = self._imp_args_desc.get().strip()
        if desc_raw == "optional description":
            desc_raw = ""

        fmt   = self._imp_detect_format(src)
        body  = self._imp_extract_body(src, fmt)
        style = self._imp_style.get()

        # Indent body for inside a function
        def indent(text, n=4):
            pad = " " * n
            return "\n".join(pad + line if line.strip() else line for line in text.splitlines())

        lines = []
        def w(s=""): lines.append(s)

        w(f"-- ── Imported: {cmd}  [{fmt} → {style}] ──────────────────────")
        w()

        if style == "addcmd":
            alias_lua = "{" + ", ".join(f'"{a}"' for a in aliases) + "}"
            w(f'addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            for line in body.splitlines():
                w("    " + line if line.strip() else line)
            w("end)")

        else:  # RegisterCommand
            alias_lua = "{" + ", ".join(f'"{a}"' for a in aliases) + "}"
            w(f'RegisterCommand({{')
            w(f'    Name        = "{cmd}",')
            w(f'    Aliases     = {alias_lua},')
            w(f'    Description = "{desc_raw or cmd + " command"}",')
            w(f'    ArgsDesc    = {{}},')
            w(f'    Permissions = {{}},')
            w(f'}}, function(args, speaker)')
            for line in body.splitlines():
                w("    " + line if line.strip() else line)
            w("end)")

        result = "\n".join(lines)
        self._set_output(self._imp_out, result)

    def _imp_to_builder(self):
        """Push the output directly into the Builder tab's body field."""
        code = self._imp_out.get("1.0", "end-1c").strip()
        if not code:
            # Try converting first if there's input
            src = self._imp_input.get("1.0", "end-1c").strip()
            if not src:
                messagebox.showinfo("Empty", "Convert a script first, or paste input.")
                return
            self._imp_do_convert()
            code = self._imp_out.get("1.0", "end-1c").strip()
            if not code:
                return

        # Push cmd name into builder
        cmd_raw = self._imp_cmd.get().strip()
        if cmd_raw and cmd_raw not in ("e.g. myscript",):
            try:
                self._cmd_name.set(cmd_raw.lower().replace(" ", "_"))
            except Exception:
                pass

        # Push aliases
        aliases_raw = self._imp_aliases.get().strip()
        if aliases_raw and aliases_raw not in ("a, ms  (comma sep)",):
            try:
                self._cmd_aliases.set(aliases_raw)
            except Exception:
                pass

        # Push body into builder body box
        try:
            self._body_box.configure(state="normal")
            self._body_box.delete("1.0", "end")
            # Strip the outer addcmd/RegisterCommand wrapper — push just the body
            import re
            inner = re.search(
                r'function\s*\(args,\s*speaker\)(.*?)^end\)',
                code, re.DOTALL | re.MULTILINE
            )
            body = inner.group(1).strip() if inner else code
            self._body_box.insert("1.0", body)
        except Exception:
            pass

        # Switch to Builder tab
        for name, btn in self._tab_btns.items():
            if "Builder" in name:
                btn.invoke()
                break

        messagebox.showinfo("Sent", f'Script body sent to Builder tab as "{cmd_raw}".')

    def _imp_clear(self):
        self._imp_input.configure(state="normal")
        self._imp_input.delete("1.0", "end")
        self._set_output(self._imp_out, "")
        self._imp_det_label.configure(text="—  paste a script above", fg=SUBTEXT)
        self._imp_cmd.set("")
        self._imp_aliases.set("")
        self._imp_args_desc.set("")

    # ── Page: GUI Maker ──────────────────────────────────────────────────────



    # ── Page: Args Builder ───────────────────────────────────────────────────

    def _build_args_page(self, parent):
        self._args_list = []

        left = tk.Frame(parent, bg=BG, width=360)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        self._label(left, "COMMAND NAME")
        self._args_cmd_name = tk.StringVar()
        self._entry(left, self._args_cmd_name, placeholder="commandname")

        self._label(left, "ALIASES")
        self._args_aliases = tk.StringVar()
        self._entry(left, self._args_aliases, placeholder="alias1, alias2")

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", pady=8)
        self._label(left, "ADD ARGUMENT")

        af = tk.Frame(left, bg=BG2)
        af.pack(fill="x", pady=(0,6))

        def arow(label, var, col=TEXT, placeholder=""):
            r = tk.Frame(af, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=col,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)
            if placeholder:
                e.insert(0, placeholder); e.configure(fg=SUBTEXT)
                def _fi(ev, _e=e, _p=placeholder):
                    if _e.get()==_p: _e.delete(0,"end"); _e.configure(fg=col)
                def _fo(ev, _e=e, _p=placeholder):
                    if not _e.get(): _e.insert(0,_p); _e.configure(fg=SUBTEXT)
                e.bind("<FocusIn>",_fi); e.bind("<FocusOut>",_fo)

        self._arg_name    = tk.StringVar()
        self._arg_default = tk.StringVar()
        arow("Name:",    self._arg_name,    CYAN,   "e.g. amount")
        arow("Default:", self._arg_default, YELLOW, "optional")

        self._label(left, "TYPE")
        type_row = tk.Frame(left, bg=BG)
        type_row.pack(fill="x", pady=(0,6))
        self._arg_type = tk.StringVar(value="string")
        TYPE_COLORS = {"string": TEXT, "number": YELLOW, "player": CYAN, "boolean": GREEN}
        for t, col in TYPE_COLORS.items():
            tk.Radiobutton(type_row, text=t, variable=self._arg_type, value=t,
                           font=FONT_SM, fg=col, bg=BG, selectcolor=BG2,
                           activebackground=BG, activeforeground=col,
                           highlightthickness=0, cursor="hand2").pack(side="left", padx=(0,10))

        self._arg_required = self._checkbox(left, "Required  (generates nil check)")

        add_row = tk.Frame(left, bg=BG)
        add_row.pack(fill="x", pady=(6,0))
        self._btn(add_row, "➕  ADD ARG", self._args_add, ACCENT).pack(side="left", padx=(0,6))
        self._btn(add_row, "🗑  CLEAR ALL",
                  lambda: (self._args_list.clear(), self._args_refresh()), BG3).pack(side="left")

        self._label(left, "ARGUMENTS  (double-click to remove)")
        lf = tk.Frame(left, bg=BORDER, bd=1)
        lf.pack(fill="x")
        self._args_listbox = tk.Listbox(
            lf, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            font=FONT_SM, bd=0, highlightthickness=0, activestyle="none", height=6
        )
        self._args_listbox.pack(fill="both", expand=True)
        self._args_listbox.bind("<Double-Button-1>", self._args_remove)

        btn_row2 = tk.Frame(left, bg=BG)
        btn_row2.pack(fill="x", pady=(8,0))
        self._btn(btn_row2, "⚡  GENERATE", self._args_generate, ACCENT).pack(side="left", padx=(0,6))

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        ref = tk.Frame(right, bg=BG2)
        ref.pack(fill="x", pady=(0,10))
        tk.Label(ref, text="Arg Types — what gets generated",
                 font=FONT_SM, fg=ACCENT, bg=BG2, anchor="w").pack(fill="x", padx=8, pady=(4,2))
        type_info = [
            ("string",  "args[n] with optional nil check"),
            ("number",  "tonumber(args[n]) with nil check"),
            ("player",  "getPlayer(args[n], speaker) loop"),
            ("boolean", "true/false from on/off/true/false/1"),
        ]
        for t, desc in type_info:
            row = tk.Frame(ref, bg=BG2)
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=t, font=(FONT_SM[0], FONT_SM[1], "bold"),
                     fg=TYPE_COLORS.get(t, TEXT), bg=BG2, width=10, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, anchor="w").pack(side="left")
        tk.Frame(ref, bg=BG2, height=4).pack()

        self._label(right, "OUTPUT")
        self._args_out = self._text_area(right, height=28, expand=True)
        self._args_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._args_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._args_out), BG3).pack(side="left")

    def _args_add(self):
        name = self._arg_name.get().strip()
        if not name or name == "e.g. amount":
            messagebox.showwarning("Missing", "Argument name required.")
            return
        default = self._arg_default.get().strip()
        if default == "optional": default = ""
        self._args_list.append({
            "name":     name,
            "type":     self._arg_type.get(),
            "required": self._arg_required.get(),
            "default":  default,
        })
        self._args_refresh()
        self._arg_name.set(""); self._arg_default.set("")

    def _args_refresh(self):
        self._args_listbox.delete(0, "end")
        TYPE_ICONS = {"string": "S", "number": "N", "player": "P", "boolean": "B"}
        for i, arg in enumerate(self._args_list):
            req = " *" if arg["required"] else ""
            default = f" = {arg['default']}" if arg["default"] else ""
            self._args_listbox.insert("end",
                f"  [{TYPE_ICONS.get(arg['type'],'?')}] [{i+1}] {arg['name']}: {arg['type']}{default}{req}")

    def _args_remove(self, event=None):
        sel = self._args_listbox.curselection()
        if sel:
            self._args_list.pop(sel[0])
            self._args_refresh()

    def _args_generate(self):
        name      = self._args_cmd_name.get().strip() or "commandname"
        aliases   = [a.strip() for a in self._args_aliases.get().split(",") if a.strip()]
        alias_str = "{" + ", ".join(f'"{a}"' for a in aliases) + "}"
        body      = generate_args_boilerplate(self._args_list)
        result    = f'addcmd("{name}", {alias_str}, function(args, speaker)\n{body}\nend)'
        self._set_output(self._args_out, result)

    # ── Page: Utilities ──────────────────────────────────────────────────────

    def _build_utilities_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=240)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        self._label(left, "UTILITIES")

        utils = {
            "detectEnvironment()": (
                "Checks which executor functions are available and rates the executor.\nFrom Zuka's main script — drop this at the top of any panel.",
                DETECT_ENV_SNIPPET.strip()
            ),
            "Utilities.findPlayer()": (
                "Resolves a player by exact name, display name, or partial match.\nSupports 'me' shortcut. From Zuka's main script.",
                FIND_PLAYER_SNIPPET.strip()
            ),
            "Levenshtein Distance": (
                "Fuzzy command suggestions — shows 'did you mean X?' when a command is mistyped.",
                LEVENSHTEIN_SNIPPET.strip()
            ),
            "Safe pcall Wrapper": (
                "Wraps any command body in pcall with DoNotif error reporting.",
                "local function SafeRun(fn, ...)\n"
                "    local ok, err = pcall(fn, ...)\n"
                "    if not ok then\n"
                "        warn('[Command Error]', err)\n"
                "        DoNotif('Error: ' .. tostring(err), 5)\n"
                "    end\n"
                "    return ok\n"
                "end"
            ),
            "Arg Count Check": (
                "Asserts a minimum number of args are present before running.",
                "local function RequireArgs(args, min, usage)\n"
                "    if #args < min then\n"
                "        DoNotif('Usage: ' .. usage, 3)\n"
                "        return false\n"
                "    end\n"
                "    return true\n"
                "end\n"
                "-- Example: if not RequireArgs(args, 1, ';speed <value>') then return end"
            ),
            "Command Cooldown": (
                "Per-command cooldown — prevents spam.",
                "local Cooldowns = {}\n"
                "local function CheckCooldown(name, seconds)\n"
                "    local last = Cooldowns[name]\n"
                "    if last and (tick() - last) < seconds then\n"
                "        DoNotif(name .. ' on cooldown. Wait ' ..\n"
                "            math.ceil(seconds - (tick() - last)) .. 's', 2)\n"
                "        return false\n"
                "    end\n"
                "    Cooldowns[name] = tick()\n"
                "    return true\n"
                "end\n"
                "-- Example: if not CheckCooldown('fly', 3) then return end"
            ),
            "Confirm Prompt": (
                "Two-step confirmation before running a dangerous command.",
                "local PendingConfirm = {}\n"
                "local function Confirm(name, action)\n"
                "    if PendingConfirm[name] then\n"
                "        PendingConfirm[name] = nil\n"
                "        action()\n"
                "    else\n"
                "        PendingConfirm[name] = true\n"
                "        DoNotif('Run ;' .. name .. ' again to confirm.', 4)\n"
                "        task.delay(4, function() PendingConfirm[name] = nil end)\n"
                "    end\n"
                "end\n"
                "-- Example: Confirm('nuke', function() execCmd('nuke') end)"
            ),
            "Player Resolver": (
                "Resolve a partial name to a full Player object.",
                "local function ResolvePlayer(input)\n"
                "    input = input:lower()\n"
                "    for _, p in ipairs(game:GetService('Players'):GetPlayers()) do\n"
                "        if p.Name:lower():find(input, 1, true) or\n"
                "           p.DisplayName:lower():find(input, 1, true) then\n"
                "            return p\n"
                "        end\n"
                "    end\n"
                "    DoNotif('Player not found: ' .. input, 2)\n"
                "end"
            ),
        }

        listbox = tk.Listbox(
            left, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            font=FONT_SM, bd=0, highlightthickness=1,
            highlightcolor=BORDER, activestyle="none", cursor="hand2"
        )
        listbox.pack(fill="both", expand=True)
        self._util_data = {}
        for name, (desc, code) in utils.items():
            listbox.insert("end", "  " + name)
            self._util_data[name] = (desc, code)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._util_desc = tk.Label(right, text="Select a utility to preview.",
                                   font=FONT_SM, fg=SUBTEXT, bg=BG2,
                                   wraplength=500, justify="left", anchor="w", padx=8, pady=8)
        self._util_desc.pack(fill="x", pady=(0,8))

        self._label(right, "CODE")
        self._util_out = self._text_area(right, height=28, expand=True)

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._util_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._util_out), BG3).pack(side="left")

        def on_select(event):
            sel = listbox.curselection()
            if not sel: return
            name = listbox.get(sel[0]).strip()
            desc, code = self._util_data.get(name, ("", ""))
            self._util_desc.configure(text=desc)
            self._util_out.configure(state="normal")
            self._util_out.delete("1.0", "end")
            self._util_out.insert("1.0", code)

        listbox.bind("<<ListboxSelect>>", on_select)

    # ── Page: Bulk Import ────────────────────────────────────────────────────

    def _build_bulk_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=420)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        self._label(left, "PASTE YOUR Commands = {} TABLE")
        tk.Label(left,
                 text="Paste your existing Commands table and the builder\nwill reverse-engineer each entry.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG, justify="left", anchor="w").pack(fill="x", pady=(0,6))

        self._bulk_input = self._text_area(left, height=14)

        self._label(left, "CONVERT TO")
        style_row = tk.Frame(left, bg=BG)
        style_row.pack(fill="x", pady=(0,8))
        self._bulk_style = tk.StringVar(value="addcmd")
        tk.Radiobutton(style_row, text="addcmd()", variable=self._bulk_style,
                       value="addcmd", font=FONT_SM, fg=CYAN, bg=BG,
                       selectcolor=BG2, activebackground=BG, activeforeground=CYAN,
                       highlightthickness=0, cursor="hand2").pack(side="left", padx=(0,14))
        tk.Radiobutton(style_row, text="RegisterCommand()", variable=self._bulk_style,
                       value="register", font=FONT_SM, fg=YELLOW, bg=BG,
                       selectcolor=BG2, activebackground=BG, activeforeground=YELLOW,
                       highlightthickness=0, cursor="hand2").pack(side="left")

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(6,0))
        self._btn(btn_row, "⚡  PARSE & CONVERT", self._bulk_parse, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR", lambda: (
            self._bulk_input.delete("1.0","end"),
            self._set_output(self._bulk_out, ""),
            self._bulk_status.configure(text="")
        ), BG3).pack(side="left")

        self._bulk_status = tk.Label(left, text="", font=FONT_SM, fg=GREEN, bg=BG, anchor="w")
        self._bulk_status.pack(fill="x", pady=(6,0))

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        self._label(right, "CONVERTED OUTPUT")
        self._bulk_out = self._text_area(right, height=32, expand=True)
        self._bulk_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._bulk_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._bulk_out), BG3).pack(side="left")

    def _bulk_parse(self):
        import re
        src   = self._bulk_input.get("1.0", "end-1c").strip()
        style = self._bulk_style.get()
        if not src:
            messagebox.showwarning("Empty", "Paste a Commands table first.")
            return

        pattern = re.compile(
            r'Commands\s*[\[\.]\s*["\']?(\w+)["\']?\s*\]?\s*=\s*function\s*\(([^)]*)\)(.*?)(?=\nCommands|\Z)',
            re.DOTALL
        )
        pattern2 = re.compile(
            r'^\s*(\w+)\s*=\s*function\s*\(([^)]*)\)(.*?)(?=\n\s*\w+\s*=\s*function|\Z)',
            re.DOTALL | re.MULTILINE
        )

        found = list(pattern.finditer(src))
        if not found:
            found = list(pattern2.finditer(src))

        results = []
        for m in found:
            name   = m.group(1).strip()
            params = m.group(2).strip()
            body   = m.group(3).strip()
            if body.endswith("end"):
                body = body[:-3].strip()
            indent = "\n".join("    " + l if l.strip() else "" for l in body.split("\n"))

            if style == "addcmd":
                results.append(f'addcmd("{name}", {{}}, function({params})\n{indent}\nend)')
            else:
                results.append(
                    f'RegisterCommand({{\n'
                    f'    Name        = "{name}",\n'
                    f'    Aliases     = {{}},\n'
                    f'    Description = "{name} command",\n'
                    f'}}, function({params})\n{indent}\nend)'
                )

        if not results:
            messagebox.showinfo("No matches",
                "Could not parse any commands.\nExpected: Commands[\"name\"] = function(...) ... end")
            return

        self._bulk_status.configure(text=f"Parsed {len(results)} command(s)")
        self._set_output(self._bulk_out, "\n\n".join(results))

    # ── Page: Script Wizard ──────────────────────────────────────────────────

    WIZARD_SCRIPT_TYPES = [
        ("Speed Modifier",      "Change your walkspeed with a command"),
        ("Fly Toggle",          "Toggle fly on/off"),
        ("Noclip Toggle",       "Walk through walls"),
        ("Infinite Jump",       "Jump infinitely"),
        ("Teleport to Player",  "Teleport yourself to someone"),
        ("Bring Player",        "Pull players to you"),
        ("Chat Spam",           "Repeat a chat message on a loop"),
        ("Fake Lag",            "Add artificial ping/lag"),
        ("Loop Notification",   "Spam a custom notification"),
        ("Custom Loop",         "Run any code on a repeating loop"),
        ("Custom Command",      "One-shot command with your own code"),
    ]

    def _build_wizard_page(self, parent):
        self._wiz_step    = 0
        self._wiz_type    = tk.StringVar()
        self._wiz_answers = {}

        header = tk.Frame(parent, bg=BG2)
        header.pack(fill="x")
        tk.Label(header, text="🧙  SCRIPT WIZARD", font=FONT_LG,
                 fg=ACCENT, bg=BG2).pack(side="left", padx=14, pady=10)
        tk.Label(header,
                 text="No Lua knowledge needed — answer a few questions and get a ready-to-run script.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="left", padx=4)

        self._wiz_progress_frame = tk.Frame(parent, bg=BG)
        self._wiz_progress_frame.pack(fill="x", padx=14, pady=(8, 0))
        self._wiz_content_frame  = tk.Frame(parent, bg=BG)
        self._wiz_content_frame.pack(fill="both", expand=True, padx=14, pady=8)
        self._wiz_out_frame      = tk.Frame(parent, bg=BG)
        self._wiz_out_frame.pack(fill="both", expand=False, padx=14, pady=(0, 8))

        self._wiz_show_step_0()

    def _wiz_clear(self):
        for f in (self._wiz_content_frame, self._wiz_out_frame, self._wiz_progress_frame):
            for w in f.winfo_children():
                w.destroy()

    def _wiz_progress(self, step, total):
        pf = self._wiz_progress_frame
        for w in pf.winfo_children():
            w.destroy()
        tk.Label(pf, text=f"Step {step} of {total}",
                 font=FONT_SM, fg=SUBTEXT, bg=BG).pack(side="left")
        bar_bg = tk.Frame(pf, bg=BG3, height=6, width=300)
        bar_bg.pack(side="left", padx=10)
        bar_bg.pack_propagate(False)
        fill_w = int(300 * (step / total))
        tk.Frame(bar_bg, bg=ACCENT, height=6, width=fill_w).place(x=0, y=0)

    def _wiz_show_step_0(self):
        self._wiz_clear()
        self._wiz_progress(1, 3)
        self._wiz_answers = {}
        cf = self._wiz_content_frame
        tk.Label(cf, text="STEP 1  —  What kind of script do you want?",
                 font=FONT_TITLE, fg=ACCENT, bg=BG).pack(anchor="w", pady=(0, 10))
        grid = tk.Frame(cf, bg=BG)
        grid.pack(fill="x")
        cols = 3
        COLORS = [CYAN, YELLOW, GREEN, ACCENT]
        for i, (name, desc) in enumerate(self.WIZARD_SCRIPT_TYPES):
            col = COLORS[i % len(COLORS)]
            row_f = tk.Frame(grid, bg=BG2, pady=6, padx=8)
            row_f.grid(row=i // cols, column=i % cols, padx=6, pady=4, sticky="nsew")
            grid.columnconfigure(i % cols, weight=1)
            tk.Label(row_f, text=name, font=FONT_TITLE, fg=col, bg=BG2, anchor="w").pack(anchor="w")
            tk.Label(row_f, text=desc, font=FONT_SM,    fg=SUBTEXT, bg=BG2, anchor="w").pack(anchor="w")
            def select(n=name):
                self._wiz_type.set(n)
                self._wiz_show_step_1(n)
            row_f.configure(cursor="hand2")
            row_f.bind("<Button-1>", lambda e, fn=select: fn())
            for child in row_f.winfo_children():
                child.configure(cursor="hand2")
                child.bind("<Button-1>", lambda e, fn=select: fn())

    def _wiz_show_step_1(self, script_type):
        self._wiz_clear()
        self._wiz_progress(2, 3)
        cf = self._wiz_content_frame
        tk.Label(cf, text=f"STEP 2  —  Configure: {script_type}",
                 font=FONT_TITLE, fg=ACCENT, bg=BG).pack(anchor="w", pady=(0, 10))
        self._wiz_field_vars = {}

        def field(label, key, default="", col=TEXT, info=""):
            row = tk.Frame(cf, bg=BG)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=FONT_SM, fg=SUBTEXT, bg=BG,
                     width=28, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            tk.Entry(row, textvariable=var, font=FONT_UI, bg=BG2, fg=col,
                     insertbackground=CYAN, bd=0, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER,
                     width=22).pack(side="left", ipady=5)
            if info:
                tk.Label(row, text=info, font=FONT_SM, fg=SUBTEXT, bg=BG).pack(side="left", padx=8)
            self._wiz_field_vars[key] = var

        def checkbox(label, key, default=False):
            var = tk.BooleanVar(value=default)
            tk.Checkbutton(cf, text=label, variable=var, font=FONT_SM, fg=TEXT, bg=BG,
                           selectcolor=BG2, activebackground=BG,
                           highlightthickness=0, cursor="hand2").pack(anchor="w")
            self._wiz_field_vars[key] = var

        safe_name = script_type.lower().replace(" ", "").replace("(", "").replace(")", "").replace("/", "")
        field("Command name:", "cmd", safe_name, CYAN, "What you type in chat")
        field("Aliases (comma sep):", "aliases", "", YELLOW, "Shortcut names")

        t = script_type
        if t == "Speed Modifier":
            field("Default speed:", "speed", "100", GREEN, "Normal Roblox = 16")
            checkbox("Allow custom speed as arg  (e.g. ;speed 200)", "custom_arg", True)
        elif t == "Fly Toggle":
            field("Fly speed:", "flyspeed", "80", GREEN)
        elif t == "Bring Player":
            checkbox("Spread players apart on arrival", "spread", True)
        elif t == "Chat Spam":
            field("Message to spam:", "msg", "Hello world!", TEXT)
            field("Delay (seconds):", "delay", "1", GREEN)
        elif t == "Fake Lag":
            field("Lag amount (seconds):", "lag", "0.3", GREEN)
        elif t == "Loop Notification":
            field("Notification text:", "notif_text", "Zuka is running!", TEXT)
            field("Duration (seconds):",   "notif_dur",  "2", GREEN)
            field("Interval (seconds):",   "notif_int",  "3", GREEN)
        elif t == "Custom Loop":
            field("Loop delay (seconds):", "loop_delay", "0.1", GREEN)
            tk.Label(cf, text="LOOP BODY  (Lua — runs every tick)",
                     font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w", pady=(8, 2))
            self._wiz_loop_body = self._text_area(cf, height=5)
            self._wiz_loop_body.insert("1.0", "-- your code here\nprint('tick')")
        elif t == "Custom Command":
            tk.Label(cf, text="COMMAND BODY  (Lua — runs once per call)",
                     font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w", pady=(8, 2))
            self._wiz_cmd_body = self._text_area(cf, height=5)
            self._wiz_cmd_body.insert("1.0", "-- your code here\nDoNotif('Hello!', 2)")

        checkbox("Show notification when command runs", "use_notif", True)
        checkbox("Wrap in pcall (silently catches errors)", "use_pcall", True)

        nav = tk.Frame(cf, bg=BG)
        nav.pack(fill="x", pady=(14, 0))
        self._btn(nav, "← Back",           self._wiz_show_step_0,                   BG3).pack(side="left", padx=(0, 8))
        self._btn(nav, "Generate Script →", lambda: self._wiz_generate(script_type), ACCENT).pack(side="left")

    def _wiz_generate(self, script_type):
        self._wiz_clear()
        self._wiz_progress(3, 3)
        cf = self._wiz_content_frame

        tk.Label(cf, text="STEP 3  —  Your Script is Ready! 🎉",
                 font=FONT_TITLE, fg=GREEN, bg=BG).pack(anchor="w", pady=(0, 6))

        v = self._wiz_field_vars
        def gbool(key):
            var = v.get(key)
            return var.get() if isinstance(var, tk.BooleanVar) else False
        def gstr(key, default=""):
            var = v.get(key)
            return var.get().strip() if isinstance(var, tk.StringVar) else default

        cmd        = gstr("cmd", "myscript").lower().replace(" ", "_") or "myscript"
        raw_al     = [a.strip() for a in gstr("aliases").split(",") if a.strip()]
        alias_lua  = "{" + ", ".join(f'"{a}"' for a in raw_al) + "}"
        use_notif  = gbool("use_notif")
        use_pcall  = gbool("use_pcall")

        code    = self._wiz_build_script(script_type, cmd, alias_lua, use_notif, use_pcall, v)
        explain = self._wiz_explain(script_type)

        of = self._wiz_out_frame
        tk.Label(of, text="💡  WHAT DOES THIS SCRIPT DO?",
                 font=FONT_SM, fg=YELLOW, bg=BG).pack(anchor="w")
        tk.Label(of, text=explain, font=FONT_SM, fg=SUBTEXT, bg=BG2,
                 wraplength=700, justify="left", anchor="w", padx=10, pady=6).pack(fill="x")

        tk.Label(of, text="OUTPUT  —  paste this into your executor",
                 font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w", pady=(8, 2))
        out_box = self._text_area(of, height=14, expand=False)
        out_box.configure(state="normal")
        out_box.insert("1.0", code)
        out_box.configure(state="disabled")

        btn_row = tk.Frame(of, bg=BG)
        btn_row.pack(fill="x", pady=(6, 0))
        self._btn(btn_row, "📋  COPY",         lambda: self._copy(out_box),              CYAN).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "💾  SAVE",          lambda: self._save(out_box),              BG3).pack(side="left",  padx=(0, 8))
        self._btn(btn_row, "⚡  TO BUILDER",    lambda: self._wiz_to_builder(code, cmd),  ACCENT).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "← Start Over",      self._wiz_show_step_0,                   BG3).pack(side="right")

    def _wiz_build_script(self, t, cmd, alias_lua, use_notif, use_pcall, v):
        def gstr(key, default=""):
            var = v.get(key)
            return var.get().strip() if isinstance(var, tk.StringVar) else default
        def gbool(key):
            var = v.get(key)
            return var.get() if isinstance(var, tk.BooleanVar) else False

        lines = []
        def w(s=""): lines.append(s)
        w(f"-- Script: {cmd}  |  Generated by Zuka Wizard")
        w(f"-- HOW TO USE: Type ;{cmd} in chat (or your panel prefix)")
        w()

        if t == "Speed Modifier":
            speed  = gstr("speed", "100")
            custom = gbool("custom_arg")
            w(f'addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("    local char = speaker.Character")
            w("    local hum  = char and char:FindFirstChildOfClass('Humanoid')")
            w("    if not hum then return DoNotif('No character.', 2) end")
            if custom:
                w(f"    local spd = tonumber(args[1]) or {speed}")
            else:
                w(f"    local spd = {speed}")
            w("    hum.WalkSpeed = spd")
            if use_notif: w(f'    DoNotif("Speed: " .. spd, 2)')
            w("end)")

        elif t == "Fly Toggle":
            spd = gstr("flyspeed", "80")
            w("do"); w("    local flyOn=false, flyConn, bVel, bGyro")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("        flyOn = not flyOn")
            w("        local char=speaker.Character if not char then return end")
            w("        local hum=char:FindFirstChildOfClass('Humanoid')")
            w("        local root=char:FindFirstChild('HumanoidRootPart')")
            w("        if not (hum and root) then return end")
            w("        if flyOn then")
            w("            hum.PlatformStand=true")
            w("            bVel=Instance.new('BodyVelocity',root) bVel.MaxForce=Vector3.new(1e9,1e9,1e9) bVel.Velocity=Vector3.zero")
            w("            bGyro=Instance.new('BodyGyro',root) bGyro.MaxTorque=Vector3.new(1e9,1e9,1e9) bGyro.P=1e6")
            w("            local cam=workspace.CurrentCamera")
            w("            local UIS=game:GetService('UserInputService')")
            w("            flyConn=game:GetService('RunService').Heartbeat:Connect(function()")
            w("                local d=Vector3.zero")
            w("                if UIS:IsKeyDown(Enum.KeyCode.W) then d=d+cam.CFrame.LookVector end")
            w("                if UIS:IsKeyDown(Enum.KeyCode.S) then d=d-cam.CFrame.LookVector end")
            w("                if UIS:IsKeyDown(Enum.KeyCode.A) then d=d-cam.CFrame.RightVector end")
            w("                if UIS:IsKeyDown(Enum.KeyCode.D) then d=d+cam.CFrame.RightVector end")
            w("                if UIS:IsKeyDown(Enum.KeyCode.Space)     then d=d+Vector3.yAxis end")
            w("                if UIS:IsKeyDown(Enum.KeyCode.LeftShift) then d=d-Vector3.yAxis end")
            w(f"                bVel.Velocity=d.Magnitude>0 and d.Unit*{spd} or Vector3.zero")
            w("                bGyro.CFrame=cam.CFrame")
            w("            end)")
            if use_notif: w('            DoNotif("Fly: ON  (WASD + Space/Shift)", 2)')
            w("        else")
            w("            if flyConn then flyConn:Disconnect() flyConn=nil end")
            w("            if bVel then bVel:Destroy() bVel=nil end")
            w("            if bGyro then bGyro:Destroy() bGyro=nil end")
            w("            hum.PlatformStand=false")
            if use_notif: w('            DoNotif("Fly: OFF", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Noclip Toggle":
            w("do"); w("    local ncOn=false, ncConn")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("        ncOn=not ncOn")
            w("        if ncOn then")
            w("            ncConn=game:GetService('RunService').Stepped:Connect(function()")
            w("                local char=speaker.Character if not char then return end")
            w("                for _,p in ipairs(char:GetDescendants()) do")
            w("                    if p:IsA('BasePart') then p.CanCollide=false end")
            w("                end")
            w("            end)")
            if use_notif: w('            DoNotif("Noclip: ON", 2)')
            w("        else")
            w("            if ncConn then ncConn:Disconnect() ncConn=nil end")
            if use_notif: w('            DoNotif("Noclip: OFF", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Infinite Jump":
            w("do"); w("    local ijOn=false, ijConn")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("        ijOn=not ijOn")
            w("        if ijOn then")
            w("            ijConn=game:GetService('UserInputService').JumpRequest:Connect(function()")
            w("                local char=speaker.Character")
            w("                local hum=char and char:FindFirstChildOfClass('Humanoid')")
            w("                if hum and hum:GetState()~=Enum.HumanoidStateType.Dead then")
            w("                    hum:ChangeState(Enum.HumanoidStateType.Jumping)")
            w("                end")
            w("            end)")
            if use_notif: w('            DoNotif("Infinite Jump: ON", 2)')
            w("        else")
            w("            if ijConn then ijConn:Disconnect() ijConn=nil end")
            if use_notif: w('            DoNotif("Infinite Jump: OFF", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Teleport to Player":
            w(f'addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("    local targets=getPlayer(args[1], speaker)")
            w("    if #targets==0 then return DoNotif('Player not found.', 2) end")
            w("    local tgt=targets[1]")
            w("    if not tgt.Character then return DoNotif('No character.', 2) end")
            w("    local myRoot=speaker.Character and speaker.Character:FindFirstChild('HumanoidRootPart')")
            w("    local tRoot=tgt.Character:FindFirstChild('HumanoidRootPart')")
            w("    if myRoot and tRoot then myRoot.CFrame=tRoot.CFrame*CFrame.new(0,0,-3) end")
            if use_notif: w("    DoNotif('Teleported to '..tgt.Name, 2)")
            w("end)")

        elif t == "Bring Player":
            spread = gbool("spread")
            w(f'addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("    local targets=getPlayer(args[1], speaker)")
            w("    if #targets==0 then return DoNotif('No players.', 2) end")
            w("    local myRoot=speaker.Character and speaker.Character:FindFirstChild('HumanoidRootPart')")
            w("    if not myRoot then return end")
            w("    for i,plr in ipairs(targets) do")
            w("        local root=plr.Character and plr.Character:FindFirstChild('HumanoidRootPart')")
            w("        if root then")
            if spread:
                w("            root.CFrame=myRoot.CFrame*CFrame.new(i*3,0,-3)")
            else:
                w("            root.CFrame=myRoot.CFrame*CFrame.new(0,0,-3)")
            w("        end"); w("    end")
            if use_notif: w("    DoNotif('Brought '..#targets..' player(s).', 2)")
            w("end)")

        elif t == "Chat Spam":
            msg   = gstr("msg", "Hello!").replace('"', '\\"')
            delay = gstr("delay", "1")
            w("do"); w("    local spamOn=false, spamThread")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("        spamOn=not spamOn")
            w("        if spamOn then")
            w("            spamThread=task.spawn(function()")
            w("                while spamOn do")
            w("                    pcall(function()")
            w("                        local tc=game:GetService('TextChatService').TextChannels:FindFirstChild('RBXGeneral')")
            w(f'                        if tc then tc:SendAsync("{msg}") end')
            w("                    end)")
            w(f"                    task.wait({delay})")
            w("                end"); w("            end)")
            if use_notif: w('            DoNotif("Chat Spam: ON", 2)')
            w("        else")
            w("            spamOn=false")
            w("            if spamThread then task.cancel(spamThread) spamThread=nil end")
            if use_notif: w('            DoNotif("Chat Spam: OFF", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Fake Lag":
            lag = gstr("lag", "0.3")
            w("do"); w("    local lagOn=false, lagConn")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w(f"        local delay=tonumber(args[1]) or {lag}")
            w("        lagOn=not lagOn")
            w("        if lagOn then")
            w("            lagConn=game:GetService('RunService').Heartbeat:Connect(function()")
            w("                local t=tick() while tick()-t<delay do end")
            w("            end)")
            if use_notif: w('            DoNotif("Fake Lag: ON ("..delay.."s)", 2)')
            w("        else")
            w("            if lagConn then lagConn:Disconnect() lagConn=nil end")
            if use_notif: w('            DoNotif("Fake Lag: OFF", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Loop Notification":
            ntxt = gstr("notif_text", "Zuka is running!").replace('"', '\\"')
            ndur = gstr("notif_dur",  "2")
            nint = gstr("notif_int",  "3")
            w("do"); w("    local notifOn=false, notifThread")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("        notifOn=not notifOn")
            w("        if notifOn then")
            w("            notifThread=task.spawn(function()")
            w("                while notifOn do")
            w(f'                    DoNotif("{ntxt}", {ndur})')
            w(f"                    task.wait({nint})")
            w("                end"); w("            end)")
            w("        else"); w("            notifOn=false")
            w("            if notifThread then task.cancel(notifThread) notifThread=nil end")
            if use_notif: w('            DoNotif("Loop notif stopped.", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Custom Loop":
            delay = gstr("loop_delay", "0.1")
            try:
                body = self._wiz_loop_body.get("1.0", "end-1c").strip()
            except Exception:
                body = "-- your code here"
            ind = "\n".join("                " + l for l in body.split("\n"))
            w("do"); w("    local loopOn=false, loopThread")
            w(f'    addcmd("{cmd}", {alias_lua}, function(args, speaker)')
            w("        loopOn=not loopOn")
            w("        if loopOn then")
            w("            loopThread=task.spawn(function()")
            w("                while loopOn do")
            w(ind)
            w(f"                    task.wait({delay})")
            w("                end"); w("            end)")
            if use_notif: w(f'            DoNotif("{cmd}: RUNNING", 2)')
            w("        else"); w("            loopOn=false")
            w("            if loopThread then task.cancel(loopThread) loopThread=nil end")
            if use_notif: w(f'            DoNotif("{cmd}: STOPPED", 2)')
            w("        end"); w("    end)"); w("end")

        elif t == "Custom Command":
            try:
                body = self._wiz_cmd_body.get("1.0", "end-1c").strip()
            except Exception:
                body = "-- your code here"
            if use_pcall:
                w(f'addcmd("{cmd}", {alias_lua}, function(args, speaker)')
                w("    local ok, err = pcall(function()")
                for l in body.split("\n"): w("        " + l)
                w("    end)")
                w("    if not ok then DoNotif('Error: '..tostring(err), 4) end")
                if use_notif: w(f'    if ok then DoNotif("{cmd}: done!", 2) end')
                w("end)")
                return "\n".join(lines)
            else:
                w(f'addcmd("{cmd}", {alias_lua}, function(args, speaker)')
                for l in body.split("\n"): w("    " + l)
                if use_notif: w(f'    DoNotif("{cmd}: done!", 2)')
                w("end)")
                return "\n".join(lines)

        raw = "\n".join(lines)
        if use_pcall and t != "Custom Command":
            indented = "\n".join("    " + l for l in raw.split("\n"))
            return (f"local ok, err = pcall(function()\n{indented}\nend)\n"
                    f'if not ok then warn("[{cmd}] Error: "..tostring(err)) end')
        return raw

    def _wiz_explain(self, t):
        EXPLAIN = {
            "Speed Modifier":     "Changes how fast your character walks. Type your command in chat. If you enabled custom arg, you can pass a number like ';speed 200'. Normal Roblox speed is 16.",
            "Fly Toggle":         "Lets your character fly using WASD + Space/Shift. Uses BodyVelocity and BodyGyro — the standard fly method. Toggle on/off with your command.",
            "Noclip Toggle":      "Lets your character walk through walls and floors by disabling collision on all body parts every Stepped frame. Toggle on/off.",
            "Infinite Jump":      "Hooks the JumpRequest event so you can jump unlimited times mid-air. Toggle on/off.",
            "Teleport to Player": "Teleports your character next to a target player. Usage: ;tp PlayerName — supports partial names.",
            "Bring Player":       "Pulls other players to your location. Supports 'all', 'others', and partial names.",
            "Chat Spam":          "Sends a message in chat on a repeating loop via TextChatService. Toggle on/off.",
            "Fake Lag":           "Blocks the RunService Heartbeat thread to simulate ping lag. Affects your own client — use carefully.",
            "Loop Notification":  "Shows a popup notification on a repeating loop. Toggle on/off.",
            "Custom Loop":        "Runs your custom Lua code on a repeating loop. Toggle on/off with your command.",
            "Custom Command":     "Runs your custom Lua code once every time you type the command in chat.",
        }
        return EXPLAIN.get(t, "Script generated by Zuka Wizard.")

    def _wiz_to_builder(self, code, cmd):
        try:
            self._body_box.configure(state="normal")
            self._body_box.delete("1.0", "end")
            self._body_box.insert("1.0", code)
            self._name_var.set(cmd)
        except Exception:
            pass
        for name, btn in self._tab_btns.items():
            if "Builder" in name:
                btn.invoke()
                break

    # ── Page: Presets ────────────────────────────────────────────────────────

    PRESETS = {
        "🏃 Movement Pack  (speed + jump + noclip)": (
            "Standalone — speed, jump power, and noclip all in one. No framework needed.",
'-- ════════════════════════════════════════\n-- Movement Pack  |  Zuka Panel\n-- ;speed [val]  ;jump [val]  ;noclip\n-- ════════════════════════════════════════\nlocal Players=game:GetService("Players")\nlocal RunService=game:GetService("RunService")\nlocal LocalPlayer=Players.LocalPlayer\nlocal PREFIX=";"\nlocal cmds={}\nlocal function addcmd(n,al,fn) cmds[#cmds+1]={NAME=n,ALIAS=al,FN=fn} end\nlocal function execCmd(s)\n    local p=s:split(" ") local n=table.remove(p,1):lower()\n    for _,c in ipairs(cmds) do\n        if c.NAME:lower()==n then task.spawn(pcall,c.FN,p,LocalPlayer) return end\n        for _,a in ipairs(c.ALIAS) do if a:lower()==n then task.spawn(pcall,c.FN,p,LocalPlayer) return end end\n    end\nend\nlocal function DoNotif(msg,dur)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="MvNotif" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LocalPlayer.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,240,0,30) f.Position=UDim2.new(0.5,-120,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(0,229,255) l.Font=Enum.Font.GothamBold l.TextSize=13 l.Text=msg\n    task.delay(dur or 2,function() if sg.Parent then sg:Destroy() end end)\nend\nLocalPlayer.Chatted:Connect(function(msg) if msg:sub(1,#PREFIX):lower()==PREFIX then execCmd(msg:sub(#PREFIX+1)) end end)\naddcmd("speed",{"ws","walkspeed"},function(args,sp)\n    local hum=sp.Character and sp.Character:FindFirstChildOfClass("Humanoid")\n    if not hum then return end hum.WalkSpeed=tonumber(args[1]) or 100\n    DoNotif("Speed: "..(args[1] or "100"),2)\nend)\naddcmd("jump",{"jp","jumppower"},function(args,sp)\n    local hum=sp.Character and sp.Character:FindFirstChildOfClass("Humanoid")\n    if not hum then return end hum.JumpPower=tonumber(args[1]) or 100\n    DoNotif("JumpPower: "..(args[1] or "100"),2)\nend)\ndo\n    local ncOn=false local ncConn\n    addcmd("noclip",{"nc","ghost"},function(args,sp)\n        ncOn=not ncOn\n        if ncOn then\n            ncConn=RunService.Stepped:Connect(function()\n                local c=sp.Character if not c then return end\n                for _,p in ipairs(c:GetDescendants()) do if p:IsA("BasePart") then p.CanCollide=false end end\n            end)\n            DoNotif("Noclip: ON",2)\n        else if ncConn then ncConn:Disconnect() ncConn=nil end DoNotif("Noclip: OFF",2) end\n    end)\nend\nDoNotif("Movement Pack loaded! ;speed / ;jump / ;noclip",4)'
        ),
        "✈️ Fly Script  (standalone)": (
            "Fully standalone fly script. No framework required. WASD + Space/Shift to move.",
'-- ════════════════════════════════════════\n-- Fly Script  |  Standalone  |  ;fly\n-- ════════════════════════════════════════\nlocal Players=game:GetService("Players")\nlocal RunService=game:GetService("RunService")\nlocal UIS=game:GetService("UserInputService")\nlocal LP=Players.LocalPlayer\nlocal PREFIX=";"\nlocal FLY_SPEED=80\nlocal flyOn=false local flyConn local bVel,bGyro\nlocal function Notif(msg)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="FlyN" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,220,0,28) f.Position=UDim2.new(0.5,-110,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(0,229,255) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg\n    task.delay(2,function() if sg.Parent then sg:Destroy() end end)\nend\nlocal function startFly()\n    local char=LP.Character if not char then return end\n    local hum=char:FindFirstChildOfClass("Humanoid")\n    local root=char:FindFirstChild("HumanoidRootPart")\n    if not(hum and root) then return end\n    hum.PlatformStand=true\n    bVel=Instance.new("BodyVelocity",root) bVel.MaxForce=Vector3.new(1e9,1e9,1e9) bVel.Velocity=Vector3.zero\n    bGyro=Instance.new("BodyGyro",root) bGyro.MaxTorque=Vector3.new(1e9,1e9,1e9) bGyro.P=1e6\n    local cam=workspace.CurrentCamera\n    flyConn=RunService.Heartbeat:Connect(function()\n        local d=Vector3.zero\n        if UIS:IsKeyDown(Enum.KeyCode.W) then d=d+cam.CFrame.LookVector end\n        if UIS:IsKeyDown(Enum.KeyCode.S) then d=d-cam.CFrame.LookVector end\n        if UIS:IsKeyDown(Enum.KeyCode.A) then d=d-cam.CFrame.RightVector end\n        if UIS:IsKeyDown(Enum.KeyCode.D) then d=d+cam.CFrame.RightVector end\n        if UIS:IsKeyDown(Enum.KeyCode.Space) then d=d+Vector3.yAxis end\n        if UIS:IsKeyDown(Enum.KeyCode.LeftShift) then d=d-Vector3.yAxis end\n        bVel.Velocity=d.Magnitude>0 and d.Unit*FLY_SPEED or Vector3.zero\n        bGyro.CFrame=cam.CFrame\n    end)\n    Notif("Fly: ON  (WASD+Space/Shift)")\nend\nlocal function stopFly()\n    if flyConn then flyConn:Disconnect() flyConn=nil end\n    if bVel then bVel:Destroy() bVel=nil end\n    if bGyro then bGyro:Destroy() bGyro=nil end\n    local hum=LP.Character and LP.Character:FindFirstChildOfClass("Humanoid")\n    if hum then hum.PlatformStand=false end\n    Notif("Fly: OFF")\nend\nLP.Chatted:Connect(function(msg)\n    local lm=msg:lower()\n    if lm==PREFIX.."fly" or lm==PREFIX.."f" then flyOn=not flyOn if flyOn then startFly() else stopFly() end end\nend)\nNotif("Fly loaded! Type ;fly to toggle.")'
        ),
        "🔍 ESP  (name tags)": (
            "Shows player name tags above heads. Toggle with ;esp.",
'-- ════════════════════════════════════════\n-- ESP Name Tags  |  ;esp to toggle\n-- ════════════════════════════════════════\nlocal Players=game:GetService("Players")\nlocal LP=Players.LocalPlayer\nlocal PREFIX=";"\nlocal espOn=false\nlocal tags={}\nlocal function Notif(msg)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="ESPn" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,180,0,26) f.Position=UDim2.new(0.5,-90,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(255,80,80) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg\n    task.delay(2,function() if sg.Parent then sg:Destroy() end end)\nend\nlocal function addTag(plr)\n    if plr==LP then return end\n    local function attach()\n        local char=plr.Character or plr.CharacterAdded:Wait()\n        local root=char:WaitForChild("HumanoidRootPart",5)\n        if not root then return end\n        local bb=Instance.new("BillboardGui",root) bb.Name="ZESP" bb.Size=UDim2.new(0,100,0,28) bb.StudsOffset=Vector3.new(0,3,0) bb.AlwaysOnTop=true bb.ResetOnSpawn=false\n        local lbl=Instance.new("TextLabel",bb) lbl.Size=UDim2.fromScale(1,1) lbl.BackgroundTransparency=1 lbl.TextColor3=Color3.fromRGB(255,80,80) lbl.Font=Enum.Font.GothamBold lbl.TextSize=14 lbl.Text=plr.Name lbl.TextStrokeTransparency=0\n        tags[plr]=bb\n    end\n    task.spawn(attach)\n    plr.CharacterAdded:Connect(function() if espOn then if tags[plr] then pcall(function() tags[plr]:Destroy() end) end task.spawn(attach) end end)\nend\nlocal function removeTag(plr) if tags[plr] then pcall(function() tags[plr]:Destroy() end) tags[plr]=nil end end\nlocal function enableESP() for _,p in ipairs(Players:GetPlayers()) do addTag(p) end Players.PlayerAdded:Connect(function(p) if espOn then addTag(p) end end) Notif("ESP: ON") end\nlocal function disableESP() for p in pairs(tags) do removeTag(p) end Notif("ESP: OFF") end\nLP.Chatted:Connect(function(msg) if msg:lower()==PREFIX.."esp" then espOn=not espOn if espOn then enableESP() else disableESP() end end end)\nNotif("ESP loaded! Type ;esp")'
        ),
        "🎯 Remote Spy  (standalone)": (
            "Logs every FireServer / InvokeServer to console. Requires hookmetamethod.",
'-- ════════════════════════════════════════\n-- Remote Spy  |  ;rspy to toggle\n-- Requires: hookmetamethod (exploit API)\n-- ════════════════════════════════════════\nlocal LP=game:GetService("Players").LocalPlayer\nlocal spyOn=false local orig\nlocal blacklist={}  -- blacklist["RemoteName"]=true to silence it\nlocal function Notif(msg)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="RSpy" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,280,0,28) f.Position=UDim2.new(0.5,-140,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(255,200,50) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg\n    task.delay(2.5,function() if sg.Parent then sg:Destroy() end end)\nend\nlocal function enable()\n    orig=hookmetamethod(game,"__namecall",newcclosure(function(self,...)\n        local m=getnamecallmethod()\n        if(m=="FireServer" or m=="InvokeServer") and (self:IsA("RemoteEvent") or self:IsA("RemoteFunction")) and not blacklist[self.Name] then\n            local a={...} local s={}\n            for i,v in ipairs(a) do s[i]=typeof(v).."("..tostring(v)..")" end\n            print(("[RemoteSpy] %s:%s(%s)"):format(self:GetFullName(),m,table.concat(s,", ")))\n        end\n        return orig(self,...)\n    end))\n    Notif("Remote Spy: ON (check console)")\nend\nlocal function disable() if orig then hookmetamethod(game,"__namecall",orig) orig=nil end Notif("Remote Spy: OFF") end\nLP.Chatted:Connect(function(msg) local lm=msg:lower() if lm==";rspy" or lm==";spy" or lm==";remotespy" then spyOn=not spyOn if spyOn then enable() else disable() end end end)\nNotif("Remote Spy loaded! Type ;rspy")'
        ),
        "🌐 Loadstring Loader": (
            "Load any URL-hosted script as a chat command. Pre-register scripts by name.",
'-- ════════════════════════════════════════\n-- Loadstring Hub Loader\n-- ;load <name>  |  ;scripts\n-- ════════════════════════════════════════\nlocal LP=game:GetService("Players").LocalPlayer\nlocal PREFIX=";"\nlocal registered={\n    ["dex"]="https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Zex.lua",\n    -- add more: ["scriptname"]="https://raw.githubusercontent.com/..."\n}\nlocal function Notif(msg,dur)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="LdrN" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,300,0,30) f.Position=UDim2.new(0.5,-150,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(80,255,150) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg l.TextTruncate=Enum.TextTruncate.AtEnd\n    task.delay(dur or 3,function() if sg.Parent then sg:Destroy() end end)\nend\nLP.Chatted:Connect(function(msg)\n    if msg:sub(1,#PREFIX):lower()~=PREFIX then return end\n    local rest=msg:sub(#PREFIX+1)\n    local parts=rest:split(" ")\n    local cmd=parts[1] and parts[1]:lower() or ""\n    local arg=parts[2] or ""\n    if cmd=="load" then\n        local url=registered[arg] or (arg:find("^https?://") and arg)\n        if not url then Notif("Unknown: "..arg,3) return end\n        Notif("Loading: "..arg.."...",2)\n        task.spawn(function()\n            local ok,err=pcall(function() loadstring(game:HttpGet(url))() end)\n            if ok then Notif(arg.." loaded!",2) else Notif("Failed: "..tostring(err):sub(1,40),4) warn(err) end\n        end)\n    elseif cmd=="scripts" then\n        local list={} for k in pairs(registered) do list[#list+1]=k end\n        Notif("Scripts: "..table.concat(list,", "),5)\n    end\nend)\nNotif("Loader ready!  ;load dex  |  ;scripts",4)'
        ),
        "📡 Auto-Farm Template": (
            "Safe auto-farm loop. Edit REMOTE_NAME and LOOP_DELAY at the top. ;farm to toggle.",
'-- ════════════════════════════════════════\n-- Auto-Farm Template  |  ;farm to toggle\n-- ════════════════════════════════════════\nlocal REMOTE_NAME = "CollectCoin"\nlocal REMOTE_ROOT = game:GetService("ReplicatedStorage")\nlocal LOOP_DELAY  = 0.5\n-- ────────────────────────────────────────\nlocal LP=game:GetService("Players").LocalPlayer\nlocal farmOn=false local farmThread\nlocal function Notif(msg,dur)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="FarmN" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,260,0,28) f.Position=UDim2.new(0.5,-130,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(255,200,80) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg\n    task.delay(dur or 2,function() if sg.Parent then sg:Destroy() end end)\nend\nlocal function findRemote()\n    for _,v in ipairs(REMOTE_ROOT:GetDescendants()) do\n        if v:IsA("RemoteEvent") and v.Name:lower()==REMOTE_NAME:lower() then return v end\n    end\nend\nLP.Chatted:Connect(function(msg)\n    if msg:lower()~=";farm" then return end\n    farmOn=not farmOn\n    if farmOn then\n        local remote=findRemote()\n        if not remote then Notif("Remote not found: "..REMOTE_NAME,3) farmOn=false return end\n        farmThread=task.spawn(function()\n            local n=0\n            while farmOn do\n                pcall(function() remote:FireServer() end)\n                n=n+1\n                if n%20==0 then Notif("Farm: "..n.." fires",1.5) end\n                task.wait(LOOP_DELAY)\n            end\n        end)\n        Notif("Auto-Farm: ON",2)\n    else\n        farmOn=false\n        if farmThread then task.cancel(farmThread) farmThread=nil end\n        Notif("Auto-Farm: OFF",2)\n    end\nend)\nNotif("Farm loaded! Edit REMOTE_NAME then type ;farm",4)'
        ),
        "🛡 Anti-Fling  (standalone)": (
            "Prevents other players from flinging your character. Zeroes their velocity every Stepped frame.",
'-- ════════════════════════════════════\n-- Anti-Fling Standalone  |  ;antifling\n-- Credits: zuka, AnthonyIsntHere\n-- ════════════════════════════════════\nlocal Players=game:GetService("Players")\nlocal RunService=game:GetService("RunService")\nlocal LP=Players.LocalPlayer\nlocal PREFIX=";"\nlocal afOn=false local afConn\nlocal function Notif(msg)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="AFn" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,220,0,28) f.Position=UDim2.new(0.5,-110,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(0,229,255) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg\n    task.delay(2,function() if sg.Parent then sg:Destroy() end end)\nend\nLP.Chatted:Connect(function(msg)\n    if msg:lower()~=PREFIX.."antifling" and msg:lower()~=PREFIX.."af" then return end\n    afOn=not afOn\n    if afOn then\n        afConn=RunService.Stepped:Connect(function()\n            for _,plr in next,Players:GetPlayers() do\n                if plr~=LP and plr.Character then\n                    pcall(function()\n                        for _,v in next,plr.Character:GetChildren() do\n                            if v:IsA("BasePart") and v.CanCollide then\n                                v.CanCollide=false\n                                if v.Name=="Torso" then v.Massless=true end\n                                v.Velocity=Vector3.new() v.RotVelocity=Vector3.new()\n                            end\n                        end\n                    end)\n                end\n            end\n        end)\n        Notif("Anti-Fling: ON")\n    else\n        if afConn then afConn:Disconnect() afConn=nil end\n        Notif("Anti-Fling: OFF")\n    end\nend)\nNotif("Anti-Fling loaded! ;antifling or ;af")'
        ),
        "🚫 Disable TouchInterests  (standalone)": (
            "Destroys all TouchTransmitter instances and disables CanTouch/CanQuery on BaseParts. Replicates to server. Made by AnthonyIsntHere.",
'-- ════════════════════════════════════\n-- Disable TouchInterests\n-- Disables serverside .Touched events\n-- Made by AnthonyIsntHere\n-- ════════════════════════════════════\nlocal LP=game:GetService("Players").LocalPlayer\nlocal function Notif(msg)\n    local ok,sg=pcall(function() local s=Instance.new("ScreenGui") s.Name="TIn" s.ResetOnSpawn=false s.Parent=game:GetService("CoreGui") return s end)\n    if not ok then sg=Instance.new("ScreenGui") sg.Parent=LP.PlayerGui end\n    local f=Instance.new("Frame",sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,280,0,28) f.Position=UDim2.new(0.5,-140,0,10) f.BorderSizePixel=0\n    Instance.new("UICorner",f).CornerRadius=UDim.new(0,6)\n    local l=Instance.new("TextLabel",f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(255,150,50) l.Font=Enum.Font.GothamBold l.TextSize=12 l.Text=msg\n    task.delay(3,function() if sg.Parent then sg:Destroy() end end)\nend\nlocal count=0\nfor _,x in next,workspace:GetDescendants() do\n    if x:IsA("TouchTransmitter") then x:Destroy() count=count+1\n    elseif x:IsA("BasePart") and (x.CanTouch or x.CanQuery) then\n        x.CanTouch,x.CanQuery=false,false count=count+1\n    end\nend\nworkspace.DescendantAdded:Connect(function(x)\n    if x:IsA("TouchTransmitter") then\n        repeat task.wait() until x:IsDescendantOf(workspace)\n        x:Destroy()\n    elseif x:IsA("BasePart") and (x.CanTouch or x.CanQuery) then\n        x.CanTouch,x.CanQuery=false,false\n    end\nend)\nNotif("TouchInterests disabled on "..count.." objects!")'
        ),
    }

    def _build_presets_page(self, parent):
        left = tk.Frame(parent, bg=BG, width=260)
        left.pack(side="left", fill="y", padx=(14, 0), pady=14)
        left.pack_propagate(False)
        hdr = tk.Frame(left, bg=BG2)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="🎯 PRESET SCRIPTS", font=FONT_TITLE,
                 fg=ACCENT, bg=BG2, anchor="w").pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(hdr, text="Ready-to-run standalone scripts.\nNo setup needed — copy and execute.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2, justify="left").pack(fill="x", padx=8, pady=(0, 6))
        self._label(left, "PRESETS")
        lb = tk.Listbox(left, bg=BG2, fg=TEXT, selectbackground=ACCENT,
                        selectforeground=TEXT, font=FONT_SM, bd=0,
                        highlightthickness=1, highlightcolor=BORDER,
                        activestyle="none", cursor="hand2")
        lb.pack(fill="both", expand=True)
        for name in self.PRESETS:
            lb.insert("end", "  " + name)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)
        self._preset_desc = tk.Label(right, text="Select a preset to preview.",
                                     font=FONT_SM, fg=SUBTEXT, bg=BG2,
                                     wraplength=500, justify="left", anchor="w", padx=8, pady=8)
        self._preset_desc.pack(fill="x", pady=(0, 8))
        self._label(right, "PREVIEW  —  full ready-to-run Lua")
        self._preset_out = self._text_area(right, height=28, expand=True)
        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6, 0))
        self._btn(out_btns, "📋  COPY",             lambda: self._copy(self._preset_out), CYAN).pack(side="left", padx=(0, 6))
        self._btn(out_btns, "💾  SAVE",             lambda: self._save(self._preset_out), BG3).pack(side="left",  padx=(0, 6))
        self._btn(out_btns, "→  SEND TO CONVERTER", self._preset_to_converter,            ACCENT).pack(side="left")

        def on_sel(event):
            sel = lb.curselection()
            if not sel: return
            name = lb.get(sel[0]).strip()
            desc, code = self.PRESETS.get(name, ("", ""))
            self._preset_desc.configure(text=desc)
            self._preset_out.configure(state="normal")
            self._preset_out.delete("1.0", "end")
            self._preset_out.insert("1.0", code.strip())
        lb.bind("<<ListboxSelect>>", on_sel)

    def _preset_to_converter(self):
        code = self._preset_out.get("1.0", "end-1c").strip()
        if not code: return messagebox.showinfo("Empty", "Select a preset first.")
        self._conv_input.delete("1.0", "end")
        self._conv_input.insert("1.0", code)
        for name, btn in self._tab_btns.items():
            if "Converter" in name: btn.invoke(); break

    # ── Page: Script Assembler ───────────────────────────────────────────────

    def _build_assembler_page(self, parent):
        self._asm_blocks = []
        header = tk.Frame(parent, bg=BG2)
        header.pack(fill="x")
        tk.Label(header, text="🔩  SCRIPT ASSEMBLER", font=FONT_LG,
                 fg=ACCENT, bg=BG2).pack(side="left", padx=14, pady=10)
        tk.Label(header, text="Combine multiple commands/snippets into one final script.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="left", padx=4)
        main = tk.Frame(parent, bg=BG)
        main.pack(fill="both", expand=True, padx=14, pady=8)
        left = tk.Frame(main, bg=BG, width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._label(left, "BLOCK LABEL")
        self._asm_label_var = tk.StringVar()
        self._entry(left, self._asm_label_var, placeholder="e.g. Fly Command")
        self._label(left, "BLOCK CODE  (paste any Lua)")
        self._asm_code_box = self._text_area(left, height=10)
        opt_f = tk.Frame(left, bg=BG)
        opt_f.pack(fill="x", pady=(4, 0))
        self._asm_use_pcall = self._checkbox(opt_f, "Wrap this block in pcall")
        add_row = tk.Frame(left, bg=BG)
        add_row.pack(fill="x", pady=(6, 0))
        self._btn(add_row, "➕  ADD BLOCK",           self._asm_add_block,  ACCENT).pack(side="left", padx=(0,6))
        self._btn(add_row, "📋  PASTE FROM CLIPBOARD", self._asm_paste,      BG3).pack(side="left")

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", pady=8)
        self._label(left, "SCRIPT HEADER")
        hf = tk.Frame(left, bg=BG2)
        hf.pack(fill="x")
        def hrow(lbl, var):
            r = tk.Frame(hf, bg=BG2); r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=lbl, font=FONT_SM, fg=SUBTEXT, bg=BG2, width=14, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=TEXT,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)
        self._asm_title  = tk.StringVar(value="My Script")
        self._asm_prefix = tk.StringVar(value=";")
        hrow("Title:",   self._asm_title)
        hrow("Prefix:",  self._asm_prefix)
        self._asm_inc_fw = self._checkbox(left, "Include full addcmd framework (addcmd, getPlayer, DoNotif, chat listener)")
        self._asm_inc_sv = self._checkbox(left, "Include common Services header")

        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self._label(right, "BLOCKS  (double-click to remove)")
        lf = tk.Frame(right, bg=BORDER, bd=1)
        lf.pack(fill="x")
        self._asm_lb = tk.Listbox(lf, bg=BG2, fg=TEXT, selectbackground=ACCENT,
                                   font=FONT_SM, bd=0, highlightthickness=0,
                                   activestyle="none", height=8)
        self._asm_lb.pack(side="left", fill="both", expand=True)
        vsb = tk.Scrollbar(lf, orient="vertical", command=self._asm_lb.yview,
                           bg=BG2, troughcolor=BG2, bd=0, width=8)
        vsb.pack(side="right", fill="y")
        self._asm_lb.configure(yscrollcommand=vsb.set)
        self._asm_lb.bind("<Double-Button-1>", self._asm_remove)
        ctrl = tk.Frame(right, bg=BG); ctrl.pack(fill="x", pady=(4, 8))
        self._btn(ctrl, "↑",        self._asm_up,                                    BG3).pack(side="left", padx=(0,4))
        self._btn(ctrl, "↓",        self._asm_down,                                  BG3).pack(side="left", padx=(0,4))
        self._btn(ctrl, "🗑 Remove", self._asm_remove,                                "#aa2222").pack(side="left", padx=(0,4))
        self._btn(ctrl, "🗑 Clear",  lambda: (self._asm_blocks.clear(), self._asm_refresh()), BG3).pack(side="left")

        self._label(right, "ASSEMBLED OUTPUT")
        self._asm_out = self._text_area(right, height=16, expand=True)
        self._asm_out.configure(state="disabled")
        out_row = tk.Frame(right, bg=BG); out_row.pack(fill="x", pady=(6, 0))
        self._btn(out_row, "⚡  ASSEMBLE", self._asm_assemble,                 ACCENT).pack(side="left", padx=(0,6))
        self._btn(out_row, "📋  COPY",     lambda: self._copy(self._asm_out),  CYAN).pack(side="left",  padx=(0,6))
        self._btn(out_row, "💾  SAVE",     lambda: self._save(self._asm_out),  BG3).pack(side="left")

    def _asm_add_block(self):
        label = self._asm_label_var.get().strip() or f"Block {len(self._asm_blocks)+1}"
        code  = self._asm_code_box.get("1.0", "end-1c").strip()
        if not code: return messagebox.showwarning("Empty", "Paste code into the block area first.")
        if self._asm_use_pcall.get():
            ind = "\n".join("        " + l for l in code.split("\n"))
            code = f"do -- {label}\n    local ok,err=pcall(function()\n{ind}\n    end)\n    if not ok then warn('[{label}]',err) end\nend"
        self._asm_blocks.append({"label": label, "code": code})
        self._asm_refresh()
        self._asm_label_var.set("")
        self._asm_code_box.delete("1.0", "end")

    def _asm_paste(self):
        try:
            t = pyperclip.paste()
            if t: self._asm_code_box.delete("1.0","end"); self._asm_code_box.insert("1.0",t)
        except Exception:
            messagebox.showinfo("Clipboard","pyperclip unavailable — paste manually (Ctrl+V).")

    def _asm_refresh(self):
        self._asm_lb.delete(0, "end")
        for i, b in enumerate(self._asm_blocks):
            n = b["code"].count("\n") + 1
            self._asm_lb.insert("end", f"  [{i+1}] {b['label']}  ({n} lines)")

    def _asm_up(self):
        sel = self._asm_lb.curselection()
        if not sel or sel[0]==0: return
        i = sel[0]; self._asm_blocks[i-1],self._asm_blocks[i]=self._asm_blocks[i],self._asm_blocks[i-1]
        self._asm_refresh(); self._asm_lb.selection_set(i-1)

    def _asm_down(self):
        sel = self._asm_lb.curselection()
        if not sel or sel[0]>=len(self._asm_blocks)-1: return
        i = sel[0]; self._asm_blocks[i],self._asm_blocks[i+1]=self._asm_blocks[i+1],self._asm_blocks[i]
        self._asm_refresh(); self._asm_lb.selection_set(i+1)

    def _asm_remove(self, event=None):
        sel = self._asm_lb.curselection()
        if sel: self._asm_blocks.pop(sel[0]); self._asm_refresh()

    def _asm_assemble(self):
        if not self._asm_blocks: return messagebox.showwarning("Empty","Add at least one block first.")
        title  = self._asm_title.get().strip()  or "My Script"
        prefix = self._asm_prefix.get().strip() or ";"
        inc_fw = self._asm_inc_fw.get()
        inc_sv = self._asm_inc_sv.get()
        lines=[]; w=lines.append
        w("-- ════════════════════════════════════════════════════════")
        w(f"-- {title}  |  Assembled by Zuka Panel")
        w(f"-- {len(self._asm_blocks)} block(s)")
        w("-- ════════════════════════════════════════════════════════"); w("")
        if inc_sv:
            for svc in ["Players","RunService","UserInputService","TweenService","ReplicatedStorage"]:
                w(f'local {svc}=game:GetService("{svc}")')
            w("local LocalPlayer=Players.LocalPlayer"); w("local speaker=LocalPlayer"); w("")
        if inc_fw:
            w(f'local PREFIX="{prefix}"'); w("local cmds={}"); w("")
            w("local function addcmd(n,al,fn) cmds[#cmds+1]={NAME=n,ALIAS=al or {},FN=fn} end")
            w("local function execCmd(s,plr)")
            w("    plr=plr or game:GetService('Players').LocalPlayer")
            w("    local p=s:split(' ') local n=table.remove(p,1):lower()")
            w("    for _,c in ipairs(cmds) do")
            w("        if c.NAME:lower()==n then task.spawn(pcall,c.FN,p,plr) return end")
            w("        for _,a in ipairs(c.ALIAS) do if a:lower()==n then task.spawn(pcall,c.FN,p,plr) return end end")
            w("    end"); w("end")
            w("local function getPlayer(arg,plr)")
            w("    if not arg or arg=='' then return {plr} end local low=arg:lower()")
            w("    if low=='me' then return {plr} end")
            w("    if low=='all' then return game:GetService('Players'):GetPlayers() end")
            w("    if low=='others' then local t={} for _,p in ipairs(game:GetService('Players'):GetPlayers()) do if p~=plr then t[#t+1]=p end end return t end")
            w("    local t={} for _,p in ipairs(game:GetService('Players'):GetPlayers()) do if p.Name:lower():find(low,1,true) then t[#t+1]=p end end return t")
            w("end")
            w("local _ng; local function DoNotif(msg,dur)")
            w("    if _ng then pcall(function() _ng:Destroy() end) end")
            w("    local ok,sg=pcall(function() local s=Instance.new('ScreenGui') s.Name='ZN' s.ResetOnSpawn=false s.Parent=game:GetService('CoreGui') return s end)")
            w("    if not ok then sg=Instance.new('ScreenGui') sg.Parent=game:GetService('Players').LocalPlayer.PlayerGui end")
            w("    _ng=sg; local f=Instance.new('Frame',sg) f.BackgroundColor3=Color3.fromRGB(14,14,22) f.Size=UDim2.new(0,280,0,32) f.Position=UDim2.new(0.5,-140,0,10) f.BorderSizePixel=0")
            w("    Instance.new('UICorner',f).CornerRadius=UDim.new(0,6)")
            w("    local l=Instance.new('TextLabel',f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.fromRGB(0,229,255) l.Font=Enum.Font.GothamBold l.TextSize=13 l.Text=msg")
            w("    task.delay(dur or 3,function() if sg.Parent then sg:Destroy() end end)")
            w("end")
            w(f"local LP=game:GetService('Players').LocalPlayer")
            w("LP.Chatted:Connect(function(msg)")
            w(f"    if msg:sub(1,#{prefix}):lower()=='{prefix}' then execCmd(msg:sub(#{prefix}+1),LP) end")
            w("end)"); w("")
        w("-- ════════════════════════════════════════════════════════")
        w("-- BLOCKS"); w("-- ════════════════════════════════════════════════════════"); w("")
        for b in self._asm_blocks:
            w(f"-- ── {b['label']} ──────────────────────────────────")
            w(b["code"]); w("")
        if inc_fw: w(f'DoNotif("{title} loaded! ({len(self._asm_blocks)} blocks)", 3)')
        self._set_output(self._asm_out, "\n".join(lines))

    # ── Page: Config Block Generator ─────────────────────────────────────────

    def _build_config_page(self, parent):
        self._cfg_entries = []
        header = tk.Frame(parent, bg=BG2)
        header.pack(fill="x")
        tk.Label(header, text="⚙️  CONFIG BLOCK GENERATOR", font=FONT_LG,
                 fg=ACCENT, bg=BG2).pack(side="left", padx=14, pady=10)
        tk.Label(header, text="Build a clean Config table at the top of any script — easy to edit, no Lua required.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="left", padx=4)
        main = tk.Frame(parent, bg=BG)
        main.pack(fill="both", expand=True, padx=14, pady=8)
        left = tk.Frame(main, bg=BG, width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._label(left, "ADD ENTRY")
        self._cfg_evars = {}
        ef = tk.Frame(left, bg=BG2); ef.pack(fill="x", pady=(0,6))
        def erow(lbl, key, col=TEXT, ph=""):
            r=tk.Frame(ef,bg=BG2); r.pack(fill="x",padx=6,pady=2)
            tk.Label(r,text=lbl,font=FONT_SM,fg=SUBTEXT,bg=BG2,width=12,anchor="w").pack(side="left")
            var=tk.StringVar()
            e=tk.Entry(r,textvariable=var,font=FONT_UI,bg=BG3,fg=col,
                       insertbackground=CYAN,bd=0,highlightthickness=1,
                       highlightcolor=ACCENT,highlightbackground=BORDER)
            e.pack(side="left",fill="x",expand=True,ipady=4)
            if ph:
                e.insert(0,ph); e.configure(fg=SUBTEXT)
                def fi(ev,_e=e,_c=col,_p=ph):
                    if _e.get()==_p: _e.delete(0,"end"); _e.configure(fg=_c)
                def fo(ev,_e=e,_c=col,_p=ph):
                    if not _e.get(): _e.insert(0,_p); _e.configure(fg=SUBTEXT)
                e.bind("<FocusIn>",fi); e.bind("<FocusOut>",fo)
            self._cfg_evars[key]=var
        erow("Name:",    "name",    CYAN,    "e.g. FlySpeed")
        erow("Default:", "default", YELLOW,  "e.g. 80")
        erow("Comment:", "comment", SUBTEXT, "brief description")

        self._label(left, "TYPE")
        tr=tk.Frame(left,bg=BG); tr.pack(fill="x",pady=(0,8))
        self._cfg_type=tk.StringVar(value="number")
        for t,col in [("number",YELLOW),("string",CYAN),("boolean",GREEN),("Color3",ACCENT)]:
            tk.Radiobutton(tr,text=t,variable=self._cfg_type,value=t,
                           font=FONT_SM,fg=col,bg=BG,selectcolor=BG2,
                           activebackground=BG,activeforeground=col,
                           highlightthickness=0,cursor="hand2").pack(side="left",padx=(0,10))

        ar=tk.Frame(left,bg=BG); ar.pack(fill="x",pady=(4,0))
        self._btn(ar,"➕  ADD ENTRY",self._cfg_add,ACCENT).pack(side="left",padx=(0,6))
        self._btn(ar,"🗑  CLEAR ALL",lambda:(self._cfg_entries.clear(),self._cfg_refresh()),BG3).pack(side="left")

        tk.Frame(left,bg=BORDER,height=1).pack(fill="x",pady=8)
        self._label(left,"ENTRIES  (double-click to remove)")
        lf=tk.Frame(left,bg=BORDER,bd=1); lf.pack(fill="x")
        self._cfg_lb=tk.Listbox(lf,bg=BG2,fg=TEXT,selectbackground=ACCENT,
                                 font=FONT_SM,bd=0,highlightthickness=0,
                                 activestyle="none",height=8)
        self._cfg_lb.pack(fill="both",expand=True)
        self._cfg_lb.bind("<Double-Button-1>",self._cfg_remove)

        tk.Frame(left,bg=BORDER,height=1).pack(fill="x",pady=8)
        self._label(left,"QUICK PRESETS")
        presets={
            "Movement":  [("FlySpeed","80","number","How fast you fly"),("WalkSpeed","100","number","Walk speed"),("JumpPower","100","number","Jump height")],
            "Visual":    [("ESPEnabled","true","boolean","Enable ESP on load"),("ESPColor","255, 80, 80","Color3","Name tag color"),("ESPTextSize","14","number","Tag text size")],
            "General":   [("Prefix",";","string","Command prefix"),("NotifDur","3","number","Default notif duration"),("Debug","false","boolean","Print debug to console")],
        }
        for pname,pfields in presets.items():
            def load(f=pfields):
                for n,d,tp,c in f:
                    self._cfg_entries.append({"name":n,"type":tp,"default":d,"comment":c})
                self._cfg_refresh()
            self._btn(left,f"Load {pname}",load,BG3).pack(fill="x",pady=1)

        br=tk.Frame(left,bg=BG); br.pack(fill="x",pady=(8,0))
        self._btn(br,"⚡  GENERATE",self._cfg_generate,ACCENT).pack(side="left")

        right=tk.Frame(main,bg=BG); right.pack(side="left",fill="both",expand=True,padx=(14,0))
        info=tk.Frame(right,bg=BG2); info.pack(fill="x",pady=(0,8))
        tk.Label(info,text="How to use",font=FONT_SM,fg=ACCENT,bg=BG2,anchor="w").pack(fill="x",padx=8,pady=(4,2))
        tk.Label(info,text="Paste the config block at the top of your script. Access values with:  Config.FlySpeed   Config.Prefix   etc.",
                 font=FONT_SM,fg=SUBTEXT,bg=BG2,anchor="w").pack(fill="x",padx=8,pady=(0,6))
        self._label(right,"GENERATED CONFIG BLOCK")
        self._cfg_out=self._text_area(right,height=28,expand=True)
        self._cfg_out.configure(state="disabled")
        ob=tk.Frame(right,bg=BG); ob.pack(fill="x",pady=(6,0))
        self._btn(ob,"📋  COPY",lambda:self._copy(self._cfg_out),CYAN).pack(side="left",padx=(0,6))
        self._btn(ob,"💾  SAVE",lambda:self._save(self._cfg_out),BG3).pack(side="left")

    def _cfg_add(self):
        name=self._cfg_evars.get("name",tk.StringVar()).get().strip()
        if not name or name=="e.g. FlySpeed": return messagebox.showwarning("Missing","Name required.")
        default=self._cfg_evars.get("default",tk.StringVar()).get().strip()
        if default=="e.g. 80": default=""
        comment=self._cfg_evars.get("comment",tk.StringVar()).get().strip()
        if comment=="brief description": comment=""
        self._cfg_entries.append({"name":name,"type":self._cfg_type.get(),"default":default,"comment":comment})
        self._cfg_refresh()
        for k in ("name","default","comment"):
            v=self._cfg_evars.get(k)
            if v: v.set("")

    def _cfg_refresh(self):
        self._cfg_lb.delete(0,"end")
        ICONS={"number":"N","string":"S","boolean":"B","Color3":"C"}
        for e in self._cfg_entries:
            self._cfg_lb.insert("end",
                f"  [{ICONS.get(e['type'],'?')}] {e['name']} = {e['default']}"
                +(f"   -- {e['comment']}" if e["comment"] else ""))

    def _cfg_remove(self,event=None):
        sel=self._cfg_lb.curselection()
        if sel: self._cfg_entries.pop(sel[0]); self._cfg_refresh()

    def _cfg_generate(self):
        if not self._cfg_entries: return messagebox.showwarning("Empty","Add at least one entry.")
        lines=[]; w=lines.append
        w("-- ── Config ────────────────────────────────────────────────")
        w("-- Edit these values to tune the script.")
        w("-- Access any value with:  Config.PropertyName")
        w("-- ─────────────────────────────────────────────────────────")
        w("local Config = {")
        pad=max(len(e["name"]) for e in self._cfg_entries)
        for e in self._cfg_entries:
            n=e["name"]; t=e["type"]; d=e["default"] or ""
            if t=="number":   val=d or "0"
            elif t=="string": val=f'"{d}"' if not d.startswith('"') else d
            elif t=="boolean":val=d if d in("true","false") else "false"
            elif t=="Color3": val=f"Color3.fromRGB({d})" if not d.startswith("Color3") else d
            else: val=d
            sp=" "*(pad-len(n)+1)
            cmt=f"  -- {e['comment']}" if e["comment"] else ""
            w(f"    {n}{sp}= {val},{cmt}")
        w("}")
        self._set_output(self._cfg_out, "\n".join(lines))




    # ── Page: ZukaTech Panel Template Generator ──────────────────────────────
    # Based on OfficialZukaTechPanelTemplate.lua by zuka (@OverZuka)

    ZUKAPLATE_SPLASH_THEMES = {
        "Default (Cyan)": {
            "accent": "Color3.fromRGB(0, 255, 255)",
            "bg":     "Color3.fromRGB(15, 15, 20)",
            "text":   "Color3.fromRGB(240, 240, 240)",
        },
        "Red Accent": {
            "accent": "Color3.fromRGB(195, 33, 35)",
            "bg":     "Color3.fromRGB(14, 10, 10)",
            "text":   "Color3.fromRGB(240, 240, 240)",
        },
        "Green Neon": {
            "accent": "Color3.fromRGB(80, 200, 80)",
            "bg":     "Color3.fromRGB(10, 15, 10)",
            "text":   "Color3.fromRGB(230, 255, 230)",
        },
        "Purple": {
            "accent": "Color3.fromRGB(171, 84, 247)",
            "bg":     "Color3.fromRGB(12, 10, 18)",
            "text":   "Color3.fromRGB(240, 240, 250)",
        },
        "Orange": {
            "accent": "Color3.fromRGB(255, 140, 0)",
            "bg":     "Color3.fromRGB(15, 12, 8)",
            "text":   "Color3.fromRGB(255, 245, 230)",
        },
    }

    def _build_zukaplate_page(self, parent):
        header = tk.Frame(parent, bg=BG2)
        header.pack(fill="x")
        tk.Label(header, text="📄  ZUKATECH PANEL TEMPLATE", font=FONT_LG,
                 fg=ACCENT, bg=BG2).pack(side="left", padx=14, pady=10)
        tk.Label(header, text="Generates the official ZukaTech v10 panel base. Add your commands in the marked section.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="left", padx=4)

        main = tk.Frame(parent, bg=BG)
        main.pack(fill="both", expand=True, padx=14, pady=8)

        left = tk.Frame(main, bg=BG, width=360)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._label(left, "PANEL IDENTITY")
        id_frame = tk.Frame(left, bg=BG2)
        id_frame.pack(fill="x", pady=(0, 8))
        self._zt_vars = {}

        def row(lbl, key, default, col=TEXT):
            r = tk.Frame(id_frame, bg=BG2); r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=lbl, font=FONT_SM, fg=SUBTEXT, bg=BG2, width=16, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=col,
                     insertbackground=CYAN, bd=0, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER).pack(side="left", fill="x", expand=True, ipady=4)
            self._zt_vars[key] = var

        row("Script title:",  "title",    "Zuka's FunBox. v2",   CYAN)
        row("Subtitle:",      "subtitle", "by OverZuka",         YELLOW)
        row("Prefix:",        "prefix",   ";",                   GREEN)
        row("Logo AssetId:",  "logo",     "rbxassetid://7243158473", SUBTEXT)
        row("Notif on load:", "loadmsg",  "We're So back. ZukaTech v10 Loaded.", TEXT)

        self._label(left, "SPLASH SCREEN THEME")
        theme_row = tk.Frame(left, bg=BG)
        theme_row.pack(fill="x", pady=(0, 6))
        self._zt_theme = tk.StringVar(value="Default (Cyan)")
        for tname in self.ZUKAPLATE_SPLASH_THEMES:
            col_map = {"Default (Cyan)": CYAN, "Red Accent": ACCENT, "Green Neon": GREEN,
                       "Purple": "#ab54f7", "Orange": "#ffa040"}
            c = col_map.get(tname, TEXT)
            tk.Radiobutton(theme_row, text=tname, variable=self._zt_theme, value=tname,
                           font=FONT_SM, fg=c, bg=BG, selectcolor=BG2,
                           activebackground=BG, activeforeground=c,
                           highlightthickness=0, cursor="hand2").pack(anchor="w")

        self._label(left, "FEATURES TO INCLUDE")
        opt_frame = tk.Frame(left, bg=BG)
        opt_frame.pack(fill="x", pady=(0, 8))
        self._zt_splash    = self._checkbox(opt_frame, "Animated splash screen on load")
        self._zt_utilities = self._checkbox(opt_frame, "Utilities table  (findPlayer, levenshtein)")
        self._zt_notifmgr  = self._checkbox(opt_frame, "NotificationManager  (queued DoNotif)")
        self._zt_envunlock = self._checkbox(opt_frame, "Environment unlock  (setreadonly, get_mt)")
        self._zt_services  = self._checkbox(opt_frame, "All standard Services pre-declared")
        self._zt_modules   = self._checkbox(opt_frame, "Modules table + Initialize loop")
        self._zt_splash.set(True); self._zt_utilities.set(True)
        self._zt_notifmgr.set(True); self._zt_services.set(True)
        self._zt_envunlock.set(True); self._zt_modules.set(True)

        self._label(left, "PRE-BUILT COMMAND STUBS TO ADD")
        stub_frame = tk.Frame(left, bg=BG2)
        stub_frame.pack(fill="x", pady=(0, 8))
        self._zt_stubs = {}
        stubs = [
            ("speed",    "Speed modifier command"),
            ("fly",      "Fly toggle"),
            ("noclip",   "Noclip toggle"),
            ("tp",       "Teleport to player"),
            ("antifling","Anti-fling toggle"),
            ("esp",      "ESP name tags"),
        ]
        for key, desc in stubs:
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(stub_frame, text=f"  {key}  —  {desc}", variable=var,
                           font=FONT_SM, fg=TEXT, bg=BG2, selectcolor=BG3,
                           activebackground=BG2, highlightthickness=0).pack(anchor="w")
            self._zt_stubs[key] = var

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(8, 0))
        self._btn(btn_row, "⚡  GENERATE TEMPLATE", self._zt_generate, ACCENT).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "🗑  RESET", self._zt_reset, BG3).pack(side="left")

        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        info = tk.Frame(right, bg=BG2)
        info.pack(fill="x", pady=(0, 8))
        tk.Label(info, text="Based on OfficialZukaTechPanelTemplate.lua by @OverZuka",
                 font=FONT_SM, fg=ACCENT, bg=BG2, anchor="w").pack(fill="x", padx=8, pady=(4, 2))
        tk.Label(info,
                 text="The generated script is the complete ZukaTech v10 framework. Add your own RegisterCommand() calls in the marked section.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG2, anchor="w", wraplength=480, justify="left").pack(fill="x", padx=8, pady=(0, 6))

        self._label(right, "GENERATED TEMPLATE")
        self._zt_out = self._text_area(right, height=32, expand=True)
        self._zt_out.configure(state="disabled")

        ob = tk.Frame(right, bg=BG); ob.pack(fill="x", pady=(6, 0))
        self._btn(ob, "📋  COPY", lambda: self._copy(self._zt_out), CYAN).pack(side="left", padx=(0, 6))
        self._btn(ob, "💾  SAVE", lambda: self._save(self._zt_out), BG3).pack(side="left")

    def _zt_reset(self):
        self._zt_vars["title"].set("Zuka's FunBox. v2")
        self._zt_vars["subtitle"].set("by OverZuka")
        self._zt_vars["prefix"].set(";")
        self._zt_vars["loadmsg"].set("We're So back. ZukaTech v10 Loaded.")
        self._zt_theme.set("Default (Cyan)")

    def _zt_generate(self):
        title    = self._zt_vars["title"].get().strip()    or "My Panel"
        subtitle = self._zt_vars["subtitle"].get().strip() or "by zuka"
        prefix   = self._zt_vars["prefix"].get().strip()   or ";"
        logo     = self._zt_vars["logo"].get().strip()     or "rbxassetid://7243158473"
        loadmsg  = self._zt_vars["loadmsg"].get().strip()  or "Loaded."
        theme    = self.ZUKAPLATE_SPLASH_THEMES.get(self._zt_theme.get(),
                       self.ZUKAPLATE_SPLASH_THEMES["Default (Cyan)"])
        do_splash    = self._zt_splash.get()
        do_utilities = self._zt_utilities.get()
        do_notifmgr  = self._zt_notifmgr.get()
        do_envunlock = self._zt_envunlock.get()
        do_services  = self._zt_services.get()
        do_modules   = self._zt_modules.get()

        lines = []; w = lines.append

        w("--[[")
        w(f"    {title}")
        w(f"    {subtitle}")
        w(f"    Generated by Zuka Panel Builder")
        w(f"    Based on OfficialZukaTechPanelTemplate.lua by @OverZuka")
        w("--]]")
        w("")

        if do_envunlock:
            w("-- ── Environment Unlock ──────────────────────────────────────────────")
            w("local _GC_START = collectgarbage('count')")
            w("local set_ro = setreadonly or (make_writeable and function(t,v) if v then make_readonly(t) else make_writeable(t) end end)")
            w("local get_mt = getrawmetatable or debug.getmetatable")
            w("local hook_meta = hookmetamethod")
            w("local new_ccl = newcclosure or function(f) return f end")
            w("local check_caller = checkcaller or function() return false end")
            w("local clone_func = clonefunction or function(f) return f end")
            w("")
            w("local function dismantle_readonly(target)")
            w("    if type(target) ~= 'table' then return end")
            w("    pcall(function()")
            w("        if set_ro then set_ro(target, false) end")
            w("        local mt = get_mt(target)")
            w("        if mt and set_ro then set_ro(mt, false) end")
            w("    end)")
            w("end")
            w("dismantle_readonly(getgenv())")
            w("dismantle_readonly(getrenv())")
            w("")

        if do_services:
            w("-- ── Services ─────────────────────────────────────────────────────────")
            for svc in ["Players","Workspace","RunService","UserInputService","TweenService",
                        "HttpService","ReplicatedStorage","StarterGui","CoreGui","Lighting",
                        "Debris","TeleportService","TextChatService","MarketplaceService",
                        "PathfindingService","CollectionService"]:
                w(f'local {svc} = game:GetService("{svc}")')
            w("local LocalPlayer  = Players.LocalPlayer")
            w("local PlayerMouse  = LocalPlayer:GetMouse()")
            w("local CurrentCamera = Workspace.CurrentCamera")
            w("")

        if do_splash:
            w("-- ── Splash Screen ───────────────────────────────────────────────────")
            w("do")
            w("    local THEME = {")
            w(f'        Title          = "{title}",')
            w(f'        Subtitle       = "{subtitle}",')
            w(f'        IconAssetId    = "{logo}",')
            w(f'        BackgroundColor = {theme["bg"]},')
            w(f'        AccentColor     = {theme["accent"]},')
            w(f'        TextColor       = {theme["text"]},')
            w("        FadeInTime  = 0.45,")
            w("        HoldTime    = 1.2,")
            w("        FadeOutTime = 0.35,")
            w("    }")
            w("    local splashGui = Instance.new('ScreenGui')")
            w("    splashGui.Name = 'SplashScreen_' .. math.random(1000,9999)")
            w("    splashGui.IgnoreGuiInset = true splashGui.ResetOnSpawn = false")
            w("    splashGui.ZIndexBehavior = Enum.ZIndexBehavior.Global")
            w("    splashGui.Parent = CoreGui")
            w("    local bg = Instance.new('Frame', splashGui)")
            w("    bg.Size = UDim2.fromScale(1,1) bg.BackgroundColor3 = THEME.BackgroundColor bg.BackgroundTransparency = 1")
            w("    local blur = Instance.new('BlurEffect', Lighting) blur.Size = 1")
            w("    local card = Instance.new('Frame', bg)")
            w("    card.Size = UDim2.fromOffset(280,240) card.Position = UDim2.fromScale(0.5,0.5)")
            w("    card.AnchorPoint = Vector2.new(0.5,0.5) card.BackgroundColor3 = Color3.fromRGB(20,20,26) card.BackgroundTransparency = 1")
            w("    Instance.new('UICorner', card).CornerRadius = UDim.new(0,18)")
            w("    local stroke = Instance.new('UIStroke', card)")
            w("    stroke.Thickness = 1 stroke.Color = THEME.AccentColor stroke.Transparency = 0")
            w("    local icon = Instance.new('ImageLabel', card)")
            w("    icon.Size = UDim2.fromOffset(80,80) icon.Position = UDim2.fromScale(0.5,0.3)")
            w("    icon.AnchorPoint = Vector2.new(0.5,0.5) icon.BackgroundTransparency = 1")
            w("    icon.ImageColor3 = THEME.AccentColor icon.Image = THEME.IconAssetId icon.ImageTransparency = 0.6")
            w("    local ttl = Instance.new('TextLabel', card)")
            w("    ttl.Size = UDim2.new(1,-24,0,32) ttl.Position = UDim2.fromScale(0.5,0.62) ttl.AnchorPoint = Vector2.new(0.5,0.5)")
            w("    ttl.BackgroundTransparency = 1 ttl.Font = Enum.Font.Oswald")
            w("    ttl.Text = THEME.Title ttl.TextSize = 24 ttl.TextColor3 = THEME.TextColor ttl.TextTransparency = 0.6")
            w("    local sub = Instance.new('TextLabel', card)")
            w("    sub.Size = UDim2.new(1,-24,0,20) sub.Position = UDim2.fromScale(0.5,0.76) sub.AnchorPoint = Vector2.new(0.5,0.5)")
            w("    sub.BackgroundTransparency = 1 sub.Font = Enum.Font.Bangers")
            w("    sub.Text = THEME.Subtitle sub.TextSize = 13 sub.TextColor3 = THEME.TextColor sub.TextTransparency = 0")
            w("    local ti = TweenInfo.new(THEME.FadeInTime, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)")
            w("    local to = TweenInfo.new(THEME.FadeOutTime, Enum.EasingStyle.Quad, Enum.EasingDirection.In)")
            w("    TweenService:Create(bg,   ti, {BackgroundTransparency=0.3}):Play()")
            w("    TweenService:Create(blur, ti, {Size=16}):Play()")
            w("    TweenService:Create(card, ti, {Size=UDim2.fromOffset(320,260)}):Play()")
            w("    TweenService:Create(icon, ti, {ImageTransparency=0}):Play()")
            w("    TweenService:Create(ttl,  ti, {TextTransparency=0}):Play()")
            w("    TweenService:Create(sub,  ti, {TextTransparency=0.2}):Play()")
            w("    task.wait(THEME.FadeInTime + THEME.HoldTime)")
            w("    TweenService:Create(bg,   to, {BackgroundTransparency=1}):Play()")
            w("    TweenService:Create(blur, to, {Size=0}):Play()")
            w("    TweenService:Create(icon, to, {ImageTransparency=1}):Play()")
            w("    TweenService:Create(ttl,  to, {TextTransparency=1}):Play()")
            w("    TweenService:Create(sub,  to, {TextTransparency=1}):Play()")
            w("    task.wait(THEME.FadeOutTime)")
            w("    blur:Destroy() splashGui:Destroy()")
            w("end")
            w("")

        if do_utilities:
            w("-- ── Utilities ───────────────────────────────────────────────────────")
            w("local Utilities = {}")
            w("function Utilities.findPlayer(inputName)")
            w("    local input = tostring(inputName):lower()")
            w("    if input == '' then return nil end")
            w("    if input == 'me' then return Players.LocalPlayer end")
            w("    local exact, partial")
            w("    for _, p in ipairs(Players:GetPlayers()) do")
            w("        local un = p.Name:lower() local dn = p.DisplayName:lower()")
            w("        if un==input or dn==input then exact=p; break end")
            w("        if not partial and (un:sub(1,#input)==input or dn:sub(1,#input)==input) then partial=p end")
            w("    end")
            w("    return exact or partial")
            w("end")
            w("function Utilities.calculateLevenshteinDistance(s1, s2)")
            w("    local m,n = #s1,#s2")
            w("    if m==0 then return n end if n==0 then return m end")
            w("    local d = {} for i=0,m do d[i]={[0]=i} end for j=0,n do d[0][j]=j end")
            w("    for i=1,m do for j=1,n do")
            w("        local c = s1:sub(i,i)==s2:sub(j,j) and 0 or 1")
            w("        d[i][j]=math.min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+c)")
            w("    end end")
            w("    return d[m][n]")
            w("end")
            w("")

        w("-- ── Core ─────────────────────────────────────────────────────────────")
        w(f'local Prefix   = "{prefix}"')
        w("local Commands  = {}")
        w("local CommandInfo = {}")
        if do_modules:
            w("local Modules   = {}")

        if do_notifmgr:
            w("")
            w("-- ── NotificationManager ────────────────────────────────────────────")
            w("local NotificationManager = {}")
            w("do")
            w("    local queue = {} local isActive = false")
            w("    local textService = game:GetService('TextService')")
            w("    local notifGui = Instance.new('ScreenGui', CoreGui)")
            w("    notifGui.Name = 'ZukaNotifGui_v2' notifGui.ZIndexBehavior = Enum.ZIndexBehavior.Global notifGui.ResetOnSpawn = false")
            w("    local function processNext()")
            w("        if isActive or #queue==0 then return end")
            w("        isActive = true")
            w("        local data = table.remove(queue,1)")
            w("        local text, dur = data[1], data[2]")
            w("        local notif = Instance.new('TextLabel')")
            w("        notif.Font = Enum.Font.GothamSemibold notif.TextSize = 12")
            w("        notif.Text = text notif.TextWrapped = true")
            w("        notif.Size = UDim2.fromOffset(300,0)")
            w("        local tb = textService:GetTextSize(text, 12, notif.Font, Vector2.new(300,1000))")
            w("        notif.Size = UDim2.fromOffset(300, tb.Y + 20)")
            w("        notif.Position = UDim2.new(0.5,-150,0,-60)")
            w("        notif.BackgroundColor3 = Color3.fromRGB(30,30,40) notif.TextColor3 = Color3.new(1,1,1)")
            w("        Instance.new('UICorner', notif).CornerRadius = UDim.new(0,6)")
            w("        Instance.new('UIStroke', notif).Color = Color3.fromRGB(80,80,100)")
            w("        notif.Parent = notifGui")
            w("        local ti1 = TweenInfo.new(0.4,Enum.EasingStyle.Quint,Enum.EasingDirection.Out)")
            w("        local ti2 = TweenInfo.new(0.4,Enum.EasingStyle.Quint,Enum.EasingDirection.In)")
            w("        local tw1 = TweenService:Create(notif,ti1,{Position=UDim2.new(0.5,-150,0,10)}) tw1:Play() tw1.Completed:Wait()")
            w("        task.wait(dur)")
            w("        local tw2 = TweenService:Create(notif,ti2,{Position=UDim2.new(0.5,-150,0,-60)}) tw2:Play() tw2.Completed:Wait()")
            w("        notif:Destroy() isActive=false task.spawn(processNext)")
            w("    end")
            w("    function NotificationManager.Send(text, duration)")
            w("        table.insert(queue, {tostring(text), duration or 1})")
            w("        task.spawn(processNext)")
            w("    end")
            w("end")
            w("function DoNotif(text, duration)")
            w("    NotificationManager.Send(text, duration)")
            w("end")
        else:
            w("")
            w("local function DoNotif(msg, dur)")
            w("    local ok,sg=pcall(function() local s=Instance.new('ScreenGui') s.Name='ZN' s.ResetOnSpawn=false s.Parent=CoreGui return s end)")
            w("    if not ok then sg=Instance.new('ScreenGui') sg.Parent=LocalPlayer.PlayerGui end")
            w("    local f=Instance.new('Frame',sg) f.BackgroundColor3=Color3.fromRGB(20,20,28) f.Size=UDim2.new(0,300,0,36) f.Position=UDim2.new(0.5,-150,0,10) f.BorderSizePixel=0")
            w("    Instance.new('UICorner',f).CornerRadius=UDim.new(0,6)")
            w("    local l=Instance.new('TextLabel',f) l.Size=UDim2.fromScale(1,1) l.BackgroundTransparency=1 l.TextColor3=Color3.new(1,1,1) l.Font=Enum.Font.GothamBold l.TextSize=13 l.Text=msg")
            w("    task.delay(dur or 2, function() if sg.Parent then sg:Destroy() end end)")
            w("end")

        w("")
        w("-- ── RegisterCommand ─────────────────────────────────────────────────")
        w("function RegisterCommand(info, func)")
        w("    if not info or not info.Name or not func then return end")
        w("    local name = info.Name:lower()")
        w("    if Commands[name] then return end")
        w("    Commands[name] = func")
        w("    if info.Aliases then")
        w("        for _, alias in ipairs(info.Aliases) do")
        w("            local al = alias:lower()")
        w("            if not Commands[al] then Commands[al] = func end")
        w("        end")
        w("    end")
        w("    table.insert(CommandInfo, info)")
        w("end")
        w("")

        # Command stubs
        stubs_to_write = [k for k, v in self._zt_stubs.items() if v.get()]
        if stubs_to_write:
            w("-- ── Pre-built Command Stubs ─────────────────────────────────────────")
            for stub in stubs_to_write:
                w(self._zt_stub_code(stub, prefix))
                w("")

        w("--[[Commands will go right below this.]]")
        w("")
        w("")
        w("")
        w("--[[Commands will go right above this.]]")
        w("")

        if do_modules:
            w("-- ── Module Initialization ───────────────────────────────────────────")
            w("for moduleName, module in pairs(Modules) do")
            w("    if type(module) == 'table' and type(module.Initialize) == 'function' then")
            w("        pcall(function()")
            w("            module:Initialize()")
            w("            print('Initialized module:', moduleName)")
            w("        end)")
            w("    end")
            w("end")
            w("")

        w("-- ── Command Processor ───────────────────────────────────────────────")
        w("local function processCommand(message)")
        w(f"    if not (message:sub(1, #{prefix}) == Prefix) then return false end")
        w("    local args = {}")
        w(f"    for word in message:sub(#{prefix}+1):gmatch('%S+') do table.insert(args, word) end")
        w("    if #args == 0 then return true end")
        w("    local cmdName = table.remove(args, 1):lower()")
        w("    local cmdFunc = Commands[cmdName]")
        w("    if cmdFunc then")
        w("        pcall(cmdFunc, args)")
        w("    else")
        w("        local best, bestDist = nil, math.huge")
        w("        if Utilities and Utilities.calculateLevenshteinDistance then")
        w("            for name in pairs(Commands) do")
        w("                local d = Utilities.calculateLevenshteinDistance(cmdName, name)")
        w("                if d < bestDist then best=name; bestDist=d end")
        w("            end")
        w("        end")
        w("        if best and bestDist <= 2 then")
        w(f'            DoNotif(\'Unknown: "\' .. cmdName .. \'". Did you mean ;\' .. best .. \'?\', 3)')
        w("        else")
        w(f"            DoNotif('Unknown command: ' .. cmdName, 3)")
        w("        end")
        w("    end")
        w("    return true")
        w("end")
        w("")
        w("-- ── Chat Listener ────────────────────────────────────────────────────")
        w("local TextChatService = game:GetService('TextChatService')")
        w("if TextChatService and TextChatService.ChatVersion == Enum.ChatVersion.TextChatService then")
        w("    TextChatService.SendingMessage:Connect(function(msg)")
        w("        if processCommand(msg.Text) then msg.ShouldSend = false end")
        w("    end)")
        w("else")
        w("    LocalPlayer.Chatted:Connect(processCommand)")
        w("end")
        w("")
        w(f'DoNotif("{loadmsg}")')

        self._set_output(self._zt_out, "\n".join(lines))

    def _zt_stub_code(self, stub, prefix):
        stubs = {
            "speed": (
                f'RegisterCommand({{Name="speed", Aliases={{"ws","walkspeed"}}, Description="Set walkspeed"}}, function(args)\n'
                f'    local char=Players.LocalPlayer.Character\n'
                f'    local hum=char and char:FindFirstChildOfClass("Humanoid")\n'
                f'    if not hum then return DoNotif("No humanoid.", 2) end\n'
                f'    hum.WalkSpeed = tonumber(args[1]) or 100\n'
                f'    DoNotif("Speed: " .. hum.WalkSpeed, 2)\n'
                f'end)'
            ),
            "fly": (
                f'do\n'
                f'    local flyOn=false local flyConn local bVel,bGyro\n'
                f'    RegisterCommand({{Name="fly", Aliases={{"f","noclipfly"}}, Description="Toggle fly"}}, function(args)\n'
                f'        flyOn=not flyOn\n'
                f'        local char=Players.LocalPlayer.Character if not char then return end\n'
                f'        local hum=char:FindFirstChildOfClass("Humanoid")\n'
                f'        local root=char:FindFirstChild("HumanoidRootPart")\n'
                f'        if not(hum and root) then return end\n'
                f'        if flyOn then\n'
                f'            hum.PlatformStand=true\n'
                f'            bVel=Instance.new("BodyVelocity",root) bVel.MaxForce=Vector3.new(1e9,1e9,1e9) bVel.Velocity=Vector3.zero\n'
                f'            bGyro=Instance.new("BodyGyro",root) bGyro.MaxTorque=Vector3.new(1e9,1e9,1e9) bGyro.P=1e6\n'
                f'            local cam=workspace.CurrentCamera local UIS=UserInputService\n'
                f'            flyConn=RunService.Heartbeat:Connect(function()\n'
                f'                local d=Vector3.zero\n'
                f'                if UIS:IsKeyDown(Enum.KeyCode.W) then d=d+cam.CFrame.LookVector end\n'
                f'                if UIS:IsKeyDown(Enum.KeyCode.S) then d=d-cam.CFrame.LookVector end\n'
                f'                if UIS:IsKeyDown(Enum.KeyCode.A) then d=d-cam.CFrame.RightVector end\n'
                f'                if UIS:IsKeyDown(Enum.KeyCode.D) then d=d+cam.CFrame.RightVector end\n'
                f'                if UIS:IsKeyDown(Enum.KeyCode.Space) then d=d+Vector3.yAxis end\n'
                f'                if UIS:IsKeyDown(Enum.KeyCode.LeftShift) then d=d-Vector3.yAxis end\n'
                f'                bVel.Velocity=d.Magnitude>0 and d.Unit*80 or Vector3.zero\n'
                f'                bGyro.CFrame=cam.CFrame\n'
                f'            end)\n'
                f'            DoNotif("Fly: ON",2)\n'
                f'        else\n'
                f'            if flyConn then flyConn:Disconnect() flyConn=nil end\n'
                f'            if bVel then bVel:Destroy() bVel=nil end\n'
                f'            if bGyro then bGyro:Destroy() bGyro=nil end\n'
                f'            hum.PlatformStand=false DoNotif("Fly: OFF",2)\n'
                f'        end\n'
                f'    end)\n'
                f'end'
            ),
            "noclip": (
                f'do\n'
                f'    local ncOn=false local ncConn\n'
                f'    RegisterCommand({{Name="noclip", Aliases={{"nc","ghost"}}, Description="Toggle noclip"}}, function(args)\n'
                f'        ncOn=not ncOn\n'
                f'        if ncOn then\n'
                f'            ncConn=RunService.Stepped:Connect(function()\n'
                f'                local char=Players.LocalPlayer.Character if not char then return end\n'
                f'                for _,p in ipairs(char:GetDescendants()) do\n'
                f'                    if p:IsA("BasePart") then p.CanCollide=false end\n'
                f'                end\n'
                f'            end)\n'
                f'            DoNotif("Noclip: ON",2)\n'
                f'        else\n'
                f'            if ncConn then ncConn:Disconnect() ncConn=nil end\n'
                f'            DoNotif("Noclip: OFF",2)\n'
                f'        end\n'
                f'    end)\n'
                f'end'
            ),
            "tp": (
                f'RegisterCommand({{Name="tp", Aliases={{"goto","teleport"}}, Description="Teleport to player"}}, function(args)\n'
                f'    if not args[1] then return DoNotif("Usage: {prefix}tp <player>", 2) end\n'
                f'    local target = Utilities and Utilities.findPlayer(args[1]) or Players:FindFirstChild(args[1])\n'
                f'    if not (target and target.Character) then return DoNotif("Player not found.", 2) end\n'
                f'    local myHRP = Players.LocalPlayer.Character and Players.LocalPlayer.Character:FindFirstChild("HumanoidRootPart")\n'
                f'    local tHRP  = target.Character:FindFirstChild("HumanoidRootPart")\n'
                f'    if myHRP and tHRP then myHRP.CFrame = tHRP.CFrame * CFrame.new(0,0,-3) end\n'
                f'    DoNotif("Teleported to " .. target.Name, 2)\n'
                f'end)'
            ),
            "antifling": (
                f'do\n'
                f'    local afOn=false local afConn\n'
                f'    RegisterCommand({{Name="antifling", Aliases={{"af"}}, Description="Prevent others from flinging you"}}, function(args)\n'
                f'        afOn=not afOn\n'
                f'        if afOn then\n'
                f'            afConn=RunService.Stepped:Connect(function()\n'
                f'                for _,plr in next,Players:GetPlayers() do\n'
                f'                    if plr~=Players.LocalPlayer and plr.Character then\n'
                f'                        pcall(function()\n'
                f'                            for _,v in next,plr.Character:GetChildren() do\n'
                f'                                if v:IsA("BasePart") and v.CanCollide then\n'
                f'                                    v.CanCollide=false\n'
                f'                                    if v.Name=="Torso" then v.Massless=true end\n'
                f'                                    v.Velocity=Vector3.new() v.RotVelocity=Vector3.new()\n'
                f'                                end\n'
                f'                            end\n'
                f'                        end)\n'
                f'                    end\n'
                f'                end\n'
                f'            end)\n'
                f'            DoNotif("Anti-Fling: ON",2)\n'
                f'        else\n'
                f'            if afConn then afConn:Disconnect() afConn=nil end\n'
                f'            DoNotif("Anti-Fling: OFF",2)\n'
                f'        end\n'
                f'    end)\n'
                f'end'
            ),
            "esp": (
                f'do\n'
                f'    local espOn=false local espTags={{}}\n'
                f'    local function addTag(plr)\n'
                f'        if plr==Players.LocalPlayer then return end\n'
                f'        task.spawn(function()\n'
                f'            local char=plr.Character or plr.CharacterAdded:Wait()\n'
                f'            local root=char:WaitForChild("HumanoidRootPart",5) if not root then return end\n'
                f'            local bb=Instance.new("BillboardGui",root) bb.Name="ZESP"\n'
                f'            bb.Size=UDim2.new(0,100,0,28) bb.StudsOffset=Vector3.new(0,3,0)\n'
                f'            bb.AlwaysOnTop=true bb.ResetOnSpawn=false\n'
                f'            local lbl=Instance.new("TextLabel",bb) lbl.Size=UDim2.fromScale(1,1)\n'
                f'            lbl.BackgroundTransparency=1 lbl.TextColor3=Color3.fromRGB(255,80,80)\n'
                f'            lbl.Font=Enum.Font.GothamBold lbl.TextSize=14 lbl.Text=plr.Name\n'
                f'            lbl.TextStrokeTransparency=0\n'
                f'            espTags[plr]=bb\n'
                f'        end)\n'
                f'    end\n'
                f'    RegisterCommand({{Name="esp", Aliases={{}}, Description="Toggle ESP name tags"}}, function(args)\n'
                f'        espOn=not espOn\n'
                f'        if espOn then\n'
                f'            for _,p in ipairs(Players:GetPlayers()) do addTag(p) end\n'
                f'            DoNotif("ESP: ON",2)\n'
                f'        else\n'
                f'            for p,bb in pairs(espTags) do pcall(function() bb:Destroy() end) end\n'
                f'            espTags={{}}\n'
                f'            DoNotif("ESP: OFF",2)\n'
                f'        end\n'
                f'    end)\n'
                f'end'
            ),
        }
        return stubs.get(stub, f'-- TODO: {stub} stub')


    def _build_guimaker_page(self, parent):
        self._gm = GUIMaker(parent)

    def _build_fx_page(self, parent):
        # Left: controls
        left = tk.Frame(parent, bg=BG, width=340)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        self._label(left, "FX TYPE")
        fx_info = {
            "🌈  Rainbow Outline":    ("Cycles through every color continuously.\nWorks on any Frame or GUI element.", "RainbowOutline"),
            "💫  Pulse Outline":      ("Single color that breathes in and out.\nGreat for buttons or notification frames.", "PulseOutline"),
            "✨  Neon Glow":          ("Double-layer stroke — sharp inner + soft outer glow.\nLooks great on dark backgrounds.", "GlowOutline"),
        }
        self._fx_type = tk.StringVar(value="🌈  Rainbow Outline")
        for name, (desc, _) in fx_info.items():
            col = {"🌈  Rainbow Outline": CYAN, "💫  Pulse Outline": YELLOW, "✨  Neon Glow": "#ab54f7"}[name]
            tk.Radiobutton(left, text=name, variable=self._fx_type, value=name,
                           font=FONT_SM, fg=col, bg=BG, selectcolor=BG2,
                           activebackground=BG, activeforeground=col,
                           highlightthickness=0, cursor="hand2",
                           command=self._fx_update_hint).pack(anchor="w", pady=2)

        self._fx_hint = tk.Label(left, text="", font=FONT_SM, fg=SUBTEXT,
                                  bg=BG2, wraplength=300, justify="left", anchor="w", padx=8, pady=6)
        self._fx_hint.pack(fill="x", pady=(4,8))

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", pady=6)
        self._label(left, "SETTINGS")

        sf = tk.Frame(left, bg=BG2)
        sf.pack(fill="x", pady=(0,8))

        def srow(label, var, col=TEXT):
            r = tk.Frame(sf, bg=BG2)
            r.pack(fill="x", padx=6, pady=3)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=14, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=col,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER, width=12)
            e.pack(side="left", ipady=4)

        self._fx_thickness = tk.StringVar(value="2")
        self._fx_speed     = tk.StringVar(value="1")
        self._fx_color     = tk.StringVar(value="0, 200, 255")
        self._fx_target    = tk.StringVar(value="Holder")
        srow("Target var:",   self._fx_target,    CYAN)
        srow("Thickness:",    self._fx_thickness,  TEXT)
        srow("Speed:",        self._fx_speed,      TEXT)
        srow("Color R,G,B:",  self._fx_color,      "#ab54f7")

        tk.Label(left, text="Color only applies to Pulse and Glow types.",
                 font=FONT_SM, fg=SUBTEXT, bg=BG, wraplength=300, justify="left").pack(anchor="w", pady=(0,8))

        self._label(left, "INCLUDE UTILITY FUNCTIONS?")
        self._fx_include_util = self._checkbox(left, "Prepend RainbowOutline / PulseOutline / GlowOutline definitions")

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(8,0))
        self._btn(btn_row, "⚡  GENERATE", self._fx_generate, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "🗑  CLEAR", lambda: self._set_output(self._fx_out, ""), BG3).pack(side="left")

        # Right: output
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        # Quick reference
        ref = tk.Frame(right, bg=BG2)
        ref.pack(fill="x", pady=(0,10))
        tk.Label(ref, text="Quick Reference — paste after your GUI code",
                 font=FONT_SM, fg=ACCENT, bg=BG2, anchor="w").pack(fill="x", padx=8, pady=(6,2))
        examples = [
            ("Rainbow on any frame:",     "RainbowOutline(MyFrame)"),
            ("Faster rainbow:",           "RainbowOutline(MyFrame, 2, 3)"),
            ("Cyan pulse:",               "PulseOutline(MyFrame, Color3.fromRGB(0,200,255))"),
            ("Purple glow:",              "GlowOutline(MyFrame, Color3.fromRGB(200,0,255), 3)"),
            ("Stop it:",                  "local stroke, conn = RainbowOutline(MyFrame)  →  conn:Disconnect()"),
        ]
        for label, code in examples:
            row = tk.Frame(ref, bg=BG2)
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=24, anchor="w").pack(side="left")
            tk.Label(row, text=code, font=(FONT_SM[0], FONT_SM[1]),
                     fg=CYAN, bg=BG2, anchor="w").pack(side="left")
        tk.Frame(ref, bg=BG2, height=4).pack()

        self._label(right, "OUTPUT")
        self._fx_out = self._text_area(right, height=28, expand=True)
        self._fx_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._fx_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._fx_out), BG3).pack(side="left")

        self._fx_update_hint()

    def _fx_update_hint(self):
        hints = {
            "🌈  Rainbow Outline":  "Cycles through every hue using HSV. Speed controls how fast it rotates. Works on any Frame.",
            "💫  Pulse Outline":    "Single color that breathes in/out. Set your color in R,G,B. Speed controls pulse rate.",
            "✨  Neon Glow":        "Two strokes layered — a sharp inner edge + a thick soft outer glow that pulses slowly.",
        }
        t = self._fx_type.get()
        self._fx_hint.configure(text=hints.get(t, ""))

    def _fx_generate(self):
        fx   = self._fx_type.get()
        tgt  = self._fx_target.get().strip() or "Holder"
        th   = self._fx_thickness.get().strip() or "2"
        spd  = self._fx_speed.get().strip() or "1"
        col  = self._fx_color.get().strip() or "0, 200, 255"

        call = ""
        if "Rainbow" in fx:
            call = f"RainbowOutline({tgt}, {th}, {spd})"
        elif "Pulse" in fx:
            call = f"PulseOutline({tgt}, Color3.fromRGB({col}), {th}, {spd})"
        elif "Glow" in fx:
            call = f"GlowOutline({tgt}, Color3.fromRGB({col}), {th})"

        result = ""
        if self._fx_include_util.get():
            result = RAINBOW_UTIL.strip() + "\n\n"
        result += f"-- Apply FX to {tgt}\n{call}"
        self._set_output(self._fx_out, result)

    # ── Page: IY Frame ───────────────────────────────────────────────────────

    def _build_iyframe_page(self, parent):
        self._iy_cmds = []

        left = tk.Frame(parent, bg=BG, width=400)
        left.pack(side="left", fill="y", padx=(14,0), pady=14)
        left.pack_propagate(False)

        self._label(left, "WINDOW SETTINGS")
        ws = tk.Frame(left, bg=BG2)
        ws.pack(fill="x", pady=(0,8))

        def wrow(label, var):
            r = tk.Frame(ws, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT, bg=BG2, width=10, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=TEXT,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)

        self._iy_title  = tk.StringVar(value="Zuka Panel")
        self._iy_prefix = tk.StringVar(value=";")
        wrow("Title:",  self._iy_title)
        wrow("Prefix:", self._iy_prefix)

        self._label(left, "THEME  (R, G, B)")
        th = tk.Frame(left, bg=BG2)
        th.pack(fill="x", pady=(0,8))

        def trow(label, var):
            r = tk.Frame(th, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT, bg=BG2, width=10, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=TEXT,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER, width=16)
            e.pack(side="left", ipady=4)

        self._iy_c1 = tk.StringVar(value="36, 36, 37")
        self._iy_c2 = tk.StringVar(value="46, 46, 47")
        self._iy_c3 = tk.StringVar(value="78, 78, 79")
        self._iy_ct = tk.StringVar(value="255, 255, 255")
        trow("Dark bg:", self._iy_c1)
        trow("Mid bg:",  self._iy_c2)
        trow("Accent:",  self._iy_c3)
        trow("Text:",    self._iy_ct)

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", pady=8)
        self._label(left, "ADD COMMAND")

        cf = tk.Frame(left, bg=BG2)
        cf.pack(fill="x", pady=(0,6))

        def crow(label, var, col=TEXT):
            r = tk.Frame(cf, bg=BG2)
            r.pack(fill="x", padx=6, pady=2)
            tk.Label(r, text=label, font=FONT_SM, fg=SUBTEXT, bg=BG2, width=10, anchor="w").pack(side="left")
            e = tk.Entry(r, textvariable=var, font=FONT_UI, bg=BG3, fg=col,
                         insertbackground=CYAN, bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side="left", fill="x", expand=True, ipady=4)

        self._iy_cmd_name  = tk.StringVar()
        self._iy_cmd_alias = tk.StringVar()
        self._iy_cmd_desc  = tk.StringVar()
        crow("Name:",    self._iy_cmd_name,  CYAN)
        crow("Aliases:", self._iy_cmd_alias, YELLOW)
        crow("Desc:",    self._iy_cmd_desc,  SUBTEXT)

        self._label(left, "COMMAND BODY  (Lua)")
        self._iy_cmd_body = self._text_area(left, height=6)

        add_row = tk.Frame(left, bg=BG)
        add_row.pack(fill="x", pady=(4,0))
        self._btn(add_row, "➕  ADD COMMAND", self._iy_add_cmd, ACCENT).pack(side="left", padx=(0,6))
        self._btn(add_row, "🗑  CLEAR ALL",
                  lambda: (self._iy_cmds.clear(), self._iy_refresh_list()), BG3).pack(side="left")

        # FX options
        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", pady=8)
        self._label(left, "VISUAL FX")
        fx_frame = tk.Frame(left, bg=BG)
        fx_frame.pack(fill="x", pady=(0,6))
        self._iy_rainbow    = self._checkbox(fx_frame, "Rainbow outline on holder")
        self._iy_pulse      = self._checkbox(fx_frame, "Pulse outline (pick color below)")
        self._iy_glow       = self._checkbox(fx_frame, "Neon glow outline")

        color_row = tk.Frame(left, bg=BG)
        color_row.pack(fill="x", pady=(0,8))
        tk.Label(color_row, text="Pulse/Glow color R,G,B:",
                 font=FONT_SM, fg=SUBTEXT, bg=BG).pack(side="left")
        self._iy_fx_color = tk.StringVar(value="0, 200, 255")
        tk.Entry(color_row, textvariable=self._iy_fx_color, font=FONT_SM,
                 bg=BG2, fg=CYAN, insertbackground=CYAN, bd=0,
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER, width=14).pack(side="left", padx=(6,0), ipady=3)

        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        ref = tk.Frame(right, bg=BG2)
        ref.pack(fill="x", pady=(0,8))
        tk.Label(ref, text="IY Player Keywords  (use in getPlayer commands)",
                 font=FONT_SM, fg=ACCENT, bg=BG2, anchor="w").pack(fill="x", padx=8, pady=(4,2))
        kws = [
            ("me",      "Speaker only"),
            ("all",     "Everyone"),
            ("others",  "Everyone except speaker"),
            ("random",  "One random player"),
            ("friends", "Speaker's friends"),
            ("team",    "Speaker's team"),
        ]
        kw_row = tk.Frame(ref, bg=BG2)
        kw_row.pack(fill="x", padx=8, pady=(0,6))
        for kw, desc in kws:
            col_frame = tk.Frame(kw_row, bg=BG2)
            col_frame.pack(side="left", padx=(0,14))
            tk.Label(col_frame, text=kw, font=(FONT_SM[0], FONT_SM[1], "bold"),
                     fg=CYAN, bg=BG2).pack(anchor="w")
            tk.Label(col_frame, text=desc, font=FONT_SM,
                     fg=SUBTEXT, bg=BG2).pack(anchor="w")

        self._label(right, "COMMANDS  (double-click to remove)")
        lf = tk.Frame(right, bg=BORDER, bd=1)
        lf.pack(fill="x")
        self._iy_listbox = tk.Listbox(
            lf, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            font=FONT_SM, bd=0, highlightthickness=0, activestyle="none", height=7
        )
        self._iy_listbox.pack(fill="both", expand=True)
        self._iy_listbox.bind("<Double-Button-1>", self._iy_remove_selected)

        gen_row = tk.Frame(right, bg=BG)
        gen_row.pack(fill="x", pady=(6,4))
        self._btn(gen_row, "⚡  GENERATE FRAME", self._iy_generate, ACCENT).pack(side="left", padx=(0,6))

        self._label(right, "OUTPUT  —  paste-and-run Lua")
        self._iy_out = self._text_area(right, height=18, expand=True)
        self._iy_out.configure(state="disabled")

        out_btns = tk.Frame(right, bg=BG)
        out_btns.pack(fill="x", pady=(6,0))
        self._btn(out_btns, "📋  COPY", lambda: self._copy(self._iy_out), CYAN).pack(side="left", padx=(0,6))
        self._btn(out_btns, "💾  SAVE", lambda: self._save(self._iy_out), BG3).pack(side="left")

    def _iy_add_cmd(self):
        name = self._iy_cmd_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Command name required.")
            return
        aliases = [a.strip() for a in self._iy_cmd_alias.get().split(",") if a.strip()]
        body    = self._iy_cmd_body.get("1.0", "end-1c")
        desc    = self._iy_cmd_desc.get().strip()
        self._iy_cmds.append({"name": name, "aliases": aliases, "body": body, "desc": desc})
        self._iy_refresh_list()
        self._iy_cmd_name.set("")
        self._iy_cmd_alias.set("")
        self._iy_cmd_desc.set("")
        self._iy_cmd_body.delete("1.0", "end")

    def _iy_refresh_list(self):
        self._iy_listbox.delete(0, "end")
        for cmd in self._iy_cmds:
            alias_str = ", ".join(cmd["aliases"]) if cmd["aliases"] else "—"
            self._iy_listbox.insert("end",
                f'  ⚡ {cmd["name"]}  [{alias_str}]'
                + (f'  —  {cmd["desc"]}' if cmd["desc"] else ""))

    def _iy_remove_selected(self, event=None):
        sel = self._iy_listbox.curselection()
        if sel:
            self._iy_cmds.pop(sel[0])
            self._iy_refresh_list()

    def _iy_generate(self):
        title  = self._iy_title.get().strip() or "Zuka Panel"
        prefix = self._iy_prefix.get().strip() or ";"
        theme  = {
            "shade1": self._iy_c1.get().strip() or "36, 36, 37",
            "shade2": self._iy_c2.get().strip() or "46, 46, 47",
            "shade3": self._iy_c3.get().strip() or "78, 78, 79",
            "text":   self._iy_ct.get().strip() or "255, 255, 255",
        }
        result = generate_iy_gui(title, prefix, self._iy_cmds, theme)

        # Inject FX
        fx_lines = []
        col = self._iy_fx_color.get().strip() or "0, 200, 255"
        if self._iy_rainbow.get() or self._iy_pulse.get() or self._iy_glow.get():
            fx_lines.append("\n" + RAINBOW_UTIL)
            fx_lines.append("-- Apply FX to the holder:")
        if self._iy_rainbow.get():
            fx_lines.append("RainbowOutline(Holder, 2, 1)")
        if self._iy_pulse.get():
            fx_lines.append(f"PulseOutline(Holder, Color3.fromRGB({col}), 2, 1.5)")
        if self._iy_glow.get():
            fx_lines.append(f"GlowOutline(Holder, Color3.fromRGB({col}), 3)")

        if fx_lines:
            result = result + "\n" + "\n".join(fx_lines)

        self._set_output(self._iy_out, result)





# ── GUI Maker ─────────────────────────────────────────────────────────────────

CANVAS_W = 480
CANVAS_H = 360
GRID     = 20

ELEM_DEFAULTS = {
    "Frame":          {"bg": "#4a6fa5", "w": 200, "h": 100, "text": None},
    "TextLabel":      {"bg": "#5aaa5a", "w": 180, "h":  40, "text": "Label"},
    "TextButton":     {"bg": "#c87832", "w": 140, "h":  36, "text": "Button"},
    "TextBox":        {"bg": "#a03278", "w": 160, "h":  36, "text": "TextBox"},
    "ImageLabel":     {"bg": "#7832c8", "w": 120, "h": 120, "text": "[ IMG ]"},
    "ScrollingFrame": {"bg": "#28aa82", "w": 200, "h": 150, "text": None},
}

HANDLE_SIZE = 8


class GMElement:
    """Represents one GUI element on the canvas."""
    _counter = 0

    def __init__(self, etype, x, y, w=None, h=None):
        GMElement._counter += 1
        d = ELEM_DEFAULTS[etype]
        self.etype    = etype
        self.name     = f"{etype}_{GMElement._counter}"
        self.x        = x
        self.y        = y
        self.w        = w or d["w"]
        self.h        = h or d["h"]
        self.bg       = d["bg"]
        self.text     = d["text"] or ""
        self.text_color = "#ffffff"
        self.text_size  = 14
        self.transparency = 0.0
        self.visible    = True
        self.corner_r   = 8
        self.zindex     = GMElement._counter + 2
        self.anchor_x   = 0.0
        self.anchor_y   = 0.0
        # scrollingframe extras
        self.canvas_w   = 480
        self.canvas_h   = 720
        # image
        self.image_id   = ""
        # logic wiring  {event: str, logic_type: str, payload: str}
        # logic_type: "execCmd" | "toggle" | "raw"
        # event: "MouseButton1Click" | "MouseButton2Click" | "MouseEnter" | "MouseLeave"
        self.logic      = []   # list of logic dicts

    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def handle_rects(self):
        """Returns dict of handle_name -> (x1,y1,x2,y2) in canvas coords."""
        s = HANDLE_SIZE
        cx, cy = self.x, self.y
        w, h   = self.w, self.h
        mids   = {
            "NW": (cx,       cy),
            "N":  (cx+w//2,  cy),
            "NE": (cx+w,     cy),
            "W":  (cx,       cy+h//2),
            "E":  (cx+w,     cy+h//2),
            "SW": (cx,       cy+h),
            "S":  (cx+w//2,  cy+h),
            "SE": (cx+w,     cy+h),
        }
        out = {}
        for name, (hx, hy) in mids.items():
            out[name] = (hx-s//2, hy-s//2, hx+s//2, hy+s//2)
        return out




def snap(v, grid=GRID, enabled=True):
    if not enabled:
        return v
    return round(v / grid) * grid


class GUIMaker:
    def __init__(self, parent):
        self.parent       = parent
        self.elements     = []        # list of GMElement, bottom=index0
        self.selected     = None
        self.undo_stack   = []
        self.redo_stack   = []
        self.snap_enabled = False
        self.grid_enabled = True
        self.proj_name    = "Untitled"
        self._drag_mode   = None      # "move" | handle name
        self._drag_start  = None      # (mx, my, orig_x, orig_y, orig_w, orig_h)
        self._prop_widgets = {}
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        p = self.parent

        # ── Top toolbar
        toolbar = tk.Frame(p, bg=BG2, height=36)
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        toolbar.pack_propagate(False)

        def tbtn(text, cmd, color=BG3):
            b = tk.Button(toolbar, text=text, font=FONT_SM, bg=color, fg=TEXT,
                          bd=0, padx=10, pady=4, cursor="hand2",
                          activebackground=ACCENT, activeforeground=TEXT,
                          command=cmd)
            b.pack(side="left", padx=2)
            return b

        tbtn("↩ Undo",    self.undo,  "#3a4aaa")
        tbtn("↪ Redo",    self.redo,  "#3a4aaa")
        tbtn("⧉ Dup",     self.duplicate_selected, "#2a6aaa")
        tbtn("🗑 Delete", self.delete_selected, "#aa2222")
        tbtn("🗑 Clear",  self.clear_all, "#882222")

        self._grid_btn = tbtn("Grid: ON", self._toggle_grid, "#223880")
        self._snap_btn = tbtn("Snap: OFF", self._toggle_snap, "#442288")

        tbtn("⬆ Export Lua", self.export_lua, "#007744")

        # project name
        tk.Label(toolbar, text="  Project:", font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="left")
        self._proj_var = tk.StringVar(value=self.proj_name)
        e = tk.Entry(toolbar, textvariable=self._proj_var, font=FONT_SM,
                     bg=BG3, fg=TEXT, bd=0, insertbackground=CYAN, width=14)
        e.pack(side="left", padx=(2, 8))
        self._proj_var.trace_add("write", lambda *_: setattr(self, "proj_name", self._proj_var.get()))

        # ── Main area
        main = tk.Frame(p, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # Left toolbox
        toolbox = tk.Frame(main, bg=BG2, width=130)
        toolbox.pack(side="left", fill="y", padx=(0, 6))
        toolbox.pack_propagate(False)

        tk.Label(toolbox, text="ELEMENTS", font=FONT_SM, fg=ACCENT,
                 bg=BG2).pack(pady=(8, 4))

        for etype, d in ELEM_DEFAULTS.items():
            icon = {"Frame":"▭","TextLabel":"T","TextButton":"B",
                    "TextBox":"I","ImageLabel":"🖼","ScrollingFrame":"⇅"}.get(etype,"?")
            btn = tk.Button(
                toolbox, text=f"{icon}  {etype}", font=FONT_SM,
                bg=BG3, fg=d["bg"], bd=0, anchor="w", padx=8, pady=6,
                cursor="hand2", activebackground=BG2, activeforeground=TEXT,
                command=lambda et=etype: self.add_element(et)
            )
            btn.pack(fill="x", pady=1)

        # Canvas area
        canvas_wrap = tk.Frame(main, bg=BG3)
        canvas_wrap.pack(side="left", fill="both", expand=True)

        tk.Label(canvas_wrap, text=f"CANVAS  ({CANVAS_W} × {CANVAS_H})",
                 font=FONT_SM, fg=SUBTEXT, bg=BG3).pack(anchor="w", padx=6, pady=(4,2))

        canvas_container = tk.Frame(canvas_wrap, bg=BG3)
        canvas_container.pack(fill="both", expand=True, padx=6, pady=(0,6))

        self.canvas = tk.Canvas(
            canvas_container,
            width=CANVAS_W, height=CANVAS_H,
            bg="#2e2e3a", highlightthickness=2,
            highlightbackground="#505070",
            cursor="crosshair"
        )
        self.canvas.pack(expand=True)

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double)
        self.canvas.bind("<ButtonPress-3>",   self._on_right_click)

        # Right panels
        right = tk.Frame(main, bg=BG, width=220)
        right.pack(side="left", fill="y", padx=(6,0))
        right.pack_propagate(False)

        # Properties
        tk.Label(right, text="PROPERTIES", font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w", pady=(4,2))
        prop_outer = tk.Frame(right, bg=BORDER, bd=1)
        prop_outer.pack(fill="both", expand=True)

        prop_canvas = tk.Canvas(prop_outer, bg=BG2, highlightthickness=0)
        prop_vsb    = tk.Scrollbar(prop_outer, orient="vertical", command=prop_canvas.yview,
                                   bg=BG2, troughcolor=BG2, bd=0, width=8)
        prop_canvas.configure(yscrollcommand=prop_vsb.set)
        prop_vsb.pack(side="right", fill="y")
        prop_canvas.pack(fill="both", expand=True)

        self._prop_frame = tk.Frame(prop_canvas, bg=BG2)
        self._prop_frame_id = prop_canvas.create_window((0,0), window=self._prop_frame, anchor="nw")

        def _prop_configure(event):
            prop_canvas.configure(scrollregion=prop_canvas.bbox("all"))
            prop_canvas.itemconfig(self._prop_frame_id, width=event.width)
        prop_canvas.bind("<Configure>", _prop_configure)
        self._prop_frame.bind("<Configure>", lambda e: prop_canvas.configure(scrollregion=prop_canvas.bbox("all")))
        prop_canvas.bind("<MouseWheel>", lambda e: prop_canvas.yview_scroll(-1*(e.delta//120), "units"))

        # Hierarchy
        tk.Label(right, text="HIERARCHY", font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w", pady=(8,2))
        hier_outer = tk.Frame(right, bg=BORDER, bd=1, height=180)
        hier_outer.pack(fill="x")
        hier_outer.pack_propagate(False)

        self._hier_list = tk.Listbox(
            hier_outer, bg=BG2, fg=TEXT, selectbackground=ACCENT,
            font=FONT_SM, bd=0, highlightthickness=0, activestyle="none"
        )
        self._hier_list.pack(fill="both", expand=True)
        self._hier_list.bind("<<ListboxSelect>>", self._hier_select)

        self._redraw()

    # ── Toolbar actions ───────────────────────────────────────────────────────

    def _toggle_grid(self):
        self.grid_enabled = not self.grid_enabled
        self._grid_btn.configure(text=f"Grid: {'ON' if self.grid_enabled else 'OFF'}")
        self._redraw()

    def _toggle_snap(self):
        self.snap_enabled = not self.snap_enabled
        self._snap_btn.configure(
            text=f"Snap: {'ON' if self.snap_enabled else 'OFF'}",
            bg="#7722cc" if self.snap_enabled else "#442288"
        )

    # ── Element management ────────────────────────────────────────────────────

    def add_element(self, etype, elem=None):
        if elem is None:
            cx = snap(CANVAS_W//2 - 60, enabled=self.snap_enabled)
            cy = snap(CANVAS_H//2 - 30, enabled=self.snap_enabled)
            elem = GMElement(etype, cx, cy)

        self.elements.append(elem)
        self._push_undo(("delete", elem))
        self.selected = elem
        self._redraw()
        self._refresh_props()
        self._refresh_hier()

    def delete_selected(self):
        if not self.selected:
            return
        self._delete_elem(self.selected)

    def _delete_elem(self, elem):
        if elem not in self.elements:
            return
        idx = self.elements.index(elem)
        self.elements.remove(elem)
        self._push_undo(("restore", elem, idx))
        if self.selected == elem:
            self.selected = None
        self._redraw()
        self._refresh_props()
        self._refresh_hier()

    def duplicate_selected(self):
        if not self.selected:
            return
        s = self.selected
        new = GMElement(s.etype, s.x + 15, s.y + 15, s.w, s.h)
        new.bg          = s.bg
        new.text        = s.text
        new.text_color  = s.text_color
        new.text_size   = s.text_size
        new.transparency= s.transparency
        new.visible     = s.visible
        new.corner_r    = s.corner_r
        new.image_id    = s.image_id
        new.canvas_w    = s.canvas_w
        new.canvas_h    = s.canvas_h
        self.add_element(s.etype, new)

    def clear_all(self):
        if not self.elements:
            return
        snapshot = list(self.elements)
        self.elements = []
        self.selected = None
        self._push_undo(("restore_all", snapshot))
        self._redraw()
        self._refresh_props()
        self._refresh_hier()

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def _push_undo(self, action):
        self.undo_stack.append(action)
        self.redo_stack.clear()
        if len(self.undo_stack) > 60:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        self._apply_inverse(action, self.redo_stack)
        self._redraw(); self._refresh_props(); self._refresh_hier()

    def redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        self._apply_inverse(action, self.undo_stack)
        self._redraw(); self._refresh_props(); self._refresh_hier()

    def _apply_inverse(self, action, other_stack):
        kind = action[0]
        if kind == "delete":
            elem = action[1]
            self.elements.append(elem)
            other_stack.append(("delete", elem))
        elif kind == "restore":
            elem, idx = action[1], action[2]
            if elem in self.elements:
                self.elements.remove(elem)
            other_stack.append(("restore", elem, idx))
        elif kind == "restore_all":
            snapshot = action[1]
            prev = list(self.elements)
            self.elements = list(snapshot)
            other_stack.append(("restore_all", prev))
        elif kind == "move":
            elem, ox, oy, nx, ny = action[1], action[2], action[3], action[4], action[5]
            elem.x, elem.y = ox, oy
            other_stack.append(("move", elem, nx, ny, ox, oy))
        elif kind == "resize":
            elem = action[1]
            ox, oy, ow, oh = action[2], action[3], action[4], action[5]
            nx, ny, nw, nh = elem.x, elem.y, elem.w, elem.h
            elem.x, elem.y, elem.w, elem.h = ox, oy, ow, oh
            other_stack.append(("resize", elem, nx, ny, nw, nh))
        elif kind == "prop":
            elem, prop, old_val, new_val = action[1], action[2], action[3], action[4]
            setattr(elem, prop, old_val)
            other_stack.append(("prop", elem, prop, new_val, old_val))
            if self.selected == elem:
                self._refresh_props()

    # ── Mouse interaction ─────────────────────────────────────────────────────

    def _canvas_xy(self, event):
        return event.x, event.y

    def _hit_handle(self, elem, mx, my):
        for name, (x1,y1,x2,y2) in elem.handle_rects().items():
            if x1 <= mx <= x2 and y1 <= my <= y2:
                return name
        return None

    def _on_press(self, event):
        mx, my = self._canvas_xy(event)

        # Check selected element handles first
        if self.selected:
            h = self._hit_handle(self.selected, mx, my)
            if h:
                self._drag_mode  = h
                self._drag_start = (mx, my,
                                    self.selected.x, self.selected.y,
                                    self.selected.w, self.selected.h)
                return

        # Hit test elements back-to-front (topmost first)
        hit = None
        for elem in reversed(self.elements):
            if elem.contains(mx, my):
                hit = elem
                break

        if hit:
            self.selected    = hit
            self._drag_mode  = "move"
            self._drag_start = (mx, my, hit.x, hit.y, hit.w, hit.h)
        else:
            self.selected   = None
            self._drag_mode = None

        self._redraw()
        self._refresh_props()
        self._refresh_hier()

    def _on_drag(self, event):
        if not self._drag_mode or not self._drag_start or not self.selected:
            return
        mx, my = self._canvas_xy(event)
        sx, sy, ox, oy, ow, oh = self._drag_start
        dx, dy = mx - sx, my - sy
        elem = self.selected

        if self._drag_mode == "move":
            elem.x = snap(max(0, min(ox + dx, CANVAS_W - elem.w)), enabled=self.snap_enabled)
            elem.y = snap(max(0, min(oy + dy, CANVAS_H - elem.h)), enabled=self.snap_enabled)

        else:
            h = self._drag_mode
            nx, ny, nw, nh = ox, oy, ow, oh
            if "E" in h: nw = max(20, ow + dx)
            if "S" in h: nh = max(20, oh + dy)
            if "W" in h:
                nw = max(20, ow - dx)
                nx = ox + (ow - nw)
            if "N" in h:
                nh = max(20, oh - dy)
                ny = oy + (oh - nh)
            elem.x = snap(nx, enabled=self.snap_enabled)
            elem.y = snap(ny, enabled=self.snap_enabled)
            elem.w = snap(nw, enabled=self.snap_enabled)
            elem.h = snap(nh, enabled=self.snap_enabled)

        self._redraw()
        # live-update pos/size fields
        self._live_update_props()

    def _on_release(self, event):
        if self._drag_mode and self._drag_start and self.selected:
            elem = self.selected
            sx, sy, ox, oy, ow, oh = self._drag_start
            if self._drag_mode == "move":
                if (ox, oy) != (elem.x, elem.y):
                    self._push_undo(("move", elem, ox, oy, elem.x, elem.y))
            else:
                if (ox,oy,ow,oh) != (elem.x,elem.y,elem.w,elem.h):
                    self._push_undo(("resize", elem, ox, oy, ow, oh))
        self._drag_mode  = None
        self._drag_start = None

    def _on_double(self, event):
        """Double-click to bring element forward in z-order."""
        if self.selected and self.selected in self.elements:
            idx = self.elements.index(self.selected)
            if idx < len(self.elements) - 1:
                self.elements.insert(idx + 1, self.elements.pop(idx))
                self.selected.zindex += 1
                self._redraw()
                self._refresh_hier()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _redraw(self):
        c = self.canvas
        c.delete("all")

        # Grid
        if self.grid_enabled:
            for x in range(0, CANVAS_W, GRID):
                c.create_line(x, 0, x, CANVAS_H, fill="#3a3a50", width=1)
            for y in range(0, CANVAS_H, GRID):
                c.create_line(0, y, CANVAS_W, y, fill="#3a3a50", width=1)

        # Elements
        for elem in self.elements:
            if not elem.visible:
                continue
            x1, y1, x2, y2 = elem.rect()
            alpha_fill = self._hex_with_alpha(elem.bg, 1.0 - elem.transparency)

            c.create_rectangle(x1, y1, x2, y2,
                                fill=alpha_fill, outline="#888", width=1,
                                tags=("elem", elem.name))

            # label
            label = elem.text if elem.text else f"[{elem.etype}]"
            c.create_text(
                x1 + elem.w//2, y1 + elem.h//2,
                text=label, fill=elem.text_color,
                font=("Consolas", min(elem.text_size, 13)),
                width=elem.w - 6, tags=("elem_text", elem.name)
            )

            # name tag top-left
            c.create_text(x1 + 3, y1 + 3, text=elem.name,
                          fill="#aaaacc", font=("Consolas", 7),
                          anchor="nw", tags=("elem_name",))

            # logic badge — ⚡ top-right if element has wired logic
            if elem.logic:
                badge_colors = {"execCmd": CYAN, "toggle": YELLOW, "raw": "#ab54f7"}
                # use color of first rule type
                bc = badge_colors.get(elem.logic[0]["type"], CYAN)
                c.create_rectangle(x2-18, y1, x2, y1+13, fill=bc, outline="")
                c.create_text(x2-9, y1+6, text=f"⚡{len(elem.logic)}",
                              fill=BG, font=("Consolas", 7, "bold"), anchor="center")

        # Selection highlight + handles
        if self.selected and self.selected in self.elements:
            elem = self.selected
            x1, y1, x2, y2 = elem.rect()
            c.create_rectangle(x1-2, y1-2, x2+2, y2+2,
                                outline=CYAN, width=2, dash=(4,2))
            for hname, (hx1,hy1,hx2,hy2) in elem.handle_rects().items():
                c.create_rectangle(hx1, hy1, hx2, hy2,
                                   fill=CYAN, outline="#ffffff", width=1)

    def _hex_with_alpha(self, hex_color, alpha):
        """Blend hex color with dark bg for transparency simulation."""
        try:
            hex_color = hex_color.lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            bg_r, bg_g, bg_b = 0x2e, 0x2e, 0x3a
            r = int(r * alpha + bg_r * (1 - alpha))
            g = int(g * alpha + bg_g * (1 - alpha))
            b = int(b * alpha + bg_b * (1 - alpha))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    # ── Hierarchy ─────────────────────────────────────────────────────────────

    def _refresh_hier(self):
        self._hier_list.delete(0, "end")
        for i, elem in enumerate(reversed(self.elements)):
            marker = "▶ " if elem == self.selected else "   "
            vis    = "" if elem.visible else " [hidden]"
            logic  = f" ⚡{len(elem.logic)}" if elem.logic else ""
            self._hier_list.insert("end", f"{marker}[Z:{elem.zindex}] {elem.name}{vis}{logic}")

    def _hier_select(self, event):
        sel = self._hier_list.curselection()
        if not sel:
            return
        idx = len(self.elements) - 1 - sel[0]
        if 0 <= idx < len(self.elements):
            self.selected = self.elements[idx]
            self._redraw()
            self._refresh_props()

    # ── Properties Panel ──────────────────────────────────────────────────────

    def _refresh_props(self):
        for w in self._prop_frame.winfo_children():
            w.destroy()
        self._prop_widgets.clear()

        if not self.selected:
            tk.Label(self._prop_frame, text="No element selected",
                     font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(pady=20)
            return

        elem = self.selected

        def prop_row(label, attr, conv=str, validate=None):
            row = tk.Frame(self._prop_frame, bg=BG2)
            row.pack(fill="x", pady=1, padx=4)
            tk.Label(row, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(getattr(elem, attr)))
            e = tk.Entry(row, textvariable=var, font=FONT_SM,
                         bg=BG3, fg=TEXT, bd=0, insertbackground=CYAN, width=12)
            e.pack(side="left", fill="x", expand=True, ipady=3)
            self._prop_widgets[attr] = var

            def on_change(*_):
                try:
                    val = conv(var.get())
                    if validate and not validate(val):
                        return
                    old = getattr(elem, attr)
                    if old != val:
                        self._push_undo(("prop", elem, attr, old, val))
                        setattr(elem, attr, val)
                        self._redraw()
                        self._refresh_hier()
                except Exception:
                    pass
            var.trace_add("write", on_change)

        def color_row(label, attr):
            row = tk.Frame(self._prop_frame, bg=BG2)
            row.pack(fill="x", pady=1, padx=4)
            tk.Label(row, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            preview = tk.Label(row, bg=getattr(elem, attr), width=3)
            preview.pack(side="left", padx=(0,4))
            var = tk.StringVar(value=getattr(elem, attr))
            e = tk.Entry(row, textvariable=var, font=FONT_SM,
                         bg=BG3, fg=TEXT, bd=0, insertbackground=CYAN, width=10)
            e.pack(side="left", fill="x", expand=True, ipady=3)
            self._prop_widgets[attr] = var

            def on_change(*_):
                val = var.get().strip()
                # accept #rrggbb or r,g,b
                if val.startswith("#") and len(val) == 7:
                    hex_val = val
                elif "," in val:
                    parts = val.split(",")
                    if len(parts) == 3:
                        try:
                            r,g,b = [max(0,min(255,int(x))) for x in parts]
                            hex_val = f"#{r:02x}{g:02x}{b:02x}"
                        except Exception:
                            return
                    else:
                        return
                else:
                    return
                old = getattr(elem, attr)
                if old != hex_val:
                    self._push_undo(("prop", elem, attr, old, hex_val))
                    setattr(elem, attr, hex_val)
                    preview.configure(bg=hex_val)
                    self._redraw()
            var.trace_add("write", on_change)

        def bool_row(label, attr):
            row = tk.Frame(self._prop_frame, bg=BG2)
            row.pack(fill="x", pady=1, padx=4)
            tk.Label(row, text=label, font=FONT_SM, fg=SUBTEXT,
                     bg=BG2, width=12, anchor="w").pack(side="left")
            var = tk.BooleanVar(value=getattr(elem, attr))
            cb = tk.Checkbutton(row, variable=var, bg=BG2,
                                selectcolor=BG3, activebackground=BG2,
                                fg=TEXT, activeforeground=TEXT,
                                highlightthickness=0, cursor="hand2")
            cb.pack(side="left")
            def on_change(*_):
                val = var.get()
                old = getattr(elem, attr)
                if old != val:
                    self._push_undo(("prop", elem, attr, old, val))
                    setattr(elem, attr, val)
                    self._redraw()
                    self._refresh_hier()
            var.trace_add("write", on_change)

        tk.Label(self._prop_frame, text=f"── {elem.etype} ──",
                 font=FONT_SM, fg=ACCENT, bg=BG2).pack(pady=(6,2))

        prop_row("Name",         "name",         str)
        prop_row("X",            "x",            int)
        prop_row("Y",            "y",            int)
        prop_row("Width",        "w",            int, lambda v: v >= 1)
        prop_row("Height",       "h",            int, lambda v: v >= 1)
        prop_row("ZIndex",       "zindex",       int)
        prop_row("CornerR",      "corner_r",     int)
        prop_row("AnchorX",      "anchor_x",     float)
        prop_row("AnchorY",      "anchor_y",     float)
        prop_row("Transparency", "transparency", float, lambda v: 0<=v<=1)
        bool_row("Visible",      "visible")
        color_row("BG Color",    "bg")

        has_text = elem.etype in ("TextLabel","TextButton","TextBox")
        if has_text:
            prop_row("Text",       "text",       str)
            prop_row("TextSize",   "text_size",  int)
            color_row("TextColor", "text_color")

        if elem.etype == "ImageLabel":
            prop_row("ImageID",  "image_id", str)

        if elem.etype == "ScrollingFrame":
            prop_row("CanvasW",  "canvas_w", int)
            prop_row("CanvasH",  "canvas_h", int)

        # Action buttons
        tk.Frame(self._prop_frame, bg=BORDER, height=1).pack(fill="x", pady=6, padx=4)

        btn_row = tk.Frame(self._prop_frame, bg=BG2)
        btn_row.pack(fill="x", padx=4, pady=2)
        tk.Button(btn_row, text="⚡ Logic", font=FONT_SM, bg="#2a2a50", fg=CYAN,
                  bd=0, padx=8, pady=4, cursor="hand2",
                  command=lambda: self._open_logic_list(elem)).pack(side="left", padx=(0,4))
        tk.Button(btn_row, text="⧉ Dup", font=FONT_SM, bg="#2a5aaa", fg=TEXT,
                  bd=0, padx=8, pady=4, cursor="hand2",
                  command=self.duplicate_selected).pack(side="left", padx=(0,4))
        tk.Button(btn_row, text="🗑 Del", font=FONT_SM, bg="#aa2222", fg=TEXT,
                  bd=0, padx=8, pady=4, cursor="hand2",
                  command=self.delete_selected).pack(side="left")

    def _live_update_props(self):
        """Update just x/y/w/h fields during drag without full rebuild."""
        if not self.selected:
            return
        elem = self.selected
        for attr in ("x", "y", "w", "h"):
            if attr in self._prop_widgets:
                try:
                    self._prop_widgets[attr].set(str(getattr(elem, attr)))
                except Exception:
                    pass

    # ── Right-click context menu ──────────────────────────────────────────────

    def _on_right_click(self, event):
        mx, my = event.x, event.y
        # hit-test
        hit = None
        for elem in reversed(self.elements):
            if elem.contains(mx, my):
                hit = elem
                break
        if not hit:
            return
        self.selected = hit
        self._redraw()
        self._refresh_props()
        self._refresh_hier()

        menu = tk.Menu(self.canvas, tearoff=0, bg=BG2, fg=TEXT,
                       activebackground=ACCENT, activeforeground=TEXT,
                       font=FONT_SM, bd=0, relief="flat")

        menu.add_command(label=f"  ⚡  Add Logic  [{hit.name}]",
                         state="disabled", font=(FONT_SM[0], FONT_SM[1], "bold"))
        menu.add_separator()
        menu.add_command(label="  🎯  execCmd  (run addcmd)",
                         command=lambda: self._open_logic_editor(hit, "execCmd"))
        menu.add_command(label="  🔀  Toggle command",
                         command=lambda: self._open_logic_editor(hit, "toggle"))
        menu.add_command(label="  📝  Raw Lua snippet",
                         command=lambda: self._open_logic_editor(hit, "raw"))

        if hit.logic:
            menu.add_separator()
            menu.add_command(label=f"  📋  View wired logic  ({len(hit.logic)} rule(s))",
                             command=lambda: self._open_logic_list(hit))
            menu.add_command(label="  🗑  Clear all logic",
                             command=lambda: self._clear_logic(hit))

        menu.add_separator()
        menu.add_command(label="  ⧉  Duplicate",  command=self.duplicate_selected)
        menu.add_command(label="  🗑  Delete",     command=self.delete_selected)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_logic_editor(self, elem, logic_type):
        EVENTS = ["MouseButton1Click", "MouseButton2Click", "MouseEnter", "MouseLeave", "MouseMoved"]
        TYPE_LABELS = {
            "execCmd": "execCmd  —  run an addcmd by name",
            "toggle":  "Toggle  —  toggle a command (bool state)",
            "raw":     "Raw Lua  —  arbitrary code block",
        }
        TYPE_COLORS = {"execCmd": CYAN, "toggle": YELLOW, "raw": "#ab54f7"}

        win = tk.Toplevel()
        win.title(f"Logic Editor — {elem.name}")
        win.configure(bg=BG)
        win.geometry("560x480")
        win.resizable(True, True)
        win.grab_set()

        # Header
        hdr = tk.Frame(win, bg=BG2)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"⚡ LOGIC EDITOR", font=FONT_TITLE, fg=ACCENT, bg=BG2).pack(side="left", padx=12, pady=8)
        tk.Label(hdr, text=TYPE_LABELS[logic_type], font=FONT_SM,
                 fg=TYPE_COLORS[logic_type], bg=BG2).pack(side="left", padx=4, pady=8)
        tk.Label(hdr, text=f"→ {elem.name}", font=FONT_SM, fg=SUBTEXT, bg=BG2).pack(side="right", padx=12, pady=8)

        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # Event selector
        tk.Label(body, text="TRIGGER EVENT", font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w")
        event_var = tk.StringVar(value="MouseButton1Click")
        event_frame = tk.Frame(body, bg=BG)
        event_frame.pack(fill="x", pady=(2,10))
        for ev in EVENTS:
            tk.Radiobutton(event_frame, text=ev, variable=event_var, value=ev,
                           font=FONT_SM, fg=TEXT, bg=BG, selectcolor=BG2,
                           activebackground=BG, activeforeground=ACCENT,
                           highlightthickness=0, cursor="hand2").pack(side="left", padx=(0,10))

        # Type-specific inputs
        if logic_type == "execCmd":
            tk.Label(body, text="COMMAND NAME  (without prefix)", font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w")
            cmd_var = tk.StringVar()
            tk.Entry(body, textvariable=cmd_var, font=FONT_UI, bg=BG2, fg=CYAN,
                     insertbackground=CYAN, bd=0, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER).pack(fill="x", ipady=5, pady=(2,8))

            tk.Label(body, text="EXTRA ARGS  (optional, space separated)", font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w")
            args_var = tk.StringVar()
            tk.Entry(body, textvariable=args_var, font=FONT_UI, bg=BG2, fg=TEXT,
                     insertbackground=CYAN, bd=0, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER).pack(fill="x", ipady=5, pady=(2,8))

            tk.Label(body, text="PREVIEW", font=FONT_SM, fg=SUBTEXT, bg=BG).pack(anchor="w")
            preview = tk.Label(body, font=("Consolas", 9), fg=CYAN, bg=BG3,
                               anchor="w", padx=8, pady=4, wraplength=500, justify="left")
            preview.pack(fill="x", pady=(2,0))

            def update_preview(*_):
                c = cmd_var.get().strip() or "commandname"
                a = args_var.get().strip()
                arg_str = (' "' + a + '"') if a else ""
                preview.configure(text=f'execCmd("{c}"{arg_str}, speaker)')
            cmd_var.trace_add("write", update_preview)
            args_var.trace_add("write", update_preview)
            update_preview()

            def do_save():
                c = cmd_var.get().strip()
                if not c:
                    messagebox.showwarning("Missing", "Enter a command name.", parent=win)
                    return
                a = args_var.get().strip()
                payload = c + ("|" + a if a else "")
                elem.logic.append({"event": event_var.get(), "type": "execCmd", "payload": payload})
                self._redraw()
                self._refresh_hier()
                win.destroy()

        elif logic_type == "toggle":
            tk.Label(body, text="COMMAND NAME  (the toggle command)", font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w")
            cmd_var = tk.StringVar()
            tk.Entry(body, textvariable=cmd_var, font=FONT_UI, bg=BG2, fg=YELLOW,
                     insertbackground=CYAN, bd=0, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER).pack(fill="x", ipady=5, pady=(2,8))

            tk.Label(body, text="LABEL ON  /  LABEL OFF  (for button text swap, optional)",
                     font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w")
            label_frame = tk.Frame(body, bg=BG)
            label_frame.pack(fill="x", pady=(2,8))
            on_var  = tk.StringVar(value="ON")
            off_var = tk.StringVar(value="OFF")
            tk.Label(label_frame, text="ON:", font=FONT_SM, fg=GREEN,  bg=BG).pack(side="left")
            tk.Entry(label_frame, textvariable=on_var,  font=FONT_UI, bg=BG2, fg=GREEN,
                     insertbackground=CYAN, bd=0, width=10,
                     highlightthickness=1, highlightcolor=ACCENT,
                     highlightbackground=BORDER).pack(side="left", ipady=4, padx=(4,14))
            tk.Label(label_frame, text="OFF:", font=FONT_SM, fg="#ff6666", bg=BG).pack(side="left")
            tk.Entry(label_frame, textvariable=off_var, font=FONT_UI, bg=BG2, fg="#ff6666",
                     insertbackground=CYAN, bd=0, width=10,
                     highlightthickness=1, highlightcolor=ACCENT,
                     highlightbackground=BORDER).pack(side="left", ipady=4, padx=(4,0))

            tk.Label(body, text="PREVIEW", font=FONT_SM, fg=SUBTEXT, bg=BG).pack(anchor="w")
            preview = tk.Label(body, font=("Consolas", 9), fg=YELLOW, bg=BG3,
                               anchor="w", padx=8, pady=4, wraplength=500, justify="left")
            preview.pack(fill="x", pady=(2,0))

            def update_preview(*_):
                c = cmd_var.get().strip() or "commandname"
                preview.configure(
                    text=f'local {c}On = false\n'
                         f'{elem.name}.MouseButton1Click:Connect(function()\n'
                         f'    {c}On = not {c}On\n'
                         f'    execCmd("{c}", speaker)\n'
                         f'    {elem.name}.Text = {c}On and "{on_var.get()}" or "{off_var.get()}"\n'
                         f'end)'
                )
            cmd_var.trace_add("write", update_preview)
            on_var.trace_add("write", update_preview)
            off_var.trace_add("write", update_preview)
            update_preview()

            def do_save():
                c = cmd_var.get().strip()
                if not c:
                    messagebox.showwarning("Missing", "Enter a command name.", parent=win)
                    return
                payload = f"{c}|{on_var.get()}|{off_var.get()}"
                elem.logic.append({"event": event_var.get(), "type": "toggle", "payload": payload})
                self._redraw()
                self._refresh_hier()
                win.destroy()

        else:  # raw
            tk.Label(body, text="LUA SNIPPET  (has access to speaker, args, element name as variable)",
                     font=FONT_SM, fg=ACCENT, bg=BG).pack(anchor="w")
            code_box = tk.Text(body, font=("Consolas", 10), bg=BG2, fg="#ab54f7",
                               insertbackground=CYAN, bd=0, height=12,
                               highlightthickness=1, highlightcolor=ACCENT,
                               highlightbackground=BORDER, padx=8, pady=6, wrap="none")
            code_box.pack(fill="both", expand=True, pady=(2,0))
            code_box.insert("1.0",
                f"-- Element: {elem.name}\n"
                f"-- Available: speaker, LocalPlayer, ScreenGui\n"
                f"DoNotif(\"{elem.name} clicked!\", 2)\n"
            )

            def do_save():
                code = code_box.get("1.0", "end-1c").strip()
                if not code:
                    messagebox.showwarning("Missing", "Write some Lua first.", parent=win)
                    return
                elem.logic.append({"event": event_var.get(), "type": "raw", "payload": code})
                self._redraw()
                self._refresh_hier()
                win.destroy()

        # Bottom buttons
        btn_bar = tk.Frame(win, bg=BG2)
        btn_bar.pack(fill="x", side="bottom")
        tk.Button(btn_bar, text="✅  SAVE LOGIC", font=FONT_SM, bg=ACCENT, fg=TEXT,
                  bd=0, padx=14, pady=7, cursor="hand2",
                  command=do_save).pack(side="left", padx=12, pady=8)
        tk.Button(btn_bar, text="✖  CANCEL", font=FONT_SM, bg=BG3, fg=TEXT,
                  bd=0, padx=14, pady=7, cursor="hand2",
                  command=win.destroy).pack(side="left")

    def _open_logic_list(self, elem):
        """View/delete existing logic rules on an element."""
        win = tk.Toplevel()
        win.title(f"Logic Rules — {elem.name}")
        win.configure(bg=BG)
        win.geometry("500x340")
        win.grab_set()

        TYPE_COLORS = {"execCmd": CYAN, "toggle": YELLOW, "raw": "#ab54f7"}

        tk.Label(win, text=f"Logic Rules on  {elem.name}", font=FONT_TITLE,
                 fg=ACCENT, bg=BG).pack(anchor="w", padx=12, pady=(10,4))

        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=12)

        def refresh():
            for w in frame.winfo_children():
                w.destroy()
            if not elem.logic:
                tk.Label(frame, text="No logic rules.", font=FONT_SM,
                         fg=SUBTEXT, bg=BG).pack(pady=20)
                return
            for i, rule in enumerate(elem.logic):
                row = tk.Frame(frame, bg=BG2)
                row.pack(fill="x", pady=2)
                color = TYPE_COLORS.get(rule["type"], TEXT)
                tk.Label(row, text=f"[{rule['event']}]", font=FONT_SM,
                         fg=SUBTEXT, bg=BG2, width=22, anchor="w").pack(side="left", padx=(6,0))
                tk.Label(row, text=rule["type"], font=FONT_SM,
                         fg=color, bg=BG2, width=10, anchor="w").pack(side="left")
                payload_short = rule["payload"][:40] + ("…" if len(rule["payload"]) > 40 else "")
                tk.Label(row, text=payload_short, font=FONT_SM,
                         fg=TEXT, bg=BG2, anchor="w").pack(side="left", padx=4)
                idx = i
                tk.Button(row, text="🗑", font=FONT_SM, bg="#aa2222", fg=TEXT,
                          bd=0, padx=6, pady=2, cursor="hand2",
                          command=lambda i=idx: (elem.logic.pop(i), refresh(),
                                                 self._redraw(), self._refresh_hier())).pack(side="right", padx=4, pady=2)

        refresh()
        tk.Button(win, text="✖  Close", font=FONT_SM, bg=BG3, fg=TEXT,
                  bd=0, padx=12, pady=6, cursor="hand2",
                  command=win.destroy).pack(side="bottom", pady=8)

    def _clear_logic(self, elem):
        if messagebox.askyesno("Clear Logic", f"Remove all logic from {elem.name}?"):
            elem.logic.clear()
            self._redraw()
            self._refresh_hier()

    # ── Export ────────────────────────────────────────────────────────────────

    def export_lua(self):
        if not self.elements:
            messagebox.showinfo("Empty", "No elements to export.")
            return

        lines = []
        def w(s): lines.append(s)

        has_logic   = any(e.logic for e in self.elements)
        has_toggles = any(r["type"] == "toggle"
                          for e in self.elements for r in e.logic)

        w("-- ════════════════════════════════════════")
        w(f"-- Generated by Zuka Panel GUI Maker")
        w(f"-- Project: {self.proj_name}")
        w("-- ════════════════════════════════════════")
        w("local Players     = game:GetService('Players')")
        w("local LocalPlayer = Players.LocalPlayer")
        if has_logic:
            w("local speaker     = LocalPlayer  -- alias used by logic")
        w("")
        w("local ScreenGui = Instance.new('ScreenGui')")
        w(f"ScreenGui.Name           = '{self.proj_name}'")
        w("ScreenGui.ResetOnSpawn   = false")
        w("ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling")
        w("ScreenGui.Parent         = LocalPlayer:WaitForChild('PlayerGui')")
        w("")

        # Emit toggle state variables up-front
        if has_toggles:
            w("-- Toggle states")
            seen_toggles = set()
            for elem in self.elements:
                for rule in elem.logic:
                    if rule["type"] == "toggle":
                        cmd = rule["payload"].split("|")[0]
                        var = f"_tog_{cmd.replace('-','_')}"
                        if var not in seen_toggles:
                            w(f"local {var} = false")
                            seen_toggles.add(var)
            w("")

        # Emit elements
        for elem in self.elements:
            n = elem.name
            w(f"-- {n}")
            w(f"local {n} = Instance.new('{elem.etype}')")
            w(f"{n}.Name                   = '{n}'")
            w(f"{n}.Size                   = UDim2.fromOffset({elem.w}, {elem.h})")
            w(f"{n}.Position               = UDim2.fromOffset({elem.x}, {elem.y})")
            w(f"{n}.AnchorPoint            = Vector2.new({elem.anchor_x}, {elem.anchor_y})")

            try:
                hx = elem.bg.lstrip("#")
                r,g,b = int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16)
            except Exception:
                r,g,b = 100,100,180
            w(f"{n}.BackgroundColor3       = Color3.fromRGB({r}, {g}, {b})")
            w(f"{n}.BackgroundTransparency = {elem.transparency}")
            w(f"{n}.BorderSizePixel        = 0")
            w(f"{n}.ZIndex                 = {elem.zindex}")
            w(f"{n}.Visible                = {str(elem.visible).lower()}")

            if elem.etype in ("TextLabel","TextButton","TextBox"):
                safe = elem.text.replace("'", "\\'")
                try:
                    hx2 = elem.text_color.lstrip("#")
                    tr,tg,tb = int(hx2[0:2],16), int(hx2[2:4],16), int(hx2[4:6],16)
                except Exception:
                    tr,tg,tb = 255,255,255
                w(f"{n}.Text                   = '{safe}'")
                w(f"{n}.TextColor3             = Color3.fromRGB({tr}, {tg}, {tb})")
                w(f"{n}.TextSize               = {elem.text_size}")
                w(f"{n}.Font                   = Enum.Font.Gotham")
                w(f"{n}.TextXAlignment         = Enum.TextXAlignment.Left")
                if elem.etype == "TextBox":
                    w(f"{n}.PlaceholderText        = 'Enter text...'")
                    w(f"{n}.ClearTextOnFocus       = false")

            if elem.etype == "ImageLabel":
                img = elem.image_id or "rbxasset://textures/ui/GuiImagePlaceholder.png"
                w(f"{n}.Image     = '{img}'")
                w(f"{n}.ScaleType = Enum.ScaleType.Fit")

            if elem.etype == "ScrollingFrame":
                w(f"{n}.ScrollBarThickness = 6")
                w(f"{n}.CanvasSize         = UDim2.fromOffset({elem.canvas_w}, {elem.canvas_h})")
                w(f"{n}.ScrollingEnabled   = true")

            w(f"do local c = Instance.new('UICorner', {n}) ; c.CornerRadius = UDim.new(0, {elem.corner_r}) end")
            w(f"{n}.Parent = ScreenGui")

            # ── Emit logic connections ────────────────────────────────────────
            if elem.logic:
                w(f"-- Logic wiring for {n}")
                for rule in elem.logic:
                    event   = rule["event"]
                    ltype   = rule["type"]
                    payload = rule["payload"]

                    if ltype == "execCmd":
                        parts   = payload.split("|", 1)
                        cmd     = parts[0].strip()
                        extra   = parts[1].strip() if len(parts) > 1 else ""
                        arg_str = (f', "{extra}"') if extra else ""
                        w(f'{n}.{event}:Connect(function()')
                        w(f'    pcall(execCmd, "{cmd}"{arg_str}, speaker)')
                        w(f'end)')

                    elif ltype == "toggle":
                        parts   = payload.split("|")
                        cmd     = parts[0].strip()
                        on_lbl  = parts[1] if len(parts) > 1 else "ON"
                        off_lbl = parts[2] if len(parts) > 2 else "OFF"
                        var     = f"_tog_{cmd.replace('-','_')}"
                        w(f'{n}.{event}:Connect(function()')
                        w(f'    {var} = not {var}')
                        w(f'    pcall(execCmd, "{cmd}", speaker)')
                        if elem.etype in ("TextLabel","TextButton","TextBox"):
                            w(f'    {n}.Text = {var} and "{on_lbl}" or "{off_lbl}"')
                        w(f'end)')

                    else:  # raw
                        w(f'{n}.{event}:Connect(function()')
                        for line in payload.split("\n"):
                            w(f'    {line}')
                        w(f'end)')

            w("")

        code = "\n".join(lines)

        # Show in popup with copy button
        win = tk.Toplevel()
        win.title("Exported Lua")
        win.configure(bg=BG)
        win.geometry("700x540")

        tk.Label(win, text=f"Generated Lua — {self.proj_name}",
                 font=FONT_TITLE, fg=ACCENT, bg=BG).pack(pady=(10,4))

        out = tk.Text(win, font=("Consolas",10), bg=BG2, fg=TEXT,
                      insertbackground=CYAN, bd=0, wrap="none", padx=8, pady=6)
        out.pack(fill="both", expand=True, padx=10)
        out.insert("1.0", code)
        out.configure(state="disabled")

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=10, pady=8)

        def do_copy():
            try:
                pyperclip.copy(code)
                messagebox.showinfo("Copied", "Lua code copied to clipboard!")
            except Exception:
                win.clipboard_clear()
                win.clipboard_append(code)
                messagebox.showinfo("Copied", "Copied via fallback.")

        def do_save():
            path = filedialog.asksaveasfilename(
                defaultextension=".lua",
                filetypes=[("Lua files","*.lua"),("All","*.*")],
                initialfile=f"{self.proj_name}.lua"
            )
            if path:
                with open(path,"w",encoding="utf-8") as f:
                    f.write(code)
                messagebox.showinfo("Saved", f"Saved:\n{path}")

        tk.Button(btn_row, text="📋 Copy", font=FONT_SM, bg=CYAN, fg=BG,
                  bd=0, padx=12, pady=5, cursor="hand2", command=do_copy).pack(side="left", padx=(0,8))
        tk.Button(btn_row, text="💾 Save .lua", font=FONT_SM, bg=BG3, fg=TEXT,
                  bd=0, padx=12, pady=5, cursor="hand2", command=do_save).pack(side="left")

# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ZukaCmdBuilder()
    app.mainloop()
