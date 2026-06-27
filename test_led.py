#!/usr/bin/env python3
"""阶段 1.5 关键验证：Joy-Con write 通路是否在 macOS 上生效。

判据（binary）：向 Joy-Con 发 Set Player Lights subcommand (0x04)，
如果 LED 灯亮 → write 通，subcommand 路线可行，进阶段 2。
灯不亮 → macOS 上 hidapi write 对 Joy-Con 无效，止损换方案。

Joy-Con Subcommand 协议：
- Output report ID 0x01 = Rumble + Subcommand
- 包: [0x01, counter, rumble×8, subcmd_id, subcmd_data...]
- counter 每包 +1 (mod 256)
- subcmd 0x04 Set Player Lights, data 1 字节: bit0=LED1 .. bit3=LED4
"""
import sys
import time
import hid

VENDOR = 0x057E
PRODUCTS = (0x2006, 0x2007)


def make_led_packet(counter, led_bits=0x0F):
    """构造 0x01 output report：开 LED。rumble 全 0（不震动）。"""
    pkt = bytearray(0x32)  # Joy-Con output report 固定 50 字节
    pkt[0] = 0x01          # report id: Rumble + Subcommand
    pkt[1] = counter & 0xFF
    # pkt[2..9] = rumble data，全 0 = 不震动
    pkt[10] = 0x04         # subcommand id: Set Player Lights
    pkt[11] = led_bits & 0x0F
    return bytes(pkt)


def find():
    return [d for d in hid.enumerate(VENDOR) if d["product_id"] in PRODUCTS]


def try_write(dev, counter, strip_report_id):
    """向 dev 写 LED 包。strip_report_id=True 时去掉首字节（mac hidapi 行为）。"""
    pkt = make_led_packet(counter, led_bits=0x0F)
    if strip_report_id:
        pkt = pkt[1:]  # hidapi 在 mac 上常自动加 report id，需去掉
    return dev.write(pkt)


def main():
    devs = find()
    if not devs:
        print("!! 没找到 Joy-Con")
        sys.exit(1)

    for info in devs:
        side = "L" if info["product_id"] == 0x2006 else "R"
        print(f"\n=== Joy-Con ({side}) ===")
        try:
            dev = hid.Device(path=info["path"])
        except Exception as e:
            print(f"!! 打开失败: {e}")
            continue

        # 两种 write 模式都试：去/不去 report-id 前缀
        for mode, strip in [("保留 report-id", False), ("去掉 report-id", True)]:
            for counter in range(3):
                try:
                    n = try_write(dev, counter, strip)
                    print(f"  [{mode}] write counter={counter} -> 返回 {n} 字节")
                except Exception as e:
                    print(f"  [{mode}] write counter={counter} 异常: {e}")
                time.sleep(0.1)
            time.sleep(0.3)

        # 留 2 秒观察灯是否亮
        print("  >> 现在观察 Joy-Con 上的 LED 灯是否亮起（2 秒）...")
        time.sleep(2)
        dev.close()
        print(f"  （Joy-Con {side} 测试结束）")

    print("\n==== 判据 ====")
    print("如果任一 Joy-Con 的 4 颗玩家灯亮起 → write 通路 OK，可进阶段 2。")
    print("灯全不亮 → macOS hidapi write 对 Joy-Con 无效，需换 IOKit 或 Pro Controller。")


if __name__ == "__main__":
    main()
