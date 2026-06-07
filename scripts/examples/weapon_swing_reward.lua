-- Drops a lucky block when a player swings the laser sword.
Events.WeaponSwing(function(event)
    if event.weapon ~= ItemType.LASER_SWORD then
        return
    end

    local entity = event.player:getEntity()
    if not entity then
        return
    end

    ItemService.dropItem(ItemType.COSMIC_LUCKY_BLOCK, entity:getPosition())
end)
