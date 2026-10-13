from __future__ import annotations

import os
from typing import List

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config.settings import LEAF_TILT_DEGREES


def encrypt_text(text: str) -> tuple[bytes, bytes, bytes]:
    if text is None or not text:
        raise ValueError("Text input must not be empty.")

    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, text.encode("utf-8"), None)
    return key, nonce, ciphertext


def bytes_to_bits(data: bytes) -> List[int]:
    return [(byte >> bit_index) & 1 for byte in data for bit_index in range(7, -1, -1)]


def text_to_bits(text: str) -> List[int]:
    if text is None:
        raise ValueError("Text input is empty.")
    return bytes_to_bits(text.encode("utf-8"))


def bits_to_byte_groups(bits: List[int], group_size: int = 8) -> List[List[int]]:
    if group_size <= 0:
        raise ValueError("Bit group size must be a positive integer.")
    if any(bit not in (0, 1) for bit in bits):
        raise ValueError("Binary input may contain only 0 and 1.")
    if len(bits) == 0:
        return []
    if len(bits) % group_size != 0:
        bits = bits + [0] * (group_size - (len(bits) % group_size))
    return [bits[index : index + group_size] for index in range(0, len(bits), group_size)]


def direction_from_bit(bit: int) -> str:
    if bit not in (0, 1):
        raise ValueError(f"Leaf mapping expects a bit value of 0 or 1, not {bit!r}.")
    return "LEFT" if bit == 0 else "RIGHT"


def angle_for_bit(bit: int) -> float:
    if bit not in (0, 1):
        raise ValueError(f"Leaf mapping expects a bit value of 0 or 1, not {bit!r}.")
    return -LEAF_TILT_DEGREES if bit == 1 else LEAF_TILT_DEGREES


def map_bits_to_leaf_states(bits: List[int]) -> List[float]:
    if len(bits) != 8:
        raise ValueError(f"An 8-bit frame requires exactly 8 bits. Received {len(bits)} bits.")
    return [angle_for_bit(bit) for bit in bits]
