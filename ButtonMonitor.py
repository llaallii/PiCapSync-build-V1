"""
This module defines the ButtonMonitor class for monitoring a physical button connected to a Raspberry Pi GPIO pin.
It uses a separate thread to continuously check the state of the button and triggers a callback function when the button is released.
The class includes debouncing logic to prevent false triggers and a method to clean up the GPIO resources when the monitoring is stopped.
"""

# Library Imports
import threading
import time
import RPi.GPIO as GPIO

class ButtonMonitor:
    def __init__(self, button_pin, start_scanning_callback, update_notification_callback):
        """
        Initializes the ButtonMonitor class.
        Args:
            button_pin (int): The GPIO pin number connected to the button.
            start_scanning_callback (function): A callback function to start scanning.
            update_notification_callback (function): A callback function for notifications.
        """
        self.button_pin = button_pin
        self.start_scanning_callback = start_scanning_callback
        self.update_notification_callback = update_notification_callback
        self.button_release_time = None
        self.stop_thread = threading.Event()
        self.debounce_time = 0.2  # seconds
        self.last_button_press_time = 0
        self.scanning_started = False  

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.update_notification_callback('GPIO setup complete.')

    def monitor_button(self):
        """
        Monitors the button state and triggers the start_scanning_callback when the button is released.
        """
        last_state = GPIO.input(self.button_pin)
        self.update_notification_callback("Monitoring button...")
        while not self.stop_thread.is_set() and not self.scanning_started:
            current_state = GPIO.input(self.button_pin)
            if current_state != last_state:
                last_state = current_state
                if current_state == GPIO.LOW:
                    self.scanning_started = False  # Reset the flag when the button is pressed
                else:
                    current_time = time.time()
                    if current_time - self.last_button_press_time > self.debounce_time:
                        self.button_release_time = current_time
                        self.start_scanning_callback()
                        self.scanning_started = True
                        self.stop_thread.set()  # Stop monitoring after button release
                        self.last_button_press_time = current_time
            time.sleep(0.01)  # Adjust this value based on responsiveness vs CPU usage
        self.update_notification_callback("Button monitoring stopped.")

    def gpio_cleanup(self):
        """
        Cleans up the GPIO resources.
        """
        GPIO.cleanup()
        self.update_notification_callback("GPIO cleanup complete.")
