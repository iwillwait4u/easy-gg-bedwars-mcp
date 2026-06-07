-- Gives every player 1 emerald every 30 seconds.
-- Uses only cached docs APIs: PlayerService.getPlayers(), InventoryService.giveItem(), ItemType.EMERALD, task.wait(), ipairs().

while task.wait(30) do
    for i, player in ipairs(PlayerService.getPlayers()) do
        InventoryService.giveItem(player, ItemType.EMERALD, 1, true)
    end
end

