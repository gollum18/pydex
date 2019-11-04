# Name: pydex.py
# Since: 10/28/2019
# Author: Christen Ford
# Purpose: Implements the dynamic hashing index algorithm. Note that the dynamic hashing algorithm is dependent
#   on the existence of a perfect hashing function. Without such a function, the resultant tree is bound to
#   be skewed in one direction or the other. In practice, this is still a very practical algorithm, however
#   in most languages, it cannot reach its theoretical best performance due to the absence of a perfect hashing
#   algorithm. This particular implementation utilizes the SHA-256 hash algorithm to provide 'good-enough'
#   hashes for operations that interact with the tree. SHA-256 also provides 32-bytes worth of binary data to
#   index into the Trie with. 32 bytes is standard industry practice AFAIK, per my Professor.
# Note that the dynamic hash algorithm is essentially a Trie data structure, and the classes provided by this
#   module are generic enough in that they can be used as a size-bounded Trie wherein each ply contains a number of
#   nodes in one of two states: either the node is a node object, or the node contains key-value pairs. The number
#   of key-value pairs is bounded by a maximum number, `n`, and a fill factor `ff`. On insertion, a new indirection node
#   is created from a key-value node if the number of entries in the key-value node exceed `n` * `ff`.
# Furthermore, the Trie in this module is implemented with dynamic node removal per the dynamic hashing algorithm.
#   When both of the key-value nodes pointed to by an indirection node are empty, the indirection node is coalesced
#   back into a key-value node. Note that this operation only happens on a deletion, however it is recursively applied
#   back up the Trie in a manner such that several coalesce operations may occur on a single deletion.

import hashlib
from sortedcontainers import SortedList

LEFT_BIT = '0'
RIGHT_BIT = '1'
LEFT_TO_RIGHT = 0
RIGHT_TO_LEFT = 1


def consume_bkey(bkey, direction):
    """
    Consumes a binary key returning the consumed bit and the partially consumed key.
    :param bkey: The binary key to consume.
    :param direction: The direction to consume the key in. One of {LEFT_TO_RIGHT, RIGHT_TO_LEFT}.
    :return: A pair consisting of ({0, 1}, {bkey[1:], bkey[:-1]}).
    :raises: ValueError if bkey is None or empty, or an invalid direction was specified.
    """
    if not bkey or (direction != LEFT_TO_RIGHT and direction != RIGHT_TO_LEFT):
        raise ValueError
    if len(bkey) == 1:
        return bkey[0], ""
    if direction == LEFT_TO_RIGHT:
        return bkey[0], bkey[1:]
    elif direction == RIGHT_TO_LEFT:
        return bkey[-1], bkey[:-1]


def extract_key(e):
    """
    Extracts the key from the given entry.
    :param e: The entry to return the key from.
    :return: To more flexibly support SortedList operations, this
    """
    if isinstance(e, _IndexEntry):
        return e.key
    else:
        return e


def bin_key(key):
    """
    Converts a key to its binary representation by hashing it against the SHA-256 hashing algorithm.
    :param key: The key to convert.
    :return: The binary representation of the keys corresponding SHA-256 hash.
    """
    digest = hashlib.sha256()
    digest.update(bytes(key))
    hk = digest.hexdigest()
    return bin(int(hk, 16))[2:]


class _IndexEntry(object):

    def __init__(self, key, value, bkey):
        """
        Returns a new instance of a _IndexEntry object.
        :param key: The key to store in the IndexEntry.
        :param value: The value to store in the IndexEntry.
        :param bkey: The binary representation of the key 'so far'. This is a compromise in space. Alternatively,
        the depth could have been stored here instead and iterated over to produce the correct partial binary hash.
        This value is used to correctly hash the key-value pair into its new bucket on overflow.
        """
        self.key = key
        self.value = value
        self.bkey = bkey


