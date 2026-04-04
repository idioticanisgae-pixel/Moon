local Players: Players = game:GetService("Players")
local RunService: RunService = game:GetService("RunService")
local ReplicatedStorage: ReplicatedStorage = game:GetService("ReplicatedStorage")

local localPlayer: Player = Players.LocalPlayer
local character: Model = localPlayer.Character or localPlayer.CharacterAdded:Wait()

local DEFENSE_SETTINGS: { [string]: any } = {
    GOD_MODE_ENABLED = true,
    DESYNC_ENABLED = true,
    DESYNC_VELOCITY = Vector3.new(0, 500, 0),
    RECONSTRUCTION_DELAY = 0.1
}

local function initiateGodMode(): ()
    if not DEFENSE_SETTINGS.GOD_MODE_ENABLED then return end

    local character = localPlayer.Character
    if not character then return end

    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not humanoid then return end

    local fakeHumanoid = humanoid:Clone()
    fakeHumanoid.Parent = character
    humanoid:Destroy()
    
    localPlayer.Character = nil
    localPlayer.Character = character
end

local function applyPhysicsDesync(): ()
    if not DEFENSE_SETTINGS.DESYNC_ENABLED then return end

    local rootPart: BasePart? = character:FindFirstChild("HumanoidRootPart")
    if not rootPart then return end

    local originalVelocity: Vector3 = rootPart.AssemblyLinearVelocity

    RunService.Heartbeat:Connect(function()
        if DEFENSE_SETTINGS.DESYNC_ENABLED then
            rootPart.AssemblyLinearVelocity = DEFENSE_SETTINGS.DESYNC_VELOCITY
            RunService.RenderStepped:Wait()
            rootPart.AssemblyLinearVelocity = originalVelocity
        end
    end)
end

local function hookMetaMethods(): ()
    local mt = getrawmetatable(game)
    local oldIndex = mt.__index
    setreadonly(mt, false)

    mt.__index = newcclosure(function(self, key)
        if not checkcaller() and self:IsA("Humanoid") and key == "Health" then
            return 100
        end
        return oldIndex(self, key)
    end)

    setreadonly(mt, true)
end

task.spawn(function()
    initiateGodMode()
    applyPhysicsDesync()
    hookMetaMethods()
end)

localPlayer.CharacterAdded:Connect(function(newChar)
    character = newChar
    task.wait(DEFENSE_SETTINGS.RECONSTRUCTION_DELAY)
    initiateGodMode()
end)
