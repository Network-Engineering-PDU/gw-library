import time
import sys

from ttgwlib.ota_helper import OtaType

# Bootloader (0) | App (1) | SD +  APP (2)

def start_ota(ota_file, ota_time, gt, nodes, ota_type):
    data = gt.ota_helper.load_ota(ota_file, ota_type)

    ota_time = int(ota_time)

    print(data)

    start_address = data["start_address"]
    size = data["size"]
    print(f"Start address: 0x{start_address:08x}")
    print(f"Size: {size}")

    for node in nodes:
        gt.models.ota.update_notify(node, ota_type, data["major"],
            data["minor"], data["fix"], data["sd_version"], size, ota_time)

    while time.monotonic() < ota_time + 3:
        remaining = ota_time - time.monotonic()
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining.".format(int(remaining)))
        sys.stdout.flush()
        time.sleep(0.25)

    gt.ota_helper.send_update()

    print("Done")

def ota_relay_store(ota_file, ota_time, gt, nodes, ota_type):
    data = gt.ota_helper.load_ota(ota_file, ota_type)
    ota_time = int(ota_time)

    print(data)

    start_address = data["start_address"]
    size = data["size"]
    print(f"Start address: 0x{start_address:08x}")
    print(f"Size: {size}")

    for node in nodes:
        gt.models.ota.relay_update(node, size, ota_time)

    while time.monotonic() < ota_time + 3:
        remaining = ota_time - time.monotonic()
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining.".format(int(remaining)))
        sys.stdout.flush()
        time.sleep(0.25)

    gt.ota_helper.send_update()

    print("Done")

def ota_relay_send(ota_file, ota_time, gt, relays, nodes, ota_type):
    data = gt.ota_helper.load_ota(ota_file, ota_type, copy=False)
    ota_time = int(ota_time)

    print(data)

    start_address = data["start_address"]
    size = data["size"]
    print(f"Start address: 0x{start_address:08x}")
    print(f"Size: {size}")


    for relay in relays:
        gt.models.ota.relay_update_task(relay, ota_time+2)

    for node in nodes:
        gt.models.ota.update_notify(node, ota_type, data["major"],
            data["minor"], data["fix"], data["sd_version"], size, ota_time)

    while time.monotonic() < ota_time + 3:
        remaining = ota_time - time.monotonic()
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining.".format(int(remaining)))
        sys.stdout.flush()
        time.sleep(0.25)

    #gt.ota_helper.send_update()
    print("Done")
