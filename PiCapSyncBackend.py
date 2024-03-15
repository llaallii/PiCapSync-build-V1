"""
This module defines the PiSyncBackend class, which is responsible for managing the overall synchronization process
between a Raspberry Pi and Bluetooth Low Energy (BLE) devices. It integrates the functionality of the ScannerBackend,
ButtonMonitor, and PacketProcessor classes to handle the scanning, button monitoring, and packet processing tasks.
"""

# Libray imports
import threading
from ScannerBackend import ScannerBackend
from ButtonMonitor import ButtonMonitor
from PacketProcessor import PacketProcessor
from database import get_data
import time

class PiSyncBackend:
    def __init__(self, update_gui_callback, update_button_callback, update_notification_callback, update_digital_signatures_callback, device_id=None, interface='hci0'):
        """
        Initializes the PiSyncBackend class.
        Args:
            update_gui_callback (function): A callback function to update the GUI.
            update_button_callback (function): A callback function to update the button state.
            update_notification_callback (function): A callback function for notifications.
            update_digital_signatures_callback (function): A callback function for digital signature updates.
            device_id (str, optional): The device ID. Defaults to None.
            interface (str, optional): The Bluetooth interface. Defaults to 'hci0'.
        """
        self.update_gui_callback = update_gui_callback
        self.update_button_callback = update_button_callback
        self.update_notification_callback = update_notification_callback
        self.update_digital_signatures_callback = update_digital_signatures_callback
        self.device_id = device_id.lower() if device_id else None
        self.interface = interface
        self.scanning = False
        self.scan_started = False 
        self.packet_processor_thread = None
        self.check_packet_count_thread = None
        self.get_dump_thread = None
        self.scanner_backend = ScannerBackend(self.update_notification_callback)
        self.button_monitor = ButtonMonitor(17, self.start_scanning, self.update_notification_callback)
        self.packet_processor = PacketProcessor(self.device_id, self.update_notification_callback, self.update_digital_signatures_callback, self.scanner_backend.packet_queue)
        self.monitoring_started = False
        self.start_monitoring()  # Start monitoring the button in a separate thread

    def start_monitoring(self):
        """
        Starts monitoring the button in a separate thread.
        """
        if not self.monitoring_started:
            threading.Thread(target=self.button_monitor.monitor_button, daemon=True).start()
            self.monitoring_started = True

    def start_scanning(self):
        """
        Starts the scanning process in separate threads for scanning, packet processing, and checking packet count.
        """
        try:
            if not self.scanning and not self.scan_started:
                while self.button_monitor.button_release_time is None:
                    time.sleep(0.01)  # Check every 100 milliseconds

                # Start scanning
                self.scanning = True
                self.scanner_backend.start_scan()
                self.scanner_backend.start_dump()
                self.get_dump_thread = threading.Thread(target=self.scanner_backend.get_dump, args=(self.device_id, self.scanning))
                self.get_dump_thread.start()
                self.packet_processor_thread = threading.Thread(target=self.packet_processor.process_packets,
                                args=(self.button_monitor.button_release_time,))
                self.check_packet_count_thread = threading.Thread(target=self.check_packet_count)
                self.packet_processor_thread.start()
                self.check_packet_count_thread.start()
                self.scan_started = True
        except Exception as e:
            print(f"Error starting scanning: {e}")

    def stop_scanning(self):
        """
        Stops the scanning process and updates the button state.
        """
        self.scanning = False
        self.scanner_backend.stop_dump()
        self.scanner_backend.stop_scan()
        self.scan_started = False
        self.update_button_callback(text = "Testing Finished", bg = '#000000') 

    def toggle_scanning(self, state):
        """
        Toggles the scanning state based on the given state.
        Args:
            state (bool): The desired state for scanning.
        """
        if state:
            pass
        else:
            self.stop_scanning()

    def update_device_id(self, new_device_id):
        """
        Updates the device ID and resets related variables.
        Args:
            new_device_id (str): The new device ID.
        """
        if new_device_id != self.device_id:
            self.device_id = new_device_id.lower()
            self.packet_processor.update_device_id(self.device_id)

    def check_packet_count(self):
        """
        Checks the packet count and updates the frontend or stops scanning accordingly.
        """
        while self.scanning:
            if self.packet_processor.packet_count <= 40:
                self.update_frontend()
            if self.packet_processor.packet_count > 40:
                self.stop_scanning()
                break
            
    def update_frontend(self):
        """
        Updates the frontend with the latest data for the device ID.
        """
        data = get_data(self.device_id)
        self.update_gui_callback(data)

    def closing_all(self):
        """
        Cleans up resources and stops scanning when closing the application.
        """
        try:
            if self.scanning:
                self.stop_scanning()
            self.button_monitor.gpio_cleanup()
            self.update_notification_callback("Cleaned up resources.")
        except Exception as e:
            self.update_notification_callback(f"Error during closing: {e}")
