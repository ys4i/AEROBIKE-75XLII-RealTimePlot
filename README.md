# AEROBIKE 75XLII Real-Time Plot

This project is designed to monitor and visualize heart rate and rotation speed data from a KONAMI AEROBIKE 75XLII in real-time using Python. The data is retrieved via a serial connection and plotted using Matplotlib.

## Note
The following document is the manual for III. It is not II.
The order in which commands are sent seems to be different between the actual device and the manual.
http://jp-chuoh.com/chuohsys/wp-content/uploads/2014/08/75xl3.pdf

## Project Structure

```
bike-realtime-plot
├── src
│   ├── main.py          # Entry point of the application
│   ├── serial_reader.py  # Handles serial communication
│   ├── plotter.py       # Responsible for plotting the data
│   └── utils.py         # Utility functions for data processing
├── requirements.txt      # Lists project dependencies
└── README.md             # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd bike-realtime-plot
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Connect your KONAMI AEROBIKE 75XLIII to your computer via the appropriate serial port.
2. Ensure the bike is in online mode.
3. Run the application:
   ```
   python src/main.py
   ```

4. The application will start retrieving data and display it in real-time.

### Mock mode (no aerobike device)

If you don't have the aerobike connected, you can run a synthetic data mode to verify the app flow and SQLite writes:

```
python src/main.py --mock
```

Quick, headless smoke check (runs for 5 seconds):

```
python src/main.py --mock --duration 5 --no-plot --no-wait
```

This creates `aerodb.sqlite` in the project root (schema: `schema.sql`).

## Dependencies

- Python 3.x
- Matplotlib
- PySerial

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
