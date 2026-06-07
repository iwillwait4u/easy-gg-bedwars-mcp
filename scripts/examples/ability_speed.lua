-- Creates a custom speed ability for the host and applies speed when used.
AbilityService.createAbility("script_speed", "MiscPrimary", {
    maxProgress = 10,
    progressPerUse = 5,
})

AbilityService.enableAbility(MatchService.getHost(), "script_speed")

Events.UseAbility(function(event)
    if event.abilityName == "script_speed" then
        StatusEffectService.giveEffect(event.entity, StatusEffectType.SPEED, 2)
    end
end)
