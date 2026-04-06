local RunService = game:GetService("RunService")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
local _require = getrenv().require


local function SanitizeCarbonModule(moduleScript)

    local success, moduleData = pcall(_require, moduleScript)
    if not success or type(moduleData) ~= "table" then return moduleData end
    local flagKeys = {"Security", "Verify", "Check", "AntiCheat", "ExploitCheck"}
    for _, key in pairs(flagKeys) do
        if rawget(moduleData, key) ~= nil then
            rawset(moduleData, key, function() return true end)
        end
    end
    if rawget(moduleData, "Hash") or rawget(moduleData, "CheckSum") then
        rawset(moduleData, "Hash", nil)
        rawset(moduleData, "CheckSum", nil)
    end
    return moduleData
end
local function ApplyRequirementHook()
    local oldRequire
    oldRequire = hookfunction(_require, newcclosure(function(module)
        if not checkcaller() and typeof(module) == "Instance" and module:IsA("ModuleScript") then
            if module.Name == "1" and module.Parent and module.Parent.Name == "Settings" then
                return SanitizeCarbonModule(module)
            end
            local name = module.Name:lower()
            if name:find("security") or name:find("anticheat") then
                return setmetatable({}, {
                    __index = function() return function() return true end end
                })
            end
        end
        return oldRequire(module)
    end))
end
local function NeutralizeRenderLoops()
    local oldBind
    oldBind = hookmethod(RunService, "BindToRenderStep", function(self, name, priority, callback)
        local lowerName = name:lower()
        if lowerName:find("ac") or lowerName:find("security") or lowerName:find("verify") then
            return nil 
        end
        return oldBind(self, name, priority, callback)
    end)
end
pcall(function()
    ApplyRequirementHook()
    NeutralizeRenderLoops()
    local mt = getrawmetatable(game)
    local oldNamecall = mt.__namecall
    setreadonly(mt, false)
    mt.__namecall = newcclosure(function(self, ...)
        local method = getnamecallmethod()
        if not checkcaller() and (method == "ClearOutput" or method == "LogService") then
            return nil
        end
        return oldNamecall(self, ...)
    end)
    setreadonly(mt, true)
end)

if 

getgenv().ZexAddon_Loaded 
    
then 
     return  
            end

getgenv().ZexAddon_Loaded = true

-- haha adonis u suck!!!!1111!!


local set_ro    =    setreadonly or (make_writeable 
      and function(t, v) if v then 
           make_readonly(t) else 
make_writeable(t) 
   end 
end) 
  or 
   function() 
end

local get_mt    = getrawmetatable or debug.getmetatable
local hook_meta  = hookmetamethod
local new_cc  = newcclosure 
        or function(f) 
      return f 
    end
local check_caller  = checkcaller or function() return false end
local hook_fn   = hookfunction or function() end
local gc    = getgc or get_gc_objects or function() return {} end
local is_our_thread = isourclosure 

or 

function() 

       return 

   false 

end


local Stats = {

    KickAttempts     = 0,
    RemotesBlocked    = 0,
    DetectionsCaught = 0,
    FunctionsHooked = 0,
    ClientChecksBlocked = 0,
    RemotesFired = 0,

}
local HookedFunctions  = {}
local cachedACTable    = nil
local originalFunctions = {}
local isUnloaded  = false
local Services = setmetatable({}, {
    __index = function(t, k)
        local ok, s = pcall(function() return game:GetService(k) end)
        if ok and s then rawset(t, k, s) end
        return s
    end
})
local function safe(fn, ...)
    local ok, result = pcall(fn, ...)
    return ok and result or nil
end
local function safeHook(original, replacement)
    if type(original) ~= "function" then return false end
    local ok = pcall(hook_fn, original, new_cc(replacement))
    if not ok then return false end
    table.insert(HookedFunctions, original)
    Stats.FunctionsHooked += 1
    return true
end
local function dismantle_readonly(target)
    if type(target) ~= "table" then return end
    pcall(function()
        if set_ro then set_ro(target, false) end
        local mt = get_mt(target)
        if mt then pcall(set_ro, mt, false) end
    end)
end
for _, fn in ipairs({ getgenv, getrenv, getreg }) do
    if type(fn) == "function" then
        local ok, env = pcall(fn)
        if ok and type(env) == "table" then
            dismantle_readonly(env)
        end
    end
end
if not game:IsLoaded() then game.Loaded:Wait() end
local Players = Services.Players
repeat task.wait(0.1) until Players and Players.LocalPlayer
local LocalPlayer = Players.LocalPlayer
local AC_SIGNATURES = {
    { "Detected",         true,  1 },
    { "RemovePlayer",     true,  1 },
    { "CheckAllClients",  true,  1 },
    { "KickedPlayers",    false, 1 },
    { "SpoofCheckCache",  false, 1 },
    { "ClientTimeoutLimit", false, 1 },
    { "CharacterCheck",   true,  0.5 },
    { "UserSpoofCheck",   true,  0.5 },
    { "AntiCheatEnabled", false, 1 },
    { "GetPlayer",        true,  0.5 },
}
local AC_SCORE_THRESHOLD = 3
local function scoreTable(v)
    if type(v) ~= "table" then return 0 end
    local score = 0
    local ok, _ = pcall(function()
        for _, sig in ipairs(AC_SIGNATURES) do
            local name, isFunc, weight = sig[1], sig[2], sig[3]
            local val = rawget(v, name)
            if val ~= nil then
                if isFunc then
                    if type(val) == "function" then score += weight end
                else
                    score += weight
                end
            end
        end
    end)
    return score
