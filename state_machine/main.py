import multiprocessing
import random
import string
from collections import defaultdict
from multiprocessing.queues import JoinableQueue, Queue
from queue import Empty

from state_machine.machine_logger import logger


class Machine:

    def __init__(self, transitions, name=None):
        self._running = multiprocessing.Event()
        self.interrupted = multiprocessing.Event()
        self.name = name or Machine.get_random_string()

        self.tasks = JoinableQueue(maxsize=-1, ctx=multiprocessing.get_context())
        self.states, self.transitions, self.start_state = self._init_machine(transitions)
        self.coordinator = Machine.Coordinator(self.tasks, self.transitions, machine=self)

    @staticmethod
    def get_random_string(length=5):
        return ''.join(random.sample(string.ascii_lowercase, length))

    def is_running(self):
        return self._running.is_set()

    def __str__(self):
        return f"StateMachine {self.name}: Running: {self.is_running()}"

    def start(self, collection):
        self._running.set()
        self.coordinator.start()
        for state in self.states:
            state.start()

        for item in collection:
            self.start_state.add(item)

    def stop(self, timeout=None):
        logger.info(f"Start stopping StateMachine {self.name}")
        self.interrupted.set()
        self.coordinator.kill()
        for state in self.states:
            state.kill()

        for state in self.states:
            state.join()
        self.coordinator.join(timeout=timeout)

        logger.info("State machine stopped")
        self._running.clear()

    def draw(self):
        # draw machine states
        return ''

    def _init_machine(self, transitions):
        start_state = None
        state_results = []
        all_states = []
        for idx, (func, details) in enumerate(transitions.items(), 1):
            state = Machine.State(name=f"State-{idx}", ready_func=func, workers=details.get('workers', 1), machine=self)
            all_states.append(state)
            logger.info(f"Create state {state}")
            state_results.append((state, details['results']))
            if details.get("start", False):
                if start_state is None:
                    start_state = state
                else:
                    raise SyntaxError("More than one start state. Fix transitions table")

        states = defaultdict(dict)
        for state, results in state_results:
            states[state.id] = {result: next((s for s, _ in state_results if s.ready_func == next_func))
                                for result, next_func in results.items()}

        logger.info("Done")
        return all_states, dict(states), start_state

    class Coordinator(multiprocessing.Process):
        def __init__(self, tasks, transitions, machine):
            super().__init__(name="Coordinator")
            self.machine = machine
            self.transitions = transitions
            self.tasks = tasks

        def run(self):
            logger.info("Coordinator is running")
            for old_task in iter(self.tasks.get, None):
                self.tasks.task_done()
                if self.machine.interrupted.is_set():
                    break
                next_state = self.transitions[old_task.state_id][old_task.result]
                logger.info(f"Move `{old_task.item}` From {old_task.state_id} to {next_state}")
                next_state.add(old_task.item)
            else:
                self.tasks.task_done()
            logger.info("Coordinator stopped!")

        def join(self, timeout=None):
            logger.info("Stopping coordinator")
            while True:
                try:
                    self.tasks.get_nowait()
                    self.tasks.task_done()
                except Empty:
                    break
            self.tasks.join()
            logger.info("coordinator joined and stopped")
            super().join(timeout)

        def add_task(self, task):
            if self.machine.interrupted.is_set():
                logger.info(f"State: machine.interrupted: avoid adding {task} to coordinator")
                return
            self.tasks.put(task)

        def kill(self):
            logger.info("Killing coordinator")
            self.tasks.put(None)

    class Task:
        def __init__(self, item, state_id, result):
            self.item = item
            self.state_id = state_id
            self.result = result

        def __str__(self):
            return f"Task on {self.item} from {self.state_id} with result {self.result}"

    class State:

        def __init__(self, name, machine, ready_func, workers=1):
            self.id = name
            self.machine = machine
            self.ready_func = ready_func
            self.name = name
            self.readq = Queue(maxsize=-1, ctx=multiprocessing.get_context())
            self.num_workers = max(1, workers)
            self.workers = []

        def __repr__(self):
            return self.__str__()

        def __str__(self):
            return self.name

        def kill(self):
            logger.info(f"Kill {self.name}")
            for _ in range(self.num_workers):
                self.readq.put(None)

        def join(self, timeout=None):
            logger.info(f"Join {self.name}")
            for worker in self.workers:
                worker.join(timeout)
            logger.info(f"Done join {self.name}")

        def start(self):
            logger.info(f"Starting {self.name} workers")
            for n in range(self.num_workers):
                state = Machine.State.Worker(n, self, self.machine.coordinator)
                state.start()
                self.workers.append(state)

        def add(self, item):
            if self.machine.interrupted.is_set():
                logger.info(f"State: machine.interrupted: avoid adding {item} to state {self.name}")
                return
            self.readq.put(item)

        class Worker(multiprocessing.Process):
            def __init__(self, idx, state, coordinator):
                super().__init__()
                self.state = state
                self.name = f"{state} worker-{idx}"
                self.readq = state.readq
                self.coordinator = coordinator

            def __str__(self):
                return self.name

            def run(self):
                logger.info(f"Run {self.name}: start")
                # Poison pill means shutdown
                for item in iter(self.readq.get, None):
                    if self.state.machine.interrupted.is_set():
                        logger.info(f"{self.name} interrupted")
                        break
                    result = self.state.ready_func(item)
                    self.coordinator.add_task(Machine.Task(item, self.state.id, result))
                else:
                    logger.info(f"{self.name} stopped")