class _DHTNode(object):

    def __init__(self, n=8, ff=0.80, direction=LEFT_TO_RIGHT, parent=None):
        """
        Defines an instance of a new Dynamic Hash Table.
        :param n: The max number of entries per bucket.
        :param ff: The fill factor for each bucket.
        :param direction: The direction to consume the key from.
        :param parent: A reference to the parent node.
        """
        if n < 3:
            n = 3
        self.n = n
        if ff < 0.25:
            ff = 0.25
        self.ff = ff
        if not (direction == LEFT_TO_RIGHT or direction == RIGHT_TO_LEFT):
            direction = LEFT_TO_RIGHT
        self.n = n
        self.ff = ff
        self.direction = direction
        self.parent = parent
        self.left = SortedList(key=extract_key)
        self.right = SortedList(key=extract_key)

    def add(self, key, value, bkey):
        """
        Adds a key-value pair to the DHT.
        :param key: The key to add.
        :param value: The corresponding value.
        :param bkey: A binary representation of the key.
        """
        bit, ck = consume_bkey(bkey, self.direction)
        if bit == LEFT_BIT:
            if isinstance(self.left, SortedList):
                self.left.add(_IndexEntry(key, value, ck))
                if len(self.left) > self.n * self.ff:
                    self._overflow(LEFT_BIT)
            elif isinstance(self.left, _DHTNode):
                self.left.add(key, value, ck)
            else:
                raise Exception()
        elif bit == RIGHT_BIT:
            if isinstance(self.right, SortedList):
                self.right.add(_IndexEntry(key, value, ck))
                if len(self.right) > self.n * self.ff:
                    self._overflow(RIGHT_BIT)
            elif isinstance(self.right, _DHTNode):
                self.right.add(key, value, ck)
            else:
                raise Exception()
        else:
            raise Exception()

    def contains(self, key, bkey):
        """
        Determines if the DHT contains at lest one key-value entry with the given key.
        :param key: The key to lookup.
        :param bkey: The binary representation of the key.
        :return: True if at least one key-value entry is found corresponding to the given key, False otherwise.
        """
        bit, ck = consume_bkey(bkey, self.direction)
        if bit == LEFT_BIT:
            if isinstance(self.left, SortedList):
                for entry in self.left:
                    if key == entry.key:
                        return True
                return False
            elif isinstance(self.left, _DHTNode):
                return self.left.contains(key, ck)
            else:
                raise Exception()
        elif bit == RIGHT_BIT:
            if isinstance(self.right, SortedList):
                for entry in self.right:
                    if key == entry.key:
                        return True
                return False
            elif isinstance(self.right, _DHTNode):
                return self.right.contains(key, ck)
            else:
                raise Exception()
        else:
            raise Exception()

    def delete(self, key, bkey):
        """
        Deletes the first matching key-value entry from the DHT.
        :param key: The key to lookup.
        :param bkey: The binary representation of the key.
        """
        bit, ck = consume_bkey(bkey, self.direction)
        if bit == LEFT_BIT:
            if isinstance(self.left, SortedList):
                discard = None
                for entry in self.left:
                    if key == entry.key:
                        discard = entry
                        break
                if discard:
                    self.left.discard(discard)
            elif isinstance(self.left, _DHTNode):
                self.left.delete(key, ck)
            else:
                raise Exception()
        elif bit == RIGHT_BIT:
            if isinstance(self.right, SortedList):
                discard = None
                for entry in self.right:
                    if key == entry.key:
                        discard = entry
                        break
                if discard:
                    self.right.discard(discard)
            elif isinstance(self.right, _DHTNode):
                self.right.delete(key, ck)
            else:
                raise Exception()
        else:
            raise Exception()
        if (isinstance(self.left, SortedList) and not self.left and
                isinstance(self.right, SortedList) and not self.right):
            self._underflow()

    def get(self, key, bkey):
        """
        Gets the first matching key-value entry from the key
        :param key: The key to lookup.
        :param bkey: The binary representation of the key.
        :return: True if at least one key-value entry is found corresponding to the given key, False otherwise.
        """
        bit, ck = consume_bkey(bkey, self.direction)
        if bit == LEFT_BIT:
            if isinstance(self.left, SortedList):
                for entry in self.left:
                    if key == entry.key:
                        return entry.value
                return None
            elif isinstance(self.left, _DHTNode):
                return self.left.get(key, ck)
            else:
                raise Exception()
        elif bit == RIGHT_BIT:
            if isinstance(self.right, SortedList):
                for entry in self.right:
                    if key == entry.key:
                        return entry.value
                return None
            elif isinstance(self.right, _DHTNode):
                return self.right.get(key, ck)
            else:
                raise Exception()
        else:
            raise Exception()

    def height(self):
        """
        Gets the height of the DHT.
        :return: The height of the DHT.
        """
        if isinstance(self.left, SortedList) and isinstance(self.right, SortedList):
            return 1
        left = 0
        right = 0
        if isinstance(self.left, _DHTNode):
            left = self.left.height() + 1
        if isinstance(self.right, _DHTNode):
            right = self.right.height() + 1
        return max(left, right)

    def traverse(self):
        """
        Traverses the DHT yielding key-value pairs as a Python generator.
        :return: A Python generator over the key-value pairs in the DHT.
        """
        if isinstance(self.left, SortedList):
            for entry in self.left:
                yield entry.key, entry.value
        elif isinstance(self.left, _DHTNode):
            yield from self.left.traverse()
        else:
            raise Exception()
        if isinstance(self.right, SortedList):
            for entry in self.right:
                yield entry.key, entry.value
        elif isinstance(self.right, _DHTNode):
            yield from self.right.traverse()
        else:
            raise Exception()

    def _overflow(self, bit):
        """
        Redistributes the indicated buckets keys to a new left and right bucket. An overflow happens when a bucket
        grows to large, i.e. its total length is greater than its maximum number of entries times its fill factor.
        :param bit: The bit representing the buck that overflowed. One of {LEFT_BIT, RIGHT_BIT}.
        """
        if bit == LEFT_BIT and isinstance(self.left, SortedList):
            new_left = _DHTNode(n=self.n, ff=self.ff, direction=self.direction, parent=self)
            for entry in self.left:
                new_left.add(entry.key, entry.value, entry.bkey)
            self.left.clear()
            self.left = new_left
        elif bit == RIGHT_BIT and isinstance(self.right, SortedList):
            new_right = _DHTNode(n=self.n, ff=self.ff, direction=self.direction, parent=self)
            for entry in self.right:
                new_right.add(entry.key, entry.value, entry.bkey)
            self.right.clear()
            self.right = new_right
        else:
            raise Exception()

    def _underflow(self):
        """
        Coalesces the two buckets pointed to by this this into a single bucket. An underflow occurs when a deletion
        causes a state where by both buckets pointed to by this node are empty. This rule is ignored for the root node.
        """
        # only underflow if we are not the root node, root node cannot underflow
        if self.parent:
            if self.parent.left == self:
                self.parent.left = SortedList(key=extract_key)
            elif self.parent.right == self:
                self.parent.right = SortedList(key=extract_key)
            else:
                raise Exception()


