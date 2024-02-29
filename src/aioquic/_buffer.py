from typing import Union, Optional


class BufferReadError(ValueError):
    """A read tried to go out-of-bounds"""


class BufferWriteError(ValueError):
    """A write tried to go out-of-bounds"""


BufferData = Union[bytes, bytearray]


class Buffer:
    def __init__(
        self,
        capacity: Optional[int] = None,
        data: Optional[BufferData] = None,
    ):
        self._data: BufferData
        if capacity is not None:
            self._data = bytearray(capacity)
            self.capacity = capacity
        elif data is not None:
            self._data = data
            self.capacity = len(self._data)
        else:
            raise ValueError("must specify either data or capacity")
        self.pos = 0
        self.end = len(self._data)

    @property
    def data(self) -> bytes:
        return bytes(self._data[: self.pos])

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int):
        if offset < 0 or offset > self.end:
            raise BufferReadError("Seek out of bounds")
        self.pos = offset

    def eof(self) -> bool:
        return self.pos == self.end

    def data_slice(self, start: int, stop: int) -> bytes:
        if start < 0 or stop < 0 or start > self.end or start > stop or stop > self.end:
            raise BufferReadError("Read out of bounds")
        return self._data[start:stop]

    def pull_bytes(self, len: int) -> bytes:
        if len < 0:
            raise BufferReadError("negative length")
        last = self.pos + len
        if last > self.end:
            raise BufferReadError("Read out of bounds")
        data = self._data[self.pos : last]
        self.pos = last
        return data

    def pull_uint8(self) -> int:
        return self.pull_bytes(1)[0]

    def pull_uint16(self) -> int:
        return int.from_bytes(self.pull_bytes(2), "big")

    def pull_uint32(self) -> int:
        return int.from_bytes(self.pull_bytes(4), "big")

    def pull_uint64(self) -> int:
        return int.from_bytes(self.pull_bytes(8), "big")

    def pull_uint_var(self) -> int:
        first = self.pull_uint8()
        kind = first >> 6
        first = first & 0x3F
        if kind == 0:
            return first
        elif kind == 1:
            second = self.pull_uint8()
            return first << 8 | second
        elif kind == 2:
            second = int.from_bytes(self.pull_bytes(3))
            return first << 24 | second
        elif kind == 3:
            second = int.from_bytes(self.pull_bytes(7))
            return first << 56 | second

    def _need(self, amount: int):
        if amount < 0:
            raise BufferWriteError("negative amount")
        if self.pos + amount > self.end:
            raise BufferWriteError("Write out of bounds")

    def push_bytes(self, data: BufferData):
        l = len(data)
        last = self.pos + l
        self._need(l)
        self._data[self.pos : self.pos + l] = data
        self.pos = last

    def push_uint8(self, value: int):
        if value < 0 or value > 255:
            raise BufferWriteError("value is not a uint8")
        self._need(1)
        self._data[self.pos] = value
        self.pos += 1

    def push_uint16(self, value: int):
        if value < 0 or value > 65535:
            raise BufferWriteError("value is not a uint16")
        self.push_bytes(int.to_bytes(value, 2, "big"))

    def push_uint32(self, value: int):
        if value < 0 or value > 4294967295:
            raise BufferWriteError("value is not a uint32")
        self.push_bytes(int.to_bytes(value, 4, "big"))

    def push_uint64(self, value: int):
        if value < 0 or value > 18446744073709551615:
            raise BufferWriteError("value is not a uint64")
        self.push_bytes(int.to_bytes(value, 8, "big"))

    def push_uint_var(self, value: int):
        if value < 0:
            raise ValueError("Integer is negative")
        elif value <= 0x3F:
            self.push_uint8(value)
        elif value <= 0x3FFF:
            self.push_uint8((value >> 8) | 0x40)
            self.push_uint8(value & 0xFF)
        elif value <= 0x3FFFFFFF:
            self.push_uint8((value >> 24) | 0x80)
            self.push_uint8((value >> 16) & 0xFF)
            self.push_uint8((value >> 8) & 0xFF)
            self.push_uint8(value & 0xFF)
        elif value <= 0x3FFFFFFFFFFFFFFF:
            self.push_uint8((value >> 56) | 0xC0)
            self.push_uint8((value >> 48) & 0xFF)
            self.push_uint8((value >> 40) & 0xFF)
            self.push_uint8((value >> 32) & 0xFF)
            self.push_uint8((value >> 24) & 0xFF)
            self.push_uint8((value >> 16) & 0xFF)
            self.push_uint8((value >> 8) & 0xFF)
            self.push_uint8(value & 0xFF)
        else:
            raise ValueError("Integer is too big for a variable-length integer")
