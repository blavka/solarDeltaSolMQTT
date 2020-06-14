'''
Created on June 14, 2020
@author: karel.blavka@gmail.com
'''


class Moving_Average:

    def __init__(self, n):
        self._n = n
        self._head = 0
        self._sum = 0
        self._counter = 0
        self._samples = [0] * n

    def feed(self, value):
        self._sum -= self._samples[self._head]

        self._samples[self._head] = value
        self._sum += value

        self._counter += 1

        self._head += 1
        if self._head == self._n:
            self._head = 0

    def reset(self):
        self._head = 0
        self._sum = 0
        self._counter = 0

    def get_avg(self):
        n = self._n if self._n < self._counter else self._counter
        return self._sum / n

    def get_counter(self):
        return self._counter