class DHT(object):

    def __init__(self, n=8, ff=0.80, direction=LEFT_TO_RIGHT):
        """
        Defines an instance of a new Dynamic Hash Table.
        :param n: The max number of entries per bucket (default: 8).
        :param ff: The fill factor for each bucket (default: 0.80).
        :param direction: The direction to consume the key from during operations. One of {LEFT_TO_RIGHT, RIGHT_TO_LEFT}
        (default: LEFT_TO_RIGHT).
        """
        if n < 3:
            n = 3
        self.n = n
        if ff < 0.25:
            ff = 0.25
        self.ff = ff
        if not (direction == LEFT_TO_RIGHT or direction == RIGHT_TO_LEFT):
            direction = LEFT_TO_RIGHT
        self.direction = direction
        self.root = _DHTNode(n=self.n, ff=self.ff, direction=self.direction)

    def add(self, key, value):
        """
        Adds a key-value pair to the DHT.
        :param key: The key to add.
        :param value: The corresponding value.
        """
        self.root.add(key, value, bin_key(key))

    def contains(self, key):
        """
        Determines if there is at least on key-value entry in the DHT with the given key.
        :param key: The key to lookup.
        :return: True if at least on key-value pair is found with the matching key, False otherwise.
        """
        return self.root.contains(key, bin_key(key))

    def delete(self, key):
        """
        Deletes a key-value pair from the DHT if the key is found.
        :param key: The key to lookup.
        """
        self.root.delete(key, bin_key(key))

    def get(self, key):
        """
        Gets the first value found for a given corresponding key.
        :param key: The key to lookup.
        :return: A value if one is found, otherwise None.
        """
        return self.root.get(key, bin_key(key))

    def height(self):
        """
        Gets the height of the DHT.
        :return: The height of the DHT.
        """
        return self.root.height()

    def traverse(self):
        """
        Traverses over the key-value pairs in the DHT, returning them as a Python generator.
        :return: A Python generator over the key-value pairs in the DHT.
        """
        yield from self.root.traverse()


def test_dht():
    from random import random
    items = [0, 1, 9, 2, 8, 3, 7, 4, 6, 5]
    dht = DHT(n=3)
    for item in items:
        dht.add(item, random() * 100)
    for item in items:
        print(dht.get(item))
    print(dht.height())
    for key, value in dht.traverse():
        print("({k} => {v})".format(k=key, v=value))
    for item in items:
        print("Contains {k}: {b}".format(k=item, b=dht.contains(item)))
    for i in items:
        dht.delete(i)
    print('-'*80)
    for key, value in dht.traverse():
        print("({k} => {v})".format(k=key, v=value))
    print(dht.height())


def test_lab():
    dht = DHT(n=5)
    kv = {}
    for key, value in kv:
        dht.add(key, value)
    for key, value in dht.traverse():
        print("{k} => {v}".format(k=key, v=value))


if __name__ == '__main__':
    test_dht()
