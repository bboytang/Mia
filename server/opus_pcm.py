"""Minimal libopus bindings for raw mono 60 ms WebSocket frames."""

import ctypes
import ctypes.util


def _library():
    name = ctypes.util.find_library("opus")
    if not name:
        raise RuntimeError("系统未安装 libopus")
    lib = ctypes.CDLL(name)
    lib.opus_encoder_create.argtypes = [
        ctypes.c_int32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)
    ]
    lib.opus_encoder_create.restype = ctypes.c_void_p
    lib.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
    lib.opus_encode.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int32,
    ]
    lib.opus_encode.restype = ctypes.c_int32
    lib.opus_decoder_create.argtypes = [
        ctypes.c_int32, ctypes.c_int, ctypes.POINTER(ctypes.c_int)
    ]
    lib.opus_decoder_create.restype = ctypes.c_void_p
    lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
    lib.opus_decode.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int16), ctypes.c_int, ctypes.c_int,
    ]
    lib.opus_decode.restype = ctypes.c_int
    return lib


class OpusEncoder:
    def __init__(self, sample_rate: int):
        self.lib = _library()
        self.samples_per_frame = sample_rate * 60 // 1_000
        error = ctypes.c_int()
        self.pointer = self.lib.opus_encoder_create(sample_rate, 1, 2048, ctypes.byref(error))
        if not self.pointer or error.value:
            raise RuntimeError(f"Opus 编码器初始化失败: {error.value}")

    def encode(self, pcm: bytes) -> bytes:
        if len(pcm) != self.samples_per_frame * 2:
            raise ValueError("PCM 帧必须为单声道 60 ms 16-bit")
        samples = (ctypes.c_int16 * self.samples_per_frame).from_buffer_copy(pcm)
        output = (ctypes.c_ubyte * 4_000)()
        length = self.lib.opus_encode(self.pointer, samples, self.samples_per_frame,
                                      output, len(output))
        if length <= 0:
            raise RuntimeError(f"Opus 编码失败: {length}")
        return bytes(output[:length])

    def close(self):
        if self.pointer:
            self.lib.opus_encoder_destroy(self.pointer)
            self.pointer = None


class OpusDecoder:
    def __init__(self, sample_rate: int):
        self.lib = _library()
        self.max_samples = sample_rate * 120 // 1_000
        error = ctypes.c_int()
        self.pointer = self.lib.opus_decoder_create(sample_rate, 1, ctypes.byref(error))
        if not self.pointer or error.value:
            raise RuntimeError(f"Opus 解码器初始化失败: {error.value}")

    def decode(self, packet: bytes) -> bytes:
        if not packet:
            raise ValueError("Opus 帧不能为空")
        source = (ctypes.c_ubyte * len(packet)).from_buffer_copy(packet)
        output = (ctypes.c_int16 * self.max_samples)()
        count = self.lib.opus_decode(self.pointer, source, len(packet),
                                     output, self.max_samples, 0)
        if count <= 0:
            raise RuntimeError(f"Opus 解码失败: {count}")
        return ctypes.string_at(output, count * 2)

    def close(self):
        if self.pointer:
            self.lib.opus_decoder_destroy(self.pointer)
            self.pointer = None
