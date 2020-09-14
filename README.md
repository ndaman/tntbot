# tntbot

A simple discord bot I wrote for managing Tooth and Tail tournaments, it's probably not written very well, but so far it works for my purposes.

The bot functionality:

## create tournaments on challonge

!start [tournament type code] [role1] [role2]

tournament type code is a two letter code, 'se' for single elimination, 'de' for double elimination, 'rr' for round robin and 'sw' for swiss.

Before calling the command, assign players to roles, each roll will be its own tournament (e.g. beginner, intermediate, premier).

## report scores and package replays

!report 3-2

first upload your replays (names can be anything as long as they are in chronological order)
After your !report command, tntbot will download your replay xml files, pad them with 'anti-spoiler' copies, rename them to match the players in your assigned match, and put the .zip file in the replay and caster channels.

## create a json list of players

!list role1 role2

This .json file is meant to interact with dzon's excellent overlay file (at present I still need to fork this to add this functionality), but it will allow you to automatically generate a list of usernames and player avatars to use with the plugin.

## ping players who haven't played or reported their matches yet

!ping round_number role1 role2

This will search for players in role1, role2, etc. who have not yet played their match for round "round_number" (should be an int) and will "mention" them all in one message reminding players to submit their replays.

## delete replays from caster channel

!cast player1 v player2

To automatically manage replay casting, once casters have downloaded a replay this command will delete the message from the caster channel.
