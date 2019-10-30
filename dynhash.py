# Name: dynhash.py
# Since: 10/28/2019
# Author: Christen Ford
# Purpose: Implements the dynamic hashing index algorithm.

from sortedcontainers import SortedList

# used to consume bits in a bitstring.
LEFT_TO_RIGHT = 0  # consumes from the left to the right
RIGHT_TO_LEFT = 1  # consumes from the right to the left

# provided for convenience when traversing the tree.
LEFT_KEY = '0'  # maps all entries keyed to '0'
RIGHT_KEY = '1'  # maps all entries keyed to '1'


# used by the SortedList to compare keys
def extract_key(e):
    return e.key


def consume_key(key, direction):
    """
    Consumes one bit from a binary key returning both the consumed bit and the remaining key.
    :param key: The binary key to consume.
    :param direction: The direction to consume from. One of {LEFT_TO_RIGHT, RIGHT_TO_LEFT}.
    :return: A pair consisting of (bit, key-1).
    :raises ValueError: If the key is not None or is not a string.
    :raises ValueError: It the direction is not one of {LEFT_TO_RIGHT, RIGHT_TO_LEFT}.
    """
    if key is None or not isinstance(key, str):
        raise ValueError
    if not (direction == LEFT_TO_RIGHT or direction == RIGHT_TO_LEFT):
        raise ValueError
    if len(key) == 1:
        return key[0], ""
    if direction == LEFT_TO_RIGHT:
        bit = key[0]
        consumed = key[1:len(key)]
    else:
        bit = key[-1]
        consumed = key[0:len(key)-1]
    return bit, consumed


def key_to_binary(key, n=32):
    """
    Converts the given key to binary with a fixed number of bits.
    :param key: The key to convert to binary.
    :param n: The number of bits to fix the binary representation of the key to.
    :return:
    :raises ValueError: If the key is None or not an integer.
    :raises ValueError: If n is less than 0.
    """
    if key is None or not isinstance(key, int):
        raise ValueError
    if n < 0:
        raise ValueError
    return format(key, '0{bits}b'.format(bits=n))


class _DHTEntry(object):
    """
    Implements an entry in a dynamic hash tree (DHT).
    """

    def __init__(self, key, value):
        """
        Returns a new instance of a _DHTEntry.
        :param key: The key stored in the DHT entry.
        :param value: The value stored in the DHT entry.
        :return: An instance of a _DHTEntry object.
        """
        self.key = key
        self.value = value


