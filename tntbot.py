import asyncio
import discord
import challonge as ch
import zipfile
import os
import json
# alternatively use apychalllonge for async

client = discord.Client()

# dicts to store tourneys created and players
tourneys = {}
players = {}

# challong api key
api_key = "secret"


@client.event
async def on_ready():
    print('we have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    # don't process bot messages
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        await message.channel.send('Hello!')

    # create tournament for users with provided role
    if message.content.startswith('!start'):
        # initialize challonge user
        try:
            user = await ch.get_user('niccolaccio', api_key)
        except asyncio.TimeoutError:
            message.channel.send('Challonge timeout, please try again later')
        # decide tournament type
        try:
            ttype = message.content.split(' ')[1]
        except ValueError:
            await message.channel.send('syntax is !start (tournament type) (role1) (role2) ...')
        if ttype == 'rr':
            ttype = ch.enums.TournamentType.round_robin
        elif ttype == 'se':
            ttype = ch.enums.TournamentType.single_elimination
        elif ttype == 'de':
            ttype = ch.enums.TournamentType.double_elimination
        elif ttype == 'sw':
            ttype = ch.enums.TournamentType.swiss
        else:
            await message.channel.send('bad tournament type, available options are rr, se, de, and sw')
            return
        try:
            allroles = message.content.split(' ')[2:]
        except ValueError:
            await message.channel.send('please select which roles to start a tournament for')
        # check for provided role
        for roles in allroles:
            # check if role exists
            group = discord.utils.get(message.guild.roles, name=roles)
            if group:
                # create tournament with that name
                tourneys[roles] = await user.create_tournament(name=roles,
                        url='miceandmen_'+roles,
                        tournament_type=ttype)
                # add all players with that role to tournament
                newplayers = group.members
                for p in newplayers:
                    pname = str(p).split('#')[0]
                    players[pname] = await tourneys[roles].add_participant(pname)
                # start tournament
                await tourneys[roles].start()
            else:
                await message.channel.send('bad role name '+roles)

    # handle match reporting logic
    if message.content.startswith('!report'):
        # initialize challonge
        try:
            user = await ch.get_user('niccolaccio', api_key)
        except asyncio.TimeoutError:
            await message.channel.send('Challonge timed out, please try again later')
        # check score has been provided correctly
        try:
            score = message.content.split(' ')[1]
        except ValueError:
            await message.channel.send('please provide a score')
        try:
            a, b = [int(i) for i in score.split('-')]
        except ValueError:
            await message.channel.send('please report score in format 3-2')
        if b > a:
            await message.channel.send('please report winning score first')
            return
        # check next available match for player
        winner = str(message.author).split('#')[0]
        match = await players[winner].get_next_match()
        #   get both player names
        pid1 = match.player1_id
        pid2 = match.player2_id
        tid = match.tournament_id
        temp = await user.get_tournament(t_id=tid)
        player1 = await temp.get_participant(p_id=pid1)
        player2 = await temp.get_participant(p_id=pid2)
        #  download and rename replay files
        n = 2*a-1
        basename = player1.name + ' v ' + player2.name
        # check attachments
        # discord does not allow multiple attachments from desktop,
        # need to get from user history
        r = 0
        msgs = await message.channel.history(limit=n+1).flatten()
        for i in range(len(msgs)-1, -1, -1):
            if msgs[i].author == message.author:
                try:
                    fname = basename + ' ' + str(r+1) + '.xml'
                    await msgs[i].attachments[0].save(fname)
                    r += 1
                    last = i
                except IndexError:
                    print('no attachment')
        if r != (a+b):
            await message.channel.send('please attach the xml replay files for all games in this match')
            return
        for i in range(r, n):
            fname = basename + ' ' + str(i+1) + '.xml'
            await msgs[last].attachments[0].save(fname)
        # save replays to zip file
        fname = basename + '.zip'
        with zipfile.ZipFile(fname, 'w') as myzip:
            for i in range(n):
                fname = basename + ' ' + str(i+1) + '.xml'
                myzip.write(fname)
        # upload new attachment to replay and caster channel
        rchannel = discord.utils.get(message.guild.text_channels, name='replays')
        cchannel = discord.utils.get(message.guild.text_channels, name='caster')
        fname = basename + '.zip'
        with open(fname, 'rb') as f:
            await rchannel.send(basename, file=discord.File(f))
            await cchannel.send(basename, file=discord.File(f))
        # delete local files
        os.remove(fname)
        for i in range(n):
            fname = basename + ' ' + str(i+1) + '.xml'
            os.remove(fname)
        # update score to challonge
        await match.report_winner(players[winner], score)
        # delete original messages (optional)
        for msg in msgs:
            if msg.author == message.author:
                await msg.delete()
        await message.delete()

    if message.content.startswith('!list'):
        # generate player list for provided role(s)
        try:
            roles = message.content.split(' ')[1:]
            playerlist = {}
        except (ValueError, IndexError):
            await message.channel.send('please include list of roles to include in generated player list')
        for r in roles:
            group = discord.utils.get(message.guild.roles, name=r)
            if group:
                playerlist[group.name] = []
                newplayers = group.members
                for p in newplayers:
                    pname = str(p).split('#')[0]
                    pavatar = str(p.avatar_url)
                    playerlist[group.name].append([pname, pavatar])
        with open('playerlist.json', 'w') as f:
            json.dump(playerlist, f)
        with open('playerlist.json', 'rb') as f:
            await message.channel.send('generated players.json for use in obs overlay', file=discord.File(f))

    if message.content.startswith('!cast'):
        # delete match from casting channel
        match = message.content[6:]
        caster = discord.utils.get(message.guild.text_channels, name='caster')
        async for msg in caster.history(limit=200):
            if match == msg.content:
                await msg.delete()
                await message.channel.send('deleted replay from casting channel')

    if message.content.startswith('!ping'):
        # ping players with unreported matches this round
        try:
            rnd = int(message.content.split(' ')[1])
        except IndexError:
            await message.channel.send('please include round number')
        try:
            roles = message.content.split(' ')[2:]
        except IndexError:
            await message.channel.send('please include roles to ping')
        try:
            user = await ch.get_user('niccolaccio', api_key)
        except asyncio.TimeoutError:
            message.channel.send('Challonge timeout, please try again later')
        await message.channel.send('checking for unplayed matches')
        pings = []
        for r in roles:
            # check if role exists
            group = discord.utils.get(message.guild.roles, name=r)
            if group:
                # check if each player has reported their match for this round
                newplayers = group.members
                for p in newplayers:
                    pname = str(p).split('#')[0]
                    match = await players[pname].get_next_match()
                    if match.round <= rnd:
                        pings.append(p.mention)
            else:
                await message.channel.send('bad role name '+roles)
        # ping players
        msg = 'Please play and report your match for round ' + str(rnd)
        for p in pings:
            msg += p
        await message.channel.send(msg)


client.run('token')
