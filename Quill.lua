local Configuration = {
    Method = "Quill",
    UseReplaceMethod = true,
    ReplaceDelay = 1
}
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local CapitaliseI = true
local ReplaceDictionary = {
    ["i"] = "I",
    ["im"] = "I am",
    ["ive"] = "I've",
    ["dont"] = "don't",
    ["doesnt"] = "doesn't",
    ["cant"] = "can't",
    ["youre"] = "you're",
    ["ur"] = "your",
    ["u"] = "you",
    ["its"] = "it's",
    ["oh"] = "oh,",
    ["thnks"] = "thanks",
    ["thx"] = "thanks",
    ["git"] = "get",
    ["gud"] = "good",
    ["gramer"] = "grammar",
    ["grammer"] = "grammar",
    ["anymor"] = "anymore",
}
local QuestionPrompts = {
    "mean",
    "ask",
    "you",
    "care",
    "script",
    "is",
    "what",
    "how"
}
local Punctuation = {
    "!",
    ".",
    "?"
}
local function ReplaceWords(Output)
    for i, Word in ipairs(Output) do
        Word = Word:lower()
        local Replace = ReplaceDictionary[Word]
        if (Replace) then
            Output[i] = Replace
        end
    end
    return Output
end
local function Capitalise(Output)
    local FirstLetter = Output[1]:sub(1, 1)
    Output[1] = FirstLetter:upper() .. Output[1]:sub(2)
    if (CapitaliseI) then
        for i, Word in ipairs(Output) do
            if (Word == "i") then
                Output[i] = "I"
            end
        end
    end
    return Output
end
local function Punctuate(Output)
    local LastWordI = #Output
    local LastWord = Output[LastWordI]
    local LastLetterI = #LastWord
    local LastLetter = LastWord:sub(LastLetterI, LastLetterI)
    if not (table.find(Punctuation, LastLetter)) then
        local Punctation = table.find(QuestionPrompts, Output[1]:lower()) and "?" or "."
        Output[LastWordI] = LastWord .. Punctation
    end
    return Output
end
local function ImproveScript(Input)
    if (Input:match("^%s*$")) then
        return Input
    end
    local Output = Input:split(" ")
    Output = ReplaceWords(Output)
    Output = Capitalise(Output)
    Output = Punctuate(Output)
    return table.concat(Output, " ")
end
local function GetQuillBotCookie()
    local Response = syn.request({
        Url = "https://rest.quillbot.com/api/tracking",
        Method = "POST"
    })
    local Cookie = Response.Headers["set-cookie"]
    syn.request({
        Url = "https://rest.quillbot.com/api/auth/spam-check",
        Method = "GET",
        Headers = {
            Cookie = Cookie
        }
    })
    return Cookie:sub(1, Cookie:find(";"))
end
local function ImproveQuillBot(Input)
    local UrlFormat = "https://rest.quillbot.com/api/paraphraser/single-paraphrase/2?text=%s&strength=2&autoflip=false&wikify=false&fthresh=-1&inputLang=en&quoteIndex=-1"
    local Response = syn.request({
        Url = UrlFormat:format(HttpService:UrlEncode(Input)),
        Method = "GET",
        Headers = {
            Cookie = GetQuillBotCookie()
        }
    })
    if (not Response.Success) then
        return Input
    end
    local Body = HttpService:JSONDecode(Response.Body)
    local Improved = Body.data[1].paras_3
    local ImprovedInput = Improved[1].alt
    return ImprovedInput
end
local function Improve(Input)
    local ImproveFunction = Configuration.Method == "Quill" and ImproveQuillBot or ImproveScript
    return ImproveFunction(Input)
end
local function ReplaceHook(Old, ReplaceI, ...)
    local args = {...}
    args[ReplaceI] = Improve(args[ReplaceI])
    return Old(unpack(args))
end
local function InitialiseReplace(ChatScript)
    local ChatMain = require(ChatScript:WaitForChild("ChatMain"))
    local ChatBar = debug.getupvalue(ChatMain.FocusChatBar, 1)
    local TextBox = ChatBar:GetTextBox()
    local LastChangedText = tick()
    local PreviousText = ""
    TextBox:GetPropertyChangedSignal("Text"):Connect(function()
        LastChangedText = tick()
    end)
    local Checker = coroutine.create(function()
        while (Configuration.UseReplaceMethod) do wait()
            if (not (tick() - LastChangedText >= Configuration.ReplaceDelay)) or (TextBox.Text == PreviousText) then
                continue
            end
            local ImprovedText = Improve(TextBox.Text)
            TextBox.Text = ImprovedText
            PreviousText = ImprovedText
        end
    end)
    coroutine.resume(Checker)
    return Checker
end
local function InitialiseHook()
    for _, v in ipairs(getgc(true)) do
        if (typeof(v) == "table" and rawget(v, "SendMessage") and rawget(v, "RegisterSayMessageFunction")) then
            local SendMessage = rawget(v, "SendMessage")
            rawset(v, "SendMessage", function(...)
                return ReplaceHook(SendMessage, 2, ...)
            end)
        end
    end
end
if (Configuration.UseReplaceMethod) then
    InitialiseReplace(Players.LocalPlayer.PlayerScripts.ChatScript)
else
    InitialiseHook()
end
