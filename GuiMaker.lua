local TweenService     = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local Players          = game:GetService("Players")
local CoreGui          = game:GetService("CoreGui")
local LocalPlayer      = Players.LocalPlayer
local FONTS = {
    "Gotham", "GothamBold", "GothamBlack", "GothamMedium",
    "Code", "RobotoMono", "Inconsolata",
    "Arial", "ArialBold",
    "SourceSans", "SourceSansBold", "SourceSansItalic", "SourceSansSemibold",
    "Ubuntu", "UbuntuBold", "UbuntuItalic",
    "Merriweather", "MerriweatherBold", "MerriweatherItalic",
    "FredokaOne", "Cartoon", "Fantasy",
    "TitilliumWeb", "Oswald", "Nunito",
}
local HALIGN = {"Left", "Center", "Right"}
local VALIGN = {"Top",  "Center", "Bottom"}
local ELEM_TYPES = {
    { Name = "Frame",          Icon = "▭",  Color = Color3.fromRGB(100,150,220) },
    { Name = "TextLabel",      Icon = "T",  Color = Color3.fromRGB(140,210, 90) },
    { Name = "TextButton",     Icon = "B",  Color = Color3.fromRGB(220,150, 80) },
    { Name = "TextBox",        Icon = "I",  Color = Color3.fromRGB(210, 90,150) },
    { Name = "ImageLabel",     Icon = " ", Color = Color3.fromRGB(150, 90,220) },
    { Name = "ImageButton",    Icon = "B",Color = Color3.fromRGB(180, 60,200) },
    { Name = "ScrollingFrame", Icon = "⇅",  Color = Color3.fromRGB( 80,200,150) },
    { Name = "UIListLayout",   Icon = "≡",  Color = Color3.fromRGB(200,180, 60) },
    { Name = "UIPadding",      Icon = "⊡",  Color = Color3.fromRGB(160,160, 60) },
}
local C = {
    BG          = Color3.fromRGB( 16, 16, 24),
    PANEL       = Color3.fromRGB( 22, 22, 34),
    PANEL2      = Color3.fromRGB( 28, 28, 42),
    ROW         = Color3.fromRGB( 34, 34, 50),
    ROW_SEL     = Color3.fromRGB( 44, 72,160),
    INPUT       = Color3.fromRGB( 20, 20, 32),
    ACCENT      = Color3.fromRGB( 90,140,255),
    ACCENT2     = Color3.fromRGB(  0,200,120),
    LIVE        = Color3.fromRGB(255,140, 40),
    DANGER      = Color3.fromRGB(220, 45, 80),
    TEXT        = Color3.fromRGB(210,215,230),
    MUTED       = Color3.fromRGB(130,135,155),
    WHITE       = Color3.new(1,1,1),
    CANVAS_BG   = Color3.fromRGB( 30, 30, 44),
    WS_BG       = Color3.fromRGB( 42, 42, 56),
}
local function hexToColor(h)
    h = h:gsub("^#","")
    if #h == 6 then
        local r = tonumber(h:sub(1,2),16)
        local g = tonumber(h:sub(3,4),16)
        local b = tonumber(h:sub(5,6),16)
        if r and g and b then return Color3.fromRGB(r,g,b) end
    end
    local p = h:split(",")
    if #p == 3 then
        local r,g,b = tonumber(p[1]),tonumber(p[2]),tonumber(p[3])
        if r and g and b then return Color3.fromRGB(r,g,b) end
    end
    return nil
end
local function colorToHex(c)
    return string.format("#%02X%02X%02X",
        math.round(c.R*255), math.round(c.G*255), math.round(c.B*255))
end
local function corner(obj, r)
    local c = Instance.new("UICorner", obj)
    c.CornerRadius = UDim.new(0, r or 6)
    return c
end
local function stroke(obj, color, thick)
    local s = Instance.new("UIStroke", obj)
    s.Color     = color or C.ACCENT
    s.Thickness = thick or 1.5
    return s
end
local function label(parent, text, size, color, font)
    local l = Instance.new("TextLabel", parent)
    l.BackgroundTransparency = 1
    l.Text     = text
    l.TextSize = size or 12
    l.TextColor3 = color or C.TEXT
    l.Font     = Enum.Font[font or "GothamBold"]
    l.TextXAlignment = Enum.TextXAlignment.Left
    return l
end
local function tween(obj, props, t, style, dir)
    TweenService:Create(obj,
        TweenInfo.new(t or 0.12, Enum.EasingStyle[style or "Quad"], Enum.EasingDirection[dir or "Out"]),
        props):Play()
end
local function isGuiObject(inst)
    return inst:IsA("GuiObject") or inst:IsA("UIBase")
end
local function isStructural(inst)
    return inst:IsA("UIListLayout") or inst:IsA("UIPadding")
        or inst:IsA("UIGridLayout") or inst:IsA("UITableLayout")
        or inst:IsA("UIAspectRatioConstraint") or inst:IsA("UISizeConstraint")
        or inst:IsA("UIStroke") or inst:IsA("UICorner")
end
local GC = {
    State = {
        Mode            = "maker",
        IsEnabled       = false,
        UI              = nil,
        Connections     = {},
        CreatedGUIs     = {},
        SelectedElement = nil,
        PropertyPanel   = nil,
        HierarchyPanel  = nil,
        GridFrame       = nil,
        UndoStack       = {},
        RedoStack       = {},
        CurrentProject  = { Name = "Untitled" },
        LiveTarget      = nil,
        LiveNodes       = {},
        LiveSelected    = nil,
        CodePreviewOpen = false,
    },
    Config = {
        GridSize    = 20,
        SnapToGrid  = false,
        ShowGrid    = true,
        DefaultSize = UDim2.fromOffset(200, 100),
    },
    UI = {},
}
function GC:PushUndo(action)
    table.insert(self.State.UndoStack, action)
    self.State.RedoStack = {}
    if #self.State.UndoStack > 60 then table.remove(self.State.UndoStack,1) end
end
function GC:Undo()
    local a = table.remove(self.State.UndoStack)
    if not a then return end
    table.insert(self.State.RedoStack, a)
    a.Undo()
    self:RefreshHierarchy()
end
function GC:Redo()
    local a = table.remove(self.State.RedoStack)
    if not a then return end
    table.insert(self.State.UndoStack, a)
    a.Do()
    self:RefreshHierarchy()
end
function GC:Snap(v)
    if not self.Config.SnapToGrid then return v end
    local g = self.Config.GridSize
    return math.floor((v + g/2) / g) * g
end
function GC:GetData(element)
    for _, d in ipairs(self.State.CreatedGUIs) do
        if d.Element == element then return d end
    end
end
function GC:MakeBtn(text, color, parent, w, h)
    local btn = Instance.new("TextButton", parent)
    btn.Size             = UDim2.fromOffset(w or 110, h or 26)
    btn.BackgroundColor3 = color
    btn.BorderSizePixel  = 0
    btn.Font             = Enum.Font.GothamBold
    btn.Text             = text
    btn.TextColor3       = C.WHITE
    btn.TextSize         = 11
    btn.AutoButtonColor  = false
    corner(btn, 5)
    btn.MouseEnter:Connect(function()
        local h2,s,v = color:ToHSV()
        tween(btn, {BackgroundColor3 = Color3.fromHSV(h2, s, math.min(v+0.14,1))})
    end)
    btn.MouseLeave:Connect(function()
        tween(btn, {BackgroundColor3 = color})
    end)
    return btn
end
function GC:MakeDraggable(handle, obj)
    local drag, ds, sp = false, nil, nil
    handle.InputBegan:Connect(function(inp)
        if inp.UserInputType == Enum.UserInputType.MouseButton1 then
            drag = true ; ds = inp.Position ; sp = obj.Position
            inp.Changed:Connect(function()
                if inp.UserInputState == Enum.UserInputState.End then drag = false end
            end)
        end
    end)
    UserInputService.InputChanged:Connect(function(inp)
        if drag and inp.UserInputType == Enum.UserInputType.MouseMovement then
            local d = inp.Position - ds
            obj.Position = UDim2.new(sp.X.Scale, sp.X.Offset+d.X, sp.Y.Scale, sp.Y.Offset+d.Y)
        end
    end)
end
function GC:DrawGrid()
    local gf = self.State.GridFrame
    if not gf then return end
    for _, c in ipairs(gf:GetChildren()) do c:Destroy() end
    if not self.Config.ShowGrid then return end
    local ws = gf.Parent
    local W, H = ws.AbsoluteSize.X, ws.AbsoluteSize.Y
    local g = self.Config.GridSize
    for x = 0, W, g do
        local line = Instance.new("Frame", gf)
        line.Size             = UDim2.new(0,1,1,0)
        line.Position         = UDim2.fromOffset(x,0)
        line.BackgroundColor3 = Color3.fromRGB(60,60,80)
        line.BorderSizePixel  = 0
        line.ZIndex           = 1
    end
    for y = 0, H, g do
        local line = Instance.new("Frame", gf)
        line.Size             = UDim2.new(1,0,0,1)
        line.Position         = UDim2.fromOffset(0,y)
        line.BackgroundColor3 = Color3.fromRGB(60,60,80)
        line.BorderSizePixel  = 0
        line.ZIndex           = 1
    end
end
function GC:_bindKeyboard()
    local conn = UserInputService.InputBegan:Connect(function(inp, gpe)
        if gpe then return end
        local ctrl = UserInputService:IsKeyDown(Enum.KeyCode.LeftControl)
                  or UserInputService:IsKeyDown(Enum.KeyCode.RightControl)
        if ctrl and inp.KeyCode == Enum.KeyCode.Z then self:Undo() end
        if ctrl and inp.KeyCode == Enum.KeyCode.Y then self:Redo() end
        if ctrl and inp.KeyCode == Enum.KeyCode.D and self.State.SelectedElement then
            if self.State.Mode == "maker" then
                self:DuplicateElement(self.State.SelectedElement)
            end
        end
        if inp.KeyCode == Enum.KeyCode.Delete and self.State.SelectedElement then
            if self.State.Mode == "maker" then
                self:DeleteElement(self.State.SelectedElement)
            end
        end
    end)
    table.insert(self.State.Connections, conn)
end
function GC:PopulateToolbox(parent)
    for _, et in ipairs(ELEM_TYPES) do
        local btn = Instance.new("TextButton", parent)
        btn.Size             = UDim2.new(1,0,0,36)
        btn.BackgroundColor3 = C.ROW
        btn.BorderSizePixel  = 0
        btn.Font             = Enum.Font.GothamBold
        btn.Text             = et.Icon .. "  " .. et.Name
        btn.TextColor3       = et.Color
        btn.TextSize         = 11
        btn.TextXAlignment   = Enum.TextXAlignment.Left
        btn.AutoButtonColor  = false
        corner(btn, 5)
        local pad = Instance.new("UIPadding", btn)
        pad.PaddingLeft = UDim.new(0, 10)
        btn.MouseEnter:Connect(function()
            tween(btn, {BackgroundColor3 = Color3.fromRGB(50,50,68)})
        end)
        btn.MouseLeave:Connect(function()
            tween(btn, {BackgroundColor3 = C.ROW})
        end)
        btn.MouseButton1Click:Connect(function()
            self:CreateElement(et.Name)
        end)
    end
