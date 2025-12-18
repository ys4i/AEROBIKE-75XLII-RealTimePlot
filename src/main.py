import argparse
import math
import serial
import time
from pathlib import Path
from db import AerobikeDB
from serial_reader import read_data, set_load

ENQ = b'\x05'
ACK = b'\x06'
EOT = b'\x04'   


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KONAMI AEROBIKE 75XLIII real-time monitor")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without the aerobike device; generates synthetic heart rate / cadence data.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Seconds to run in mock mode (0 = until Ctrl+C).",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Disable matplotlib plotting (useful for headless/CI).",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for Enter key on exit.",
    )
    parser.add_argument("--subject-code", default="S001", help="Subject code (e.g. S001).")
    parser.add_argument("--load-watt", type=int, default=100, help="Load watt (10-400).")
    parser.add_argument("--serial-port", default="/dev/ttyUSB0", help="Serial port path.")
    parser.add_argument("--baud-rate", type=int, default=9600, help="Serial baud rate.")
    parser.add_argument("--timeout", type=float, default=3.0, help="Serial read timeout (seconds).")
    return parser


def _mock_read_data(elapsed_s: float):
    heart_rate = 75 + 12 * math.sin(elapsed_s / 6.0) + 3 * math.sin(elapsed_s / 1.5)
    rotation_speed = 80 + 18 * math.sin(elapsed_s / 4.0) + 4 * math.sin(elapsed_s / 1.2)
    return int(round(heart_rate)), int(round(rotation_speed))


def main():
    args = _build_arg_parser().parse_args()

    SERIAL_PORT = args.serial_port
    BAUD_RATE = args.baud_rate
    TIMEOUT = args.timeout
    SUBJECT_CODE = args.subject_code
    LOAD_WATT = args.load_watt

    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "aerodb.sqlite"
    schema_path = project_root / "schema.sql"

    plot_enabled = not args.no_plot
    if plot_enabled:
        import matplotlib.pyplot as plt

        plt.ion()
        fig, ax = plt.subplots()
        ax.set_title("Real-Time Heart Rate and Rotation Speed")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Values")
        heart_rate_line, = ax.plot([], [], label="Heart Rate (bpm)", color="r")
        rotation_speed_line, = ax.plot([], [], label="Rotation Speed (rpm)", color="b")
        ax.legend()

    times = []
    heart_rates = []
    rotation_speeds = []

    ser = None
    db = None
    session_id = None
    t0 = None
    write_count = 0
    try:
        print(f"--- KONAMI AEROBIKE 75XLIII Real-time Monitor (Matplotlib) ---")
        print(f"SQLite DB path: {db_path}")
        if args.mock:
            print("*** MOCK MODE: no aerobike device / no serial port ***")
            db = AerobikeDB(str(db_path))
            db.init_schema(str(schema_path))
            member_id = db.get_or_create_member(SUBJECT_CODE)
            session_id = db.start_session(member_id, float(LOAD_WATT), memo="mock")
            print(f"Session started: session_id={session_id} subject_code={SUBJECT_CODE} load_watt={LOAD_WATT}")
            t0 = time.perf_counter()
            write_count = 0
        else:
            print(f"Attempting to open serial port: {SERIAL_PORT}")
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=TIMEOUT,
            )
            print(f"Serial port {SERIAL_PORT} opened successfully.")

            print("Sending ENQ to connect...")
            ser.flushInput()
            ser.write(ENQ)
            response_enq = ser.read(1)

            if response_enq == ACK:
                print("Connection established (received ACK). Sending ACK back...")
                ser.write(ACK)
                time.sleep(0.5)  # 0.5秒～1秒にしてみる
                if set_load(ser, LOAD_WATT):
                    print(f"Load set to {LOAD_WATT}W.")
                else:
                    print("Failed to set load.")

                db = AerobikeDB(str(db_path))
                db.init_schema(str(schema_path))
                member_id = db.get_or_create_member(SUBJECT_CODE)
                session_id = db.start_session(member_id, float(LOAD_WATT), memo="realtime")
                print(f"Session started: session_id={session_id} subject_code={SUBJECT_CODE} load_watt={LOAD_WATT}")
                t0 = time.perf_counter()
                write_count = 0
            else:
                print(
                    f"Failed to establish connection. Expected ACK, got: {response_enq} (hex: {response_enq.hex()})"
                )
                print("Please ensure the aerobike is in online mode (START/STOP key + Power ON).")
                print("Also, check your SERIAL_PORT setting.")
                if not args.no_wait:
                    input("\nPress Enter to exit...")
                return

        print("\n--- READY FOR DATA ACQUISITION ---")
        if not args.mock:
            print("*** IMPORTANT: Please ensure the aerobike is in ONLINE mode and start pedaling NOW! ***")
        print("*** Also ensure a heart rate sensor is connected and active if testing heart rate. ***")
        print("\nPress Ctrl+C to stop the monitor.")
        time.sleep(2)

        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if args.mock:
                heart_rate, rotation_speed = _mock_read_data(elapsed_time)
            else:
                heart_rate, rotation_speed = read_data(ser)

            # コマンドラインに表示
            print(f"Time: {elapsed_time:.1f}s | Heart Rate: {heart_rate} bpm | Rotation Speed: {rotation_speed} rpm", end='\r')

            if db is not None and session_id is not None and t0 is not None:
                t_ms = int((time.perf_counter() - t0) * 1000)
                db.insert_sample(
                    session_id,
                    t_ms,
                    hr_bpm=heart_rate,
                    cadence_rpm=rotation_speed,
                )
                write_count += 1
                if write_count % 10 == 0:
                    db.commit()

            if heart_rate is not None:
                heart_rates.append(heart_rate)
                times.append(elapsed_time)

            if rotation_speed is not None:
                rotation_speeds.append(rotation_speed)

            if plot_enabled:
                heart_rate_line.set_data(times, heart_rates)
                rotation_speed_line.set_data(times, rotation_speeds)

                ax.relim()
                ax.autoscale_view()
                plt.pause(0.1)
            else:
                time.sleep(0.1)

            if args.mock and args.duration > 0 and elapsed_time >= args.duration:
                break

    except KeyboardInterrupt:
        print("\n--- Stopping data acquisition. ---")
    except Exception as e:
        import sys
        sys.stderr.write(f"\nAn unexpected error occurred: {e}\n")
    finally:
        if db is not None:
            try:
                db.commit()
                if session_id is not None:
                    db.end_session(session_id)
                    print(f"\nSession ended: session_id={session_id}")
            finally:
                db.close()

        if ser and ser.is_open:
            print("Sending EOT to disconnect...")
            ser.flushInput()
            ser.write(EOT)
            response_eot = ser.read(1)
            if response_eot == EOT:
                print("Disconnected (received EOT).")
            elif response_eot == ACK: 
                print(f"Disconnected (received ACK {response_eot.hex()} instead of EOT).")
            else:
                print(f"Did not receive EOT response. Expected EOT, got: {response_eot} (hex: {response_eot.hex()})")
            ser.close()
            print("Serial port closed.")
        if args.no_wait:
            print("Monitor stopped.")
        else:
            print("Monitor stopped. Press Enter to close terminal...")
            input()

if __name__ == "__main__":
    main()
