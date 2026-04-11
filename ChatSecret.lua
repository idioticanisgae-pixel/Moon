local SignalManager = loadstring(game:HttpGet("https://raw.githubusercontent.com/idioticanisgae-pixel/Moon/refs/heads/main/Manager.lua"))()
local Manager = SignalManager.new()
local Configuration = {
    Secret = "hello comrade",
    Signals = Manager,
    Exploiters = {},
    Connections = {}
}
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
local AllChatType = Enum.PlayerChatType.All
Manager:Add("ExploiterJoined")
Manager:Add("ExploiterLeaving")
Manager:Add("ExploiterChatted")
Configuration.Connections.ChatConnection = Players.PlayerChatted:Connect(function(ChatType, Player, Message, TargetPlayer)
    if (Player ~= LocalPlayer and Message == Configuration.Secret and ChatType == AllChatType and TargetPlayer == nil and not table.find(Configuration.Exploiters, Player)) then
        table.insert(Configuration.Exploiters, Player)
        Players:Chat(Configuration.Secret)
        Manager:Fire("ExploiterJoined", Player)
    end
end)
Configuration.Connections.PlayerConnection = Players.PlayerRemoving:Connect(function(Player)
    local i = table.find(Configuration.Exploiters, Player)
    if (i) then
        table.remove(Configuration.Exploiters, i)
        Manager:Fire("ExploiterLeaving", Player)
    end
end)
Configuration.Connections.ChattedConnection = Players.PlayerChatted:Connect(function(ChatType, Player, Message, TargetPlayer)
    if (table.find(Configuration.Exploiters, Player)) then
        Manager:Fire("ExploiterChatted", ChatType, Player, Message, TargetPlayer)
    end
end)
Players:Chat(Configuration.Secret)
return Configuration
