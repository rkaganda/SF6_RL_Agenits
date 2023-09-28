local gameStateBufferPath = "env/game_env_buffer.buf"
local gameStateBufferFile = io.open(gameStateBufferPath, "r+")

local actionsBufferPath = "env/actions_buffer.buf"
local actionsBufferPathFile = io.open(actionsBufferPath, "r")

local gameStateFormatPath = "env/game_env.format"
local gameStateFormatFile = io.open(gameStateFormatPath, "r")
local gameStateFormatString = gameStateFormatFile:read("*l")
local gameStateFormat = {}

local actionKeyMappingPath = "env/action_key_mapping.json"
local action_key_mapping = json.load_file(actionKeyMappingPath)
local action_key_status = {}
local last_action_key_status = {}
local flagTriggerValue = 11
local updateFrameCount 


local function generate_enum(typename)
    local t = sdk.find_type_definition(typename)
    if not t then return {} end

    local fields = t:get_fields()
    local enum = {}

    for i, field in ipairs(fields) do
        if field:is_static() then
            local name = field:get_name()
            local raw_value = field:get_data(nil)

            --log.debug(name .. " = " .. tostring(raw_value))

            enum[raw_value] = name
        end
    end

    return enum
end

local keyboardKeys = generate_enum("via.hid.KeyboardKey")
local inputDigitalFlags = generate_enum("app.InputDigitalFlag")

local gBattle
local p1 = {}
local p2 = {}

local last_invalid_frame = 0
local game_state_frame = 0
local recent_digital = 0

p1.absolute_range = 0
p1.relative_range = 0
p2.absolute_range = 0
p2.relative_range = 0


for value in string.gmatch(gameStateFormatString, "[^,]+") do
    table.insert(gameStateFormat, value)
end
gameStateFormatFile:close()


function bitand(a, b)
    local result = 0
    local bitval = 1
    while a > 0 and b > 0 do
      if a % 2 == 1 and b % 2 == 1 then -- test the rightmost bits
          result = result + bitval      -- set the current bit
      end
      bitval = bitval * 2 -- shift left
      a = math.floor(a/2) -- shift right
      b = math.floor(b/2)
    end
    return result
end

local abs = function(num)
	if num < 0 then
		return num * -1
	else
		return num
	end
end

local function read_sfix(sfix_obj)
    if sfix_obj.w then
        return Vector4f.new(tonumber(sfix_obj.x:call("ToString()")), tonumber(sfix_obj.y:call("ToString()")), tonumber(sfix_obj.z:call("ToString()")), tonumber(sfix_obj.w:call("ToString()")))
    elseif sfix_obj.z then
        return Vector3f.new(tonumber(sfix_obj.x:call("ToString()")), tonumber(sfix_obj.y:call("ToString()")), tonumber(sfix_obj.z:call("ToString()")))
    elseif sfix_obj.y then
        return Vector2f.new(tonumber(sfix_obj.x:call("ToString()")), tonumber(sfix_obj.y:call("ToString()")))
    end
    return tonumber(sfix_obj:call("ToString()"))
end


local function waitForActionsBuffer()
    frameNumber = tostring(game_state_frame)

    if not actionsBufferPathFile then
        log.debug("Failed to open actionsBufferPathFile")
        return
    end

    local buffer_content
    local actions_table = {}

    while true do
        actionsBufferPathFile:seek("set")
        buffer_content = actionsBufferPathFile:read("*l")
        actions_table = {}
        for s in string.gmatch(buffer_content, "[^,]+") do
            table.insert(actions_table, s)
        end
        if actions_table[1] == frameNumber then
            for action_mapping, action_key in pairs(action_key_mapping) do -- for each action key mapping
                -- log.debug("action_mapping="..action_mapping.." action_key="..action_key)
                action_table_key = tonumber(action_mapping)+1  
                if actions_table[action_table_key] then -- if there is a table for that key
                    -- log.debug("action_table_key="..action_table_key.." value="..actions_table[action_table_key])
                    last_action_key_status[action_key] = action_key_status[action_key]
                    action_key_status[action_key] = tonumber(actions_table[action_table_key]) -- first action_table element is frame_number
                    -- log.debug("action_key_status action_key="..action_key..","..action_key_status[action_key])
                else
                    --log.debug("no mapping for "..action_key)
                end
            end
            -- log.debug("last_action_key_status ="..json.dump_string(last_action_key_status))
            -- log.debug("action_key_status ="..json.dump_string(action_key_status))
            return -- leave while true
        else
            actions_table = {}
        end
    end
