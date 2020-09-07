import asyncio
import time
from asyncio import run, create_task, CancelledError
from typing import List, Dict
from dataclasses import dataclass, asdict, field
import json
import zmq
from zmq.asyncio import Context, Socket


@dataclass
class GameState:
     cards_in_pile: Dict[int, List[int]]

     def update(self, event):
         for key, value in event['cards_in_pile'].items():
             self.cards_in_pile[int(key)] = value

     def to_json(self):
         d = dict(
             cards_in_pile=self.cards_in_pile,
         )
         return json.dumps(d)

     #def from_json(self, data):
     #    d = json.loads(data)
     #    for key, value in d['cards_in_pile']:
     #        self.cards_in_pile[int(key)] = [int(w) for w in value]


SERVER_UPDATE_TICK_HZ = 10


async def update_from_client(gs: GameState, sock: Socket):
    try:
        while True:
            msg = await sock.recv_json()
            counter = msg['counter']
            event_dict = msg['event']

            # update game sate
            gs.update(event_dict)
            #print(gs)
            # event_dict = await sock.recv_json()
            #print(f'Got event dict: {event_dict}')
    except asyncio.CancelledError:
        pass


async def ticker(sock1, sock2):

    # A task to receive keyboard and mouse inputs from players.
    # This will also update the game state, gs.
    gs = GameState(cards_in_pile=dict())
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
