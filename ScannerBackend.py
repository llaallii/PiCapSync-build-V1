"""
This module defines a ScannerBackend class for scanning and processing Bluetooth Low Energy (BLE) packets. 
It uses subprocesses to interact with system commands for scanning (hcitool) and dumping (hcidump) BLE packets. 
The class provides methods to start and stop scanning and dumping, process the dumped packets, and 
convert little endian hex strings to big endian. 
It also uses a queue to store processed packet information and a callback function to provide updates.
"""

# Library imports
import time
import queue
import subprocess
import datetime

class ScannerBackend:
    def __init__(self, update_notification_callback):
        """
       __init__(self, update_notification_callback)
        Constructor for the ScannerBackend class.
        args -> update_notification_callback: A callback function that receives update notifications.
        """
        # Initialize the class with a callback function for updates
        self.packet_queue = queue.Queue()  # Create a queue to hold packet data
        self.update_notification_callback = update_notification_callback  # Store the callback function
        self.scan_process = None  # Initialize scan process variable
        self.dump_process = None  # Initialize dump process variable
        self.mac_address = None  # Initialize MAC address variable

    def start_scan(self):
        """
        Starts the BLE scanning process using the hcitool command. 
        Notifies the callback function when scanning starts or if there's an error.
        """
        try:
            # Start a subprocess to scan for BLE devices, capturing duplicates
            self.scan_process = subprocess.Popen(['sudo', 'hcitool', 'lescan', '--duplicates'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.update_notification_callback("BLE scan started.")  # Notify that scanning has started
        except Exception as e:
            self.update_notification_callback(f"Error starting BLE scan: {e}")  # Notify if there's an error

    def stop_scan(self):
        """
        Stops the BLE scanning process and notifies the callback function when scanning stops or if there's an error.
        """
        try:
            if self.scan_process:
                self.scan_process.terminate()  # Terminate the scan process
                self.scan_process = None  # Reset the scan process variable
                self.update_notification_callback("BLE scan stopped.")  # Notify that scanning has stopped
        except Exception as e:
            self.update_notification_callback(f"Error stopping BLE scan: {e}")  # Notify if there's an error

    def start_dump(self):
        """
        Starts the packet dumping process using the hcidump command. 
        Notifies the callback function when dumping starts or if there's an err
        """
        try:
            # Start a subprocess to dump BLE packets
            self.dump_process = subprocess.Popen(['sudo', 'hcidump', '--raw'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.update_notification_callback("Packet dump started.")  # Notify that packet dumping has started
        except Exception as e:
            self.update_notification_callback(f"Error starting packet dump: {e}")  # Notify if there's an error

    def stop_dump(self):
        """
        Stops the packet dumping process. Notifies the callback function when dumping stops or if there's an error.
        """
        try:
            if self.dump_process:
                self.dump_process.terminate()  # Terminate the dump process
                self.dump_process = None  # Reset the dump process variable
                self.update_notification_callback("Packet dump stopped.")  # Notify that packet dumping has stopped
        except Exception as e:
            self.update_notification_callback(f"Error stopping packet dump: {e}")  # Notify if there's an error

    def get_dump(self, target_device_id, scanning):
        """
        Continuously reads and processes packets from the dump process while scanning is active.
        args -> target_device_id: The identifier of the target device to look for in the dumped packets.
                scanning: A boolean indicating whether scanning is still active.
        """
        try:
            packet_lines = []  # Initialize an empty list to hold packet lines
            # Continue reading lines from the dump process while scanning and the process is running
            while scanning and self.dump_process and self.dump_process.poll() is None:
                line = self.dump_process.stdout.readline()  # Read a line from the dump process
                if not line:
                    break  # Break the loop if no line is read
                raw_line = line.decode().strip()  # Decode and strip the line
                if raw_line.startswith('> 04 3E'):  # Check if the line indicates the start of a new packet
                    if packet_lines:
                        self.process_dump(target_device_id, packet_lines)  # Process the previous packet
                    packet_lines = [raw_line]  # Start a new packet
                else:
                    packet_lines.append(raw_line)  # Add the line to the current packet
            if packet_lines:
                self.process_dump(target_device_id, packet_lines)  # Process the last packet
        except Exception as e:
            self.update_notification_callback(f"Error getting packet dump: {e}")  # Notify if there's an error

    def process_dump(self, target_device_id, packet_lines):
        """
        Processes a single packet dump to extract information such as the MAC address, RSSI, event type, and advertising data. 
        If the packet is from the target device, 
        it puts the extracted information into the packet queue and notifies the callback function.

        args -> target_device_id: The identifier of the target device to compare with the packet's device ID.
                packet_lines: A list of lines representing the raw packet data.
        """
        raw_packet = ' '.join(packet_lines)  # Join the packet lines into a single string
        packet_parts = raw_packet.split(' ')  # Split the packet into parts
        mac_parts = packet_parts[8:14]  # Extract the MAC address parts
        # Check if the target device ID matches and the MAC address is not already set
        if target_device_id == self.convert_little_endian_to_big_endian(''.join(packet_parts[23:31]).lower()) and self.mac_address is None:
            target_mac_address = ':'.join(mac_parts[::-1]).lower()  # Convert the MAC address to the standard format
            self.mac_address = target_mac_address  # Set the MAC address
            timestamp = time.time()  # Get the current timestamp
            # Calculate the RSSI value
            rssi = int(packet_parts[-1], 16) - 256 if int(packet_parts[-1], 16) > 127 else int(packet_parts[-1], 16)
            event_type_code = packet_parts[6]  # Get the event type code
            # Map the event type code to a human-readable string
            event_type = {
                '00': 'Connectable undirected advertising',
                '01': 'Connectable directed advertising',
                '02': 'Scannable undirected advertising',
                '03': 'Non-connectable undirected advertising',
                '04': 'Scan Response'
            }.get(event_type_code, 'Unknown')
            length_data_section = int(packet_parts[15], 16) + 1  # Get the length of the data section
            ad_data = packet_parts[15:15 + length_data_section]  # Extract the advertising data
            ad_data_str = ''.join(ad_data).lower()  # Convert the advertising data to a string
            # Create a dictionary with the packet information
            packet_info = {
                'raw_packet': raw_packet,
                'event_type': event_type,
                'mac_address': self.mac_address,
                'ad_data': ad_data_str,
                'rssi': rssi,
                'timestamp': timestamp
            }
            self.packet_queue.put(packet_info)  # Put the packet information in the queue
            # Notify with various information about the target device
            self.update_notification_callback(f"Target device found {self.mac_address}")
            self.update_notification_callback(f"Event type: {event_type}")
            self.update_notification_callback(f"RSSI: {rssi}")
            self.update_notification_callback(f"Timestamp: {datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d, %H:%M:%S')}")
            self.update_notification_callback(f"Advertising data: {ad_data_str}")
            self.update_notification_callback(f"____________________________________________________")
        # Check if the packet is from the target device based on the MAC address
        elif self.mac_address is not None and ':'.join(mac_parts[::-1]).lower() == self.mac_address:
            timestamp = time.time()  # Get the current timestamp
            # Calculate the RSSI value
            rssi = int(packet_parts[-1], 16) - 256 if int(packet_parts[-1], 16) > 127 else int(packet_parts[-1], 16)
            event_type_code = packet_parts[6]  # Get the event type code
            # Map the event type code to a human-readable string
            event_type = {
                '00': 'Connectable undirected advertising',
                '01': 'Connectable directed advertising',
                '02': 'Scannable undirected advertising',
                '03': 'Non-connectable undirected advertising',
                '04': 'Scan Response'
            }.get(event_type_code, 'Unknown')
            length_data_section = int(packet_parts[15], 16) + 1  # Get the length of the data section
            ad_data = packet_parts[15:15 + length_data_section]  # Extract the advertising data
            ad_data_str = ''.join(ad_data).lower()  # Convert the advertising data to a string
            # Create a dictionary with the packet information
            packet_info = {
                'raw_packet': raw_packet,
                'event_type': event_type,
                'mac_address': self.mac_address,
                'ad_data': ad_data_str,
                'rssi': rssi,
                'timestamp': timestamp
            }
            self.packet_queue.put(packet_info)  # Put the packet information in the queue
            # Notify with various information about the target device
            self.update_notification_callback(f"Target device found {self.mac_address}")
            self.update_notification_callback(f"Event type: {event_type}")
            self.update_notification_callback(f"RSSI: {rssi}")
            self.update_notification_callback(f"Timestamp: {datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d, %H:%M:%S')}")
            self.update_notification_callback(f"Advertising data: {ad_data_str}")
            self.update_notification_callback(f"____________________________________________________")

    def convert_little_endian_to_big_endian(self, little_endian_hex):
        """
        Converts a hexadecimal string from little endian to big endian format.
        args -> little_endian_hex: A hex string in little endian format.
        """
        byte_chunks = [little_endian_hex[i:i+2] for i in range(0, len(little_endian_hex), 2)]
        big_endian_hex = ''.join(reversed(byte_chunks))
        return big_endian_hex
