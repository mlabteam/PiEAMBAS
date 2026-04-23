local dt = 0.01 -- период дескритизации [cекунды]
local distance_change = 0 -- изменение расстояние до дома за один цикл [метры]
local delta_yaw_degree = 0 -- изменение угла по яву за один цикл, зависит от рейта и периода дискретизации [градусы]

local time_constant = 0.3
local apperiodic_output = 0

local big_circle = 0
local small_circle = 0

local RC1 = rc:get_channel(1)   
local RC2 = rc:get_channel(2)   
local RC3 = rc:get_channel(3)   
local RC4 = rc:get_channel(4)   

local time_now = 0
local time_prev = 0
local delta_t = 0
local i = 0

local home_position = ahrs:get_home() -- координаты точки дома, которые задаются при взлете, в дальнейшем не изменяются
local drone_position = ahrs:get_home() -- координаты дрона, которые изменяются в процессе полета, в начале полета совпадают с координатами дома

function update()

    if not ahrs:initialised() then
        return update, 10000
    end
    
    if i == 0 and ahrs:initialised() then
        home_position = ahrs:get_home()
        i = 1
    end
    

    local pwm_enable_autocontrol_mode = rc:get_pwm(7) -- канал для включения режима

    local pwm_big_circle_pitch = 1450
    local pwm_big_circle_roll= 1550
    local pwm_big_circle_yaw = 1550
    local pwm_small_circle_pitch = 1350
    local pwm_small_circle_roll = 1650
    local pwm_small_circle_yaw = 1650


    -- if time_now/1000 >= 40 then
    --     home_position:offset(delta_t/1000*12*math.sin(0.7), delta_t/1000*12*math.cos(0.7))
    -- end
    
    local drone_position = ahrs:get_position() -- координаты дрона, которые изменяются в процессе полета
    local home_position = ahrs:get_home() -- координаты точки дома, которые задаются при взлете, в дальнейшем не изменяются
   
    if not drone_position or not home_position then
        gcs:send_text(6, "Position or home not available")
        return update, 10000
    end
   
    local horizontal_distance_home = drone_position:get_distance(home_position) 
    local vertical_distance_home = (drone_position:alt() - home_position:alt()) / 100
    local distance_to_home = math.sqrt(horizontal_distance_home^2 + vertical_distance_home^2) -- дистанция между точной дома и дроном [метры]
    
    -- local distance_to_home = drone_position:get_distance_3d(home_position)

    -- если включаем режим 
    if pwm_enable_autocontrol_mode >= 1500 then

        apperiodic_output = distance_change * dt / time_constant + apperiodic_output
        distance_change = distance_to_home - apperiodic_output -- изменение дистанции [метры]

        if distance_change <= 0 then -- если приближаемся
            
            RC1:set_override(pwm_big_circle_roll)
            RC2:set_override(pwm_big_circle_pitch)
            RC4:set_override(pwm_big_circle_yaw)
            -- RC3:set_override(1950)
            gcs:send_text(6, string.format("Distance:%.2f distance_change:%f PWM_ROLL:%f", distance_to_home, distance_change, rc:get_pwm(1)))
        else
            
            RC1:set_override(pwm_small_circle_roll)
            RC2:set_override(pwm_small_circle_pitch)
            RC4:set_override(pwm_small_circle_yaw)
            -- RC3:set_override(1550)
            gcs:send_text(6, string.format("Distance:%.2f distance_change:%f PWM_ROLL:%f", distance_to_home, distance_change, rc:get_pwm(1)))
        end
    else    
        gcs:send_text(6, string.format("Distance:%.2f time_now:%.2f", distance_to_home, time_now))
        gcs:send_text(6, string.format("big_circle:%.2f small_circle:%.2f", pwm_big_circle_pitch, pwm_small_circle_pitch))
        return update, 1000
    end

    time_now = vehicle:get_time_flying_ms():toint()
    delta_t = time_now - time_prev
    time_prev = time_now
    
    return update, dt*1000
end

return update()