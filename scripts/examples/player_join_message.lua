-- Sends a chat message when a player joins the creative match server.

Events.PlayerAdded(function(event)
    ChatService.sendMessage(event.player.name .. " joined the game!")
end)