end
function GC:CreateElement(etype, snapshot)
    local ws = self.UI.Workspace
    local element = Instance.new(etype)
    local idx = #self.State.CreatedGUIs + 1
    element.Name            = etype .. "_" .. idx
    element.BorderSizePixel = 0
    element.ZIndex          = (snapshot and snapshot.ZIndex) or (idx + 2)
    local isStruct = etype == "UIListLayout" or etype == "UIPadding"
    if not isStruct then
        element.Size             = (snapshot and snapshot.Size)     or self.Config.DefaultSize
        element.Position         = (snapshot and snapshot.Position) or UDim2.fromOffset(
            self:Snap(math.random(40,260)), self:Snap(math.random(40,180))
        )
        element.BackgroundColor3 = (snapshot and snapshot.BackgroundColor3)
            or Color3.fromRGB(math.random(90,210), math.random(90,210), math.random(90,210))
    end
    if etype == "TextLabel" or etype == "TextButton" or etype == "TextBox" then
        element.Text             = (snapshot and snapshot.Text)       or element.Name
        element.TextColor3       = (snapshot and snapshot.TextColor3) or C.WHITE
        element.Font             = (snapshot and snapshot.Font)       or Enum.Font.Gotham
        element.TextSize         = (snapshot and snapshot.TextSize)   or 14
        element.TextXAlignment   = (snapshot and snapshot.TextXAlignment) or Enum.TextXAlignment.Left
        element.TextYAlignment   = (snapshot and snapshot.TextYAlignment) or Enum.TextYAlignment.Center
        if etype == "TextBox" then
            element.PlaceholderText  = "Enter text…"
            element.ClearTextOnFocus = false
        end
    end
    if etype == "ImageLabel" or etype == "ImageButton" then
        element.Image     = (snapshot and snapshot.Image) or "rbxasset://textures/ui/GuiImagePlaceholder.png"
        element.ScaleType = Enum.ScaleType.Fit
    end
    if etype == "ScrollingFrame" then
        element.ScrollingEnabled   = true
        element.ScrollBarThickness = 6
        element.CanvasSize         = (snapshot and snapshot.CanvasSize) or UDim2.fromOffset(480,720)
    end
    if etype == "UIListLayout" then
        element.Padding          = UDim.new(0,4)
        element.SortOrder        = Enum.SortOrder.LayoutOrder
        element.FillDirection    = Enum.FillDirection.Vertical
    end
    if etype == "UIPadding" then
        element.PaddingTop    = UDim.new(0,8)
        element.PaddingBottom = UDim.new(0,8)
        element.PaddingLeft   = UDim.new(0,8)
        element.PaddingRight  = UDim.new(0,8)
    end
    local cr = (snapshot and snapshot.CornerRadius) or 8
    if not isStruct then
        Instance.new("UICorner", element).CornerRadius = UDim.new(0, cr)
    end
    element.Parent = ws
    local data = {
        Element      = element,
        Type         = etype,
        CornerRadius = cr,
        Connections  = {},
        IsStruct     = isStruct,
    }
    table.insert(self.State.CreatedGUIs, data)
    if not isStruct then
        self:MakeElementInteractive(element, data)
    end
    self:RefreshHierarchy()
    self:SelectElement(element)
    if not snapshot then
        self:PushUndo({
            Do = function()
                element.Parent = ws
                table.insert(self.State.CreatedGUIs, data)
                self:RefreshHierarchy()
            end,
            Undo = function()
                element.Parent = nil
                for i,d in ipairs(self.State.CreatedGUIs) do
                    if d.Element == element then table.remove(self.State.CreatedGUIs,i) break end
                end
                if self.State.SelectedElement == element then
                    self.State.SelectedElement = nil
                    self:UpdatePropertiesPanel(nil)
                end
                self:RefreshHierarchy()
            end
        })
    end
    return element
end
function GC:DuplicateElement(element)
    local data = self:GetData(element)
    if not data then return end
    local snap = {
        Size             = UDim2.fromOffset(element.Size.X.Offset, element.Size.Y.Offset),
        Position         = UDim2.fromOffset(element.Position.X.Offset+15, element.Position.Y.Offset+15),
        BackgroundColor3 = element.BackgroundColor3,
        ZIndex           = element.ZIndex,
        CornerRadius     = data.CornerRadius or 8,
    }
    if element:IsA("TextLabel") or element:IsA("TextButton") or element:IsA("TextBox") then
        snap.Text           = element.Text
        snap.TextColor3     = element.TextColor3
        snap.TextSize       = element.TextSize
        snap.Font           = element.Font
        snap.TextXAlignment = element.TextXAlignment
        snap.TextYAlignment = element.TextYAlignment
    end
    if element:IsA("ImageLabel") or element:IsA("ImageButton") then snap.Image = element.Image end
    if element:IsA("ScrollingFrame") then
        snap.CanvasSize = UDim2.fromOffset(element.CanvasSize.X.Offset, element.CanvasSize.Y.Offset)
    end
    self:CreateElement(data.Type, snap)
end
function GC:MakeElementInteractive(element, data)
    local canvasPanel = self.UI.Canvas
    local selBox = Instance.new("Frame", canvasPanel)
    selBox.Name                   = "SelBox_" .. element.Name
    selBox.BackgroundTransparency = 1
    selBox.BorderSizePixel        = 0
    selBox.Visible                = false
    selBox.ZIndex                 = 200
    stroke(selBox, C.ACCENT, 2)
    local function syncSel()
        if not element or not element.Parent then return end
        local ws    = self.UI.Workspace
        local wsAbs = ws.AbsolutePosition
        local cpAbs = canvasPanel.AbsolutePosition
        local ox = (wsAbs.X - cpAbs.X) + element.Position.X.Offset
        local oy = (wsAbs.Y - cpAbs.Y) + element.Position.Y.Offset
        selBox.Size     = UDim2.fromOffset(element.AbsoluteSize.X + 6, element.AbsoluteSize.Y + 6)
        selBox.Position = UDim2.fromOffset(ox - 3, oy - 3)
    end
    local HANDLES = {
        {n="NW",ax=0,  ay=0,  cx=true, cy=true},
        {n="N", ax=0.5,ay=0,  cx=false,cy=true},
        {n="NE",ax=1,  ay=0,  cx=true, cy=true},
        {n="W", ax=0,  ay=0.5,cx=true, cy=false},
        {n="E", ax=1,  ay=0.5,cx=true, cy=false},
        {n="SW",ax=0,  ay=1,  cx=true, cy=true},
        {n="S", ax=0.5,ay=1,  cx=false,cy=true},
        {n="SE",ax=1,  ay=1,  cx=true, cy=true},
    }
    local hInst = {}
    for _, hd in ipairs(HANDLES) do
        local h = Instance.new("TextButton", selBox)
        h.Size             = UDim2.fromOffset(10,10)
        h.AnchorPoint      = Vector2.new(0.5,0.5)
        h.Position         = UDim2.new(hd.ax,0,hd.ay,0)
        h.BackgroundColor3 = C.ACCENT
        h.BorderSizePixel  = 0
        h.ZIndex           = 201
        h.Text             = ""
        h.AutoButtonColor  = false
        corner(h, 2)
        hInst[hd.n] = {frame=h, meta=hd}
    end
    local resizing, dragging, resizeHandle = false, false, nil
    local dragStart, startPos, startSize   = nil, nil, nil
    for _, hdata in pairs(hInst) do
        hdata.frame.MouseButton1Down:Connect(function()
            self:SelectElement(element)
            resizing     = true
            dragging     = false
            resizeHandle = hdata.meta
            dragStart    = UserInputService:GetMouseLocation()
            startPos     = {X=element.Position.X.Offset, Y=element.Position.Y.Offset}
            startSize    = {W=element.Size.X.Offset,     H=element.Size.Y.Offset}
        end)
    end
    local ec = element.InputBegan:Connect(function(inp)
        if inp.UserInputType ~= Enum.UserInputType.MouseButton1 then return end
        if resizing then return end
        self:SelectElement(element)
        dragging  = true
        dragStart = inp.Position
        startPos  = {X=element.Position.X.Offset, Y=element.Position.Y.Offset}
        startSize = {W=element.Size.X.Offset,     H=element.Size.Y.Offset}
    end)
    local mc = UserInputService.InputChanged:Connect(function(inp)
        if inp.UserInputType ~= Enum.UserInputType.MouseMovement then return end
        if resizing and resizeHandle then
            local mn = UserInputService:GetMouseLocation()
            local d  = mn - dragStart
            local hd = resizeHandle
            local nx,ny = startPos.X, startPos.Y
            local nw,nh = startSize.W, startSize.H
            if hd.cx then
                if hd.ax == 0 then nw=math.max(20,startSize.W-d.X) ; nx=startPos.X+(startSize.W-nw)
                else nw=math.max(20,startSize.W+d.X) end
            end
            if hd.cy then
                if hd.ay == 0 then nh=math.max(20,startSize.H-d.Y) ; ny=startPos.Y+(startSize.H-nh)
                else nh=math.max(20,startSize.H+d.Y) end
            end
            element.Position = UDim2.fromOffset(self:Snap(nx), self:Snap(ny))
            element.Size     = UDim2.fromOffset(self:Snap(nw), self:Snap(nh))
            syncSel()
            self:UpdatePropertiesPanel(element)
        elseif dragging then
            local d = inp.Position - dragStart
            element.Position = UDim2.fromOffset(self:Snap(startPos.X+d.X), self:Snap(startPos.Y+d.Y))
            syncSel()
        end
    end)
    local rc = UserInputService.InputEnded:Connect(function(inp)
        if inp.UserInputType ~= Enum.UserInputType.MouseButton1 then return end
        if (dragging or resizing) and startPos and startSize then
            local oldPos  = UDim2.fromOffset(startPos.X, startPos.Y)
            local oldSize = UDim2.fromOffset(startSize.W, startSize.H)
            local newPos, newSize = element.Position, element.Size
            if oldPos ~= newPos or oldSize ~= newSize then
                self:PushUndo({
                    Do   = function() element.Position=newPos ; element.Size=newSize ; syncSel() ; self:UpdatePropertiesPanel(element) end,
                    Undo = function() element.Position=oldPos ; element.Size=oldSize ; syncSel() ; self:UpdatePropertiesPanel(element) end,
                })
            end
        end
        dragging = false ; resizing = false ; resizeHandle = nil
    end)
    data.Connections = {ec, mc, rc}
    data.SelectionBox = selBox
    data.SyncSelBox   = syncSel
end
function GC:SelectElement(element)
    if self.State.SelectedElement == element then return end
    if self.State.SelectedElement then
        local od = self:GetData(self.State.SelectedElement)
        if od and od.SelectionBox then od.SelectionBox.Visible = false end
    end
    self.State.SelectedElement = element
    local d = self:GetData(element)
    if d and d.SelectionBox then
        d.SyncSelBox()
        d.SelectionBox.Visible = true
    end
    self:UpdatePropertiesPanel(element)
    self:RefreshHierarchy()