end
local function findACTable()
    local objs
    local ok = pcall(function() objs = gc(true) end)
    if not ok or not objs then return nil end
    for _, v in ipairs(objs) do
        local ok2, isT = pcall(function() return type(v) == "table" end)
        if ok2 and isT and scoreTable(v) >= AC_SCORE_THRESHOLD then
            return v
        end
    end
    return nil
end
local function hookACTable(tbl)
    if not tbl then return end
    if type(tbl.Detected) == "function" then
        safeHook(tbl.Detected, function(player, action, info)
            Stats.DetectionsCaught += 1
        end)
    end
    if type(tbl.RemovePlayer) == "function" then
        safeHook(tbl.RemovePlayer, function(p, info)
            Stats.KickAttempts += 1
        end)
    end
    if type(tbl.CheckAllClients) == "function" then
        safeHook(tbl.CheckAllClients, function(...)
            Stats.ClientChecksBlocked += 1
        end)
    end
    if type(tbl.UserSpoofCheck) == "function" then
        safeHook(tbl.UserSpoofCheck, function(p, ...)
            return nil
        end)
    end
    if type(tbl.CharacterCheck) == "function" then
        safeHook(tbl.CharacterCheck, function(...) end)
    end
    if type(tbl.KickedPlayers) == "table" then
        local mt = getmetatable(tbl.KickedPlayers) or {}
        rawset(mt, "__index", function() return false end)
        rawset(mt, "__newindex", function() end)
        rawset(mt, "__len", function() return 0 end)
        pcall(setmetatable, tbl.KickedPlayers, mt)
    end
    if type(tbl.SpoofCheckCache) == "table" then
        local mt = {}
        rawset(mt, "__index", function(t, k)
            return {{
                Id          = k,
                Username    = LocalPlayer.Name,
                DisplayName = LocalPlayer.DisplayName,
                UserId      = LocalPlayer.UserId,
            }}
        end)
        rawset(mt, "__newindex", function() end)
        pcall(setmetatable, tbl.SpoofCheckCache, mt)
    end
    if tbl.ClientTimeoutLimit ~= nil then
        pcall(function() tbl.ClientTimeoutLimit = math.huge end)
    end
    if tbl.AntiCheatEnabled ~= nil then
        pcall(function() tbl.AntiCheatEnabled = false end)
    end
end
local function findAndPatchRemoteClients()
    local userId = tostring(LocalPlayer.UserId)
    local objs
    local ok = pcall(function() objs = gc(true) end)
    if not ok or not objs then return end
    for _, v in ipairs(objs) do
        local ok2, isT = pcall(function() return type(v) == "table" end)
        if not (ok2 and isT) then continue end
        local ok3, client, hasMaxLen = pcall(function()
            return rawget(v, userId), rawget(v, "MaxLen")
        end)
        if not (ok3 and type(client) == "table") then continue end
        local ok4, hasLastUpdate = pcall(function()
            return rawget(client, "LastUpdate") ~= nil
        end)
        if ok4 and hasLastUpdate and hasMaxLen ~= nil then
            task.spawn(function()
                while not isUnloaded do
                    task.wait(8)
                    pcall(function()
                        local c = v[userId]
                        if c then
                            c.LastUpdate   = os.time()
                            c.PlayerLoaded = true
                        end
                    end)
                end
            end)
        end
    end
end
local REMOTE_BLOCK_EXACT = {
    ["__FUNCTION"]     = true,
    ["_FUNCTION"]      = true,
    ["ClientCheck"]    = true,
    ["ProcessCommand"] = true,
    ["ClientLoaded"]   = true,
    ["ActivateCommand"]= true,
    ["Disconnect"]     = true,
}
local REMOTE_BLOCK_PATTERNS = {
    "anticheat", "anti_cheat", "kickplayer", "banplayer",
    "reportexploit", "detectclient", "cheatcheck",
}
local function shouldBlockRemote(remoteName)
    if REMOTE_BLOCK_EXACT[remoteName] then return true end
    local lower = remoteName:lower()
    for _, pat in ipairs(REMOTE_BLOCK_PATTERNS) do
        if lower:find(pat, 1, true) then return true end
    end
    return false
