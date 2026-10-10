"""Native IPv4 adapter enumeration without DNS or internet probes."""

import ipaddress
import socket
import sys


def _windows_addresses():
    import ctypes as ct

    class SocketAddress(ct.Structure):
        _fields_ = [("pointer", ct.c_void_p), ("length", ct.c_int)]

    class Unicast(ct.Structure):
        pass

    Unicast._fields_ = [("alignment", ct.c_uint64), ("next", ct.POINTER(Unicast)),
                       ("address", SocketAddress)]

    class Adapter(ct.Structure):
        pass

    # Prefix of IP_ADAPTER_ADDRESSES_LH through OperStatus; later fields unused.
    Adapter._fields_ = [("alignment", ct.c_uint64), ("next", ct.POINTER(Adapter)),
                       ("name", ct.c_char_p), ("unicast", ct.POINTER(Unicast)),
                       ("anycast", ct.c_void_p), ("multicast", ct.c_void_p), ("dns", ct.c_void_p),
                       ("suffix", ct.c_void_p), ("description", ct.c_void_p), ("friendly", ct.c_void_p),
                       ("physical", ct.c_ubyte * 8), ("physical_length", ct.c_uint32),
                       ("flags", ct.c_uint32), ("mtu", ct.c_uint32), ("type", ct.c_uint32),
                       ("status", ct.c_int)]
    query = ct.WinDLL("iphlpapi").GetAdaptersAddresses
    query.argtypes = (ct.c_uint32, ct.c_uint32, ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_uint32))
    query.restype = ct.c_uint32
    size = ct.c_uint32(15000)
    for _ in range(3):
        buffer = ct.create_string_buffer(size.value)
        result = query(socket.AF_INET, 2 | 4 | 8, None, buffer, ct.byref(size))
        if result == 111:  # ERROR_BUFFER_OVERFLOW: adapters changed during enumeration.
            continue
        if result == 232:  # ERROR_NO_DATA
            return []
        if result:
            raise OSError(result, "Could not enumerate local IPv4 adapters.")
        addresses = []
        adapter = ct.cast(buffer, ct.POINTER(Adapter))
        while adapter:
            if adapter.contents.status == 1:  # IfOperStatusUp
                unicast = adapter.contents.unicast
                while unicast:
                    address = unicast.contents.address
                    if address.pointer and address.length >= 8:
                        raw = ct.string_at(address.pointer, 8)
                        if int.from_bytes(raw[:2], "little") == socket.AF_INET:
                            addresses.append(socket.inet_ntoa(raw[4:8]))
                    unicast = unicast.contents.next
            adapter = adapter.contents.next
        return addresses
    raise OSError("Local IPv4 adapter enumeration buffer kept changing.")


def _linux_addresses():
    import fcntl
    import struct

    addresses = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        for _, name in socket.if_nameindex():
            request = struct.pack("256s", name.encode()[:15])
            try:
                flags = fcntl.ioctl(probe.fileno(), 0x8913, request)  # SIOCGIFFLAGS
                if struct.unpack_from("H", flags, 16)[0] & 1:  # IFF_UP
                    result = fcntl.ioctl(probe.fileno(), 0x8915, request)  # SIOCGIFADDR
                    addresses.append(socket.inet_ntoa(result[20:24]))
            except OSError:
                continue  # Interface has no IPv4 address or disappeared.
    return addresses


def network_addresses():
    try:
        addresses = _windows_addresses() if sys.platform == "win32" else _linux_addresses() if sys.platform.startswith("linux") else []
    except OSError:
        addresses = []
    # Preserve native route/interface ordering within each address category.
    addresses = list(dict.fromkeys(value for value in addresses
                     if not ipaddress.ip_address(value).is_loopback
                     and not ipaddress.ip_address(value).is_unspecified))
    return sorted(addresses, key=lambda value: (ipaddress.ip_address(value).is_link_local,
                                               not ipaddress.ip_address(value).is_private)) or ["127.0.0.1"]