end
function GC:DeleteElement(element)
    local savedType, savedData
    for i, d in ipairs(self.State.CreatedGUIs) do
        if d.Element == element then
            savedType = d.Type ; savedData = d
            table.remove(self.State.CreatedGUIs, i)
            break
        end
    end
    if not savedData then return end
    if savedData.Connections then
        for _, c in ipairs(savedData.Connections) do if c then c:Disconnect() end end
    end
    if savedData.SelectionBox then savedData.SelectionBox:Destroy() end
    local snap = {
        Size=element.Size, Position=element.Position,
        BackgroundColor3=element.BackgroundColor3, ZIndex=element.ZIndex,
        CornerRadius=savedData.CornerRadius or 8,
    }
    if element:IsA("TextLabel") or element:IsA("TextButton") or element:IsA("TextBox") then
        snap.Text=element.Text ; snap.TextColor3=element.TextColor3
        snap.TextSize=element.TextSize ; snap.Font=element.Font
        snap.TextXAlignment=element.TextXAlignment ; snap.TextYAlignment=element.TextYAlignment
    end
    if element:IsA("ImageLabel") or element:IsA("ImageButton") then snap.Image=element.Image end
    if element:IsA("ScrollingFrame") then
        snap.CanvasSize=UDim2.fromOffset(element.CanvasSize.X.Offset, element.CanvasSize.Y.Offset)
    end
    element:Destroy()
    self.State.SelectedElement = nil
    self:UpdatePropertiesPanel(nil)
    self:RefreshHierarchy()
    self:PushUndo({
        Undo = function() self:CreateElement(savedType, snap) end,
        Do   = function()
            local l = self.State.CreatedGUIs[#self.State.CreatedGUIs]
            if l then self:DeleteElement(l.Element) end
        end
    })
end
function GC:ClearCanvas()
    for _, d in ipairs(self.State.CreatedGUIs) do
        if d.Connections then for _,c in ipairs(d.Connections) do if c then c:Disconnect() end end end
        if d.SelectionBox then d.SelectionBox:Destroy() end
        if d.Element then d.Element:Destroy() end
    end
    self.State.CreatedGUIs = {} ; self.State.UndoStack = {} ; self.State.RedoStack = {}
    self.State.SelectedElement = nil
    self:UpdatePropertiesPanel(nil)
    self:RefreshHierarchy()
end
function GC:RefreshHierarchy()
    if self.State.Mode == "live" then
        self:RefreshLiveHierarchy()
        return
    end
    local panel = self.State.HierarchyPanel
    if not panel then return end
    for _, c in ipairs(panel:GetChildren()) do
        if not c:IsA("UIListLayout") then c:Destroy() end
    end
    for _, d in ipairs(self.State.CreatedGUIs) do
        local e = d.Element
        if not e or not e.Parent then continue end
        local isSel = (self.State.SelectedElement == e)
        local row = Instance.new("TextButton", panel)
        row.Size             = UDim2.new(1,-6,0,26)
        row.BorderSizePixel  = 0
        row.Font             = Enum.Font.Code
        row.TextSize         = 11
        row.TextXAlignment   = Enum.TextXAlignment.Left
        row.AutoButtonColor  = false
        row.BackgroundColor3 = isSel and C.ROW_SEL or C.ROW
        row.TextColor3       = isSel and C.WHITE   or C.MUTED
        row.Text             = "  [" .. e.ZIndex .. "]  " .. e.Name
        corner(row, 4)
        row.MouseButton1Click:Connect(function() self:SelectElement(e) end)
        local function zBtn(lbl, off, delta)
            local b = Instance.new("TextButton", row)
            b.Size             = UDim2.fromOffset(18,18)
            b.Position         = UDim2.new(1,off,0.5,-9)
            b.BackgroundColor3 = Color3.fromRGB(60,60,90)
            b.BorderSizePixel  = 0
            b.Font             = Enum.Font.GothamBold
            b.Text             = lbl ; b.TextSize = 9 ; b.TextColor3 = C.WHITE
            corner(b, 3)
            b.MouseButton1Click:Connect(function()
                local oz = e.ZIndex
                local nz = math.max(3, oz+delta)
                e.ZIndex = nz
                self:PushUndo({
                    Do   = function() e.ZIndex=nz ; self:RefreshHierarchy() end,
                    Undo = function() e.ZIndex=oz ; self:RefreshHierarchy() end,
                })
                self:RefreshHierarchy()
                self:UpdatePropertiesPanel(e)
            end)
        end
        zBtn("▲",-42,1) ; zBtn("▼",-21,-1)
    end
end
function GC:UpdatePropertiesPanel(element)
    local panel = self.State.PropertyPanel
    if not panel then return end
    for _, c in ipairs(panel:GetChildren()) do
        if not c:IsA("UIListLayout") then c:Destroy() end
    end
    if not element then return end
    local data = self:GetData(element)
    local function prop(name, val, onChange)
        local con = Instance.new("Frame", panel)
        con.Size             = UDim2.new(1,-6,0,48)
        con.BackgroundColor3 = C.ROW
        con.BorderSizePixel  = 0
        corner(con, 5)
        local lbl = Instance.new("TextLabel", con)
        lbl.Size=UDim2.new(1,-10,0,18) ; lbl.Position=UDim2.fromOffset(6,4)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local inp = Instance.new("TextBox", con)
        inp.Size=UDim2.new(1,-12,0,20) ; inp.Position=UDim2.fromOffset(6,24)
        inp.BackgroundColor3=C.INPUT ; inp.BorderSizePixel=0
        inp.Font=Enum.Font.Code ; inp.Text=tostring(val)
        inp.TextColor3=C.WHITE ; inp.TextSize=11
        inp.ClearTextOnFocus=false
        corner(inp, 4)
        inp.FocusLost:Connect(function() onChange(inp.Text) end)
    end
    local function colorProp(name, color, onChange)
        local con = Instance.new("Frame", panel)
        con.Size=UDim2.new(1,-6,0,50) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl = Instance.new("TextLabel", con)
        lbl.Size=UDim2.new(1,-46,0,18) ; lbl.Position=UDim2.fromOffset(6,4)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local preview = Instance.new("Frame", con)
        preview.Size=UDim2.fromOffset(26,26) ; preview.Position=UDim2.new(1,-32,0,4)
        preview.BackgroundColor3=color ; preview.BorderSizePixel=0
        corner(preview,4) ; stroke(preview, Color3.fromRGB(80,80,100), 1)
        local inp = Instance.new("TextBox", con)
        inp.Size=UDim2.new(1,-12,0,20) ; inp.Position=UDim2.fromOffset(6,26)
        inp.BackgroundColor3=C.INPUT ; inp.BorderSizePixel=0
        inp.Font=Enum.Font.Code ; inp.Text=colorToHex(color)
        inp.TextColor3=C.WHITE ; inp.TextSize=11 ; inp.PlaceholderText="#RRGGBB or R,G,B"
        inp.ClearTextOnFocus=false
        corner(inp,4)
        inp.FocusLost:Connect(function()
            local nc = hexToColor(inp.Text)
            if nc then
                preview.BackgroundColor3=nc
                onChange(nc)
                inp.Text=colorToHex(nc)
            end
        end)
    end
    local function toggleProp(name, val, onChange)
        local con = Instance.new("Frame", panel)
        con.Size=UDim2.new(1,-6,0,34) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl = Instance.new("TextLabel", con)
        lbl.Size=UDim2.new(1,-54,1,0) ; lbl.Position=UDim2.fromOffset(6,0)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local v = val
        local tb = Instance.new("TextButton", con)
        tb.Size=UDim2.fromOffset(46,22) ; tb.Position=UDim2.new(1,-52,0.5,-11)
        tb.BorderSizePixel=0 ; tb.Font=Enum.Font.GothamBold
        tb.TextSize=10 ; tb.TextColor3=C.WHITE ; tb.AutoButtonColor=false
        corner(tb,4)
        local function ref()
            tb.Text=v and "ON" or "OFF"
            tb.BackgroundColor3 = v and C.ACCENT2 or C.DANGER
        end
        ref()
        tb.MouseButton1Click:Connect(function() v=not v ; ref() ; onChange(v) end)
    end
    local function dropProp(name, options, current, onChange)
        local con = Instance.new("Frame", panel)
        con.Size=UDim2.new(1,-6,0,48) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl = Instance.new("TextLabel", con)
        lbl.Size=UDim2.new(1,-10,0,18) ; lbl.Position=UDim2.fromOffset(6,4)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local ci = 1
        for i,v in ipairs(options) do if v==current then ci=i break end end
        local curLabel = Instance.new("TextButton", con)
        curLabel.Size=UDim2.new(1,-12,0,20) ; curLabel.Position=UDim2.fromOffset(6,24)
        curLabel.BackgroundColor3=C.INPUT ; curLabel.BorderSizePixel=0
        curLabel.Font=Enum.Font.Code ; curLabel.Text="◀  "..options[ci].."  ▶"
        curLabel.TextColor3=C.WHITE ; curLabel.TextSize=11
        curLabel.AutoButtonColor=false
        corner(curLabel,4)
        curLabel.MouseButton1Click:Connect(function()
            ci = ci % #options + 1
            curLabel.Text = "◀  "..options[ci].."  ▶"
            onChange(options[ci])
        end)
    end
    prop("Name", element.Name, function(v)
        local old=element.Name ; element.Name=v
        self:PushUndo({Do=function() element.Name=v end, Undo=function() element.Name=old end})
        self:RefreshHierarchy()
    end)
    local isStruct = data and data.IsStruct
    if not isStruct then
        prop("Size X", element.Size.X.Offset, function(v)
            element.Size=UDim2.fromOffset(tonumber(v) or 200, element.Size.Y.Offset)
            if data then data.SyncSelBox() end
        end)
        prop("Size Y", element.Size.Y.Offset, function(v)
            element.Size=UDim2.fromOffset(element.Size.X.Offset, tonumber(v) or 100)
            if data then data.SyncSelBox() end
        end)
        prop("Pos X", element.Position.X.Offset, function(v)
            element.Position=UDim2.fromOffset(tonumber(v) or 0, element.Position.Y.Offset)
            if data then data.SyncSelBox() end
        end)
        prop("Pos Y", element.Position.Y.Offset, function(v)
            element.Position=UDim2.fromOffset(element.Position.X.Offset, tonumber(v) or 0)
            if data then data.SyncSelBox() end
        end)
        prop("ZIndex", element.ZIndex, function(v)
            local old=element.ZIndex ; local nz=math.max(1,tonumber(v) or 1)
            element.ZIndex=nz
            self:PushUndo({Do=function() element.ZIndex=nz end, Undo=function() element.ZIndex=old end})
            self:RefreshHierarchy()
        end)
        prop("Corner Radius", (data and data.CornerRadius) or 8, function(v)
            local r=math.max(0,tonumber(v) or 8)
            if data then data.CornerRadius=r end
            local c=element:FindFirstChildOfClass("UICorner")
            if c then c.CornerRadius=UDim.new(0,r) end
        end)
        prop("AnchorPoint X", element.AnchorPoint.X, function(v)
            element.AnchorPoint=Vector2.new(math.clamp(tonumber(v) or 0,0,1), element.AnchorPoint.Y)
            if data then data.SyncSelBox() end
        end)
        prop("AnchorPoint Y", element.AnchorPoint.Y, function(v)
            element.AnchorPoint=Vector2.new(element.AnchorPoint.X, math.clamp(tonumber(v) or 0,0,1))
            if data then data.SyncSelBox() end
        end)
        colorProp("BG Color", element.BackgroundColor3, function(c) element.BackgroundColor3=c end)
        prop("BG Transparency", element.BackgroundTransparency, function(v)
            element.BackgroundTransparency=math.clamp(tonumber(v) or 0,0,1)
        end)
        toggleProp("Visible", element.Visible, function(v) element.Visible=v end)
    end
    if element:IsA("TextLabel") or element:IsA("TextButton") or element:IsA("TextBox") then
        prop("Text", element.Text, function(v) element.Text=v end)
        prop("Text Size", element.TextSize, function(v) element.TextSize=tonumber(v) or 14 end)
        colorProp("Text Color", element.TextColor3, function(c) element.TextColor3=c end)
        prop("Text Transparency", element.TextTransparency, function(v)
            element.TextTransparency=math.clamp(tonumber(v) or 0,0,1)
        end)
        toggleProp("Text Wrapped", element.TextWrapped, function(v) element.TextWrapped=v end)
        toggleProp("Text Scaled", element.TextScaled, function(v) element.TextScaled=v end)
        local fontName = tostring(element.Font):gsub("Enum%.Font%.","")
        dropProp("Font", FONTS, fontName, function(v)
            pcall(function() element.Font = Enum.Font[v] end)
        end)
        dropProp("H Align", HALIGN,
            tostring(element.TextXAlignment):gsub("Enum%.TextXAlignment%.",""),
            function(v) pcall(function() element.TextXAlignment=Enum.TextXAlignment[v] end) end)
        dropProp("V Align", VALIGN,
            tostring(element.TextYAlignment):gsub("Enum%.TextYAlignment%.",""),
            function(v) pcall(function() element.TextYAlignment=Enum.TextYAlignment[v] end) end)
        if element:IsA("TextBox") then
            prop("Placeholder", element.PlaceholderText, function(v) element.PlaceholderText=v end)
            toggleProp("Clear On Focus", element.ClearTextOnFocus, function(v) element.ClearTextOnFocus=v end)
        end
    end
    if element:IsA("ImageLabel") or element:IsA("ImageButton") then
        prop("Image ID", element.Image, function(v) element.Image=v end)
        prop("Image Transparency", element.ImageTransparency, function(v)
            element.ImageTransparency=math.clamp(tonumber(v) or 0,0,1)
        end)
        dropProp("Scale Type", {"Fit","Crop","Stretch","Tile","Slice"},
            tostring(element.ScaleType):gsub("Enum%.ScaleType%.",""),
            function(v) pcall(function() element.ScaleType=Enum.ScaleType[v] end) end)
    end
    if element:IsA("ScrollingFrame") then
        prop("Canvas W", element.CanvasSize.X.Offset, function(v)
            element.CanvasSize=UDim2.fromOffset(tonumber(v) or 480, element.CanvasSize.Y.Offset)
        end)
        prop("Canvas H", element.CanvasSize.Y.Offset, function(v)
            element.CanvasSize=UDim2.fromOffset(element.CanvasSize.X.Offset, tonumber(v) or 720)
        end)
        prop("Scrollbar Thickness", element.ScrollBarThickness, function(v)
            element.ScrollBarThickness=tonumber(v) or 6
        end)
        toggleProp("Scrolling Enabled", element.ScrollingEnabled, function(v)
            element.ScrollingEnabled=v
        end)
    end
    if element:IsA("UIListLayout") then
        prop("Padding", element.Padding.Offset, function(v)
            element.Padding=UDim.new(0, tonumber(v) or 4)
        end)
        dropProp("Fill Direction", {"Vertical","Horizontal"},
            tostring(element.FillDirection):gsub("Enum%.FillDirection%.",""),
            function(v) pcall(function() element.FillDirection=Enum.FillDirection[v] end) end)
        dropProp("H Align", {"Left","Center","Right"},
            tostring(element.HorizontalAlignment):gsub("Enum%.HorizontalAlignment%.",""),
            function(v) pcall(function() element.HorizontalAlignment=Enum.HorizontalAlignment[v] end) end)
        dropProp("V Align", {"Top","Center","Bottom"},
            tostring(element.VerticalAlignment):gsub("Enum%.VerticalAlignment%.",""),
            function(v) pcall(function() element.VerticalAlignment=Enum.VerticalAlignment[v] end) end)
    end
    if element:IsA("UIPadding") then
        prop("Pad Top",    element.PaddingTop.Offset,    function(v) element.PaddingTop=UDim.new(0,tonumber(v) or 0) end)
        prop("Pad Bottom", element.PaddingBottom.Offset, function(v) element.PaddingBottom=UDim.new(0,tonumber(v) or 0) end)
        prop("Pad Left",   element.PaddingLeft.Offset,   function(v) element.PaddingLeft=UDim.new(0,tonumber(v) or 0) end)
        prop("Pad Right",  element.PaddingRight.Offset,  function(v) element.PaddingRight=UDim.new(0,tonumber(v) or 0) end)
    end
    if not isStruct then
        local dupBtn = self:MakeBtn("⧉  DUPLICATE  (Ctrl+D)", C.ACCENT, panel, 0, 30)
        dupBtn.Size = UDim2.new(1,-6,0,30)
        dupBtn.MouseButton1Click:Connect(function() self:DuplicateElement(element) end)
    end
    local delBtn = self:MakeBtn("🗑  DELETE ELEMENT", C.DANGER, panel, 0, 30)
    delBtn.Size = UDim2.new(1,-6,0,30)
    delBtn.MouseButton1Click:Connect(function() self:DeleteElement(element) end)
end
function GC:ExportCode()
    local lines = {}
    local w = function(s) table.insert(lines,s) end
    w("-- ════════════════════════════════════════")
    w("-- Generated by GUI Creator v2  (Zuka)")
    w("-- Project: " .. self.State.CurrentProject.Name)
    w("-- ════════════════════════════════════════")
    w("local Players     = game:GetService('Players')")
    w("local LocalPlayer = Players.LocalPlayer")
    w("")
    w("local ScreenGui = Instance.new('ScreenGui')")
    w("ScreenGui.Name           = '"..self.State.CurrentProject.Name.."'")
    w("ScreenGui.ResetOnSpawn   = false")
    w("ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling")
    w("ScreenGui.Parent         = LocalPlayer:WaitForChild('PlayerGui')")
    w("")
    for _, data in ipairs(self.State.CreatedGUIs) do
        local e = data.Element
        if not e or not e.Parent then continue end
        local n = e.Name
        w("-- " .. n)
        w(string.format("local %s = Instance.new('%s')", n, data.Type))
        w(string.format("%s.Name = '%s'", n, n))
        if not data.IsStruct then
            w(string.format("%s.Size = UDim2.fromOffset(%d, %d)", n, e.Size.X.Offset, e.Size.Y.Offset))
            w(string.format("%s.Position = UDim2.fromOffset(%d, %d)", n, e.Position.X.Offset, e.Position.Y.Offset))
            w(string.format("%s.AnchorPoint = Vector2.new(%g, %g)", n, e.AnchorPoint.X, e.AnchorPoint.Y))
            w(string.format("%s.BackgroundColor3 = Color3.fromRGB(%d, %d, %d)",
                n, math.round(e.BackgroundColor3.R*255), math.round(e.BackgroundColor3.G*255), math.round(e.BackgroundColor3.B*255)))
            w(string.format("%s.BackgroundTransparency = %g", n, e.BackgroundTransparency))
            w(string.format("%s.BorderSizePixel = 0", n))
            w(string.format("%s.ZIndex = %d", n, e.ZIndex))
            w(string.format("%s.Visible = %s", n, tostring(e.Visible)))
        end
        if e:IsA("TextLabel") or e:IsA("TextButton") or e:IsA("TextBox") then
            w(string.format("%s.Text = '%s'", n, e.Text:gsub("'","\\'")))
            w(string.format("%s.TextColor3 = Color3.fromRGB(%d, %d, %d)",
                n, math.round(e.TextColor3.R*255), math.round(e.TextColor3.G*255), math.round(e.TextColor3.B*255)))
            w(string.format("%s.TextSize = %d", n, e.TextSize))
            w(string.format("%s.Font = Enum.Font.%s", n, tostring(e.Font):gsub("Enum%.Font%.","")) )
            w(string.format("%s.TextXAlignment = Enum.TextXAlignment.%s", n, tostring(e.TextXAlignment):gsub("Enum%.TextXAlignment%.","")) )
            w(string.format("%s.TextYAlignment = Enum.TextYAlignment.%s", n, tostring(e.TextYAlignment):gsub("Enum%.TextYAlignment%.","")) )
            w(string.format("%s.TextWrapped = %s", n, tostring(e.TextWrapped)))
        end
        if e:IsA("ImageLabel") or e:IsA("ImageButton") then
            w(string.format("%s.Image = '%s'", n, e.Image))
            w(string.format("%s.ScaleType = Enum.ScaleType.%s", n, tostring(e.ScaleType):gsub("Enum%.ScaleType%.","")) )
        end
        if e:IsA("ScrollingFrame") then
            w(string.format("%s.ScrollBarThickness = %d", n, e.ScrollBarThickness))
            w(string.format("%s.CanvasSize = UDim2.fromOffset(%d, %d)", n, e.CanvasSize.X.Offset, e.CanvasSize.Y.Offset))
            w(string.format("%s.ScrollingEnabled = %s", n, tostring(e.ScrollingEnabled)))
        end
        if e:IsA("UIListLayout") then
            w(string.format("%s.Padding = UDim.new(0, %d)", n, e.Padding.Offset))
            w(string.format("%s.FillDirection = Enum.FillDirection.%s", n, tostring(e.FillDirection):gsub("Enum%.FillDirection%.","")) )
            w(string.format("%s.SortOrder = Enum.SortOrder.LayoutOrder", n))
        end
        if e:IsA("UIPadding") then
            w(string.format("%s.PaddingTop    = UDim.new(0, %d)", n, e.PaddingTop.Offset))
            w(string.format("%s.PaddingBottom = UDim.new(0, %d)", n, e.PaddingBottom.Offset))
            w(string.format("%s.PaddingLeft   = UDim.new(0, %d)", n, e.PaddingLeft.Offset))
            w(string.format("%s.PaddingRight  = UDim.new(0, %d)", n, e.PaddingRight.Offset))
        end
        if not data.IsStruct then
            local cr = data.CornerRadius or 8
            w(string.format("do local _c = Instance.new('UICorner', %s); _c.CornerRadius = UDim.new(0, %d) end", n, cr))
        end
        w(string.format("%s.Parent = ScreenGui", n))
        w("")
    end
    local code = table.concat(lines, "\n")
    self:ShowCodePreview(code)
    if setclipboard then
        setclipboard(code)
        print("[GUICreator] ✓ Copied to clipboard")
    else
        print(code)
    end
end
function GC:ShowCodePreview(code)
    local existing = self.UI.MainFrame:FindFirstChild("CodePreview")
    if existing then existing:Destroy() end
    local panel = Instance.new("Frame", self.UI.MainFrame)
    panel.Name             = "CodePreview"
    panel.Size             = UDim2.new(0,520,1,-90)
    panel.Position         = UDim2.new(0.5,-260,0,86)
    panel.BackgroundColor3 = Color3.fromRGB(12,12,20)
    panel.BorderSizePixel  = 0
    panel.ZIndex           = 500
    corner(panel, 8)
    stroke(panel, C.ACCENT2, 2)
    local topbar = Instance.new("Frame", panel)
    topbar.Size=UDim2.new(1,0,0,34) ; topbar.BackgroundColor3=C.PANEL ; topbar.BorderSizePixel=0
    corner(topbar, 8)
    local ttl = Instance.new("TextLabel", topbar)
    ttl.Size=UDim2.new(1,-90,1,0) ; ttl.Position=UDim2.fromOffset(12,0)
    ttl.BackgroundTransparency=1 ; ttl.Font=Enum.Font.GothamBold
    ttl.Text="📋  GENERATED CODE" ; ttl.TextColor3=C.ACCENT2 ; ttl.TextSize=13
    ttl.TextXAlignment=Enum.TextXAlignment.Left
    local closeBtn = self:MakeBtn("✕ CLOSE", C.DANGER, topbar, 80, 24)
    closeBtn.Position = UDim2.new(1,-86,0.5,-12)
    closeBtn.MouseButton1Click:Connect(function() panel:Destroy() end)
    local scroll = Instance.new("ScrollingFrame", panel)
    scroll.Size=UDim2.new(1,-16,1,-42) ; scroll.Position=UDim2.fromOffset(8,38)
    scroll.BackgroundTransparency=1 ; scroll.BorderSizePixel=0
    scroll.ScrollBarThickness=4 ; scroll.ScrollBarImageColor3=C.ACCENT2
    scroll.CanvasSize=UDim2.fromOffset(0,0) ; scroll.AutomaticCanvasSize=Enum.AutomaticSize.Y
    local codeLabel = Instance.new("TextLabel", scroll)
    codeLabel.Size=UDim2.new(1,-10,0,0) ; codeLabel.AutomaticSize=Enum.AutomaticSize.Y
    codeLabel.BackgroundTransparency=1 ; codeLabel.Font=Enum.Font.Code
    codeLabel.Text=code ; codeLabel.TextColor3=Color3.fromRGB(180,220,150)
    codeLabel.TextSize=11 ; codeLabel.TextXAlignment=Enum.TextXAlignment.Left
    codeLabel.TextYAlignment=Enum.TextYAlignment.Top
    codeLabel.TextWrapped=false
end
function GC:GetAllScreenGuis()
    local results = {}
    local pg = LocalPlayer:FindFirstChild("PlayerGui")
    if not pg then return results end
    for _, ch in ipairs(pg:GetChildren()) do
        if ch:IsA("ScreenGui") and ch.Name ~= "GUICreator_Zuka" then
            table.insert(results, ch)
        end
    end
    pcall(function()
        for _, ch in ipairs(CoreGui:GetChildren()) do
            if ch:IsA("ScreenGui") and ch.Name ~= "GUICreator_Zuka" then
                table.insert(results, ch)
            end
        end
    end)
    return results
end
function GC:OpenLivePicker()
    local existing = self.UI.MainFrame:FindFirstChild("LivePicker")
    if existing then existing:Destroy() ; return end
    local modal = Instance.new("Frame", self.UI.MainFrame)
    modal.Name             = "LivePicker"
    modal.Size             = UDim2.fromOffset(340, 420)
    modal.Position         = UDim2.new(0.5,-170,0.5,-210)
    modal.BackgroundColor3 = C.PANEL
    modal.BorderSizePixel  = 0
    modal.ZIndex           = 600
    corner(modal, 10)
    stroke(modal, C.LIVE, 2)
    self:MakeDraggable(modal, modal)
    local ttl = Instance.new("TextLabel", modal)
    ttl.Size=UDim2.new(1,0,0,38) ; ttl.BackgroundTransparency=1
    ttl.Font=Enum.Font.GothamBold ; ttl.Text="🔍  SELECT A SCREENGUI TO EDIT"
    ttl.TextColor3=C.LIVE ; ttl.TextSize=13
    ttl.TextXAlignment=Enum.TextXAlignment.Center
    local closeBtn = self:MakeBtn("✕", C.DANGER, modal, 28, 28)
    closeBtn.Position=UDim2.new(1,-32,0,5)
    closeBtn.MouseButton1Click:Connect(function() modal:Destroy() end)
    local scroll = Instance.new("ScrollingFrame", modal)
    scroll.Size=UDim2.new(1,-16,1,-50) ; scroll.Position=UDim2.fromOffset(8,42)
    scroll.BackgroundTransparency=1 ; scroll.BorderSizePixel=0
    scroll.ScrollBarThickness=4 ; scroll.ScrollBarImageColor3=C.LIVE
    scroll.CanvasSize=UDim2.fromOffset(0,0) ; scroll.AutomaticCanvasSize=Enum.AutomaticSize.Y
    local lay = Instance.new("UIListLayout", scroll)
    lay.Padding=UDim.new(0,5) ; lay.SortOrder=Enum.SortOrder.LayoutOrder
    local guis = self:GetAllScreenGuis()
    if #guis == 0 then
        local none = Instance.new("TextLabel", scroll)
        none.Size=UDim2.new(1,0,0,40) ; none.BackgroundTransparency=1
        none.Font=Enum.Font.GothamBold ; none.Text="No ScreenGuis found."
        none.TextColor3=C.MUTED ; none.TextSize=13
    else
        for _, gui in ipairs(guis) do
            local childCount = #gui:GetDescendants()
            local row = self:MakeBtn("🖥  " .. gui.Name .. "  (" .. childCount .. " descendants)", C.ROW, scroll, 0, 40)
            row.Size=UDim2.new(1,0,0,40)
            row.TextSize=12 ; row.TextXAlignment=Enum.TextXAlignment.Left
            local pad = Instance.new("UIPadding", row) ; pad.PaddingLeft=UDim.new(0,10)
            row.MouseButton1Click:Connect(function()
                modal:Destroy()
                self:LoadLiveGui(gui)
            end)
        end
    end
    local refBtn = self:MakeBtn("⟳  Refresh List", C.ACCENT, modal, 130, 26)
    refBtn.Position=UDim2.new(0.5,-65,1,-34)
    refBtn.MouseButton1Click:Connect(function()
        modal:Destroy()
        self:OpenLivePicker()
    end)
end
function GC:LoadLiveGui(gui)
    self.State.Mode       = "live"
    self.State.LiveTarget = gui
    self.State.LiveNodes  = {}
    self.State.LiveSelected = nil
    if self.UI.ModeLabel then
        self.UI.ModeLabel.Text            = "⚡  LIVE EDIT: " .. gui.Name
        self.UI.ModeLabel.TextColor3      = C.LIVE
    end
    if self.UI.ModeBar then
        self.UI.ModeBar.BackgroundColor3 = Color3.fromRGB(40,25,10)
    end
    if self.UI.Toolbox   then self.UI.Toolbox.Visible   = false end
    if self.UI.LivePanel then self.UI.LivePanel.Visible  = true  end
    if self.UI.Canvas then
        self.UI.Canvas.Visible = false
    end
    if self.UI.HierPanel then
        self.UI.HierPanel.Parent   = self.UI.MainFrame
        self.UI.HierPanel.Size     = UDim2.new(0, 360, 1, -90)
        self.UI.HierPanel.Position = UDim2.fromOffset(183, 86)
    end
    if self.UI.RightCol then
        self.UI.RightCol.Parent   = self.UI.MainFrame
        self.UI.RightCol.Size     = UDim2.new(0, 280, 1, -90)
        self.UI.RightCol.Position = UDim2.new(1, -290, 0, 86)
    end
    self:RefreshLiveHierarchy()
    print("[GUICreator] Live editing: " .. gui:GetFullName())
end
function GC:ExitLiveMode()
    self.State.Mode         = "maker"
    self.State.LiveTarget   = nil
    self.State.LiveNodes    = {}
    self.State.LiveSelected = nil
    if self.UI.ModeLabel then
        self.UI.ModeLabel.Text       = "▸ GUI CREATOR  v2.0  —  Ctrl+Z  Ctrl+Y  Ctrl+D  Del"
        self.UI.ModeLabel.TextColor3 = C.ACCENT
    end
    if self.UI.ModeBar then
        self.UI.ModeBar.BackgroundColor3 = C.PANEL
    end
    if self.UI.Toolbox   then self.UI.Toolbox.Visible   = true  end
    if self.UI.LivePanel then self.UI.LivePanel.Visible  = false end
    if self.UI.Canvas    then self.UI.Canvas.Visible     = true  end
    if self.UI.HierPanel and self.UI.RightCol then
        self.UI.HierPanel.Parent   = self.UI.RightCol
        self.UI.HierPanel.Size     = UDim2.new(1, 0, 0.48, -4)
        self.UI.HierPanel.Position = UDim2.new(0, 0, 0.52, 4)
    end
    if self.UI.RightCol then
        self.UI.RightCol.Parent   = self.UI.MainFrame
        self.UI.RightCol.Size     = UDim2.new(0, 240, 1, -90)
        self.UI.RightCol.Position = UDim2.new(1, -250, 0, 86)
    end
    self:UpdatePropertiesPanel(nil)
    self:RefreshHierarchy()
end
function GC:RefreshLiveHierarchy()
    local panel = self.State.HierarchyPanel
    if not panel then return end
    for _, c in ipairs(panel:GetChildren()) do
        if not c:IsA("UIListLayout") then c:Destroy() end
    end
    local target = self.State.LiveTarget
    if not target then return end
    local expanded = {}
    for _, nd in ipairs(self.State.LiveNodes) do
        if nd.expanded then expanded[nd.inst] = true end
    end
    self.State.LiveNodes = {}
    local function buildTree(inst, depth)
        if not inst or not inst.Parent then return end
        local isSel = (self.State.LiveSelected == inst)
        local row = Instance.new("Frame", panel)
        row.Size             = UDim2.new(1,-6,0,24)
        row.BackgroundColor3 = isSel and C.ROW_SEL or (depth==0 and Color3.fromRGB(30,30,50) or C.ROW)
        row.BorderSizePixel  = 0
        corner(row, 4)
        local isExpanded = expanded[inst] or false
        local kids = {}
        for _, ch in ipairs(inst:GetChildren()) do
            if isGuiObject(ch) or isStructural(ch) then
                table.insert(kids, ch)
            end
        end
        local hasKids = #kids > 0
        local toggle = Instance.new("TextButton", row)
        toggle.Size             = UDim2.fromOffset(16,16)
        toggle.Position         = UDim2.fromOffset(4 + depth*14, 4)
        toggle.BackgroundTransparency = 1
        toggle.BorderSizePixel  = 0
        toggle.Font             = Enum.Font.GothamBold
        toggle.TextSize         = 11
        toggle.TextColor3       = C.MUTED
        toggle.Text             = hasKids and (isExpanded and "▾" or "▸") or "•"
        toggle.AutoButtonColor  = false
        local nameBtn = Instance.new("TextButton", row)
        local indentX = 24 + depth*14
        nameBtn.Size             = UDim2.new(1,-indentX-4,1,0)
        nameBtn.Position         = UDim2.fromOffset(indentX,0)
        nameBtn.BackgroundTransparency = 1
        nameBtn.BorderSizePixel  = 0
        nameBtn.Font             = Enum.Font.Code
        nameBtn.TextSize         = 11
        nameBtn.TextXAlignment   = Enum.TextXAlignment.Left
        nameBtn.AutoButtonColor  = false
        local classShort = inst.ClassName
        local typeColor = Color3.fromRGB(140,200,255)
        if isStructural(inst) then typeColor=Color3.fromRGB(220,200,80)
        elseif inst:IsA("TextButton") or inst:IsA("ImageButton") then typeColor=Color3.fromRGB(220,140,80)
        elseif inst:IsA("TextLabel") then typeColor=Color3.fromRGB(140,220,100)
        elseif inst:IsA("ImageLabel") then typeColor=Color3.fromRGB(180,120,240) end
        nameBtn.TextColor3 = isSel and C.WHITE or typeColor
        nameBtn.Text       = inst.Name .. "  [" .. classShort .. "]"
        local nd = {inst=inst, depth=depth, expanded=isExpanded}
        table.insert(self.State.LiveNodes, nd)
        nameBtn.MouseButton1Click:Connect(function()
            self.State.LiveSelected = inst
            self:UpdateLivePropertiesPanel(inst)
            self:RefreshLiveHierarchy()
        end)
        if hasKids then
            toggle.MouseButton1Click:Connect(function()
                nd.expanded = not nd.expanded
                self:RefreshLiveHierarchy()
            end)
        end
        if isExpanded and hasKids then
            for _, ch in ipairs(kids) do
                buildTree(ch, depth+1)
            end
        end
    end
    buildTree(target, 0)
end
function GC:UpdateLivePropertiesPanel(inst)
    self.State.SelectedElement = inst
    local panel = self.State.PropertyPanel
    if not panel then return end
    for _, c in ipairs(panel:GetChildren()) do
        if not c:IsA("UIListLayout") then c:Destroy() end
    end
    if not inst then return end
    local hdr = Instance.new("TextLabel", panel)
    hdr.Size=UDim2.new(1,-6,0,28) ; hdr.BackgroundColor3=Color3.fromRGB(40,25,10)
    hdr.BorderSizePixel=0 ; hdr.Font=Enum.Font.GothamBold
    hdr.Text="  ⚡ " .. inst.ClassName .. "  ·  " .. inst.Name
    hdr.TextColor3=C.LIVE ; hdr.TextSize=11
    hdr.TextXAlignment=Enum.TextXAlignment.Left
    corner(hdr,5)
    local pad = Instance.new("UIPadding",hdr) ; pad.PaddingLeft=UDim.new(0,6)
    local function safeProp(name, getter, setter, toStr, fromStr)
        local ok, val = pcall(getter)
        if not ok then return end
        local con = Instance.new("Frame", panel)
        con.Size=UDim2.new(1,-6,0,48) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl = Instance.new("TextLabel",con)
        lbl.Size=UDim2.new(1,-10,0,18) ; lbl.Position=UDim2.fromOffset(6,4)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local inp = Instance.new("TextBox",con)
        inp.Size=UDim2.new(1,-12,0,20) ; inp.Position=UDim2.fromOffset(6,24)
        inp.BackgroundColor3=C.INPUT ; inp.BorderSizePixel=0
        inp.Font=Enum.Font.Code ; inp.Text=toStr(val)
        inp.TextColor3=C.LIVE ; inp.TextSize=11
        inp.ClearTextOnFocus=false
        corner(inp,4)
        inp.FocusLost:Connect(function()
            local nv = fromStr(inp.Text)
            if nv ~= nil then
                local oldOk, oldVal = pcall(getter)
                if not oldOk then oldVal = val end
                pcall(setter, nv)
                local newOk, newVal = pcall(getter)
                if newOk then val = newVal end
                inp.Text = toStr(val)
                self:PushUndo({
                    Do   = function() pcall(setter, nv) end,
                    Undo = function() pcall(setter, oldVal) end,
                })
            end
        end)
    end
    local function safeColorProp(name, getter, setter)
        local ok, color = pcall(getter)
        if not ok then return end
        local con = Instance.new("Frame",panel)
        con.Size=UDim2.new(1,-6,0,50) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl=Instance.new("TextLabel",con)
        lbl.Size=UDim2.new(1,-46,0,18) ; lbl.Position=UDim2.fromOffset(6,4)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local preview=Instance.new("Frame",con)
        preview.Size=UDim2.fromOffset(26,26) ; preview.Position=UDim2.new(1,-32,0,4)
        preview.BackgroundColor3=color ; preview.BorderSizePixel=0
        corner(preview,4) ; stroke(preview,Color3.fromRGB(80,80,100),1)
        local inp=Instance.new("TextBox",con)
        inp.Size=UDim2.new(1,-12,0,20) ; inp.Position=UDim2.fromOffset(6,26)
        inp.BackgroundColor3=C.INPUT ; inp.BorderSizePixel=0
        inp.Font=Enum.Font.Code ; inp.Text=colorToHex(color)
        inp.TextColor3=C.LIVE ; inp.TextSize=11
        inp.PlaceholderText="#RRGGBB" ; inp.ClearTextOnFocus=false
        corner(inp,4)
        inp.FocusLost:Connect(function()
            local nc=hexToColor(inp.Text)
            if nc then
                local old=color
                preview.BackgroundColor3=nc
                pcall(setter,nc)
                inp.Text=colorToHex(nc)
                self:PushUndo({
                    Do=function() pcall(setter,nc) end,
                    Undo=function() pcall(setter,old) end,
                })
            end
        end)
    end
    local function safeToggle(name, getter, setter)
        local ok, v = pcall(getter)
        if not ok then return end
        local con=Instance.new("Frame",panel)
        con.Size=UDim2.new(1,-6,0,34) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl=Instance.new("TextLabel",con)
        lbl.Size=UDim2.new(1,-54,1,0) ; lbl.Position=UDim2.fromOffset(6,0)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local tb=Instance.new("TextButton",con)
        tb.Size=UDim2.fromOffset(46,22) ; tb.Position=UDim2.new(1,-52,0.5,-11)
        tb.BorderSizePixel=0 ; tb.Font=Enum.Font.GothamBold
        tb.TextSize=10 ; tb.TextColor3=C.WHITE ; tb.AutoButtonColor=false
        corner(tb,4)
        local function ref() tb.Text=v and "ON" or "OFF" ; tb.BackgroundColor3=v and C.ACCENT2 or C.DANGER end
        ref()
        tb.MouseButton1Click:Connect(function()
            local old=v ; v=not v ; ref()
            local nv=v
            pcall(setter,nv)
            self:PushUndo({
                Do=function() pcall(setter,nv) end,
                Undo=function() pcall(setter,old) end,
            })
        end)
    end
    local function safeDrop(name, options, getter, setter)
        local ok, cur = pcall(getter)
        if not ok then return end
        local curStr = tostring(cur):gsub("Enum%.[^%.]+%.","")
        local ci=1
        for i,v in ipairs(options) do if v==curStr then ci=i break end end
        local con=Instance.new("Frame",panel)
        con.Size=UDim2.new(1,-6,0,48) ; con.BackgroundColor3=C.ROW ; con.BorderSizePixel=0
        corner(con,5)
        local lbl=Instance.new("TextLabel",con)
        lbl.Size=UDim2.new(1,-10,0,18) ; lbl.Position=UDim2.fromOffset(6,4)
        lbl.BackgroundTransparency=1 ; lbl.Font=Enum.Font.GothamBold
        lbl.Text=name ; lbl.TextColor3=C.MUTED ; lbl.TextSize=10
        lbl.TextXAlignment=Enum.TextXAlignment.Left
        local curLbl=Instance.new("TextButton",con)
        curLbl.Size=UDim2.new(1,-12,0,20) ; curLbl.Position=UDim2.fromOffset(6,24)
        curLbl.BackgroundColor3=C.INPUT ; curLbl.BorderSizePixel=0
        curLbl.Font=Enum.Font.Code ; curLbl.Text="◀  "..options[ci].."  ▶"
        curLbl.TextColor3=C.LIVE ; curLbl.TextSize=11 ; curLbl.AutoButtonColor=false
        corner(curLbl,4)
        curLbl.MouseButton1Click:Connect(function()
            ci=ci%#options+1
            curLbl.Text="◀  "..options[ci].."  ▶"
            pcall(setter, options[ci])
        end)
    end
    safeProp("Name",
        function() return inst.Name end,
        function(v) inst.Name=v ; self:RefreshLiveHierarchy() end,
        tostring, tostring)
    if inst:IsA("GuiObject") then
        safeProp("Size X", function() return inst.Size.X.Offset end,
            function(v) inst.Size=UDim2.fromOffset(tonumber(v) or inst.Size.X.Offset, inst.Size.Y.Offset) end,
            tostring, tonumber)
        safeProp("Size Y", function() return inst.Size.Y.Offset end,
            function(v) inst.Size=UDim2.fromOffset(inst.Size.X.Offset, tonumber(v) or inst.Size.Y.Offset) end,
            tostring, tonumber)
        safeProp("Pos X", function() return inst.Position.X.Offset end,
            function(v) inst.Position=UDim2.fromOffset(tonumber(v) or inst.Position.X.Offset, inst.Position.Y.Offset) end,
            tostring, tonumber)
        safeProp("Pos Y", function() return inst.Position.Y.Offset end,
            function(v) inst.Position=UDim2.fromOffset(inst.Position.X.Offset, tonumber(v) or inst.Position.Y.Offset) end,
            tostring, tonumber)
        safeProp("Size X Scale", function() return inst.Size.X.Scale end,
            function(v) inst.Size=UDim2.new(tonumber(v) or 0,inst.Size.X.Offset,inst.Size.Y.Scale,inst.Size.Y.Offset) end,
            tostring, tonumber)
        safeProp("Size Y Scale", function() return inst.Size.Y.Scale end,
            function(v) inst.Size=UDim2.new(inst.Size.X.Scale,inst.Size.X.Offset,tonumber(v) or 0,inst.Size.Y.Offset) end,
            tostring, tonumber)
        safeProp("Pos X Scale", function() return inst.Position.X.Scale end,
            function(v) inst.Position=UDim2.new(tonumber(v) or 0,inst.Position.X.Offset,inst.Position.Y.Scale,inst.Position.Y.Offset) end,
            tostring, tonumber)
        safeProp("Pos Y Scale", function() return inst.Position.Y.Scale end,
            function(v) inst.Position=UDim2.new(inst.Position.X.Scale,inst.Position.X.Offset,tonumber(v) or 0,inst.Position.Y.Offset) end,
            tostring, tonumber)
        safeProp("ZIndex", function() return inst.ZIndex end,
            function(v) inst.ZIndex=math.max(0,tonumber(v) or 1) end,
            tostring, tonumber)
        safeProp("Rotation", function() return inst.Rotation end,
            function(v) inst.Rotation=tonumber(v) or 0 end,
            tostring, tonumber)
        safeColorProp("BG Color",
            function() return inst.BackgroundColor3 end,
            function(v) inst.BackgroundColor3=v end)
        safeProp("BG Transparency", function() return inst.BackgroundTransparency end,
            function(v) inst.BackgroundTransparency=math.clamp(tonumber(v) or 0,0,1) end,
            tostring, tonumber)
        safeToggle("Visible",
            function() return inst.Visible end,
            function(v) inst.Visible=v end)
        safeToggle("Clips Descendants",
            function() return inst.ClipsDescendants end,
            function(v) inst.ClipsDescendants=v end)
    end
    if inst:IsA("TextLabel") or inst:IsA("TextButton") or inst:IsA("TextBox") then
        safeProp("Text", function() return inst.Text end,
            function(v) inst.Text=v end, tostring, tostring)
        safeProp("Text Size", function() return inst.TextSize end,
            function(v) inst.TextSize=tonumber(v) or 14 end, tostring, tonumber)
        safeColorProp("Text Color",
            function() return inst.TextColor3 end,
            function(v) inst.TextColor3=v end)
        safeProp("Text Transparency", function() return inst.TextTransparency end,
            function(v) inst.TextTransparency=math.clamp(tonumber(v) or 0,0,1) end,
            tostring, tonumber)
        safeToggle("Text Wrapped",
            function() return inst.TextWrapped end,
            function(v) inst.TextWrapped=v end)
        safeToggle("Text Scaled",
            function() return inst.TextScaled end,
            function(v) inst.TextScaled=v end)
        safeDrop("Font", FONTS,
            function() return tostring(inst.Font):gsub("Enum%.Font%.","") end,
            function(v) pcall(function() inst.Font=Enum.Font[v] end) end)
        safeDrop("H Align", HALIGN,
            function() return tostring(inst.TextXAlignment):gsub("Enum%.TextXAlignment%.","") end,
            function(v) pcall(function() inst.TextXAlignment=Enum.TextXAlignment[v] end) end)
        safeDrop("V Align", VALIGN,
            function() return tostring(inst.TextYAlignment):gsub("Enum%.TextYAlignment%.","") end,
            function(v) pcall(function() inst.TextYAlignment=Enum.TextYAlignment[v] end) end)
        if inst:IsA("TextBox") then
            safeProp("Placeholder",
                function() return inst.PlaceholderText end,
                function(v) inst.PlaceholderText=v end, tostring, tostring)
        end
    end
    if inst:IsA("ImageLabel") or inst:IsA("ImageButton") then
        safeProp("Image", function() return inst.Image end,
            function(v) inst.Image=v end, tostring, tostring)
        safeProp("Image Transparency", function() return inst.ImageTransparency end,
            function(v) inst.ImageTransparency=math.clamp(tonumber(v) or 0,0,1) end,
            tostring, tonumber)
        safeColorProp("Image Color",
            function() return inst.ImageColor3 end,
            function(v) inst.ImageColor3=v end)
        safeDrop("Scale Type", {"Fit","Crop","Stretch","Tile","Slice"},
            function() return tostring(inst.ScaleType):gsub("Enum%.ScaleType%.","") end,
            function(v) pcall(function() inst.ScaleType=Enum.ScaleType[v] end) end)
    end
    if inst:IsA("ScrollingFrame") then
        safeProp("Canvas W", function() return inst.CanvasSize.X.Offset end,
            function(v) inst.CanvasSize=UDim2.fromOffset(tonumber(v) or 0,inst.CanvasSize.Y.Offset) end,
            tostring, tonumber)
        safeProp("Canvas H", function() return inst.CanvasSize.Y.Offset end,
            function(v) inst.CanvasSize=UDim2.fromOffset(inst.CanvasSize.X.Offset,tonumber(v) or 0) end,
            tostring, tonumber)
        safeProp("Scrollbar Thickness", function() return inst.ScrollBarThickness end,
            function(v) inst.ScrollBarThickness=tonumber(v) or 6 end, tostring, tonumber)
        safeToggle("Scrolling Enabled",
            function() return inst.ScrollingEnabled end,
            function(v) inst.ScrollingEnabled=v end)
    end
    if inst:IsA("UIListLayout") then
        safeProp("Padding", function() return inst.Padding.Offset end,
            function(v) inst.Padding=UDim.new(0,tonumber(v) or 4) end, tostring, tonumber)
        safeDrop("Fill Direction", {"Vertical","Horizontal"},
            function() return tostring(inst.FillDirection):gsub("Enum%.FillDirection%.","") end,
            function(v) pcall(function() inst.FillDirection=Enum.FillDirection[v] end) end)
    end
    if inst:IsA("UIPadding") then
        safeProp("Pad Top",    function() return inst.PaddingTop.Offset end,    function(v) inst.PaddingTop=UDim.new(0,tonumber(v) or 0) end, tostring, tonumber)
        safeProp("Pad Bottom", function() return inst.PaddingBottom.Offset end, function(v) inst.PaddingBottom=UDim.new(0,tonumber(v) or 0) end, tostring, tonumber)
        safeProp("Pad Left",   function() return inst.PaddingLeft.Offset end,   function(v) inst.PaddingLeft=UDim.new(0,tonumber(v) or 0) end, tostring, tonumber)
        safeProp("Pad Right",  function() return inst.PaddingRight.Offset end,  function(v) inst.PaddingRight=UDim.new(0,tonumber(v) or 0) end, tostring, tonumber)
    end
    if inst:IsA("UICorner") then
        safeProp("Corner Radius", function() return inst.CornerRadius.Offset end,
            function(v) inst.CornerRadius=UDim.new(0,math.max(0,tonumber(v) or 0)) end,
            tostring, tonumber)
    end
    if inst:IsA("UIStroke") then
        safeProp("Thickness", function() return inst.Thickness end,
            function(v) inst.Thickness=math.max(0,tonumber(v) or 1) end, tostring, tonumber)
        safeColorProp("Stroke Color",
            function() return inst.Color end,
            function(v) inst.Color=v end)
    end
    if inst:IsA("ScreenGui") then
        safeToggle("Enabled",
            function() return inst.Enabled end,
            function(v) inst.Enabled=v end)
        safeToggle("Reset On Spawn",
            function() return inst.ResetOnSpawn end,
            function(v) inst.ResetOnSpawn=v end)
        safeProp("Display Order", function() return inst.DisplayOrder end,
            function(v) inst.DisplayOrder=tonumber(v) or 0 end, tostring, tonumber)
    end
    local highlightBtn = self:MakeBtn("👁  HIGHLIGHT IN GAME", C.LIVE, panel, 0, 30)
    highlightBtn.Size=UDim2.new(1,-6,0,30)
    highlightBtn.MouseButton1Click:Connect(function()
        if not inst:IsA("GuiObject") then return end
        local oldColor = inst.BackgroundColor3
        local oldTrans = inst.BackgroundTransparency
        local flash = 4
        local function doFlash(n)
            if n <= 0 then
                pcall(function() inst.BackgroundColor3=oldColor ; inst.BackgroundTransparency=oldTrans end)
                return
            end
            pcall(function() inst.BackgroundColor3=C.LIVE ; inst.BackgroundTransparency=0 end)
            task.delay(0.15, function()
                pcall(function() inst.BackgroundColor3=oldColor ; inst.BackgroundTransparency=oldTrans end)
                task.delay(0.15, function() doFlash(n-1) end)
            end)
        end
        doFlash(flash)
    end)
end
function GC:_createUI()
    local sg = Instance.new("ScreenGui")
    sg.Name           = "GUICreator_Zuka"
    sg.ResetOnSpawn   = false
    sg.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    sg.Parent         = CoreGui
    self.State.UI     = sg
    local mf = Instance.new("Frame", sg)
    mf.Name             = "MainFrame"
    mf.Size             = UDim2.fromOffset(1200, 700)
    mf.Position         = UDim2.fromScale(0.5, 0.5)
    mf.AnchorPoint      = Vector2.new(0.5, 0.5)
    mf.BackgroundColor3 = C.BG
    mf.BorderSizePixel  = 0
    corner(mf, 12)
    stroke(mf, C.ACCENT, 2)
    self.UI.MainFrame = mf
    local modeBar = Instance.new("Frame", mf)
    modeBar.Name             = "ModeBar"
    modeBar.Size             = UDim2.new(1,0,0,40)
    modeBar.BackgroundColor3 = C.PANEL
    modeBar.BorderSizePixel  = 0
    corner(modeBar, 12)
    self.UI.ModeBar = modeBar
    local modeLabel = Instance.new("TextLabel", modeBar)
    modeLabel.Size               = UDim2.new(0.55,0,1,0)
    modeLabel.Position           = UDim2.fromOffset(15,0)
    modeLabel.BackgroundTransparency = 1
    modeLabel.Font               = Enum.Font.Code
    modeLabel.Text               = "By Zuka"
    modeLabel.TextColor3         = C.ACCENT
    modeLabel.TextSize           = 13
    modeLabel.TextXAlignment     = Enum.TextXAlignment.Left
    self.UI.ModeLabel = modeLabel
    local projLbl = Instance.new("TextLabel", modeBar)
    projLbl.Size=UDim2.fromOffset(56,20) ; projLbl.Position=UDim2.new(0.57,0,0.5,-10)
    projLbl.BackgroundTransparency=1 ; projLbl.Font=Enum.Font.GothamBold
    projLbl.Text="Project:" ; projLbl.TextColor3=C.MUTED ; projLbl.TextSize=10
    projLbl.TextXAlignment=Enum.TextXAlignment.Right
    local projInput = Instance.new("TextBox", modeBar)
    projInput.Size=UDim2.fromOffset(120,22) ; projInput.Position=UDim2.new(0.57,60,0.5,-11)
    projInput.BackgroundColor3=C.INPUT ; projInput.BorderSizePixel=0
    projInput.Font=Enum.Font.Code ; projInput.Text=self.State.CurrentProject.Name
    projInput.TextColor3=C.TEXT ; projInput.TextSize=11
    projInput.ClearTextOnFocus=false
    corner(projInput,4)
    projInput.FocusLost:Connect(function()
        self.State.CurrentProject.Name = projInput.Text~="" and projInput.Text or "Untitled"
        projInput.Text = self.State.CurrentProject.Name
    end)
    local closeBtn = self:MakeBtn("×", C.DANGER, modeBar, 30, 30)
    closeBtn.TextSize=20 ; closeBtn.Position=UDim2.new(1,-35,0,5)
    closeBtn.MouseButton1Click:Connect(function() self:Disable() end)
    self:MakeDraggable(modeBar, mf)
    local topBar = Instance.new("Frame", mf)
    topBar.Size=UDim2.new(1,-20,0,36) ; topBar.Position=UDim2.fromOffset(10,44)
    topBar.BackgroundColor3=C.PANEL2 ; topBar.BorderSizePixel=0 ; topBar.ZIndex=10
    corner(topBar,6)
    local topLayout=Instance.new("UIListLayout",topBar)
    topLayout.FillDirection=Enum.FillDirection.Horizontal
    topLayout.Padding=UDim.new(0,5)
    topLayout.VerticalAlignment=Enum.VerticalAlignment.Center
    Instance.new("UIPadding",topBar).PaddingLeft=UDim.new(0,8)
    local exportBtn = self:MakeBtn("⬆ EXPORT CODE", C.ACCENT2, topBar)
    exportBtn.MouseButton1Click:Connect(function() self:ExportCode() end)
    local liveBtn = self:MakeBtn("LIVE EDIT", C.LIVE, topBar, 100)
    liveBtn.MouseButton1Click:Connect(function()
        if self.State.Mode=="live" then
            self:ExitLiveMode()
            liveBtn.Text="⚡ LIVE EDIT"
            liveBtn.BackgroundColor3=C.LIVE
        else
            self:OpenLivePicker()
        end
    end)
    self.UI.LiveBtn = liveBtn
    local undoBtn = self:MakeBtn("↩ UNDO", C.ACCENT, topBar, 80)
    undoBtn.MouseButton1Click:Connect(function() self:Undo() end)
    local redoBtn = self:MakeBtn("↪ REDO", C.ACCENT, topBar, 80)
    redoBtn.MouseButton1Click:Connect(function() self:Redo() end)
    local clearBtn = self:MakeBtn("CLEAR", C.DANGER, topBar, 80)
    clearBtn.MouseButton1Click:Connect(function() self:ClearCanvas() end)
    local gridBtn = self:MakeBtn("GRID: ON", Color3.fromRGB(80,80,180), topBar, 90)
    gridBtn.MouseButton1Click:Connect(function()
        self.Config.ShowGrid = not self.Config.ShowGrid
        gridBtn.Text = "GRID: "..(self.Config.ShowGrid and "ON" or "OFF")
        self:DrawGrid()
    end)
    local snapBtn = self:MakeBtn("SNAP: OFF", Color3.fromRGB(110,70,180), topBar, 90)
    snapBtn.MouseButton1Click:Connect(function()
        self.Config.SnapToGrid = not self.Config.SnapToGrid
        snapBtn.Text = "SNAP: "..(self.Config.SnapToGrid and "ON" or "OFF")
        snapBtn.BackgroundColor3 = self.Config.SnapToGrid
            and Color3.fromRGB(170,70,255) or Color3.fromRGB(110,70,180)
    end)
    local leftPanel = Instance.new("Frame", mf)
    leftPanel.Name             = "Toolbox"
    leftPanel.Size             = UDim2.new(0,165,1,-90)
    leftPanel.Position         = UDim2.fromOffset(10,86)
    leftPanel.BackgroundColor3 = C.PANEL2
    leftPanel.BorderSizePixel  = 0
    corner(leftPanel,8)
    self.UI.Toolbox = leftPanel
    local toolboxTitle = label(leftPanel, "ELEMENTS", 12, C.MUTED)
    toolboxTitle.Size=UDim2.new(1,0,0,28)
    local toolScroll = Instance.new("ScrollingFrame", leftPanel)
    toolScroll.Size=UDim2.new(1,-8,1,-34) ; toolScroll.Position=UDim2.fromOffset(4,30)
    toolScroll.BackgroundTransparency=1 ; toolScroll.BorderSizePixel=0
    toolScroll.ScrollBarThickness=3 ; toolScroll.ScrollBarImageColor3=C.ACCENT
    toolScroll.CanvasSize=UDim2.fromOffset(0,0) ; toolScroll.AutomaticCanvasSize=Enum.AutomaticSize.Y
    local tlayout=Instance.new("UIListLayout",toolScroll)
    tlayout.Padding=UDim.new(0,4) ; tlayout.SortOrder=Enum.SortOrder.LayoutOrder
    self:PopulateToolbox(toolScroll)
    local livePanel = Instance.new("Frame", mf)
    livePanel.Name             = "LivePanel"
    livePanel.Size             = UDim2.new(0,165,1,-90)
    livePanel.Position         = UDim2.fromOffset(10,86)
    livePanel.BackgroundColor3 = Color3.fromRGB(28,18,8)
    livePanel.BorderSizePixel  = 0
    livePanel.Visible          = false
    corner(livePanel,8)
    stroke(livePanel, C.LIVE, 1.5)
    self.UI.LivePanel = livePanel
    local liveTitle = label(livePanel, "⚡ LIVE MODE", 12, C.LIVE)
    liveTitle.Size=UDim2.new(1,0,0,28) ; liveTitle.TextXAlignment=Enum.TextXAlignment.Center
    local liveTip = label(livePanel, "  Click any node in the\n  hierarchy to inspect\n  and edit it live.", 11, C.MUTED, "Gotham")
    liveTip.Size=UDim2.new(1,0,0,60) ; liveTip.Position=UDim2.fromOffset(0,34)
    liveTip.TextWrapped=true ; liveTip.TextYAlignment=Enum.TextYAlignment.Top
    local exitLiveBtn = self:MakeBtn("← EXIT LIVE MODE", C.DANGER, livePanel, 145, 30)
    exitLiveBtn.Position=UDim2.new(0.5,-72,1,-40)
    exitLiveBtn.MouseButton1Click:Connect(function()
        self:ExitLiveMode()
        self.UI.LiveBtn.Text="LIVE EDIT"
    end)
    local canvas = Instance.new("Frame", mf)
    canvas.Name             = "Canvas"
    canvas.Size             = UDim2.new(1,-560,1,-90)
    canvas.Position         = UDim2.fromOffset(183,86)
    canvas.BackgroundColor3 = C.CANVAS_BG
    canvas.BorderSizePixel  = 0
    canvas.ClipsDescendants = false
    corner(canvas,8)
    self.UI.Canvas = canvas
    local canvasLbl = label(canvas, "CANVAS  (480 × 360)", 11, C.MUTED)
    canvasLbl.Size=UDim2.new(1,0,0,24)
    canvasLbl.TextXAlignment=Enum.TextXAlignment.Center
    local ws = Instance.new("Frame", canvas)
    ws.Name             = "Workspace"
    ws.Size             = UDim2.fromOffset(480,360)
    ws.Position         = UDim2.new(0.5,0,0.5,0)
    ws.AnchorPoint      = Vector2.new(0.5,0.5)
    ws.BackgroundColor3 = C.WS_BG
    ws.BorderSizePixel  = 0
    ws.ClipsDescendants = true
    stroke(ws, Color3.fromRGB(70,70,100), 2)
    self.UI.Workspace = ws
    local gridFrame = Instance.new("Frame", ws)
    gridFrame.Name               = "GridOverlay"
    gridFrame.Size               = UDim2.new(1,0,1,0)
    gridFrame.BackgroundTransparency = 1
    gridFrame.BorderSizePixel    = 0
    gridFrame.ZIndex             = 1
    self.State.GridFrame = gridFrame
    self:DrawGrid()
    local rightCol = Instance.new("Frame", mf)
    rightCol.Name             = "RightCol"
    rightCol.Size             = UDim2.new(0,240,1,-90)
    rightCol.Position         = UDim2.new(1,-250,0,86)
    rightCol.BackgroundTransparency = 1
    rightCol.BorderSizePixel  = 0
    self.UI.RightCol = rightCol
    local propPanel = Instance.new("Frame", rightCol)
    propPanel.Name             = "Properties"
    propPanel.Size             = UDim2.new(1,0,0.52,-4)
    propPanel.BackgroundColor3 = C.PANEL2
    propPanel.BorderSizePixel  = 0
    corner(propPanel,8)
    local propTitle = label(propPanel, "PROPERTIES", 12, C.MUTED)
    propTitle.Size=UDim2.new(1,0,0,28)
    propTitle.TextXAlignment=Enum.TextXAlignment.Center
    local propScroll = Instance.new("ScrollingFrame", propPanel)
    propScroll.Size=UDim2.new(1,-8,1,-32) ; propScroll.Position=UDim2.fromOffset(4,30)
    propScroll.BackgroundTransparency=1 ; propScroll.BorderSizePixel=0
    propScroll.ScrollBarThickness=3 ; propScroll.ScrollBarImageColor3=C.ACCENT
    propScroll.CanvasSize=UDim2.fromOffset(0,0) ; propScroll.AutomaticCanvasSize=Enum.AutomaticSize.Y
    local pl=Instance.new("UIListLayout",propScroll)
    pl.Padding=UDim.new(0,5) ; pl.SortOrder=Enum.SortOrder.LayoutOrder
    self.State.PropertyPanel = propScroll
    local hierPanel = Instance.new("Frame", rightCol)
    hierPanel.Name             = "Hierarchy"
    hierPanel.Size             = UDim2.new(1,0,0.48,-4)
    hierPanel.Position         = UDim2.new(0,0,0.52,4)
    hierPanel.BackgroundColor3 = C.PANEL2
    hierPanel.BorderSizePixel  = 0
    corner(hierPanel,8)
    self.UI.HierPanel = hierPanel
    local hierTitle = label(hierPanel, "HIERARCHY", 12, C.MUTED)
    hierTitle.Size=UDim2.new(1,0,0,28)
    hierTitle.TextXAlignment=Enum.TextXAlignment.Center
    local hierRefreshBtn = self:MakeBtn("⟳", C.LIVE, hierPanel, 22, 20)
    hierRefreshBtn.Position=UDim2.new(1,-26,0,4)
    hierRefreshBtn.TextSize=14
    hierRefreshBtn.MouseButton1Click:Connect(function()
        if self.State.Mode=="live" then self:RefreshLiveHierarchy() end
    end)
    local hierScroll = Instance.new("ScrollingFrame", hierPanel)
    hierScroll.Size=UDim2.new(1,-8,1,-32) ; hierScroll.Position=UDim2.fromOffset(4,30)
    hierScroll.BackgroundTransparency=1 ; hierScroll.BorderSizePixel=0
    hierScroll.ScrollBarThickness=3 ; hierScroll.ScrollBarImageColor3=C.ACCENT
    hierScroll.CanvasSize=UDim2.fromOffset(0,0) ; hierScroll.AutomaticCanvasSize=Enum.AutomaticSize.Y
    local hl=Instance.new("UIListLayout",hierScroll)
    hl.Padding=UDim.new(0,3) ; hl.SortOrder=Enum.SortOrder.LayoutOrder
    self.State.HierarchyPanel = hierScroll
    self:_bindKeyboard()
end
function GC:Enable()
    if self.State.IsEnabled then return end
    self.State.IsEnabled = true
    self:_createUI()
    print("[GUICreator v2] ✓ Enabled")
    print("  Maker mode: drag, resize, Ctrl+Z/Y/D, Del")
end
function GC:Disable()
    if not self.State.IsEnabled then return end
    self.State.IsEnabled = false
    for _, c in pairs(self.State.Connections) do if c then c:Disconnect() end end
    table.clear(self.State.Connections)
    for _, d in ipairs(self.State.CreatedGUIs) do
        if d.Connections then for _,c in ipairs(d.Connections) do if c then c:Disconnect() end end end
    end
    if self.State.UI then self.State.UI:Destroy() ; self.State.UI=nil end
    self.State.CreatedGUIs={} ; self.State.UndoStack={} ; self.State.RedoStack={}
    self.State.SelectedElement=nil ; self.State.GridFrame=nil
    self.State.Mode="maker" ; self.State.LiveTarget=nil
    self.UI = {}
    print("[GUICreator v2]  Disabled")
end
function GC:Toggle()
    if self.State.IsEnabled then self:Disable() else self:Enable() end
end
GC:Enable()
