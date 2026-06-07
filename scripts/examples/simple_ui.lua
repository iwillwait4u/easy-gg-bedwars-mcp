-- Creates a simple global progress bar that resets every 30 seconds.

local rewardBar = UIService.createProgressBar(30)
rewardBar:setText("Next reward")
rewardBar:set(0)

while task.wait(1) do
    rewardBar:add(1)
    if rewardBar:get() >= 30 then
        rewardBar:set(0)
    end
end

