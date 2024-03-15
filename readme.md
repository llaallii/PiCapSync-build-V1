# PiSyncApp

PiSyncApp is a Bluetooth Low Energy (BLE) scanning application designed for the cCap packet capturing and analysing packets BLE data from it and it's beaconing starting time after cCap get's triggered. It provides a graphical user interface (GUI) for monitoring and see BLE packets from cCap getting processed, including features such as starting and stopping testing, displaying packet information, and saving testing data to an Excel file. The application integrates with various backend components to handle scanning, button monitoring, packet processing, and data management.

## Features

- Monitor the state of a physical button connected to the Raspberry Pi GPIO.
- Start and stop cCap Packet Capture Testing with GUI control.
- Display real-time packet information and digital signatures and HMAC Keys.
- Process and validate BLE packets, including data integrity checks using HMAC.
- Save BLE beaconing data from cCap to an Excel file for further analysis.


## Components

The PiSyncApp consists of several modules:

- `PiSyncApp`: The main application module that provides the GUI and integrates other components.
- `PiSyncBackend`: Manages the overall synchronization process, including scanning, button monitoring, and packet processing.
- `ScannerBackend`: Handles the scanning of BLE devices and dumping of BLE packets.
- `ButtonMonitor`: Monitors the state of a physical lever button connected to the Raspberry Pi GPIO's.
- `PacketProcessor`: Processes BLE packets, performs data integrity checks, and updates attributes based on packet information.
- `database`: Provides functions for managing and storing device data, and saving data to an Excel file.

## Installation

1. Ensure you have Python 3 installed on your Raspberry Pi.
2. Install the required Python packages:

   ```bash
   pip3 install tkinter pandas openpyxl RPi.GPIO
