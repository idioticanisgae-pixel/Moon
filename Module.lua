local taskwait = task.wait or wait
local taskspawn = task.spawn or function(f, ...)
    return coroutine.resume(coroutine.create(f), ...)
end
local Signal = {}
Signal.__index = Signal
Signal.__type = "Signal"
Signal.ClassName = "Signal"
local Connection = {}
Connection.__index = Connection
Connection.__type = "Connection"
Connection.ClassName = "Connection"
function Connection.new(Signal: table, Callback: any): table
    local typeofSignal = typeof(Signal)
    assert(typeofSignal == "table" and Signal.ClassName == "Signal", "bad argument #1 to 'new' (Signal expected, got " .. typeofSignal .. ")")
    local typeofCallback = typeof(Callback)
    assert(typeofCallback == "function", "bad argument #2 for 'new' (function expected, got " .. typeofCallback .. ")")
    local self = setmetatable({}, Connection)
    self.Function = Callback
    self.State = true
    self.Signal = Signal
    return self
end
function Connection.Enable(self: table): nil
    self.State = true
end
function Connection.Disable(self: table): nil
    self.State = false
end
function Connection.Disconnect(self: table): nil
    local Connections = self.Signal.Connections
    local selfInTable = table.find(Connections, self)
    table.remove(Connections, selfInTable)
end
Connection.disconnect = Connection.Disconnect
function Signal.new(Name: string): table
    local typeofName = typeof(Name)
    assert(typeofName == "string", "bad argument #1 for 'new' (string expected, got " .. typeofName .. ")")
    local self = setmetatable({}, Signal)
    self.Name = Name
    self.Connections = {}
    return self
end
function Signal.Connect(self: table, Callback: any): table
    local typeofCallback = typeof(Callback)
    assert(typeofCallback == "function", "bad argument #1 for 'Connect' (function expected, got " .. typeofCallback .. ")")
    local connection = Connection.new(self, Callback)
    table.insert(self.Connections, connection)
    return connection
end
Signal.connect = Signal.Connect
function Signal.DisconnectAll(self: table)
    for i = #self.Connections, 1, -1 do
        self.Connections[i]:Disconnect()
    end
end
function Signal.Fire(self: table, ...): nil
    for _, connection in ipairs(self.Connections) do
        if not (connection.State) then
            continue
        end
        taskspawn(connection.Function, ...)
    end
end
Signal.fire = Signal.Fire
function Signal.Wait(self: table, Timeout: number, Filter: FunctionalTest): any
    Timeout = Timeout or (1/0)
    Filter = Filter or function(...) return true end
    local Return = {}
    local Fired = false
    local connection = self:Connect(function(...)
        if (Filter(...)) then
            Return = {...}
            Fired = true
        end
    end)
    local Start = tick()
    while (true) do
        taskwait()
        local timeElapsed = tick() - Start
        if not (Fired or timeElapsed > Timeout) then
            continue
        end
        break
    end
    connection:Disconnect()
    return unpack(Return)
end
Signal.wait = Signal.Wait
function Signal.Destroy(self: table): nil
    self = nil
end
Signal.destroy = Signal.destroy
return Signal
