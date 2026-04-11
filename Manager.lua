local SignalBuilder = loadstring(game:HttpGet("https://raw.githubusercontent.com/idioticanisgae-pixel/Moon/refs/heads/main/Module.lua"))()
local Manager = {}
Manager.__index = Manager
do
    function Manager.new()
        local self = setmetatable({}, Manager)
        self.Signals = {}
        return self
    end
    function Manager.Get(self, SignalName)
        return self.Signals[SignalName]
    end
    function Manager.Add(self, Signal)
        if (typeof(Signal) == "string") then
            Signal = SignalBuilder.new(Signal)
        end
        self.Signals[Signal.Name] = Signal
    end
    function Manager.Remove(self, SignalName)
        self.Signals[SignalName] = nil
    end
    Manager.Create = Manager.Add
    function Manager.Fire(self, SignalName, ...)
        local Signal = self:Get(SignalName)
        assert(Signal, "signal does not exist")
        return Signal:Fire(...)
    end
    function Manager.Connect(self, SignalName, ...)
        local Signal = self:Get(SignalName)
        assert(Signal, "signal does not exist")
        return Signal:Connect(...)
    end
    function Manager.Disconnect(self, SignalName)
        if (SignalName) then
            local Signal = self:Get(SignalName)
            assert(Signal, "signal does not exist")
            return Signal:DisconnectAll()
        end
        for _, Signal in pairs(self.Signals) do
            Signal:DisconnectAll()
        end
    end
    function Manager.Wait(self, SignalName, Timeout, Filter)
        local Signal = self:Get(SignalName)
        assert(Signal, "signal does not exist")
        return Signal:Wait(Timeout, Filter)
    end
end
return ManagerM
