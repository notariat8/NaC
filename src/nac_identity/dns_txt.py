from __future__ import annotations

import os
import random
import socket
import struct
from pathlib import Path


DNS_TYPE_TXT = 16
DNS_CLASS_IN = 1


def resolve_txt_records(record_name: str, *, nameserver: str | None = None, timeout: float = 3.0) -> dict:
    normalized_name = record_name.strip().lower().rstrip(".")
    query_id = random.SystemRandom().randrange(0, 65536)
    server = nameserver or _default_nameserver()
    query = build_dns_txt_query(normalized_name, query_id)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(query, (server, 53))
            response, _address = sock.recvfrom(4096)
        values = parse_dns_txt_response(response, expected_query_id=query_id)
    except TimeoutError:
        return {"name": normalized_name, "values": [], "resolver_error": "timeout", "nameserver": server}
    except OSError as exc:
        return {"name": normalized_name, "values": [], "resolver_error": f"os_error:{exc.__class__.__name__}", "nameserver": server}
    except ValueError as exc:
        return {"name": normalized_name, "values": [], "resolver_error": str(exc), "nameserver": server}

    return {
        "name": normalized_name,
        "values": values,
        "resolver_error": "" if values else "not_found",
        "nameserver": server,
    }


def build_dns_txt_query(record_name: str, query_id: int) -> bytes:
    header = struct.pack("!HHHHHH", query_id, 0x0100, 1, 0, 0, 0)
    question = _encode_dns_name(record_name) + struct.pack("!HH", DNS_TYPE_TXT, DNS_CLASS_IN)
    return header + question


def parse_dns_txt_response(response: bytes, *, expected_query_id: int) -> list[str]:
    if len(response) < 12:
        raise ValueError("dns_response_too_short")

    query_id, flags, qdcount, ancount, _nscount, _arcount = struct.unpack("!HHHHHH", response[:12])
    if query_id != expected_query_id:
        raise ValueError("dns_query_id_mismatch")

    rcode = flags & 0x000F
    if rcode == 3:
        return []
    if rcode != 0:
        raise ValueError(f"dns_rcode_{rcode}")

    offset = 12
    question_names: list[str] = []
    for _index in range(qdcount):
        question_name, offset = _read_dns_name(response, offset)
        question_names.append(question_name)
        offset += 4

    expected_owner = question_names[0] if question_names else ""

    values: list[str] = []
    for _index in range(ancount):
        answer_owner, offset = _read_dns_name(response, offset)
        if offset + 10 > len(response):
            raise ValueError("dns_answer_too_short")
        record_type, record_class, _ttl, data_length = struct.unpack("!HHIH", response[offset : offset + 10])
        offset += 10
        if offset + data_length > len(response):
            raise ValueError("dns_rdata_truncated")
        data = response[offset : offset + data_length]
        offset += data_length

        if answer_owner == expected_owner and record_type == DNS_TYPE_TXT and record_class == DNS_CLASS_IN:
            values.extend(_decode_txt_chunks(data))

    return values


def _encode_dns_name(record_name: str) -> bytes:
    labels = record_name.strip().rstrip(".").split(".")
    encoded = bytearray()
    for label in labels:
        raw = label.encode("idna")
        if not raw or len(raw) > 63:
            raise ValueError("dns_label_invalid")
        encoded.append(len(raw))
        encoded.extend(raw)
    encoded.append(0)
    return bytes(encoded)


def _skip_dns_name(message: bytes, offset: int) -> int:
    _name, new_offset = _read_dns_name(message, offset)
    return new_offset


def _read_dns_name(message: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    final_offset = offset
    jumped = False
    seen_offsets: set[int] = set()

    while True:
        if offset >= len(message):
            raise ValueError("dns_name_out_of_bounds")
        if offset in seen_offsets:
            raise ValueError("dns_name_pointer_loop")
        seen_offsets.add(offset)
        length = message[offset]
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(message):
                raise ValueError("dns_pointer_out_of_bounds")
            pointer = ((length & 0x3F) << 8) | message[offset + 1]
            if not jumped:
                final_offset = offset + 2
            offset = pointer
            jumped = True
            continue
        if length == 0:
            if not jumped:
                final_offset = offset + 1
            return ".".join(labels), final_offset
        offset += 1
        if offset + length > len(message):
            raise ValueError("dns_name_label_truncated")
        labels.append(message[offset : offset + length].decode("idna").lower())
        offset += length


def _decode_txt_chunks(data: bytes) -> list[str]:
    values: list[str] = []
    offset = 0
    chunks: list[str] = []
    while offset < len(data):
        length = data[offset]
        offset += 1
        chunk = data[offset : offset + length]
        if len(chunk) != length:
            raise ValueError("dns_txt_chunk_truncated")
        chunks.append(chunk.decode("utf-8", errors="replace"))
        offset += length
    if chunks:
        values.append("".join(chunks))
    return values


def _default_nameserver() -> str:
    resolv_conf = Path("/etc/resolv.conf")
    if resolv_conf.is_file():
        for line in resolv_conf.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                return parts[1]
    return os.environ.get("NAC_DNS_NAMESERVER", "1.1.1.1")
