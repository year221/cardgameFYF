import asyncio
import time
from asyncio import run, create_task, CancelledError
from typing import List, Dict
from dataclasses import dataclass, asdict, field
import json
import zmq
from zmq.asyncio import Context, Socket

import gameutil
#mport GameState, Event, json_obj_hook

SERVER_UPDATE_TICK_HZ = 10


async def update_from_client(gs: gameutil.GameState, sock: Socket):
    try:
        while True:


            msg = await sock.recv_json(object_hook=gameutil.json_obj_hook)
            counter = msg['counter']
            event_dict = msg['event']
            print(msg)
            #print(event_dict)
            # update game sate
            print({key: val for key, val in gs.cards_in_pile.items() if key != 0})
            gs.update_from_event(gameutil.Event(**event_dict))
            print('***')
            #print(gs)
            # event_dict = await sock.recv_json()
            #print(f'Got event dict: {event_dict}')
    except asyncio.CancelledError:
        pass


async def ticker(sock1, sock2):

    # A task to receive keyboard and mouse inputs from players.
    # This will also update the game state, gs.
    gs = gameutil.GameState(
        n_pile=0,
        # cards_in_pile={0: list(zip(list(range(108)), ['U'] * 108)),
        #                6: [], 7: [], 8: [], 9: [], 10: [], 11: [], 12: [], 13: [], 14: [], 15: [], 16: [], 17: [],
        #                18: [], 19: [], 20: [], 21: [], 22: [], 23: []
        #                },
        cards_in_pile={0:list(range(108)),
                       6:[], 7:[], 8:[], 9:[], 10:[], 11:[], 12:[], 13:[], 14:[], 15:[], 16:[], 17:[], 18:[], 19:[], 20:[], 21:[], 22:[], 23:[]
                       },
        cards_status={w:'U' for w in range(108)},
        n_player=6,
        player_assignment={0:'test'},
        status='Game'
    )
    t = create_task(update_from_client(gs, sock2))

    # Send out the game state to all players 60 times per second.
    try:
        while True:
            await sock1.send_string(gs.to_json())
            #print('.', end='', flush=True)
            await asyncio.sleep(1 / SERVER_UPDATE_TICK_HZ)
    except asyncio.CancelledError:
        t.cancel()
        await t


async def main():
    ctx = Context()

    sock_push_gamestate: Socket = ctx.socket(zmq.PUB)
    sock_push_gamestate.bind('tcp://*:25000')

    sock_recv_player_evts: Socket = ctx.socket(zmq.PULL)
    sock_recv_player_evts.bind('tcp://*:25001')

    ticker_task = asyncio.create_task(
        ticker(sock_push_gamestate, sock_recv_player_evts),
    )
    try:
        await asyncio.wait(
            [ticker_task],
            return_when=asyncio.FIRST_COMPLETED
        )
    except CancelledError:
        print('Cancelled')
    finally:
        ticker_task.cancel()
        await ticker_task
        sock_push_gamestate.close(1)
        sock_recv_player_evts.close(1)
        ctx.destroy(linger=1000)


if __name__ == '__main__':
    run(main())