end


local function writeGameEnvToBuffer()
    if not gameStateBufferFile then
        log.debug("Failed to open game buffer.")
        return
    end
    gameStateBufferFile:seek("set")

    --log.debug("game_state_frame="..game_state_frame)
    local frameRow = game_state_frame
    for p_num=1, 2 do
        for i, gameEnvValue in ipairs(gameStateFormat) do
            if p_num == 1 then
                frameRow = frameRow .. "," .. p1[gameEnvValue]
            else
                frameRow = frameRow .. "," .. p2[gameEnvValue]
            end
        end
    end
    --log.debug("\n"..frameRow.."\n")
    gameStateBufferFile:write(frameRow .. "\n")
    gameStateBufferFile:flush()
    waitForActionsBuffer()
end

re.on_script_reset(function()
    actionsBufferPathFile:close()
    gameStateBufferFile:close()
end)

local function updateActionKeys()
    --print("-----")
    inputManager = sdk.get_managed_singleton("app.InputManager")

    inputManagerState = inputManager._State

    if inputManagerState then
        inputDeviceStateKeyboard = inputManagerState._Keyboard
        if inputDeviceStateKeyboard then
            inputDeviceStateKeyboardKeys = inputDeviceStateKeyboard._Keys
            if inputDeviceStateKeyboardKeys then
                for i, key in pairs(inputDeviceStateKeyboardKeys) do
                    if key then
                        local action_key = action_key_status[keyboardKeys[key.Value]]
                        if action_key then -- if there is action mapping for this key
                            if action_key == 1 then
                                --log.debug("keyboardKeys[key.Value]="..keyboardKeys[key.Value])
                                key.Flags = flagTriggerValue -- set the flag to the action status
                                key.TriggerFrame = updateFrameCount
                            end
                        end
                    end
                end
            end
        end
    end
end



