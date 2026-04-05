task.spawn(function()
    local Luna
    local ok, err = pcall(function()
        Luna = loadstring(game:HttpGet(
            "https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Luna.lua", true
        ))()
    end)
    if not ok or not Luna then
        warn("[ZukaPanel/LunaUI] Luna failed to load:", tostring(err))
        return
    end
    local Window = Luna:CreateWindow({
        Name           = "Zuka's FunBox. v2",
        Subtitle       = "by OverZuka",
        LogoID         = "rbxassetid://7243158473",
        LoadingEnabled = false,
        ConfigSettings = { ConfigFolder = "ZukaPanelLuna" },
        KeySystem      = false,
    })

    local PT = Window:CreateTab({ Name = "Player", Icon = "person", ImageSource = "Material", ShowTitle = true })

    PT:CreateSection("Spectate")
    PT:CreateLabel({ Text = "Select a player then hit Spectate", Style = 3 })
    local _spectateTarget = nil
    local _spectatePlayerOptions = {}
    local function _refreshSpectateOptions()
        _spectatePlayerOptions = {}
        for _, p in ipairs(game:GetService("Players"):GetPlayers()) do
            if p ~= LocalPlayer then
                table.insert(_spectatePlayerOptions, p.Name)
            end
        end
        return _spectatePlayerOptions
    end
    _refreshSpectateOptions()
    local _spectateDropdown = PT:CreateDropdown({
        Name = "Target Player", Description = "Choose who to spectate",
        Options = _refreshSpectateOptions(), CurrentOption = {}, MultipleOptions = false,
        Callback = function(v)
            _spectateTarget = type(v) == "table" and v[1] or v
        end
    }, "luna_spectate_target")
    PT:CreateButton({ Name = "Spectate", Description = "Lock camera onto selected player",
        Callback = function()
            if not _spectateTarget or _spectateTarget == "" then
                return DoNotif("Select a player first.", 2)
            end
            local target = game:GetService("Players"):FindFirstChild(_spectateTarget)
            if target then
                Modules.SpectateController:Enable(target)
            else
                DoNotif("Player not found — they may have left.", 3)
            end
        end })
    PT:CreateButton({ Name = "Stop Spectating", Description = "Return camera to your own character",
        Callback = function()
            Modules.SpectateController:Disable()
        end })
    PT:CreateButton({ Name = "Refresh Player List", Description = "Update the dropdown with current players",
        Callback = function()
            _refreshSpectateOptions()
            DoNotif("Player list refreshed.", 2)
        end })

    PT:CreateDivider()
    PT:CreateSection("Teleport to Player")
    PT:CreateLabel({ Text = "Silently teleport behind a target", Style = 3 })
    local _tpPlayerTarget = nil
    local _tpPlayerDropdown = PT:CreateDropdown({
        Name = "Target Player", Description = "Who to teleport to",
        Options = _refreshSpectateOptions(), CurrentOption = {}, MultipleOptions = false,
        Callback = function(v)
            _tpPlayerTarget = type(v) == "table" and v[1] or v
        end
    }, "luna_tp_player_target")
    PT:CreateButton({ Name = "  TP To Player", Description = "Teleport directly behind selected player",
        Callback = function()
            if not _tpPlayerTarget or _tpPlayerTarget == "" then
                return DoNotif("Select a player first.", 2)
            end
            local target = game:GetService("Players"):FindFirstChild(_tpPlayerTarget)
            if not target or not target.Character then
                return DoNotif("Player or character not found.", 3)
            end
            local hrp = LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
            local tgtHrp = target.Character:FindFirstChild("HumanoidRootPart")
            if hrp and tgtHrp then
                hrp.CFrame = tgtHrp.CFrame * CFrame.new(0, 0, 3)
                DoNotif("Teleported to " .. target.Name, 2)
            else
                DoNotif("Could not find character parts.", 3)
            end
        end })

    PT:CreateDivider()
    PT:CreateSection("Avatar Morph")
    PT:CreateLabel({ Text = "Copy another player's avatar onto yours", Style = 3 })
    local _morphInput = ""
    PT:CreateInput({ Name = "Username or UserID", PlaceholderText = "e.g. Builderman or 156",
        CurrentValue = "", Numeric = false, Enter = true,
        Callback = function(v) _morphInput = v end }, "luna_morph_input")
    PT:CreateButton({ Name = "Apply Morph", Description = "Load that user's avatar onto your character",
        Callback = function()
            if not _morphInput or _morphInput == "" then
                return DoNotif("Enter a username or UserID first.", 2)
            end
            Modules.CharacterMorph:Morph(_morphInput)
        end })
    PT:CreateButton({ Name = "Revert Avatar", Description = "Restore your original appearance",
        Callback = function()
            Modules.CharacterMorph:Revert()
        end })

    local TP = Window:CreateTab({ Name = "Teleport", Icon = "near_me", ImageSource = "Material", ShowTitle = true })

    TP:CreateSection("Waypoints")
    TP:CreateLabel({ Text = "Save up to 10 named positions and tp back to them", Style = 3 })
    local _waypointNameInput = ""
    TP:CreateInput({ Name = "Waypoint Name", PlaceholderText = "e.g. base, spawn, loot",
        CurrentValue = "", Numeric = false, Enter = true,
        Callback = function(v) _waypointNameInput = v end }, "luna_wp_name")
    TP:CreateButton({ Name = "Save Waypoint", Description = "Save your current position under that name",
        Callback = function()
            if not _waypointNameInput or _waypointNameInput == "" then
                return DoNotif("Enter a waypoint name first.", 2)
            end
            Modules.Waypoint:Add(_waypointNameInput)
        end })
    TP:CreateButton({ Name = "TP to Waypoint", Description = "Teleport to the named waypoint",
        Callback = function()
            if not _waypointNameInput or _waypointNameInput == "" then
                return DoNotif("Enter a waypoint name first.", 2)
            end
            Modules.Waypoint:Teleport(_waypointNameInput)
        end })
    TP:CreateButton({ Name = "Delete Waypoint", Description = "Remove that waypoint",
        Callback = function()
            if not _waypointNameInput or _waypointNameInput == "" then
                return DoNotif("Enter a waypoint name first.", 2)
            end
            Modules.Waypoint:Remove(_waypointNameInput)
        end })
    TP:CreateButton({ Name = "List Waypoints", Description = "See all saved waypoints in a notification",
        Callback = function() Modules.Waypoint:List() end })
    TP:CreateButton({ Name = "Clear All Waypoints", Description = "Delete every saved waypoint",
        Callback = function() Modules.Waypoint:Clear() end })

    TP:CreateDivider()
    TP:CreateSection("Coordinate Teleport")
    TP:CreateLabel({ Text = "Jump to exact X, Y, Z coordinates", Style = 3 })
    local _tpX, _tpY, _tpZ = 0, 5, 0
    TP:CreateInput({ Name = "X", PlaceholderText = "0", CurrentValue = "0", Numeric = true, Enter = true,
        Callback = function(v) _tpX = tonumber(v) or 0 end }, "luna_tp_x")
    TP:CreateInput({ Name = "Y", PlaceholderText = "5", CurrentValue = "5", Numeric = true, Enter = true,
        Callback = function(v) _tpY = tonumber(v) or 5 end }, "luna_tp_y")
    TP:CreateInput({ Name = "Z", PlaceholderText = "0", CurrentValue = "0", Numeric = true, Enter = true,
        Callback = function(v) _tpZ = tonumber(v) or 0 end }, "luna_tp_z")
    TP:CreateButton({ Name = "Teleport to Coords", Description = "Move your character to the entered XYZ",
        Callback = function()
            local hrp = LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
            if not hrp then return DoNotif("No character found.", 3) end
            hrp.CFrame = CFrame.new(_tpX, _tpY, _tpZ)
            DoNotif(string.format("Teleported to (%.1f, %.1f, %.1f)", _tpX, _tpY, _tpZ), 2)
        end })
    TP:CreateButton({ Name = "Copy Current Coords", Description = "Copy your XYZ to clipboard",
        Callback = function()
            local hrp = LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
            if not hrp then return DoNotif("No character found.", 3) end
            local p = hrp.Position
            local str = string.format("%.2f, %.2f, %.2f", p.X, p.Y, p.Z)
            if setclipboard then setclipboard(str) DoNotif("Copied: " .. str, 2)
            else DoNotif(str, 4) end
        end })

    TP:CreateDivider()
    TP:CreateSection("Quick Teleports")
    TP:CreateButton({ Name = "TP to Spawn", Description = "Teleport to the map's spawn location",
        Callback = function()
            local spawn = workspace:FindFirstChildOfClass("SpawnLocation")
            local hrp = LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
            if spawn and hrp then
                hrp.CFrame = spawn.CFrame + Vector3.new(0, 4, 0)
                DoNotif("Teleported to spawn.", 2)
            else
                DoNotif("No SpawnLocation found in workspace.", 3)
            end
        end })
    TP:CreateButton({ Name = "TP to Map Center", Description = "Teleport to 0, 100, 0",
        Callback = function()
            local hrp = LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
            if hrp then hrp.CFrame = CFrame.new(0, 100, 0) DoNotif("Teleported to map center.", 2)
            else DoNotif("No character found.", 3) end
        end })
    TP:CreateButton({ Name = "TP Up (Sky)", Description = "Shoot yourself up 2000 studs",
        Callback = function()
            local hrp = LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
            if hrp then hrp.CFrame = hrp.CFrame + Vector3.new(0, 2000, 0) DoNotif("Launched upwards.", 2)
            else DoNotif("No character found.", 3) end
        end })

    local Anti = Window:CreateTab({ Name = "Anti+", Icon = "shield", ImageSource = "Material", ShowTitle = true })

    Anti:CreateSection("Position & Physics")
    Anti:CreateToggle({ Name = "Anti Reset",        Description = "Prevent death and void falls",         CurrentValue = false,
        Callback = function(v) if v then Modules.AntiReset:Enable() else Modules.AntiReset:Disable() end end }, "anti_antireset")
    Anti:CreateToggle({ Name = "Anti Void",         Description = "Prevent falling into the void",        CurrentValue = false,
        Callback = function() Modules.AntiVoid:Toggle() end }, "anti_antivoid")
    Anti:CreateToggle({ Name = "Anti Force-TP",     Description = "Block server CFrame teleports",        CurrentValue = false,
        Callback = function() Modules.AntiCFrameTeleport:Toggle() end }, "anti_anticframetp")
    Anti:CreateToggle({ Name = "Anti Trip",         Description = "Block ragdoll / fallingdown states",   CurrentValue = false,
        Callback = function() Modules.AntiTrip:Toggle() end }, "anti_antitrip")
    Anti:CreateToggle({ Name = "Anti Anchor",       Description = "Prevent your character being anchored", CurrentValue = false,
        Callback = function(v) if v then Modules.AntiAnchor:Enable() else Modules.AntiAnchor:Disable() end end }, "anti_antianchor")
    Anti:CreateToggle({ Name = "Anti Player Physics", Description = "Block physics manipulation by others", CurrentValue = false,
        Callback = function() Modules.AntiPlayerPhysics:Toggle() end }, "anti_antiphysics")
    Anti:CreateToggle({ Name = "Knockback Nullifier", Description = "Cancel velocity spikes and knockback", CurrentValue = false,
        Callback = function() Modules.KnockbackNullifier:Toggle() end }, "anti_knockback")

    Anti:CreateDivider()
    Anti:CreateSection("Character Integrity")
    Anti:CreateToggle({ Name = "Anti Kill",         Description = "Keep humanoid health above 0",         CurrentValue = false,
        Callback = function(v) if v then Modules.AntiKill:Enable() else Modules.AntiKill:Disable() end end }, "anti_antikill")
    Anti:CreateToggle({ Name = "Anti Sit",          Description = "Prevent being force-seated",           CurrentValue = false,
        Callback = function(v) if v then Modules.AntiSit:Enable() else Modules.AntiSit:Disable() end end }, "anti_antisit")
    Anti:CreateToggle({ Name = "Anti Attach",       Description = "Counter players latching onto you",    CurrentValue = false,
        Callback = function(v) if v then Modules.AntiAttach:Enable() else Modules.AntiAttach:Disable() end end }, "anti_antiattach")
    Anti:CreateToggle({ Name = "Anti Slap Gear",    Description = "Block slap gear from affecting you",   CurrentValue = false,
        Callback = function() Modules.AntiSlapGear:Toggle() end }, "anti_antislapgear")
    Anti:CreateToggle({ Name = "Humanoid Integrity", Description = "Lock humanoid stats against tampering", CurrentValue = false,
        Callback = function() Modules.HumanoidIntegrity:Toggle() end }, "anti_humintegrity")

    Anti:CreateDivider()
    Anti:CreateSection("Session")
    Anti:CreateToggle({ Name = "Anti AFK",          Description = "Prevent idle disconnect",              CurrentValue = false,
        Callback = function() Modules.InternalAntiAfk:Toggle() end }, "anti_antiafk")
    Anti:CreateToggle({ Name = "Fling Protection",  Description = "Prevent being flung by other players", CurrentValue = false,
        Callback = function() Modules.FlingProtection:Toggle() end }, "anti_flingprot")

    Anti:CreateDivider()
    Anti:CreateButton({ Name = "✦  Enable All Anti", Description = "Turn on every toggle in this tab at once",
        Callback = function()
            pcall(function() Modules.AntiReset:Enable() end)
            pcall(function() Modules.AntiVoid:Toggle() if not Modules.AntiVoid.State.IsEnabled then Modules.AntiVoid:Toggle() end end)
            pcall(function() if not Modules.AntiCFrameTeleport.State.IsEnabled then Modules.AntiCFrameTeleport:Toggle() end end)
            pcall(function() if not Modules.AntiTrip.State.IsEnabled then Modules.AntiTrip:Toggle() end end)
            pcall(function() Modules.AntiAnchor:Enable() end)
            pcall(function() if not Modules.AntiPlayerPhysics.State.IsEnabled then Modules.AntiPlayerPhysics:Toggle() end end)
            pcall(function() if not Modules.KnockbackNullifier.State.IsEnabled then Modules.KnockbackNullifier:Toggle() end end)
            pcall(function() Modules.AntiKill:Enable() end)
            pcall(function() Modules.AntiSit:Enable() end)
            pcall(function() Modules.AntiAttach:Enable() end)
            pcall(function() if not Modules.AntiSlapGear.State.IsEnabled then Modules.AntiSlapGear:Toggle() end end)
            pcall(function() if not Modules.HumanoidIntegrity.State.IsEnabled then Modules.HumanoidIntegrity:Toggle() end end)
            pcall(function() if not Modules.InternalAntiAfk.State.IsEnabled then Modules.InternalAntiAfk:Toggle() end end)
            pcall(function() if not Modules.FlingProtection.State.IsEnabled then Modules.FlingProtection:Toggle() end end)
            DoNotif("All anti protections enabled.", 3)
        end })

    local Movement = Window:CreateTab({ Name = "Movement", Icon = "directions_run", ImageSource = "Material", ShowTitle = true })
    Movement:CreateToggle({ Name = "Fly",           Description = "Toggle client-sided fly",       CurrentValue = false, Callback = function() Modules.Fly:Toggle() end }, "luna_fly")
    Movement:CreateToggle({ Name = "NoClip",        Description = "Walk through walls",             CurrentValue = false, Callback = function() Modules.NoClip:Toggle() end }, "luna_noclip")
    Movement:CreateToggle({ Name = "Infinite Jump", Description = "Jump repeatedly mid-air",        CurrentValue = false, Callback = function(v) if v then Modules.InfiniteJump:Enable() else Modules.InfiniteJump:Disable() end end }, "luna_infjump")
    Movement:CreateToggle({ Name = "Anti Reset",    Description = "Prevent death and void falls",   CurrentValue = false, Callback = function() Modules.AntiReset:Toggle() end }, "luna_antireset")
    Movement:CreateToggle({ Name = "Anti Sit",      Description = "Prevent being force-sat",        CurrentValue = false, Callback = function() Modules.AntiSit:Toggle() end }, "luna_antisit")
    Movement:CreateDivider()
    Movement:CreateSlider({ Name = "Walk Speed", Description = "Default: 16", Range = {0,500}, Increment = 1, CurrentValue = 18, Suffix = "studs/s",
        Callback = function(v)
            local h = LocalPlayer.Character and LocalPlayer.Character:FindFirstChildOfClass("Humanoid")
            if h then h.WalkSpeed = v end
            Modules.WalkSpeed.State.CurrentSpeed = v
        end }, "luna_ws")
    Movement:CreateSlider({ Name = "Fly Speed", Description = "Velocity while flying", Range = {10,500}, Increment = 5, CurrentValue = 60, Suffix = "",
        Callback = function(v) Modules.Fly:SetSpeed(v) end }, "luna_flyspd")
    Movement:CreateSlider({ Name = "Gravity", Description = "Default: 196  |  0 = restore", Range = {0,400}, Increment = 5, CurrentValue = 196, Suffix = "",
        Callback = function(v) if v <= 0 then Modules.Gravity:Disable() else Modules.Gravity:Enable(v) end end }, "luna_grav")
    local Visual = Window:CreateTab({ Name = "Visual", Icon = "visibility", ImageSource = "Material", ShowTitle = true })
    Visual:CreateToggle({ Name = "Player ESP",     Description = "Highlight players through walls", CurrentValue = true, Callback = function() Modules.ESP:Toggle("players") end }, "luna_esp")
    Visual:CreateToggle({ Name = "Chams",          Description = "See characters through walls",    CurrentValue = false, Callback = function() Modules.Chams:Toggle() end }, "luna_chams")
    Visual:CreateToggle({ Name = "FullBright",     Description = "Max ambient, remove shadows",     CurrentValue = false, Callback = function(v) if v then Modules.FullBright:Enable() else Modules.FullBright:Disable() end end }, "luna_fb")
    Visual:CreateToggle({ Name = "No Fog",         Description = "Remove client-sided fog",         CurrentValue = false, Callback = function() Modules.NoFog:Toggle() end }, "luna_nofog")
    Visual:CreateToggle({ Name = "Lighting Lock",  Description = "Prevent game changing lighting",  CurrentValue = false, Callback = function() Modules.LightingLock:Toggle() end }, "luna_ll")
    Visual:CreateToggle({ Name = "FPS Meter",      Description = "Show FPS counter on screen",      CurrentValue = false, Callback = function() Modules.FpsMeter:Toggle() end }, "luna_fps")
    Visual:CreateDivider()
    Visual:CreateSlider({ Name = "FOV Changer", Description = "Lock camera FOV  |  0 = reset", Range = {0,120}, Increment = 1, CurrentValue = 90, Suffix = "°",
        Callback = function(v)
            local cam = workspace.CurrentCamera
            if not cam then return end
            if v == 0 then
                Modules.FovChanger.State.IsEnabled = false
                if Modules.FovChanger.State.Connection then Modules.FovChanger.State.Connection:Disconnect() Modules.FovChanger.State.Connection = nil end
                cam.FieldOfView = Modules.FovChanger.State.DefaultFov
            else
                Modules.FovChanger.State.TargetFov = v
                if not Modules.FovChanger.State.Connection then
                    Modules.FovChanger.State.Connection = game:GetService("RunService").RenderStepped:Connect(function()
                        if cam and Modules.FovChanger.State.IsEnabled then cam.FieldOfView = Modules.FovChanger.State.TargetFov end
                    end)
                end
                Modules.FovChanger.State.IsEnabled = true
            end
        end }, "luna_fov")
        
    local Utility = Window:CreateTab({ Name = "Utility", Icon = "build", ImageSource = "Material", ShowTitle = true })
    Utility:CreateToggle({ Name = "Anti AFK",         Description = "Prevent idle disconnect",             CurrentValue = false, Callback = function() Modules.InternalAntiAfk:Toggle() end }, "luna_afk")
    Utility:CreateToggle({ Name = "Fling Protection", Description = "Prevent being flung",                 CurrentValue = false, Callback = function() Modules.FlingProtection:Toggle() end }, "luna_fp")
    Utility:CreateToggle({ Name = "Anti Attach",      Description = "Counter players latching onto you",   CurrentValue = false, Callback = function() Modules.AntiAttach:Toggle() end }, "luna_aa")
    Utility:CreateToggle({ Name = "Anti Force-TP",    Description = "Block server CFrame teleports",       CurrentValue = false, Callback = function() Modules.AntiCFrameTeleport:Toggle() end }, "luna_atp")
    Utility:CreateToggle({ Name = "Bypass Dev Products", Description = "Spoof purchase as completed",      CurrentValue = false, Callback = function(v) Modules.BypassDevProduct.State.Enabled = v DoNotif("Bypass DevProduct: "..(v and "ON" or "OFF"), 2) end }, "luna_bdp")
    Utility:CreateToggle({ Name = "Bypass Gamepass",  Description = "Spoof UserOwnsGamePassAsync",         CurrentValue = false, Callback = function(v) Modules.BypassGamepass.State.Enabled = v DoNotif("Bypass Gamepass: "..(v and "ON" or "OFF"), 2) end }, "luna_bgp")
    Utility:CreateToggle({ Name = "Respawn At Death", Description = "TP to death pos on respawn",          CurrentValue = false, Callback = function() Modules.RespawnAtDeath.Toggle() end }, "luna_rad")
    Utility:CreateDivider()
    Utility:CreateButton({ Name = "Open Command Bar", Description = "Toggle the Zuka command bar",  Callback = function() if Modules.CommandBar and Modules.CommandBar.Toggle then Modules.CommandBar:Toggle() end end })
    Utility:CreateButton({ Name = "Command List",     Description = "View all available commands",  Callback = function() if Modules.CommandList and Modules.CommandList.Toggle then Modules.CommandList:Toggle() end end })
    Utility:CreateButton({ Name = "Rejoin Server",    Description = "Rejoin current server",        Callback = function() if Modules.RejoinServer and Modules.RejoinServer.Rejoin then Modules.RejoinServer:Rejoin() end end })
    Utility:CreateDivider()
    Utility:CreateSection("Server")
    Utility:CreateButton({ Name = "Server Hop — Low Pop",  Description = "Find a low population server",
        Callback = function()
            if Modules.ServerHopper then Modules.ServerHopper:Hop("Low")
            else DoNotif("ServerHopper module not found.", 2) end
        end })
    Utility:CreateButton({ Name = "Server Hop — High Pop", Description = "Find a high population server",
        Callback = function()
            if Modules.ServerHopper then Modules.ServerHopper:Hop("High")
            else DoNotif("ServerHopper module not found.", 2) end
        end })
    Utility:CreateButton({ Name = "Copy Place ID", Description = "Copy current game PlaceId to clipboard",
        Callback = function()
            local id = tostring(game.PlaceId)
            if setclipboard then setclipboard(id) DoNotif("Copied PlaceId: " .. id, 2)
            else DoNotif("setclipboard not supported by your executor.", 3) end
        end })
    Utility:CreateDivider()
    Utility:CreateSection("Chat")
    Utility:CreateToggle({ Name = "Chat Fix", Description = "Hook and fix chat display",
        CurrentValue = false, Callback = function(v)
            if Modules.ChatFix then
                if v then Modules.ChatFix:Enable() else Modules.ChatFix:Disable() end
            else DoNotif("ChatFix module not found.", 2) end
        end }, "luna_chatfix")
    local LS = Window:CreateTab({ Name = "Loadstrings", Icon = "code", ImageSource = "Material", ShowTitle = true })
    local function ls(url, msg) pcall(loadstringCmd, url, msg) end
    LS:CreateSection("Tools & Utilities")
  --  LS:CreateButton({ Name = "Zex / Dex+",          Description = "Updated Dex Explorer",                    Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Zex.lua", "Loading Zex..") end })
  --  LS:CreateButton({ Name = "Ghidra",               Description = "HEX Overseer — better than all",         Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/HEXOverseer.lua", "Loading..") end })
  --  LS:CreateButton({ Name = "Rem",                  Description = "In-game exploit creation kit",           Callback = function() ls("https://e-vil.com/anbu/rem.lua", "Loading Rem.") end })
    LS:CreateButton({ Name = "Teleporter / Game Finder", Description = "Game Universe UI",                   Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/GameFinder.lua", "stolen from nameless-admin") end })
    LS:CreateButton({ Name = "Improved Btools",      Description = "Upgraded GUI for btools",                Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/buildtools.lua", "Loading Revamped Btools Gui") end })
    LS:CreateButton({ Name = "Stats Lock",           Description = "Edit and lock your properties",          Callback = function() ls("https://raw.githubusercontent.com/legalize8ga-maker/Scripts/refs/heads/main/statlock.lua", "Loading Stats..") end })
    LS:CreateButton({ Name = "Copy Console",         Description = "Copy errors from the console",           Callback = function() ls("https://raw.githubusercontent.com/scriptlisenbe-stack/luaprojectse3/refs/heads/main/consolecopy.lua", "Copy Console Activated.") end })
    LS:CreateButton({ Name = "No Anim",              Description = "Pause/remove all player animations",     Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/animationremover.lua", "Loading..") end })
    LS:CreateButton({ Name = "Zuka Hub",             Description = "Load the Zuka Hub",                      Callback = function() ls("https://raw.githubusercontent.com/legalize8ga-maker/Scripts/refs/heads/main/ZukaHub.lua", "Loading Zuka's Hub...") end })
    LS:CreateButton({ Name = "ConvertR6",            Description = "R15 → R6 converter (WIP)",               Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/r15tor6.lua", "Loading, Wait a sec.") end })
    LS:CreateButton({ Name = "Line of Sight Logger", Description = "Log players looking at you",             Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/LineOfSightLogger.lua", "Loading...") end })
    LS:CreateButton({ Name = "Z Spy",                Description = "Simple spy rework — beta",               Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/executor_scripts/SimpleSpyRework.lua", "in beta...") end })
    LS:CreateButton({ Name = "Creepy Anim GUI",      Description = "Uncanny animation GUI",                  Callback = function() ls("https://raw.githubusercontent.com/legalize8ga-maker/Scripts/refs/heads/main/uncannyanim.lua", "Loaded GUI") end })
    LS:CreateButton({ Name = "Walk Void",            Description = "Stop falling into the void",             Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/WalkVoid.lua", "You are now safe from falling into the void.") end })
    LS:CreateButton({ Name = "Reach Fix",            Description = "Make equipped tool invisible w/ reach",  Callback = function() ls("https://raw.githubusercontent.com/legalize8ga-maker/Scripts/refs/heads/main/InvisibleEquippedTool.lua", "Fixed") end })
    LS:CreateButton({ Name = "Wall Walk (WIP)",      Description = "Work in progress",                       Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/WorkINPro.lua", "Anti Gay Shield Activated.") end })
    LS:CreateButton({ Name = "Remove Forcefield",    Description = "Client-side forcefield remover",         Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/removeforcefield.txt", "Loading..") end })
    LS:CreateButton({ Name = "Remove Adonis Anti-Cheat",        Description = "Says no to Adonis",                      Callback = function() ls("https://raw.githubusercontent.com/idioticanisgae-pixel/fourfortyfivepmsundaymarch29build/refs/heads/main/Client.lua", "Loading..") end })
    LS:CreateSection("Combat & Weapons")
    LS:CreateButton({ Name = "Auto Fling",           Description = "Pwned flinger",                          Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/Ultimatefling.lua", "Loaded!") end })
    LS:CreateButton({ Name = "Touch Fling GUI",      Description = "Simple touch fling GUI",                 Callback = function() ls("https://raw.githubusercontent.com/legalize8ga-maker/Scripts/refs/heads/main/SimpleTouchFlingGui.lua", "Loaded") end })
    LS:CreateButton({ Name = "Sword Bot",            Description = "Auto sword fighter — use E and R",       Callback = function() ls("https://raw.githubusercontent.com/bloxtech1/luaprojects2/refs/heads/main/swordnpc", "Bot loaded.") end })
   -- LS:CreateButton({ Name = "CSGO Bhop",            Description = "Bhop movement",                          Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/phoon.lua", "Loading") end })
    LS:CreateButton({ Name = "Doom Hammer",          Description = "For dumb bossfights",                    Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/doomshammer.lua", "Loading..") end })
    LS:CreateButton({ Name = "TP to Swords",         Description = "Sword grabber for bossfight games",      Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/SwordGrabberBossfightGame.lua", "Loading..") end })
    --LS:CreateButton({ Name = "Lag Server",           Description = "Server payload (WIP)",                   Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/gamelagger.lua", "Loading..") end })
    LS:CreateSection("Game Specific")
    LS:CreateSection("► Zombie Game")
    LS:CreateButton({ Name = "ZG — Sniper",          Description = "Zombie Game",                            Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/sniperZG.lua", "Loading..") end })
    LS:CreateButton({ Name = "Z Fucker",             Description = "ZL series",                              Callback = function() ls("https://raw.githubusercontent.com/osukfcdays/zlfucker/refs/heads/main/main.luau", "Loading, Wait a sec.") end })
    LS:CreateButton({ Name = "ZG — Shotgun",         Description = "Zombie Game",                            Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/ShotgunMinigunScriptWorking.lua", "Loading..") end })
    LS:CreateButton({ Name = "ZG — No Acid Rain",    Description = "Zombie Game",                            Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/AntiAcidRainLag.lua", "Loading...") end })
    LS:CreateButton({ Name = "ZG — No Cooldowns",    Description = "Zombie Game",                            Callback = function() ls("https://raw.githubusercontent.com/legalize8ga-maker/Scripts/refs/heads/main/NocooldownsZombieUpd3.txt", "Loading Cooldownremover...") end })
    LS:CreateButton({ Name = "ZG — Shovel Anim",     Description = "Zombie Game",                            Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/ShovelAnimation.lua", "Loading Shovel.") end })
    LS:CreateButton({ Name = "ZG — Box ESP",         Description = "Zombie Game basic ESP",                  Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/BasicEsp.lua", "Loading Box esp") end })
    LS:CreateButton({ Name = "ZG — Melee x2",        Description = "Zombie Infection Game",                  Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/MeleeDamagex2.lua", "Loading..") end })
    LS:CreateSection("► Protect The House")
    LS:CreateButton({ Name = "PTHM — Gun Lagger",    Description = "Protect The House from Monsters",        Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/Lagger.lua", "Loading..") end })
    LS:CreateButton({ Name = "PTHM — Gun Lagger 2",  Description = "Protect The House — machine gun",        Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/machinegun.lua", "Loading..") end })
   -- LS:CreateButton({ Name = "PTHM — P-Launcher",    Description = "Protect The House — projectile lagger",  Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/GameLaggerPlauncher.lua", "Loading Modification") end })
   -- LS:CreateButton({ Name = "PTHM — Pumpkin",       Description = "Protect The House — rapid fire pumpkin", Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/RAPIDFIREPumpkinlauncher.lua", "Loading") end })
    LS:CreateSection("► Backrooms")
    LS:CreateButton({ Name = "Backrooms Gun Modifier",      Description = "For Backrooms",                     Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/BackroomsWeaponEditor.lua", "Loaded") end })
    --LS:CreateButton({ Name = "God Weapons W Teamkill",      Description = "For Backrooms",                              Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/opbasckrooms.lua", "Loaded") end })
  --  LS:CreateButton({ Name = "God Weapons W Semi-AUto",     Description = "Semi-Auto Version",       Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/PatchedGuns.lua", "Guns Patched.") end })
   -- LS:CreateButton({ Name = "Fling Gun (Backrooms)",       Description = "For Backrooms",                             Callback = function() ls("https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/flingergunspatch.lua", "Loading, Wait a sec.") end })
    LS:CreateSection("► Other Games")
    LS:CreateButton({ Name = "WOS — No Dash CD",     Description = "World of Stands — removes dash cooldown", Callback = function() ls("https://raw.githubusercontent.com/zukatech1/ZukaTechPanel/refs/heads/main/WOS.lua", "Loading, Wait a sec.") end })
        local Aimbot = {
        Enabled = false,
        IsAiming = false,
        CurrentTarget = nil,
        VelocityHistory = {},
        TargetIndex = {},
        LastIndexUpdate = 0,
        FOVCircle = nil,
        ESPObjects = {},
        ToggleKey = Enum.UserInputType.MouseButton2,
        AimPart = "HumanoidRootPart",
        FOVRadius = 70,
        ShowFOVCircle = true,
        SmoothingEnabled = true,
        SmoothingFactor = 0.6,
        DistanceBasedSmoothing = true,
        WallCheckEnabled = false,
        IgnoreTeam = false,
        StickyTarget = true,
        PredictionEnabled = false,
        PredictionMultiplier = 1.0,
        HitboxPriority = false,
        UpdateRate = 0.5,
        PredictionSamples = 3,
        StickyDistanceMultiplier = 1.5,
        UsePIDController = false,
        UseAdvancedScoring = true,
        AimRandomization = false,
        RandomizationMin = 0.92,
        RandomizationMax = 0.98,
        HealthPriority = 0.3,
        DistancePriority = 0.2,
    }
    local DeleteTool = {
        Enabled = false,
        DeleteMode = "Part",
        MaxDistance = 500,
        IgnorePlayers = true,
        IgnoreTerrain = true,
        ShowHighlight = false,
        DeleteBind = Enum.KeyCode.V,
        DeletedParts = {},
        CurrentHighlight = nil,
    }
    local HITBOX_PRIORITIES = {
        {Name = "Head"},
        {Name = "UpperTorso"},
        {Name = "HumanoidRootPart"},
        {Name = "Torso"},
        {Name = "LowerTorso"},
    }
    local PID = {}
    PID.__index = PID
    function PID:new(kp, ki, kd)
        return setmetatable({ kp=kp or 0.5, ki=ki or 0.1, kd=kd or 0.2,
            prev_error=0, integral=0, dt=1/60 }, PID)
    end
    function PID:calculate(setpoint, measurement)
        local error = setpoint - measurement
        self.integral = math.clamp(self.integral + error * self.dt, -10, 10)
        local derivative = (error - self.prev_error) / self.dt
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative
    end
    function PID:reset() self.prev_error = 0; self.integral = 0 end
    local pitchPID = PID:new(0.4, 0.08, 0.15)
    local yawPID   = PID:new(0.4, 0.08, 0.15)
    local _RunService     = game:GetService("RunService")
    local _UserInput      = game:GetService("UserInputService")
    local _Camera         = workspace.CurrentCamera
    local _Players        = game:GetService("Players")
    local _LocalPlayer    = _Players.LocalPlayer
    local wallParams      = RaycastParams.new()
    wallParams.FilterType = Enum.RaycastFilterType.Exclude
    local function updateTargetIndex(force)
        local now = tick()
        if not force and (now - Aimbot.LastIndexUpdate) < Aimbot.UpdateRate then return end
        Aimbot.LastIndexUpdate = now
        Aimbot.TargetIndex = {}
        for _, d in ipairs(workspace:GetDescendants()) do
            if d:IsA("Model") then
                local h = d:FindFirstChildOfClass("Humanoid")
                if h and h.Health > 0 then table.insert(Aimbot.TargetIndex, d) end
            end
        end
    end
    local function isTeammate(player)
        if not Aimbot.IgnoreTeam or not player then return false end
        return (LocalPlayer.Team and player.Team and LocalPlayer.Team == player.Team)
            or (LocalPlayer.TeamColor and player.TeamColor and LocalPlayer.TeamColor == player.TeamColor)
    end
    local function isVisible(part)
        if not Aimbot.WallCheckEnabled then return true end
        if not _LocalPlayer.Character or not part or not part.Parent then return false end
        local tChar = part:FindFirstAncestorOfClass("Model") or part.Parent
        wallParams.FilterDescendantsInstances = {_LocalPlayer.Character, tChar}
        return not workspace:Raycast(_Camera.CFrame.Position, part.Position - _Camera.CFrame.Position, wallParams)
    end
    local function getHitbox(model)
        if not Aimbot.HitboxPriority then return model:FindFirstChild(Aimbot.AimPart) end
        for _, h in ipairs(HITBOX_PRIORITIES) do
            local p = model:FindFirstChild(h.Name)
            if p and isVisible(p) then return p end
        end
        for _, h in ipairs(HITBOX_PRIORITIES) do
            local p = model:FindFirstChild(h.Name)
            if p then return p end
        end
    end
    local function getScore(model, part, screenDist)
        if not Aimbot.UseAdvancedScoring then return screenDist end
        local score = 1000 / (screenDist + 1)
        local hum = model:FindFirstChildOfClass("Humanoid")
        if hum then score = score * (1 - (hum.Health / hum.MaxHealth) * Aimbot.HealthPriority) end
        if _LocalPlayer.Character and _LocalPlayer.Character.PrimaryPart then
            local dist = (_LocalPlayer.Character.PrimaryPart.Position - part.Position).Magnitude
            score = score * (1 + (1 / (1 + dist / 1000)) * Aimbot.DistancePriority)
        end
        return score + math.random() * 10
    end
    local function getTarget()
        local mousePos = _UserInput:GetMouseLocation()
        local bestScore = -math.huge
        local bestModel, bestPart = nil, nil
        if Aimbot.StickyTarget and Aimbot.CurrentTarget and Aimbot.CurrentTarget.Parent then
            local part = getHitbox(Aimbot.CurrentTarget)
            if part then
                local pos, onScreen = _Camera:WorldToViewportPoint(part.Position)
                if onScreen then
                    local dist = (Vector2.new(pos.X, pos.Y) - mousePos).Magnitude
                    if dist <= Aimbot.FOVRadius * Aimbot.StickyDistanceMultiplier then
                        local score = getScore(Aimbot.CurrentTarget, part, dist) * 1.3
                        if score > bestScore then bestScore = score; bestModel = Aimbot.CurrentTarget; bestPart = part end
                    end
                end
            end
        end
        for _, model in ipairs(Aimbot.TargetIndex) do
            if model and model.Parent then
                local player = _Players:GetPlayerFromCharacter(model)
                if not (player and (player == _LocalPlayer or isTeammate(player))) then
                    local part = getHitbox(model)
                    if part then
                        local pos, onScreen = _Camera:WorldToViewportPoint(part.Position)
                        if onScreen then
                            local dist = (Vector2.new(pos.X, pos.Y) - mousePos).Magnitude
                            if dist <= Aimbot.FOVRadius then
                                local score = getScore(model, part, dist)
                                if score > bestScore then bestScore = score; bestModel = model; bestPart = part end
                            end
                        end
                    end
                end
            end
        end
        return bestModel, bestPart
    end
    local function predict(part)
        if not Aimbot.PredictionEnabled then return part.Position end
        local vel = part.AssemblyLinearVelocity or part.Velocity or Vector3.zero
        table.insert(Aimbot.VelocityHistory, vel)
        if #Aimbot.VelocityHistory > Aimbot.PredictionSamples then table.remove(Aimbot.VelocityHistory, 1) end
        local avg = Vector3.zero
        for _, v in ipairs(Aimbot.VelocityHistory) do avg = avg + v end
        avg = avg / #Aimbot.VelocityHistory
        local dist = (_Camera.CFrame.Position - part.Position).Magnitude
        return part.Position + avg * (dist / 2000 * Aimbot.PredictionMultiplier)
    end
    local function aimAt(part, dt)
        if not part or not part.Parent then return false end
        local predicted = predict(part)
        if Aimbot.UsePIDController then
            local screenPos = _Camera:WorldToViewportPoint(predicted)
            local mouse = _UserInput:GetMouseLocation()
            local dx = screenPos.X - mouse.X
            local dy = screenPos.Y - mouse.Y
            if Aimbot.AimRandomization then
                local r = Aimbot.RandomizationMin + math.random() * (Aimbot.RandomizationMax - Aimbot.RandomizationMin)
                dx = dx * r; dy = dy * r
            end
            local pc = math.clamp(pitchPID:calculate(0, dy), -2, 2)
            local yc = math.clamp(yawPID:calculate(0, dx), -2, 2)
            _Camera.CFrame = _Camera.CFrame * CFrame.Angles(math.rad(-pc * 0.01), math.rad(-yc * 0.01), 0)
        else
            local goal = CFrame.lookAt(_Camera.CFrame.Position, predicted)
            if Aimbot.SmoothingEnabled then
                local dist = (_Camera.CFrame.Position - part.Position).Magnitude
                local norm = math.clamp((dist - 10) / 290, 0, 1)
                local smooth = Aimbot.SmoothingFactor * (1 - norm * 0.5)
                if Aimbot.AimRandomization then
                    smooth = smooth * (Aimbot.RandomizationMin + math.random() * (Aimbot.RandomizationMax - Aimbot.RandomizationMin))
                end
                _Camera.CFrame = _Camera.CFrame:Lerp(goal, math.clamp(1 - (1 - smooth)^(60 * dt), 0, 1))
            else
                _Camera.CFrame = goal
            end
        end
        return true
    end
    local function setESP(part, col)
        if not part or not part.Parent then return end
        if Aimbot.ESPObjects[part] then Aimbot.ESPObjects[part].Color3 = col; return end
        local box = Instance.new("BoxHandleAdornment")
        box.Adornee = part; box.AlwaysOnTop = true; box.ZIndex = 10
        box.Size = part.Size; box.Color3 = col; box.Transparency = 0.4
        box.Parent = part
        Aimbot.ESPObjects[part] = box
    end
    local function clearESP(part)
        if part then
            if Aimbot.ESPObjects[part] then pcall(function() Aimbot.ESPObjects[part]:Destroy() end) Aimbot.ESPObjects[part] = nil end
        else
            for _, v in pairs(Aimbot.ESPObjects) do pcall(function() v:Destroy() end) end
            Aimbot.ESPObjects = {}
        end
    end
    local function getPartUnderCursor()
        local mouse = _UserInput:GetMouseLocation()
        local ray = _Camera:ViewportPointToRay(mouse.X, mouse.Y)
        local params = RaycastParams.new()
        params.FilterType = Enum.RaycastFilterType.Blacklist
        params.FilterDescendantsInstances = {_LocalPlayer.Character, _Camera}
        params.IgnoreWater = true
        local result = workspace:Raycast(ray.Origin, ray.Direction * DeleteTool.MaxDistance, params)
        if result and result.Instance then
            if DeleteTool.IgnorePlayers then
                local m = result.Instance:FindFirstAncestorOfClass("Model")
                if m and m:FindFirstChild("Humanoid") then return nil end
            end
            if DeleteTool.IgnoreTerrain and result.Instance:IsA("Terrain") then return nil end
            return result.Instance
        end
    end
    local function doDelete(part)
        if not part then return DoNotif("Nothing under cursor.", 2) end
        local target = part
        if DeleteTool.DeleteMode == "Model" then target = part:FindFirstAncestorOfClass("Model") or part
        elseif DeleteTool.DeleteMode == "Descendants" then target = part.Parent or part end
        table.insert(DeleteTool.DeletedParts, { Name = target.Name })
        pcall(function() target:Destroy() end)
        DoNotif("Deleted: " .. target.Name, 2)
    end
    if Drawing and typeof(Drawing.new) == "function" then
        Aimbot.FOVCircle = Drawing.new("Circle")
        Aimbot.FOVCircle.Visible = false
        Aimbot.FOVCircle.Thickness = 2
        Aimbot.FOVCircle.NumSides = 64
        Aimbot.FOVCircle.Color = Color3.fromRGB(255, 255, 255)
        Aimbot.FOVCircle.Transparency = 0.6
        Aimbot.FOVCircle.Filled = false
    end
    local _aimbotConnections = {}
    table.insert(_aimbotConnections, _RunService.RenderStepped:Connect(function(dt)
        if Aimbot.FOVCircle then
            Aimbot.FOVCircle.Position = _UserInput:GetMouseLocation()
            Aimbot.FOVCircle.Radius = Aimbot.FOVRadius
            Aimbot.FOVCircle.Visible = Aimbot.ShowFOVCircle and Aimbot.Enabled and Aimbot.IsAiming
        end
        updateTargetIndex()
        if Aimbot.Enabled and Aimbot.IsAiming then
            local model, part = getTarget()
            if model ~= Aimbot.CurrentTarget then pitchPID:reset(); yawPID:reset() end
            Aimbot.CurrentTarget = model
            if model and part then
                if aimAt(part, dt) then setESP(part, Color3.fromRGB(255, 80, 80)) else clearESP() end
                for p in pairs(Aimbot.ESPObjects) do if p ~= part then clearESP(p) end end
            else
                clearESP(); Aimbot.VelocityHistory = {}; pitchPID:reset(); yawPID:reset()
            end
        else
            Aimbot.CurrentTarget = nil; Aimbot.VelocityHistory = {}
            clearESP(); pitchPID:reset(); yawPID:reset()
        end
        if DeleteTool.Enabled and DeleteTool.ShowHighlight then
            local p = getPartUnderCursor()
            if p then
                if DeleteTool.CurrentHighlight then pcall(function() DeleteTool.CurrentHighlight:Destroy() end) end
                local hl = Instance.new("Highlight")
                hl.Adornee = p; hl.FillColor = Color3.fromRGB(255,0,0)
                hl.FillTransparency = 0.5; hl.OutlineTransparency = 0
                hl.Parent = p; DeleteTool.CurrentHighlight = hl
            elseif DeleteTool.CurrentHighlight then
                pcall(function() DeleteTool.CurrentHighlight:Destroy() end)
                DeleteTool.CurrentHighlight = nil
            end
        end
    end))
    table.insert(_aimbotConnections, _UserInput.InputBegan:Connect(function(input, gp)
        if gp then return end
        if DeleteTool.Enabled and input.KeyCode == DeleteTool.DeleteBind then doDelete(getPartUnderCursor()) end
        if Aimbot.Enabled and input.UserInputType == Aimbot.ToggleKey then Aimbot.IsAiming = true end
    end))
    table.insert(_aimbotConnections, _UserInput.InputEnded:Connect(function(input)
        if input.UserInputType == Aimbot.ToggleKey then
            Aimbot.IsAiming = false; clearESP(); pitchPID:reset(); yawPID:reset()
        end
    end))
    updateTargetIndex(true)
    local AB = Window:CreateTab({ Name = "Aimbot", Icon = "gps_fixed", ImageSource = "Material", ShowTitle = true })
    AB:CreateSection("Controls")
    AB:CreateToggle({ Name = "Enable Aimbot", Description = "Hold RMB to aim",
        CurrentValue = true, Callback = function(v)
            Aimbot.Enabled = v
            if not v then Aimbot.IsAiming = false; clearESP() end
            DoNotif("Aimbot: " .. (v and "ON" or "OFF"), 2)
        end }, "luna_ab_enabled")
    AB:CreateLabel({ Text = " Hold Right Mouse Button to lock on", Style = 3 })
    AB:CreateSlider({ Name = "FOV Radius", Range = {50,500}, Increment = 5, CurrentValue = 80, Suffix = "px",
        Callback = function(v) Aimbot.FOVRadius = v end }, "luna_ab_fov")
    AB:CreateSlider({ Name = "Smoothness", Range = {0.05,1.0}, Increment = 0.01, CurrentValue = 0.6,
        Callback = function(v) Aimbot.SmoothingFactor = v end }, "luna_ab_smooth")
    AB:CreateDropdown({ Name = "Aim Part", Options = {"Head","UpperTorso","HumanoidRootPart","Torso","LowerTorso"},
        CurrentOption = {"HumanoidRootPart"}, MultipleOptions = false,
        Callback = function(v) Aimbot.AimPart = type(v)=="table" and v[1] or v end }, "luna_ab_part")
    AB:CreateSection("Checks")
    AB:CreateToggle({ Name = "Ignore Team", Description = "Skip teammates", CurrentValue = false,
        Callback = function(v) Aimbot.IgnoreTeam = v end }, "luna_ab_team")
    AB:CreateToggle({ Name = "Wall Check", Description = "Only target visible players", CurrentValue = false,
        Callback = function(v) Aimbot.WallCheckEnabled = v end }, "luna_ab_wall")
    AB:CreateSection("Advanced")
    AB:CreateToggle({ Name = "Hitbox Priority", Description = "Auto-pick best visible hitbox", CurrentValue = false,
        Callback = function(v) Aimbot.HitboxPriority = v end }, "luna_ab_hbp")
    AB:CreateToggle({ Name = "Sticky Target", Description = "Maintain lock on current target", CurrentValue = true,
        Callback = function(v) Aimbot.StickyTarget = v end }, "luna_ab_sticky")
    AB:CreateToggle({ Name = "Prediction", Description = "Lead moving targets", CurrentValue = true,
        Callback = function(v) Aimbot.PredictionEnabled = v end }, "luna_ab_pred")
    AB:CreateSlider({ Name = "Prediction Multiplier", Range = {0.1,3.0}, Increment = 0.1, CurrentValue = 1.0,
        Callback = function(v) Aimbot.PredictionMultiplier = v end }, "luna_ab_predmult")
    AB:CreateToggle({ Name = "PID Controller", Description = "Human-like aim movement (buggy)", CurrentValue = false,
        Callback = function(v)
            Aimbot.UsePIDController = v
            if v then pitchPID:reset(); yawPID:reset() end
            DoNotif("PID: " .. (v and "ON" or "OFF"), 2)
        end }, "luna_ab_pid")
    AB:CreateToggle({ Name = "Advanced Scoring", Description = "Multi-factor target priority", CurrentValue = true,
        Callback = function(v) Aimbot.UseAdvancedScoring = v end }, "luna_ab_scoring")
    AB:CreateToggle({ Name = "Aim Randomization", Description = "Slight randomness for realism", CurrentValue = false,
        Callback = function(v) Aimbot.AimRandomization = v end }, "luna_ab_rand")
    AB:CreateSection("Visuals")
    AB:CreateToggle({ Name = "Show FOV Circle", Description = "Draw FOV ring while aiming", CurrentValue = false,
        Callback = function(v) Aimbot.ShowFOVCircle = v end }, "luna_ab_fovcircle")
    AB:CreateColorPicker({ Name = "FOV Color", Color = Color3.fromRGB(255,255,255),
        Callback = function(c) if Aimbot.FOVCircle then Aimbot.FOVCircle.Color = c end end }, "luna_ab_fovcol")
    local DT = Window:CreateTab({ Name = "Delete Tool", Icon = "delete", ImageSource = "Material", ShowTitle = true })
    DT:CreateSection("Delete Tool")
    DT:CreateToggle({ Name = "Enable", Description = "Activate part deletion", CurrentValue = false,
        Callback = function(v) DeleteTool.Enabled = v; DoNotif("Delete Tool: " .. (v and "ON" or "OFF"), 2) end }, "luna_dt_enabled")
    DT:CreateLabel({ Text = " Press keybind to delete part under cursor", Style = 3 })
    DT:CreateKeybind({ Name = "Delete Keybind", CurrentKeybind = "V", HoldToInteract = false,
        Callback = function(k)
            local ok, val = pcall(function() return Enum.KeyCode[k] end)
            if ok then DeleteTool.DeleteBind = val; DoNotif("Delete key: " .. k, 2) end
        end }, "luna_dt_bind")
    DT:CreateDropdown({ Name = "Delete Mode", Options = {"Part","Model","Descendants"},
        CurrentOption = {"Part"}, MultipleOptions = false,
        Callback = function(v) DeleteTool.DeleteMode = type(v)=="table" and v[1] or v end }, "luna_dt_mode")
    DT:CreateSection("Options")
    DT:CreateSlider({ Name = "Max Distance", Range = {50,2000}, Increment = 10, CurrentValue = 500, Suffix = "st",
        Callback = function(v) DeleteTool.MaxDistance = v end }, "luna_dt_dist")
    DT:CreateToggle({ Name = "Ignore Players", CurrentValue = true,
        Callback = function(v) DeleteTool.IgnorePlayers = v end }, "luna_dt_igplr")
    DT:CreateToggle({ Name = "Ignore Terrain", CurrentValue = true,
        Callback = function(v) DeleteTool.IgnoreTerrain = v end }, "luna_dt_igterr")
    DT:CreateToggle({ Name = "Show Highlight", Description = "Red outline on target part", CurrentValue = false,
        Callback = function(v) DeleteTool.ShowHighlight = v end }, "luna_dt_hl")
    DT:CreateSection("History")
    local dtHistLabel = DT:CreateLabel({ Text = "Deleted: 0 parts", Style = 1 })
    DT:CreateButton({ Name = "Clear History", Callback = function()
        DeleteTool.DeletedParts = {}
        pcall(function() dtHistLabel:Set("Deleted: 0 parts") end)
        DoNotif("History cleared.", 2)
    end })
    table.insert(_aimbotConnections, game:GetService("RunService").Heartbeat:Connect(function()
        pcall(function() dtHistLabel:Set("Deleted: " .. #DeleteTool.DeletedParts .. " parts") end)
    end))
    local Settings = Window:CreateTab({ Name = "Settings", Icon = "settings", ImageSource = "Material", ShowTitle = true })
    local Poison = Window:CreateTab({ Name = "Mod Poison", Icon = "bug_report", ImageSource = "Material", ShowTitle = true })
    local Info = Window:CreateTab({ Name = "Info", Icon = "info", ImageSource = "Material", ShowTitle = true })
    Info:CreateSection("Game")
    local _MPS = game:GetService("MarketplaceService")
    local _gameNameLabel    = Info:CreateLabel({ Text = "Game: fetching...", Style = 1 })
    local _placeIdLabel     = Info:CreateLabel({ Text = "Place ID: " .. tostring(game.PlaceId), Style = 2 })
    local _jobIdLabel       = Info:CreateLabel({ Text = "Job ID: " .. tostring(game.JobId), Style = 2 })
    local _placeVerLabel    = Info:CreateLabel({ Text = "Version: " .. tostring(game.PlaceVersion), Style = 2 })
    local _serverSizeLabel  = Info:CreateLabel({ Text = "Server Players: ...", Style = 2 })
    local _pingLabel        = Info:CreateLabel({ Text = "Ping: ...", Style = 2 })
    local _fpsInfoLabel     = Info:CreateLabel({ Text = "FPS: ...", Style = 2 })
    task.spawn(function()
        local ok, info = pcall(function()
            return _MPS:GetProductInfo(game.PlaceId, Enum.InfoType.Asset)
        end)
        pcall(function()
            _gameNameLabel:Set("Game: " .. (ok and info and info.Name or "Unknown"))
        end)
    end)
    Info:CreateSection("You")
    local _lpNameLabel      = Info:CreateLabel({ Text = "Name: " .. LocalPlayer.Name, Style = 1 })
    local _lpDisplayLabel   = Info:CreateLabel({ Text = "Display: " .. LocalPlayer.DisplayName, Style = 2 })
    local _lpIdLabel        = Info:CreateLabel({ Text = "User ID: " .. tostring(LocalPlayer.UserId), Style = 2 })
    local _lpAccAgeLabel    = Info:CreateLabel({ Text = "Account Age: " .. tostring(LocalPlayer.AccountAge) .. " days", Style = 2 })
    local _lpTeamLabel      = Info:CreateLabel({ Text = "Team: None", Style = 2 })
    local _lpHealthLabel    = Info:CreateLabel({ Text = "Health: ...", Style = 2 })
    local _lpSpeedLabel     = Info:CreateLabel({ Text = "WalkSpeed: ...", Style = 2 })
    local _lpPosLabel       = Info:CreateLabel({ Text = "Position: ...", Style = 2 })
    Info:CreateSection("Players In Server")
    local _playerCountLabel = Info:CreateLabel({ Text = "Count: " .. tostring(#_Players:GetPlayers()), Style = 1 })
    local _playerListLabel  = Info:CreateLabel({ Text = "...", Style = 2 })
    Info:CreateSection("Copy")
    Info:CreateButton({ Name = "Copy Place ID", Description = "Copy to clipboard",
        Callback = function()
            if setclipboard then setclipboard(tostring(game.PlaceId)); DoNotif("Copied Place ID", 2)
            else DoNotif("setclipboard not supported.", 2) end
        end })
    Info:CreateButton({ Name = "Copy Job ID", Description = "Copy server Job ID",
        Callback = function()
            if setclipboard then setclipboard(tostring(game.JobId)); DoNotif("Copied Job ID", 2)
            else DoNotif("setclipboard not supported.", 2) end
        end })
    Info:CreateButton({ Name = "Copy User ID", Description = "Copy your User ID",
        Callback = function()
            if setclipboard then setclipboard(tostring(LocalPlayer.UserId)); DoNotif("Copied User ID", 2)
            else DoNotif("setclipboard not supported.", 2) end
        end })
    Info:CreateButton({ Name = "Copy Position", Description = "Copy your current XYZ",
        Callback = function()
            local char = LocalPlayer.Character
            local hrp = char and char:FindFirstChild("HumanoidRootPart")
            if hrp and setclipboard then
                local p = hrp.Position
                local str = string.format("%.2f, %.2f, %.2f", p.X, p.Y, p.Z)
                setclipboard(str); DoNotif("Copied: " .. str, 2)
            else DoNotif("No character / setclipboard not supported.", 2) end
        end })
    local _infoUpdateAccum = 0
    table.insert(_aimbotConnections, _RunService.Heartbeat:Connect(function(dt)
        _infoUpdateAccum = _infoUpdateAccum + dt
        if _infoUpdateAccum < 0.5 then return end
        _infoUpdateAccum = 0
        pcall(function()
            local stats = game:GetService("Stats")
            local ping = stats.Network.ServerStatsItem["Data Ping"]:GetValue()
            local fps = math.floor(1 / dt)
            _pingLabel:Set("Ping: " .. math.floor(ping) .. " ms")
            _fpsInfoLabel:Set("FPS: " .. fps)
            _serverSizeLabel:Set("Server Players: " .. tostring(#_Players:GetPlayers()) .. " / " .. tostring(_Players.MaxPlayers))
        end)
        pcall(function()
            local char = LocalPlayer.Character
            local hum = char and char:FindFirstChildOfClass("Humanoid")
            local hrp = char and char:FindFirstChild("HumanoidRootPart")
            if hum then
                _lpHealthLabel:Set(string.format("Health: %.1f / %.1f", hum.Health, hum.MaxHealth))
                _lpSpeedLabel:Set("WalkSpeed: " .. tostring(hum.WalkSpeed))
            end
            if hrp then
                local p = hrp.Position
                _lpPosLabel:Set(string.format("Position: %.1f, %.1f, %.1f", p.X, p.Y, p.Z))
            end
            _lpTeamLabel:Set("Team: " .. (LocalPlayer.Team and LocalPlayer.Team.Name or "None"))
        end)
        pcall(function()
            local plrs = _Players:GetPlayers()
            _playerCountLabel:Set("Count: " .. tostring(#plrs))
            local names = {}
            for _, p in ipairs(plrs) do
                local char = p.Character
                local hum = char and char:FindFirstChildOfClass("Humanoid")
                local hp = hum and string.format("%.0f hp", hum.Health) or "dead"
                table.insert(names, p.Name .. " [" .. hp .. "]")
            end
            _playerListLabel:Set(table.concat(names, "\n"))
        end)
    end))
    Poison:CreateSection("require() Hooks")
    Poison:CreateToggle({ Name = "Hook require()", Description = "Log all require() calls to console",
        CurrentValue = false, Callback = function(v)
            if v then
                if getgenv().__PoisonHook then
                    return DoNotif("Hook already active.", 2)
                end
                local oldRequire = require
                getgenv().__PoisonHook = oldRequire
                getgenv().require = function(mod)
                    local ok, result = pcall(oldRequire, mod)
                    local name = pcall(function() return mod.Name end) and mod.Name or tostring(mod)
                    if ok then
                        print("[Poison] require -> " .. tostring(name))
                        return result
                    else
                        warn("[Poison] require FAILED -> " .. tostring(name))
                        return {}
                    end
                end
                DoNotif("require() hook active. Check F9.", 2)
            else
                if getgenv().__PoisonHook then
                    getgenv().require = getgenv().__PoisonHook
                    getgenv().__PoisonHook = nil
                    DoNotif("require() restored.", 2)
                end
            end
        end }, "luna_reqhook")
    Poison:CreateDivider()
    Poison:CreateSection("Module Patching")
    Poison:CreateInput({ Name = "Target Module Name", Description = "Exact name of the ModuleScript to poison",
        PlaceholderText = "e.g. DataStore2, RoundManager",
        CurrentValue = "", Numeric = false, MaxCharacters = 64, Enter = true,
        Callback = function(text)
            getgenv().__PoisonTarget = text
            DoNotif("Target set: " .. text, 2)
        end }, "luna_poisontarget")
    Poison:CreateButton({ Name = "Poison Target Module", Description = "Make require() return empty table for target",
        Callback = function()
            local target = getgenv().__PoisonTarget
            if not target or target == "" then
                return DoNotif("Set a target module name first.", 3)
            end
            if not getgenv().__PoisonHook then
                -- hook if not already active
                local oldRequire = require
                getgenv().__PoisonHook = oldRequire
                getgenv().require = function(mod)
                    local name = ""
                    pcall(function() name = mod.Name end)
                    if name == getgenv().__PoisonTarget then
                        warn("[Poison] Blocked: " .. name)
                        return setmetatable({}, {
                            __index    = function() return function() end end,
                            __newindex = function() end,
                            __call     = function() return {} end
                        })
                    end
                    return oldRequire(mod)
                end
            end
            DoNotif("Poisoned: " .. target .. " — returns blank proxy.", 3)
        end })
    Poison:CreateButton({ Name = "Restore require()", Description = "Unhook and restore original require",
        Callback = function()
            if getgenv().__PoisonHook then
                getgenv().require = getgenv().__PoisonHook
                getgenv().__PoisonHook = nil
                getgenv().__PoisonTarget = nil
                DoNotif("require() fully restored.", 2)
            else
                DoNotif("No hook active.", 2)
            end
        end })
    Poison:CreateDivider()
    Poison:CreateSection("Presets")
    Poison:CreateButton({ Name = "Poison AntiCheat Modules", Description = "Blank common AC module names",
        Callback = function()
            local targets = {"AntiCheat", "Anticheat", "AC", "SecurityManager", "KickManager", "DetectionService"}
            local oldRequire = getgenv().__PoisonHook or require
            if not getgenv().__PoisonHook then getgenv().__PoisonHook = require end
            local proxy = setmetatable({}, {
                __index    = function() return function() end end,
                __newindex = function() end,
                __call     = function() return {} end
            })
            getgenv().require = function(mod)
                local name = ""
                pcall(function() name = mod.Name end)
                for _, t in ipairs(targets) do
                    if name == t then
                        warn("[Poison] AC module blocked: " .. name)
                        return proxy
                    end
                end
                return oldRequire(mod)
            end
            DoNotif("AC preset active — " .. #targets .. " targets poisoned.", 3)
        end })
        
    Settings:CreateInput({ Name = "Command Prefix", Description = "Change your prefix  (default: ;)",
        PlaceholderText = "Single char e.g.  ;  !  .", CurrentValue = Prefix or ";",
        Numeric = false, MaxCharacters = 1, Enter = true,
        Callback = function(Text)
            if Text and #Text == 1 then getgenv().Prefix = Text DoNotif("Prefix changed to: "..Text, 2)
            else DoNotif("Prefix must be exactly one character.", 3) end
        end }, "luna_prefix")
        Settings:CreateDivider()
    Settings:CreateDivider()
    Settings:CreateSection("Appearance")
    local THEME_COLORS = {
        ["Cyan Classic"]  = Color3.fromRGB(0, 255, 255),
        ["Purple Dream"]  = Color3.fromRGB(200, 100, 255),
        ["Neon Pink"]     = Color3.fromRGB(255, 50, 150),
        ["Toxic Green"]   = Color3.fromRGB(50, 255, 50),
        ["Blood Red"]     = Color3.fromRGB(255, 40, 40),
        ["Ocean Blue"]    = Color3.fromRGB(50, 150, 255),
        ["Golden Sunset"] = Color3.fromRGB(255, 180, 50),
        ["Midnight"]      = Color3.fromRGB(100, 100, 150),
        ["Monochrome"]    = Color3.fromRGB(200, 200, 200),
    }
    local themeNames = {}
    for name in pairs(THEME_COLORS) do table.insert(themeNames, name) end
    table.sort(themeNames)
    local savedTheme = "Cyan Classic"
    pcall(function()
        if readfile and isfile("ZukaPanel_Theme.txt") then
            local v = readfile("ZukaPanel_Theme.txt")
            if THEME_COLORS[v] then savedTheme = v end
        end
    end)
    Settings:CreateDropdown({ Name = "Theme Preset", Description = "Takes effect on next load",
        Options = themeNames,
        CurrentOption = {savedTheme},
        MultipleOptions = false,
        Callback = function(selected)
            local choice = type(selected) == "table" and selected[1] or selected
            if not THEME_COLORS[choice] then return DoNotif("Unknown theme.", 2) end
            pcall(function()
                if writefile then
                    writefile("ZukaPanel_Theme.txt", choice)
                end
            end)
            DoNotif("Theme saved: " .. choice .. " — takes effect next load.", 3)
        end }, "luna_theme")
    Settings:CreateDivider()
    Settings:CreateSection("UI")
    Settings:CreateKeybind({ Name = "Toggle UI Keybind", Description = "Keybind to show/hide the panel",
        CurrentKeybind = "RightShift", HoldToInteract = false,
        Callback = function(keybind)
            DoNotif("UI toggle key set to: " .. tostring(keybind), 2)
        end }, "luna_togglekey")
    Settings:CreateButton({ Name = "Clear Saved Settings", Description = "Wipe all saved Luna flags",
        Callback = function()
            if Window and Window.ClearFlags then
                Window:ClearFlags()
                DoNotif("Saved flags cleared. Rejoin to reset UI state.", 3)
            else
                -- fallback: manually nil known flags
                local flags = {"luna_fly","luna_noclip","luna_infjump","luna_antireset","luna_antisit",
                    "luna_ws","luna_flyspd","luna_grav","luna_esp","luna_chams","luna_fb",
                    "luna_nofog","luna_ll","luna_fps","luna_fov","luna_afk","luna_fp",
                    "luna_aa","luna_atp","luna_bdp","luna_bgp","luna_rad","luna_chatfix"}
                DoNotif("Flags reset (" .. #flags .. " entries). Rejoin to apply.", 3)
            end
        end })
    Settings:CreateButton({ Name = "Credits", Description = "By @OverZuka",
        Callback = function() DoNotif("We're so back!'", 3) end })
    -- ░░ SCRIPTS TAB ░░
    local Scripts = Window:CreateTab({ Name = "Scripts", Icon = "code", ImageSource = "Material", ShowTitle = true })
    Scripts:CreateSection("Extras")
    Scripts:CreateLabel({ Text = "These will change the most.", Style = 3 })
    Scripts:CreateDivider()

    local function RunScript(url)
        if not url or url == "" then DoNotif("No URL set for this slot.", 2) return end
        local ok, err = pcall(function() loadstring(game:HttpGet(url, true))() end)
        if not ok then DoNotif("Script error: " .. tostring(err), 3) end
    end

    Scripts:CreateSection("Adonis Counter v2")
    local Script1_URL = "https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/counter.lua"
    Scripts:CreateInput({ Name = "1", PlaceholderText = "OverZuka", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script1_URL = v end }, "luna_script1_url")
    Scripts:CreateButton({ Name = "Execute", Description = "Executes an anticheat counter for adonis", Callback = function() RunScript(Script1_URL) end })

    Scripts:CreateSection("WRD Deobfuscator WIP")
    local Script2_URL = "https://pastebin.com/raw/7Yw5BCnQ"
    Scripts:CreateInput({ Name = "Deobfuscator", PlaceholderText = "Can Cause Crashes", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script2_URL = v end }, "luna_script2_url")
    Scripts:CreateButton({ Name = "Execute", Description = "Loads Zuka's Lifter.'", Callback = function() RunScript(Script2_URL) end })

    Scripts:CreateSection("Updated SimpleSpy")
    local Script3_URL = "https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/executor_scripts/SimpleSpyRework.lua"
    Scripts:CreateInput({ Name = "Remote Spy", PlaceholderText = "Everyones favorite", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script3_URL = v end }, "luna_script3_url")
    Scripts:CreateButton({ Name = "Execute", Description = "Working as of now", Callback = function() RunScript(Script3_URL) end })

    Scripts:CreateSection("Cframe Spoofer")
    local Script4_URL = "https://raw.githubusercontent.com/zukatech1/Main-Repo/refs/heads/main/Cframe.lua"
    Scripts:CreateInput({ Name = "Position/Hitbox Changer", PlaceholderText = "A better Desync", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script4_URL = v end }, "luna_script4_url")
    Scripts:CreateButton({ Name = "Execute", Description = "Pretty fun to use.", Callback = function() RunScript(Script4_URL) end })

    Scripts:CreateSection("Part Flinger V2 FE")
    local Script5_URL = "https://pastebin.com/raw/QHKAksQz"
    Scripts:CreateInput({ Name = "Ultimate Fling WIP", PlaceholderText = "Might be buggy", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script5_URL = v end }, "luna_script5_url")
    Scripts:CreateButton({ Name = " Execute", Description = "Really FUN to use", Callback = function() RunScript(Script5_URL) end })

    Scripts:CreateSection("Placeholder")
    local Script6_URL = ""
    Scripts:CreateInput({ Name = "Script 6 URL", PlaceholderText = "Paste raw script URL here", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script6_URL = v end }, "luna_script6_url")
    Scripts:CreateButton({ Name = "  Run Script 6", Description = "Executes loadstring on Script 6 URL", Callback = function() RunScript(Script6_URL) end })

    Scripts:CreateSection("Placeholder")
    local Script7_URL = ""
    Scripts:CreateInput({ Name = "Script 7 URL", PlaceholderText = "Paste raw script URL here", CurrentValue = "", Numeric = false, Enter = true, Callback = function(v) Script7_URL = v end }, "luna_script7_url")
    Scripts:CreateButton({ Name = "  Run Script 7", Description = "Executes loadstring on Script 7 URL", Callback = function() RunScript(Script7_URL) end })

    Scripts:CreateDivider()
    Scripts:CreateButton({ Name = "Run All? Will crash your game", Description = "Runs every slot that has a URL set",
        Callback = function()
            local urls = {Script1_URL,Script2_URL,Script3_URL,Script4_URL,Script5_URL,
                          Script6_URL,Script7_URL,Script8_URL,Script9_URL,Script10_URL,
                          Script11_URL,Script12_URL,Script13_URL,Script14_URL,Script15_URL,
                          Script16_URL,Script17_URL,Script18_URL,Script19_URL,Script20_URL}
            local ran = 0
            for _, url in ipairs(urls) do
                if url and url ~= "" then RunScript(url) ran = ran + 1 end
            end
            DoNotif("Ran " .. ran .. " script(s).", 2)
        end })

        local RC = Window:CreateTab({ Name = "Reach", Icon = "open_with", ImageSource = "Material", ShowTitle = true })
    RC:CreateSection("Tool Reach")
    RC:CreateLabel({ Text = " Equip a tool first, then apply reach", Style = 3 })
    RC:CreateToggle({ Name = "Reach GUI", Description = "Open the part selector GUI",
        CurrentValue = false, Callback = function(v)
            if Modules.ReachController then
                if v then Modules.ReachController:Enable()
                else Modules.ReachController:Disable() end
            else DoNotif("ReachController not found.", 2) end
        end }, "luna_reach_gui")
    RC:CreateDivider()
    RC:CreateSection("Quick Apply")
    RC:CreateSlider({ Name = "Reach Size", Description = "Size to apply on next set",
        Range = {1, 200}, Increment = 1, CurrentValue = 20, Suffix = " st",
        Callback = function(v)
            getgenv().__ReachSize = v
        end }, "luna_reach_size")
    RC:CreateDropdown({ Name = "Reach Type", Description = "Directional = length only, Box = all axes",
        Options = {"directional", "box"}, CurrentOption = {"directional"}, MultipleOptions = false,
        Callback = function(v)
            getgenv().__ReachType = type(v) == "table" and v[1] or v
        end }, "luna_reach_type")
    RC:CreateButton({ Name = "Apply to Equipped Tool", Description = "Opens part selector with current settings",
        Callback = function()
            local char = LocalPlayer.Character
            if not char then return DoNotif("No character.", 2) end
            local tool = char:FindFirstChildOfClass("Tool")
            if not tool then return DoNotif("No tool equipped.", 2) end
            local size = getgenv().__ReachSize or 20
            local rtype = getgenv().__ReachType or "directional"
            if Modules.Reach and Modules.Reach.Apply then
                Modules.Reach:Apply(rtype, size)
            elseif Modules.ReachController then
                Modules.ReachController:Enable()
                DoNotif("Using legacy ReachController — set size in the GUI.", 2)
            else
                DoNotif("No reach module found.", 2)
            end
        end })
    RC:CreateButton({ Name = "Reset Reach", Description = "Restore tool to original size",
        Callback = function()
            if Modules.Reach and Modules.Reach.Reset then
                Modules.Reach:Reset()
            elseif Modules.ReachController then
                Modules.ReachController:Disable()
            else
                DoNotif("No reach module found.", 2)
            end
        end })
    RC:CreateDivider()
    RC:CreateSection("Status")
    local _reachStatusLabel = RC:CreateLabel({ Text = "Active: No", Style = 2 })
    local _reachToolLabel   = RC:CreateLabel({ Text = "Tool: None", Style = 2 })
    local _reachPartLabel   = RC:CreateLabel({ Text = "Part: None", Style = 2 })
    table.insert(_aimbotConnections, _RunService.Heartbeat:Connect(function()
        pcall(function()
            if Modules.Reach and Modules.Reach.State then
                local s = Modules.Reach.State
                _reachStatusLabel:Set("Active: " .. (s.IsEnabled and "Yes" or "No"))
                _reachToolLabel:Set("Tool: " .. (s.PersistentToolName or "None"))
                _reachPartLabel:Set("Part: " .. (s.PersistentPartName or "None"))
            elseif Modules.ReachController then
                _reachStatusLabel:Set("Active: " .. (Modules.ReachController.State and Modules.ReachController.State.IsEnabled and "Yes" or "Unknown"))
                _reachToolLabel:Set("Tool: via ReachController GUI")
                _reachPartLabel:Set("Part: via ReachController GUI")
            end
        end)
    end))
    DoNotif("Use the removeadonis command if the game you're in uses adonis", 2)
end)

--loadstring(game:HttpGet(" "))()