end
local function installNamecallHook()
    local mt = get_mt(game)
    if not mt then return end
    local oldNamecall = mt.__namecall
    originalFunctions.namecall = oldNamecall
    pcall(set_ro, mt, false)
    mt.__namecall = new_cc(function(self, ...)
        if isUnloaded then return oldNamecall(self, ...) end
        local method = getnamecallmethod()
        local args   = { ... }
        if check_caller() then
            return oldNamecall(self, ...)
        end
        if method == "Kick" and self == LocalPlayer then
            local msg = tostring(args[1] or ""):lower()
            local acKeywords = { "adonis", "anti.?cheat", "exploit", "acli", "detected", "cheat", "ban" }
            for _, kw in ipairs(acKeywords) do
                if msg:find(kw) then
                    Stats.KickAttempts += 1
                    return nil
                end
            end
        end
        if method == "FireServer" or method == "InvokeServer" then
            local name = (typeof(self) == "Instance" and self.Name) or ""
            if shouldBlockRemote(name) then
                Stats.RemotesBlocked += 1
                if method == "InvokeServer" then
                    return "Pong"
                end
                return nil
            end
            Stats.RemotesFired += 1
        end
        return oldNamecall(self, ...)
    end)
    pcall(set_ro, mt, true)
end
local function installDebugHooks()
    local function isHooked(fn)
        for _, h in ipairs(HookedFunctions) do
            if fn == h then return true end
        end
        return false
    end
    local function wrapDebugFn(fn, fallback)
        if type(fn) ~= "function" then return end
        pcall(hook_fn, fn, new_cc(function(target, ...)
            if isHooked(target) then return fallback end
            return fn(target, ...)
        end))
    end
    wrapDebugFn(debug.info or debug.getinfo, nil)
    wrapDebugFn(debug.getupvalues, {})
    wrapDebugFn(debug.getlocals, {})
    wrapDebugFn(debug.getconstants, {})
    if debug.setupvalue then
    end
end
local function protectKick()
    local origKick = LocalPlayer.Kick
    originalFunctions.kick = origKick
    safeHook(origKick, function(self, reason, ...)
        if check_caller() then
            return origKick(self, reason, ...)
        end
        if self == LocalPlayer then
            local msg = tostring(reason or ""):lower()
            local acKeywords = { "adonis", "anti.?cheat", "exploit", "acli", "cheat", "ban", "detected" }
            for _, kw in ipairs(acKeywords) do
                if msg:find(kw) then
                    Stats.KickAttempts += 1
                    return nil
                end
            end
        end
        return origKick(self, reason, ...)
    end)
end
local oldRequire
oldRequire = hook_fn(getrenv().require, new_cc(function(module)
    if check_caller() then return oldRequire(module) end
    if typeof(module) == "Instance" then
        local name = module.Name:lower()
        if name:find("topbar") or name:find("icon") or
           name:find("adonis") or name:find("aethetic") then
            return setmetatable({}, {
                __index    = function() return function() end end,
                __newindex = function() end,
                __call     = function() return {} end,
            })
        end
    end
    return oldRequire(module)
end))
local function rescan()
    local tbl = findACTable()
    if tbl and tbl ~= cachedACTable then
        cachedACTable = tbl
        hookACTable(tbl)
        warn("[ZexAddon] New AC table found and hooked during rescan.")
    end
    findAndPatchRemoteClients()
end
local function initialize()
    installNamecallHook()
    installDebugHooks()
    protectKick()
    cachedACTable = findACTable()
    if cachedACTable then
        hookACTable(cachedACTable)
        end
      findAndPatchRemoteClients()
    task.spawn(function()
        while not isUnloaded do
            task.wait(15)
            rescan()
        end
    end)
    task.spawn(function()
        while not isUnloaded do
            task.wait(60)
            warn(string.format(
                "[ZexAddon] Stats | Kicks blocked: %d | Remotes blocked: %d | Detections caught: %d | Client checks blocked: %d | Hooks installed: %d",
                Stats.KickAttempts, Stats.RemotesBlocked, Stats.DetectionsCaught,
                Stats.ClientChecksBlocked, Stats.FunctionsHooked
            ))
        end
    end)
end
getgenv().ZexAddon = {
    Version = "2.0",
    GetStats = function()
        return {
            KickAttempts        = Stats.KickAttempts,
            RemotesBlocked      = Stats.RemotesBlocked,
            DetectionsCaught    = Stats.DetectionsCaught,
            ClientChecksBlocked = Stats.ClientChecksBlocked,
            FunctionsHooked     = Stats.FunctionsHooked,
            RemotesFired        = Stats.RemotesFired,
        }
    end,
    Rescan = function()
        rescan()
        warn("[ZexAddon] Manual rescan complete.")
    end,
    Unload = function()
        isUnloaded = true
        getgenv().ZexAddon_Loaded = nil
        warn("[ZexAddon] Unloaded.")
    end,
    BlockRemote = function(name)
        REMOTE_BLOCK_EXACT[name] = true
        warn("[ZexAddon] Blocking remote: " .. tostring(name))
    end,
    UnblockRemote = function(name)
        REMOTE_BLOCK_EXACT[name] = nil
    end,
    PrintStats = function()
        local s = getgenv().ZexAddon.GetStats()
        for k, v in pairs(s) do
            print(string.format("  %s: %d", k, v))
        end
    end,
}
initialize()
print("[ZexAddon] v2.0 ready.")
