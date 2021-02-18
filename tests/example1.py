import random
import time
import unittest
from enum import Enum
from random import choice

from state_machine.machine_logger import logger
from state_machine.main import Machine


class ResultEnum(Enum):
    SUCCESS = 1
    FAILURE = 2


def func1(item):
    time.sleep(random.choice(range(1, 3)))
    return choice([True, False])


def func2(item):
    time.sleep(random.choice(range(1, 3)))
    return choice([1, 2])


def func3(item):
    time.sleep(random.choice(range(1, 3)))
    return choice([ResultEnum.SUCCESS, ResultEnum.FAILURE])


def func4(item):
    time.sleep(random.choice(range(1, 3)))
    return True


def a1(*args, **kwargs):
    time.sleep(random.choice(range(1, 3)))
    return random.choice((0, 1))


def a2(*args, **kwargs):
    time.sleep(random.choice(range(1, 3)))
    return random.choice((0, 1))


class MachineStateTests(unittest.TestCase):
    def test_4_states(self):
        transitions = {func1: {'results': {True: func2,
                                           False: func3},
                               'workers': 2,
                               'start': True
                               },
                       func2: {'results': {1: func3,
                                           2: func2},
                               },
                       func3: {'results': {ResultEnum.SUCCESS: func2,
                                           ResultEnum.FAILURE: func4},
                               'workers': 4},
                       func4: {'results': {True: func1},
                               'workers': 1}
                       }

        machine = Machine(transitions=transitions)
        machine.start(collection=list(range(5)))
        x = 0
        while machine.is_running():
            # Do more stuff meanwhile
            x += 1
            if x == 10:
                break
            time.sleep(1)
        machine.stop()

    def test_sanity(self):
        transitions = {a1: {'start': True,
                            'results': {0: a1,
                                        1: a2},
                            'workers': 2},
                       a2: {'results': {0: a2,
                                        1: a1},
                            'workers': 2},

                       }
        machine = Machine(transitions=transitions, name="testing123")
        logger.info(machine)

        machine.start(list(range(2)))
        time.sleep(3)
        machine.stop()
