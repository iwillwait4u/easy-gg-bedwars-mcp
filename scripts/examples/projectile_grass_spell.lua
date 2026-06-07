-- Turns dirt into grass when Whim's nature spell projectile hits it.
Events.ProjectileHit(function(event)
    if event.projectileType ~= "mage_spell_nature" then
        return
    end

    local block = BlockService.getBlockAt(event.position)
    if not block or block.blockType ~= ItemType.DIRT then
        return
    end

    BlockService.placeBlock(ItemType.GRASS, event.position)
    ModelService.createModel(ModelType.DAISY, block.position + Vector3.new(0, 2.5, 0))
end)
