import time
# from uncertainties import ufloat
from threading import Thread, Event

import zmq
import logging
import json
# from threading import Thread

logger = logging.getLogger('zmqConn')


class genericAnswer(Exception):
    pass


class customEx(Exception):
    pass


class zmqDevice(object):
    """docstring for ZMQdevice"""

    def __init__(self, zmqcontext=None, port_rep=5556, port_req=5557, ip_req='192.168.1.103', *args, **kwargs):
        """reverse portnumbers for server devices!"""
        super(zmqDevice, self).__init__(*args, **kwargs)
        try:

            self.tcp_rep = zmqcontext.socket(zmq.REP)
            self.tcp_req = zmqcontext.socket(zmq.REQ)
        except AttributeError:
            self.zmq_context = zmq.Context()
            self.tcp_rep = self.zmq_context.socket(zmq.REP)
            self.tcp_req = self.zmq_context.socket(zmq.REQ)

        self.tcp_rep.bind(f"tcp://*:{port_rep}")
        self.tcp_req.connect(f"tcp://{ip_req}:{port_req}")

    def zmqquery_handle(self):
        """handle all currently available messages"""
        try:
            while True:
                message = self.tcp_rep.recv(flags=zmq.NOBLOCK)
                logger.debug(f'received message: {message}')
                # print(f'received message: {message}')
                try:
                    self.handlefun(message_bytes=message)
                except genericAnswer as gen:
                    self.tcp_rep.send_string("{}".format(gen))
        except zmq.Again:
            pass
            # print('nothing to work')

    def zmqquery(self, query):
        """perform one query via zmq"""
        try:
            self.tcp_req.send_string(f'{query}')
            while True:
                try:
                    message = self.tcp_req.recv(flags=zmq.NOBLOCK)
                    raise customEx
                except zmq.Again:
                    time.sleep(0.2)
                    logger.debug('no answer')
        except zmq.ZMQError as e:
            logger.exception('There was an error in the zmq communication!', e)
            return -1
        except customEx:
            return message

    def zmqquery_dict(self, query):
        """perform one query via zmq, expecting json-like response"""
        try:
            self.tcp_req.send_string(f'{query}')
            while True:
                try:
                    message = self.tcp_req.recv_json(flags=zmq.NOBLOCK)
                    raise customEx
                except zmq.Again:
                    time.sleep(0.2)
                    logger.debug('no answer')
                except json.decoder.JSONDecodeError:
                    logger.exception('json dictquery failed -- non-json returned!')
        except zmq.ZMQError as e:
            logger.exception('There was an error in the zmq communication!', e)
            return -1
        except customEx:
            return message

    def handlefun(self, message):
        """to be implemented by specific device, handling messages"""
        raise NotImplementedError


class zmqServer(zmqDevice):
    """zmqServer with exchanged ports, for other side of communication"""

    def __init__(self, *args, **kwargs):
        super(zmqServer, self).__init__(
            port_rep=5557, port_req=5556, *args, **kwargs)


class Timerthread(Thread):

    def __init__(self, event=None, interval=0.5, *args, **kwargs):
        super(Timerthread, self).__init__(*args, **kwargs)
        self.interval = interval
        self.counter = 0
        if event is None:
            self.stopped = Event()
        else:
            self.stopped = event

    def run(self):
        while not self.stopped.wait(self.interval):
            # print(f"my thread is working hard! {self.counter}")
            self.work()
            # self.counter += 1

    def work(self):
        """to be implemented by child class!"""
        raise NotImplementedError


class TestHandler(zmqServer, Timerthread):
    """docstring for PressureHandler"""

    def __init__(self, *args, **kwargs):
        super(TestHandler, self).__init__(*args, **kwargs)
        self._pressure = 5

    def handlefun(self, message):
        if message == b'p?':
            self.tcp_rep.send_string(f'{self._pressure}')
        else:
            self.tcp_rep.send_string(f'received: {message}, can reply to "p?"')

    def work(self):
        self.zmqquery_handle()


if __name__ == '__main__':
    stopevent = Event()
    dev = TestHandler(event=stopevent, interval=0.1)
    dev.start()
    try:
        time.sleep(200)
    finally:
        stopevent.set()
