import zlib
import uuid
import time


def busy_loop():
    start = time.time()
    for i in range(0, 50):
        text = ''.join([str(uuid.uuid4()) for _ in range(0, 10000)])
        text_encoded = text.encode('utf8')
        text_compressed = zlib.compress(text_encoded)
        zlib.decompress(text_compressed)
    end = time.time()
    delta = round(end - start, 2)
    print(f"Execution time: {delta}s")


if __name__ == '__main__':
    busy_loop()