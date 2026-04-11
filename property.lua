local mt = getrawmetatable(game)
local backupindex = mt.__index
local backupnewindex = mt.__newindex
setreadonly(mt, false)
local BLEnv = getfenv(gethiddenproperty)
mt.__index = newcclosure(function(t, k)
    if (checkcaller() and debug.validlevel(3) and getfenv(3) ~= BLEnv) then
        local success, data = pcall(function() return backupindex(t, k) end)
        return (success and data) or gethiddenproperty(t, k)
    end
    return backupindex(t, k)
end)
mt.__newindex = newcclosure(function(t, k, v)
    if (checkcaller() and debug.validlevel(3) and getfenv(3) ~= BLEnv) then
        local success, data = pcall(function() return backupnewindex(t, k, v) end)
        return (success and data) or sethiddenproperty(t, k, v)
    end
    return backupnewindex(t, k, v)
end)
setreadonly(mt, true)
