-- Adds custom shop items when the match starts.
Events.MatchStart(function(event)
    ShopService.addItem(ItemType.SOLAR_PANEL, 1, ItemType.DIAMOND, 3)
    ShopService.addItem(ItemType.TENNIS_RACKET, 1, ItemType.IRON, 15)
end)