class _DHTNode(object):
    """
    Implements a node in a dynamic hash tree. Used by the DHT class to perform internal operations on the tree.
    """

    def __init__(self, parent=None, depth=0, n=8, direction=RIGHT_TO_LEFT):
        """
        Returns an instance of a _DHTNode with the specified max bucket size and parent.
        :param n: The max bucket size.
        :param parent: A pointer to the parent node.
        :param direction: The direction to consume the key from.
        """
        self.n = n
        self.depth = depth
        self.parent = parent
        self.direction = direction
        self.internal = False
        self.left_child = SortedList(key=extract_key)
        self.right_child = SortedList(key=extract_key)

    def add(self, key, bitstring, value):
        """
        Adds a key-value pair to the DHTNode.
        :param key: The key ordinate of the key-value pair.
        :param bitstring: The key as a partially consumed bitstring.
        :param value: The value ordinate of the key-value pair.
        """
        tree_key, consumed_key = consume_key(bitstring, self.direction)
        if tree_key == LEFT_KEY:
            if isinstance(self.left_child, _DHTNode):
                self.left_child.add(key, consumed_key, value)
            elif isinstance(self.left_child, SortedList):
                self.left_child.add(_DHTEntry(key, value))
                if len(self.left_child) > self.n:
                    self._overflow(LEFT_KEY)
            else:
                raise Exception()
        elif tree_key == RIGHT_KEY:
            if isinstance(self.right_child, _DHTNode):
                self.right_child.add(key, consumed_key, value)
            elif isinstance(self.right_child, SortedList):
                self.right_child.add(_DHTEntry(key, value))
                if len(self.right_child) > self.n:
                    self._overflow(RIGHT_KEY)
            else:
                raise Exception()
        else:
            raise KeyError()

    def contains(self, key, bitstring):
        """
        Determines if the tree contains the given key.
        :param key: The key to lookup.
        :param bitstring: A partially consumed bitstring representation of the key.
        :return: True if the key is found in the tree, False otherwise.
        """
        tree_key, consumed_key = consume_key(key, bitstring)
        if tree_key == LEFT_KEY:
            if isinstance(self.left_child, _DHTNode):
                return self.left_child.contains(key, consumed_key)
            elif isinstance(self.left_child, SortedList):
                for entry in self.left_child:
                    if entry.key == key:
                        return True
                return False
            else:
                raise KeyError
        elif tree_key == RIGHT_KEY:
            if isinstance(self.right_child, _DHTNode):
                return self.right_child.contains(key, consumed_key)
            elif isinstance(self.right_child, SortedList):
                for entry in self.right_child:
                    if entry.key == key:
                        return True
                return False
            else:
                raise KeyError
        else:
            raise Exception()

    def delete(self, key, bitstring):
        """
        Deletes a key-value pair from the value with the specified key.
        :param key: The key ordinate of the key-value pair.
        :param bitstring: The key as a partially consumed bitstring.
        """
        tree_key, consumed_key = consume_key(bitstring, self.direction)
        if tree_key == LEFT_KEY:
            if isinstance(self.left_child, _DHTNode):
                self.left_child.delete(key, consumed_key)
            elif isinstance(self.left_child, SortedList):
                self.left_child.discard(key)
            else:
                raise Exception()
        elif tree_key == RIGHT_KEY:
            if isinstance(self.right_child, _DHTNode):
                self.right_child.delete(key, consumed_key)
            elif isinstance(self.right_child, SortedList):
                self.right_child.discard(key)
            else:
                raise Exception()
        else:
            raise KeyError()
        # can only underflow when we are a leaf node and both buckets are empty
        if (isinstance(self.left_child, SortedList) and not self.left_child and
                isinstance(self.right_child, SortedList) and not self.right_child):
            self._underflow()

    def get(self, key, bitstring):
        """
        Gets a value from the tree.
        :param key: The key to lookup.
        :param bitstring: A partially consumed bitstring version of the key.
        :return: The value corresponding to the first instance of the key, else None.
        """
        tree_key, consumed_key = consume_key(key, bitstring)
        if tree_key == LEFT_KEY:
            if isinstance(self.left_child, _DHTNode):
                return self.left_child.contains(key, consumed_key)
            elif isinstance(self.left_child, SortedList):
                for entry in self.left_child:
                    if entry.key == key:
                        return entry.value
                return None
            else:
                raise KeyError
        elif tree_key == RIGHT_KEY:
            if isinstance(self.right_child, _DHTNode):
                return self.right_child.contains(key, consumed_key)
            elif isinstance(self.right_child, SortedList):
                for entry in self.right_child:
                    if entry.key == key:
                        return entry.value
                return None
            else:
                raise KeyError
        else:
            raise Exception()

    def height(self):
        """
        Returns the height of this node.
        :return: The height of this node.
        """
        if isinstance(self.left_child, _DHTNode):
            left_height = self.left_child.height() + 1
        elif isinstance(self.left_child, SortedList):
            left_height = 1
        else:
            raise Exception()
        if isinstance(self.right_child, _DHTNode):
            right_height = self.right_child.height() + 1
        elif isinstance(self.right_child, SortedList):
            right_height = 1
        else:
            raise Exception()
        return max(left_height, right_height)

    def _overflow(self, tree_key):
        """
        Handles overflows when they occur. This process converts the node into an internal node and redistributes its
        data values between two new DHTNodes that take the place of `left` and `right`.
        :param tree_key: Key corresponding to the branch that overflowed, one of {LEFT_KEY, RIGHT_KEY}.
        """
        if tree_key == LEFT_KEY:
            if not isinstance(self.left_child, SortedList):
                raise Exception()
            new_left = _DHTNode(self, n=self.n, depth=self.depth+1)
            for entry in self.left_child:
                consumed_key = key_to_binary(entry.key)
                for i in range(self.depth):
                    _, consumed_key = consume_key(consumed_key, self.direction)
                new_left.add(entry.key, consumed_key, entry.value)
            self.left_child = new_left
        elif tree_key == RIGHT_KEY:
            if not isinstance(self.right_child, SortedList):
                raise Exception()
            new_right = _DHTNode(self, n=self.n, depth=self.depth+1)
            for entry in self.right_child:
                consumed_key = key_to_binary(entry.key)
                for i in range(self.depth):
                    _, consumed_key = consume_key(consumed_key, self.direction)
                new_right.add(entry.key, consumed_key, entry.value)
            self.right_child = new_right
        else:
            raise ValueError()
        self.internal = True

    def _underflow(self):
        """
        Handles underflows when they occur. An underflow occurs when a deletion causes a node branches to both have
        empty buckets. Collapses two empty branches into a single bucket.
        """
        self.left_child = None
        self.right_child = None
        if self.parent.left_child == self:
            self.parent.left_child = SortedList(key=extract_key)
        elif self.parent.right_child == self:
            self.parent.right_child = SortedList(key=extract_key)
        else:
            raise Exception
        self.internal = False


class DHT(object):
    """
    Implements a dynamic hash tree for use in indexing.
    """

    def __init__(self, n=8):
        """
        Returns a new instance of a DHT with a specified max number of entries per node.
        :param n: The max number of entries per node.
        """
        self.root = _DHTNode(n=n)

    def add(self, key, value):
        """
        Adds a key-value pair to the DHT.
        :param key: The key ordinate of the key-value pair.
        :param value: The value ordinate of the key-value pair.
        """
        self.root.add(key, key_to_binary(key), value)

    def contains(self, key):
        """
        Determines if the DHT contains a key-value pair given its key.
        :param key: The key ordinate of the key-value pair.
        :return: True if the DHT contains a key-value pair with the given key.
        """
        return self.root.contains(key, key_to_binary(key))

    def delete(self, key):
        """
        Deletes the first instance of a matching key-value pair with the given key.
        :param key: The key ordinate of the key-value pair.
        """
        self.root.delete(key, key_to_binary(key))

    def get(self, key):
        """
        Retrieves a the value from a key-value pair in the DHT.
        :param key: The key ordinate of the key-value pair to lookup.
        :return: The value if the key-value pair is found, otherwise None.
        """
        return self.root.get(key, key_to_binary(key))

    def height(self):
        """
        Gets the height of the DHT.
        :return: The height of the DHT.
        """
        return self.root.height()


def test_dynamic_hashing():
    items = [5, 1, 9, 3, 8, 2, 6, 0, 7]
    tree = DHT(n=3)
    for i in range(len(items)):
        tree.add(items[i], i)
    print('Height:', tree.height())


if __name__ == '__main__':
    test_dynamic_hashing()