re.on_frame(function()
    gBattle = sdk.find_type_definition("gBattle")
    if gBattle then
        updateActionKeys()

        local sPlayer = gBattle:get_field("Player"):get_data(nil)
        local cPlayer = sPlayer.mcPlayer
        local BattleTeam = gBattle:get_field("Team"):get_data(nil)
        local cTeam = BattleTeam.mcTeam
		-- Charge Info
		local storageData = gBattle:get_field("Command"):get_data(nil).StorageData
		local p1ChargeInfo = storageData.UserEngines[0].m_charge_infos
		local p2ChargeInfo = storageData.UserEngines[1].m_charge_infos
		-- Fireball
		local sWork = gBattle:get_field("Work"):get_data(nil)
		local cWork = sWork.Global_work
		-- Action States
		local p1Engine = gBattle:get_field("Rollback"):get_data():GetLatestEngine().ActEngines[0]._Parent._Engine
		local p2Engine = gBattle:get_field("Rollback"):get_data():GetLatestEngine().ActEngines[1]._Parent._Engine
		
		-- p1.mActionId = cPlayer[0].mActionId
		p1.mActionId = p1Engine:get_ActionID()
		p1.mActionFrame = math.floor(read_sfix(p1Engine:get_ActionFrame()))
		p1.mEndFrame = math.floor(read_sfix(p1Engine:get_ActionFrameNum()))
		p1.mMarginFrame = math.floor(read_sfix(p1Engine:get_MarginFrame()))
		p1.HP_cap = cPlayer[0].vital_old
		p1.current_HP = cPlayer[0].vital_new
		p1.HP_cooldown = cPlayer[0].healing_wait
        p1.dir = cPlayer[0].BitValue
        -- p1.dir = bitand(cPlayer[0].BitValue, 128) == 128
        -- p1.dir = p1.dir and 1 or 0 -- bool to int conversion
        p1.hitstop = cPlayer[0].hit_stop
		p1.hitstun = cPlayer[0].damage_time
		p1.blockstun = cPlayer[0].guard_time
        p1.stance = cPlayer[0].pose_st
		p1.throw_invuln = cPlayer[0].catch_muteki
		p1.full_invuln = cPlayer[0].muteki_time
        p1.juggle = cPlayer[0].combo_dm_air
        p1.drive = cPlayer[0].focus_new
        p1.drive_cooldown = cPlayer[0].focus_wait
        p1.super = cTeam[0].mSuperGauge
		p1.buff = cPlayer[0].style_timer
		p1.posX = cPlayer[0].pos.x.v / 6553600.0
        p1.posY = cPlayer[0].pos.y.v / 6553600.0
        p1.spdX = cPlayer[0].speed.x.v / 6553600.0
        p1.spdY = cPlayer[0].speed.y.v / 6553600.0
        p1.aclX = cPlayer[0].alpha.x.v / 6553600.0
        p1.aclY = cPlayer[0].alpha.y.v / 6553600.0
		p1.pushback = cPlayer[0].vector_zuri.speed.v / 6553600.0
        p1.act_st = cPlayer[0].act_st
   
		
		p2.mActionId = cPlayer[1].mActionId
		p2.mActionId = p2Engine:get_ActionID()
		p2.mActionFrame = math.floor(read_sfix(p2Engine:get_ActionFrame()))
		p2.mEndFrame = math.floor(read_sfix(p2Engine:get_ActionFrameNum()))
		p2.mMarginFrame = math.floor(read_sfix(p2Engine:get_MarginFrame()))
		p2.HP_cap = cPlayer[1].vital_old
		p2.current_HP = cPlayer[1].vital_new
		p2.HP_cooldown = cPlayer[1].healing_wait
        p2.dir = bitand(cPlayer[1].BitValue, 128) == 128
        p2.dir = p2.dir and 1 or 0 -- bool to int conversion
        p2.hitstop = cPlayer[1].hit_stop
		p2.hitstun = cPlayer[1].damage_time
		p2.blockstun = cPlayer[1].guard_time
        p2.stance = cPlayer[1].pose_st
		p2.throw_invuln = cPlayer[1].catch_muteki
		p2.full_invuln = cPlayer[1].muteki_time
        p2.juggle = cPlayer[1].combo_dm_air
        p2.drive = cPlayer[1].focus_new
        p2.drive_cooldown = cPlayer[1].focus_wait
        p2.super = cTeam[1].mSuperGauge
		p2.buff = cPlayer[1].style_timer
		
		p2.posX = cPlayer[1].pos.x.v / 6553600.0
        p2.posY = cPlayer[1].pos.y.v / 6553600.0
        p2.spdX = cPlayer[1].speed.x.v / 6553600.0
        p2.spdY = cPlayer[1].speed.y.v / 6553600.0
        p2.aclX = cPlayer[1].alpha.x.v / 6553600.0
        p2.aclY = cPlayer[1].alpha.y.v / 6553600.0
		p2.pushback = cPlayer[1].vector_zuri.speed.v / 6553600.0
        p2.act_st = cPlayer[1].act_st


        p1.chargeInfo = 0
        -- p1.chargeInfo = p1ChargeInfo -- TODO
        -- TODO
        -- if p1.chargeInfo:get_Count() > 0 then
        --     for i=0,p1.chargeInfo:get_Count() - 1 do
        --         local value = p1.chargeInfo:get_Values()._dictionary._entries[i].value
        --         if value ~= nil then
        --             imgui.text("Move " .. i + 1 .. " Charge Time: " .. value.charge_frame)
        --             imgui.text("Move " .. i + 1 .. " Charge Keep Time: " .. value.keep_frame)
        --         end
        --     end
        -- end
        p2.chargeInfo = 0
        -- p2.chargeInfo = p2ChargeInfo -- TODO
        -- TODO
        -- if p2.chargeInfo:get_Count() > 0 then
        --     for i=0,p2.chargeInfo:get_Count() - 1 do
        --         local value = p2.chargeInfo:get_Values()._dictionary._entries[i].value
        --         if value ~= nil then
        --             imgui.text("Move " .. i + 1 .. " Charge Time: " .. value.charge_frame)
        --             imgui.text("Move " .. i + 1 .. " Charge Keep Time: " .. value.keep_frame)
        --         end
        --     end
        -- end

        
		
		-- P1 Fireball
        for i, obj in pairs(cWork) do
            if obj.owner_add ~= nil and obj.pl_no == 0 then
                -- if imgui.tree_node("Projectile " .. i) then
                --     imgui.text("Action ID: " .. obj.mActionId)
                --     imgui.text("Position X: " .. obj.pos.x.v / 6553600.0)
                --     imgui.text("Position Y: " .. obj.pos.y.v / 6553600.0)
                --     imgui.text("Speed X: " .. obj.speed.x.v / 6553600.0)
                --     imgui.tree_pop()
                -- end
            end
        end
					
        -- P2 Fireball
        for i, obj in pairs(cWork) do
            if obj.owner_add ~= nil and obj.pl_no == 1 then
                -- if imgui.tree_node("Projectile " .. i) then
                --     imgui.text("Action ID: " .. obj.mActionId)
                --     imgui.text("Position X: " .. obj.pos.x.v / 6553600.0)
                --     imgui.text("Position Y: " .. obj.pos.y.v / 6553600.0)
                --     imgui.text("Speed X: " .. obj.speed.x.v / 6553600.0)
                --     imgui.tree_pop()
                -- end
            end
        end
        writeGameEnvToBuffer()
    end
    game_state_frame = game_state_frame + 1  
end)


