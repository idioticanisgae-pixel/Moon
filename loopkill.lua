local Players: Players = game:GetService("Players")
local ReplicatedStorage: ReplicatedStorage = game:GetService("ReplicatedStorage")
local localPlayer: Player = Players.LocalPlayer
local events: Folder = ReplicatedStorage:WaitForChild("Events")
local damageRemote: RemoteEvent = events:WaitForChild("GunDamage")
local RESEARCH_CONFIG: { [string]: any } = {
    KILL_ALL_ENABLED = true,
    DAMAGE_VALUE = 100,
    ITERATION_DELAY = 0.1
}
local function executeKillLoop(): ()
    while RESEARCH_CONFIG.KILL_ALL_ENABLED do
        for _, targetPlayer in ipairs(Players:GetPlayers()) do
            if targetPlayer ~= localPlayer and targetPlayer.Character then
                local humanoid = targetPlayer.Character:FindFirstChildOfClass("Humanoid")
                if humanoid and humanoid.Health > 0 then
                    pcall(function()
                        damageRemote:FireServer(targetPlayer, RESEARCH_CONFIG.DAMAGE_VALUE)
                    end)
                end
            end
        end
        task.wait(RESEARCH_CONFIG.ITERATION_DELAY)
    end
end
task.spawn(executeKillLoop)
