#!/usr/bin/env python3
"""阶段 1 happy-path：验证能打开 Joy-Con 并读到 HID 报文。

只做一件事：连上左/右 Joy-Con，读若干帧，把原始字节打出来。
不解析、不映射、不模拟按键。通了再进阶段 2。

依赖：hidapi 官方 Python 绑定（pip install hidapi，import 名仍是 hid）。
"""
import sys
import hid

VENDOR = 0x057E
PRODUCT_L = 0x2006  # Joy-Con (L)
PRODUCT_R = 0x2007  # Joy-Con (R)

# Joy-Con HID 标准输入报告长度 49 字节
READ_LEN = 49


def find_devices():
    """枚举所有任天堂 Joy-Con HID 设备（enumerate 返回 dict 列表）。"""
    return [d for d in hid.enumerate(VENDOR)
            if d["product_id"] in (PRODUCT_L, PRODUCT_R)]


def probe(device_info, frames=20):
    """打开单个设备，读 N 帧原始报文打印。"""
    pid = device_info["product_id"]
    side = "L" if pid == PRODUCT_L else "R"
    print(f"\n=== 打开 Joy-Con ({side}) ===")
    print(f"path: {device_info['path']}")

    try:
        dev = hid.Device(path=device_info["path"])
        prod = getattr(dev, "product", None) or device_info.get("product_string", "")
        print(f"打开成功: product={prod!r}")
        print(f"读 {frames} 帧原始报文（每帧 {READ_LEN} 字节）—— 期间请按几下 Joy-Con 按键：")
        for i in range(frames):
            data = dev.read(READ_LEN, timeout=2000)
            if not data:
                print(f"  [{i:02d}] (超时无数据)")
                continue
            hex_str = " ".join(f"{b:02X}" for b in data)
            rid = data[0] if len(data) > 0 else 0
            btns = data[3:6] if len(data) >= 6 else b""
            print(f"  [{i:02d}] rid=0x{rid:02X} btns={bytes(btns).hex(' ').upper()} | {hex_str}")
        print(f"=== Joy-Con ({side}) 读帧完成 ===")
        dev.close()
        return True
    except Exception as e:
        print(f"!! 打开/读取失败: {type(e).__name__}: {e}")
        return False


def main():
    devices = find_devices()
    if not devices:
        print("!! 没找到任天堂 Joy-Con 设备。请确认蓝牙已连接。")
        sys.exit(1)

    print(f"找到 {len(devices)} 个 Joy-Con 设备。")
    ok = 0
    for d in devices:
        if probe(d):
            ok += 1
    print(f"\n==== 结果: {ok}/{len(devices)} 个设备读帧成功 ====")
    sys.exit(0 if ok == len(devices) else 1)


if __name__ == "__main__":
    main()
