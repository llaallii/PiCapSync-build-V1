"""
This module defines a PacketProcessor class for processing Bluetooth Low Energy (BLE) packets. 
It updates various attributes based on the packet information, performs data integrity checks using HMAC, 
and updates average values for frequency and RSSI. The class also provides methods to convert hex strings 
to decimal and big endian formats, and to reset variables for a new device ID.
"""

# Library imports
import datetime
from database import device_id_entry, update_attribute
from secret_key import secret_key
import hmac
import hashlib

class PacketProcessor:
    def __init__(self, device_id, update_notification_callback, update_digital_signatures_callback, packet_queue):
        """
        Constructor for the PacketProcessor class.
        Args:
            device_id (str): The unique identifier for the device.
            update_notification_callback (function): A callback function for notifications.
            update_digital_signatures_callback (function): A callback function for digital signature updates.
            packet_queue (queue.Queue): A queue for storing packet information.
        """
        # Initialize class variables
        self.device_id = device_id
        self.update_notification_callback = update_notification_callback
        self.update_digital_signatures_callback = update_digital_signatures_callback
        self.packet_queue = packet_queue
        device_id_entry(self.device_id)  # Register the device ID in the database
        # Initialize packet processing variables
        self.packet_count = 0
        self.total_time_gap = 0.0
        self.average_gap = 0.0
        self.cCap_broadcasting_start_time = 0.0
        self.error_count = 0
        self.first_packet_time = None
        self.last_packet_time = None
        self.rssi = None
        self.average_rssi = None
        self.scannable_undirected_advertising_data = None
        self.digital_signature_scannable_undirected_advertising = None
        self.scan_response_data = None
        self.digital_signature_scan_response_data = None
        self.message = None
        self.digital_signature = None
        self.old_digital_signature_scan_response_data = None
        self.old_digital_signature_scannable_undirected_advertising = None
        self.data_integrity_check_success_count = 0
        self.scan_response_data_count = 0
        self.scannable_undirected_advertising_data_count = 0

    def process_packets(self, button_release_time):
        """
        Continuously processes packets from the packet queue. It updates various attributes based on the packet information,
        performs data integrity checks, and updates average values.
        Args:
            button_release_time (float): The time when the button was released, used to calculate the time gap.
        """
        while True:
            packet_info = self.packet_queue.get()  # Get the next packet from the queue
            self.update_company_name(packet_info)  # Update the company name attribute
            self.update_packet_count()  # Update the packet count
            self.update_first_packet_info(packet_info, button_release_time)  # Update information related to the first packet
            self.update_time_gap_and_rssi(packet_info)  # Update the time gap and RSSI
            self.update_advertising_data(packet_info)  # Update advertising data
            self.data_integrity_check()  # Perform data integrity check
            self.update_average_values()  # Update average frequency and RSSI

    def update_company_name(self, packet_info):
        """
        Updates the company name attribute based on the advertising data in the packet.
        Args:
            packet_info (dict): A dictionary containing packet information.
        """
        company_name = 'SHL' if packet_info['ad_data'][2:8] == 'ff130c' else 'Unknown'
        update_attribute(self.device_id, 'Company Name', company_name)

    def update_packet_count(self):
        """
        Increments the packet count and updates the corresponding attribute in the database.
        """
        self.packet_count += 1
        update_attribute(self.device_id, 'Packet Count', self.packet_count)

    def update_first_packet_info(self, packet_info, button_release_time):
        """
        Updates information related to the first packet received, such as the first packet time, RSSI, and time gap.
        Args:
            packet_info (dict): A dictionary containing packet information.
            button_release_time (float): The time when the button was released, used to calculate the time gap.
        """
        if self.packet_count == 1:
            self.first_packet_time = packet_info['timestamp']
            self.rssi = packet_info['rssi']
            self.cCap_broadcasting_start_time = self.first_packet_time - button_release_time
            update_attribute(self.device_id, 'First Packet Time', datetime.datetime.fromtimestamp(self.first_packet_time).strftime('%Y-%m-%d, %H:%M:%S'))
            update_attribute(self.device_id, 'Button Release Time', datetime.datetime.fromtimestamp(button_release_time).strftime('%Y-%m-%d, %H:%M:%S'))
            update_attribute(self.device_id, 'Time Gap', self.cCap_broadcasting_start_time)

    def update_time_gap_and_rssi(self, packet_info):
        """
        Updates the time gap between packets and the cumulative RSSI.
        Args:
            packet_info (dict): A dictionary containing packet information.
        """
        if self.packet_count > 1 and self.last_packet_time is not None:
            time_gap = packet_info['timestamp'] - self.last_packet_time
            self.total_time_gap += time_gap
            self.average_gap = self.total_time_gap / (self.packet_count - 1)
            self.rssi += packet_info['rssi']
        self.last_packet_time = packet_info['timestamp']

    def update_advertising_data(self, packet_info):
        """
        Updates the advertising data based on the event type in the packet.
        Args:
            packet_info (dict): A dictionary containing packet information.
        """
        if packet_info['event_type'] == 'Scannable undirected advertising':
            self.update_scannable_undirected_advertising_data(packet_info)
        elif packet_info['event_type'] == 'Scan Response':
            self.update_scan_response_data(packet_info)

    def update_scannable_undirected_advertising_data(self, packet_info):
        """
        Updates the scannable undirected advertising data and its digital signature.
        Args:
            packet_info (dict): A dictionary containing packet information.
        """
        if self.digital_signature_scannable_undirected_advertising is None or packet_info['ad_data'][32:62] != self.old_digital_signature_scannable_undirected_advertising:
            self.scannable_undirected_advertising_data_count += 1
            self.scannable_undirected_advertising_data = packet_info['ad_data'][8:32]
            self.digital_signature_scannable_undirected_advertising = packet_info['ad_data'][32:62]
            self.old_digital_signature_scannable_undirected_advertising = self.digital_signature_scannable_undirected_advertising

    def update_scan_response_data(self, packet_info):
        """
        Updates the scan response data and its digital signature.
        Args:
            packet_info (dict): A dictionary containing packet information.
        """
        if self.digital_signature_scan_response_data is None or packet_info['ad_data'][8:42] != self.old_digital_signature_scan_response_data:
            self.scan_response_data_count += 1
            self.scan_response_data = packet_info['ad_data'][42:62]
            self.digital_signature_scan_response_data = packet_info['ad_data'][8:42]
            self.old_digital_signature_scan_response_data = self.digital_signature_scan_response_data

    def data_integrity_check(self):
        """
        Performs a data integrity check using HMAC and the secret key. Updates the database with the result.
        """
        if self.scannable_undirected_advertising_data and self.scan_response_data and self.digital_signature_scannable_undirected_advertising and self.digital_signature_scan_response_data:
            self.digital_signature_little_indian = self.digital_signature_scannable_undirected_advertising + self.digital_signature_scan_response_data
            self.digital_signature = self.convert_little_endian_to_big_endian(self.digital_signature_little_indian)
            self.message = self.scannable_undirected_advertising_data + self.scan_response_data
            hmac_obj = hmac.new(bytes.fromhex(secret_key), bytes.fromhex(self.message), hashlib.sha256)
            hamc_computed_key = hmac_obj.hexdigest()
            if hamc_computed_key == self.digital_signature:
                self.data_integrity_check_success_count += 1
                update_attribute(self.device_id, 'Digital Signature Matched', True)
                update_attribute(self.device_id, 'Data Integrity Check Success Count', self.data_integrity_check_success_count)
            else:
                update_attribute(self.device_id, 'Digital Signature Matched', False)
            self.update_additional_attributes()
            self.update_digital_signatures_callback("_________________________________________________________")
            self.update_digital_signatures_callback(f"Digital Signature: {self.digital_signature}")
            self.update_digital_signatures_callback(f"HMAC: {hamc_computed_key}")
            self.update_digital_signatures_callback("_________________________________________________________")

    def check_error_codes(self, hex_code):
        # Convert hex string to integer
        code = int(hex_code, 16)

        errors = {
            0: "No error",
            1: "Real-time clock failure",
            2: "Cannot write log data to flash",
            4: "BLE-related failure",
            8: "HMAC key data integrity failure. The beacon data is invalid.",
            16: "Device ID data integrity failure. The Device ID is invalid.",
        }

        if code == 0:
            return 0, errors[0]

        error_messages = []
        for bit, message in errors.items():
            if code & bit:
                error_messages.append(message)

        if error_messages:
            return 1, ", ".join(error_messages)
        else:
            return 1, "Unknown error"

    def update_additional_attributes(self):
        """
        Updates additional attributes based on the message content.
        """
        if self.message[0:2] == '02':
            update_attribute(self.device_id, 'Payload Version', self.message[0:2])
        if self.message[4:6] == '00':
            update_attribute(self.device_id, 'Device Type', 'cCap')
        update_attribute(self.device_id, 'FW Version', self.hex_to_dotted_decimal(self.message[6:8]))
        update_attribute(self.device_id, 'Device ID', self.convert_little_endian_to_big_endian(self.message[8:24]))
        update_attribute(self.device_id, 'Time Reference', int(self.convert_little_endian_to_big_endian(self.message[24:30]), 16))
        update_attribute(self.device_id, 'Temperature', self.hex_to_decimal(self.message[32:34]))
        update_attribute(self.device_id, 'Event Ordinal Number', int(self.convert_little_endian_to_big_endian(self.message[34:38]), 16))
        error_code, error_message = self.check_error_codes(self.message[38:40])
        self.error_count += error_code
        update_attribute(self.device_id, 'Error Numbers', self.error_count)
        update_attribute(self.device_id, 'Error Message', error_message)

    def update_average_values(self):
        """
        Updates the average frequency and RSSI values in the database.
        """
        if self.packet_count > 1:
            update_attribute(self.device_id, 'Average Frequency', 1 / self.average_gap)
            self.average_rssi = self.rssi / self.packet_count
            update_attribute(self.device_id, 'Average RSSI', self.average_rssi)

    def convert_little_endian_to_big_endian(self, little_endian_hex):
        """
        Converts a hexadecimal string from little endian to big endian format.
        Args:
            little_endian_hex (str): A hex string in little endian format.
        Returns:
            str: The converted hex string in big endian format.
        """
        byte_chunks = [little_endian_hex[i:i+2] for i in range(0, len(little_endian_hex), 2)]
        big_endian_hex = ''.join(reversed(byte_chunks))
        return big_endian_hex

    def hex_to_decimal(self, hex_str):
        """
        Converts a hexadecimal string to a decimal number represented as a string.
        Args:
            hex_str (str): A hex string.
        Returns:
            str: The decimal number as a string.
        """
        return '.'.join(str(int(hex_str[i:i+2], 16)) for i in range(0, len(hex_str), 2))

    def hex_to_dotted_decimal(self, hex_str):
        """
        Converts a hexadecimal string to a dotted decimal format.
        Args:
            hex_str (str): A hex string.
        Returns:
            str: The dotted decimal representation of the number.
        """
        decimal_number = int(hex_str, 16)
        return '.'.join(str(digit) for digit in str(decimal_number))

    def update_device_id(self, new_device_id):
        """
        Updates the device ID and resets related variables.
        Args:
            new_device_id (str): The new device ID.
        """
        self.device_id = new_device_id.lower()
        device_id_entry(self.device_id)
        self.reset_variables()

    def reset_variables(self):
        """
        Resets variables related to packet processing.
        """
        self.packet_count = 0
        self.total_time_gap = 0.0
        self.average_gap = 0.0
        self.first_packet_time = None
        self.last_packet_time = None
        self.rssi = None
        self.average_rssi = None
