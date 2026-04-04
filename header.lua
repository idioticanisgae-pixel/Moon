local _rawequal = rawequal
local _rawget   = rawget
local _rawset   = rawset
local _tostring = tostring
local _type     = type
local _pcall    = pcall
local _error    = error
local _load     = load or loadstring
local function kill(reason)
    _error("‼ " .. _tostring(reason), 0)
end
do
    if game:GetService("RunService"):IsStudio() then
        kill("Studio execution blocked")
    end
end
do
    local executorGlobals = {
        "getgenv", "getrenv", "getrawmetatable", "setreadonly",
        "hookmetamethod", "hookfunction", "newcclosure",
        "getnamecallmethod", "checkcaller", "getconnections",
        "firesignal", "Drawing", "WebSocket", "request",
        "http_request", "readfile", "writefile", "isfile",
        "isfolder", "makefolder", "delfile", "isexecutorclosure",
        "clonefunction", "gethui",
    }
    local genv = type(getgenv) == "function" and getgenv() or nil
    local found = false
    for _, g in ipairs(executorGlobals) do
        if genv and _type(genv) == "table" and _rawget(genv, g) ~= nil then
            found = true; break
        end
        if _type(_G) == "table" and _rawget(_G, g) ~= nil then
            found = true; break
        end
    end
    if not found then
        kill("Unauthorized environment")
    end
end
do
    local genv    = type(getgenv) == "function" and getgenv() or nil
    local current = (genv and _rawget(genv, "load"))
                 or (genv and _rawget(genv, "loadstring"))
                 or _rawget(_G, "load")
                 or _rawget(_G, "loadstring")
    if current ~= nil and _type(current) == "function" then
        local isExecWrapped = isexecutorclosure and isexecutorclosure(current)
        local isNative      = iscclosure and iscclosure(current)
        if not isExecWrapped and not isNative then
            kill("load/loadstring is a hooked Lua closure")
        end
    end
end
do
    if checkcaller and not checkcaller() then
        kill("Untrusted caller detected")
    end
end
do
    local INTERVAL = 15
    task.spawn(function()
        while task.wait(INTERVAL) do
            local genv = type(getgenv) == "function" and getgenv() or nil
            local checkTargets = {
                (genv and _rawget(genv, "load"))       or _rawget(_G, "load"),
                (genv and _rawget(genv, "loadstring")) or _rawget(_G, "loadstring"),
            }
            for _, fn in ipairs(checkTargets) do
                if fn ~= nil and _type(fn) == "function" then
                    local isExecWrapped = isexecutorclosure and isexecutorclosure(fn)
                    local isNative      = iscclosure and iscclosure(fn)
                    if not _rawequal(fn, _load) and not isExecWrapped and not isNative then
                        kill("Runtime: load/loadstring was replaced with a Lua closure")
                    end
                end
            end
        end
    end)
end