local function on_pre_get_digital(args)
    local last_invalid_frame = sdk.to_int64(args[4])
    last_digital_key = keyboardKeys[sdk.to_int64(args[3])]
end
local function on_post_get_digital(retval)
    if retval then
        local retval_address = sdk.to_int64(retval)
        if retval_address ~= 0 then
            --log.debug("************")
            -- log.debug("retval="..sdk.to_managed_object(retval):get_type_definition():get_full_name())
            local key = sdk.to_managed_object(retval)
            -- log.debug(keyboardKeys[key.Value])
            local action_key = last_action_key_status[keyboardKeys[key.Value]]
            if action_key then -- if there is action mapping for this key
                if action_key == 1 then
                    key.Flags = flagTriggerValue -- set the flag to the action status
                    --key.TriggerFrame = key.MinTriggerFrame + 1
                    -- log.debug("Value="..keyboardKeys[key.Value])
                    -- log.debug("flag="..key.Flags)
                    -- log.debug("TriggerFrame="..key.TriggerFrame)
                end
            end
            --log.debug("************")
            return sdk.to_ptr(key)
        end
    end
    return retval
end
sdk.hook(sdk.find_type_definition("app.InputDeviceStateKeyboard"):get_method("GetDigital"), on_pre_get_digital, on_post_get_digital)


local function on_pre_update(args)
    -- log.debug("update caller="..sdk.to_managed_object(args[2]):get_type_definition():get_full_name())
    -- log.debug("frame Count="..sdk.to_int64(args[4]))
    updateFrameCount = sdk.to_int64(args[4])
end
local function on_post_update(retval)
    
end
sdk.hook(sdk.find_type_definition("app.InputState"):get_method("Update"), on_pre_update, on_post_update)