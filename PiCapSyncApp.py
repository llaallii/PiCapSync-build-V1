import tkinter as tk
from PiCapSyncBackend import PiSyncBackend
from database import save_data_to_excel

class PiSyncApp:
    def __init__(self, root):
        """
        Initializes the PiSyncApp class.
        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.root = root
        root.title("BLE Scanner")
        root.geometry("1000x1200")

        # Styling
        root.configure(bg="#34495E")

        # Main frame
        main_frame = tk.Frame(root, bg="#34495E")
        main_frame.pack(padx=10, pady=10, expand=True, fill="both")

        # Device ID Entry Frame
        device_id_frame = tk.Frame(main_frame, bg="#34495E")
        device_id_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        tk.Label(device_id_frame, text="Enter Device ID:", bg="#34495E", fg="white", font=("Helvetica", 12)).pack(side="left", padx=(10, 0))
        self.device_id_entry = tk.Entry(device_id_frame, width=30)
        self.device_id_entry.pack(side="left", padx=(10, 0))
        self.device_id_entry.insert(0, '120D0082421E0127')

        # Data Sections Frame
        data_frame = tk.Frame(main_frame, bg="#34495E")
        data_frame.grid(row=1, column=0, columnspan=4, sticky="ew")
        self.labels = [
            "Packet Count", "Company Name", "Time Gap", "Average RSSI",
            "Average Frequency", "Button Release Time", "First Packet Time",
            "Payload Version", "Device ID", "FW Version", "Device Type",
            "Time Reference", "Temperature", "Event Ordinal Number",
            "Data Integrity Check Success Count", "Digital Signature Matched",
            "Error Numbers", "Error Message"
        ]
        self.value_entries = {}
        for i, label_text in enumerate(self.labels):
            label_widget = tk.Label(data_frame, text=f"{label_text}:", bg="#34495E", fg="white", font=("Helvetica", 10))
            label_widget.grid(row=i, column=0, sticky="e", padx=10, pady=5)
            value_entry = tk.Entry(data_frame, bg="#D6DBDF", fg="black", font=("Helvetica", 10), width=25)
            value_entry.grid(row=i, column=1, sticky="w", padx=10, pady=5)
            value_entry.insert(0, "N/A")
            value_entry.config(state="readonly")
            self.value_entries[label_text] = value_entry

        # Start/Stop Testing Buttons
        self.testing_button = tk.Button(main_frame, text="Start Testing", command=self.toggle_testing, bg="#2ECC71", fg="white")
        self.testing_button.grid(row=2, column=0, columnspan=4, pady=10, sticky="ew")

        # Save Data Button
        self.save_data_button = tk.Button(main_frame, text="Save Data", command=lambda: save_data_to_excel(self.device_id_entry.get(), self.update_notification), bg="#3498DB", fg="white")
        self.save_data_button.grid(row=3, column=0, columnspan=4, pady=10, sticky="ew")

        # Reset Button
        self.reset_button = tk.Button(main_frame, text="Reset", command=self.reset_app, bg="#E74C3C", fg="white")
        self.reset_button.grid(row=4, column=0, columnspan=4, pady=10, sticky="ew")

        # Packet Information Panel
        packet_info_frame = tk.LabelFrame(main_frame, text="Notification and Packet Information", bg="#34495E", fg="white", font=("Helvetica", 12), width=500, height=400)
        packet_info_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="nsew")
        packet_info_frame.grid_propagate(False)
        self.packet_info_text = tk.Text(packet_info_frame, bg="#34495E", fg="white", font=("Helvetica", 10), wrap="word", state="disabled", height=20, width=60)
        self.packet_info_text.pack(expand=True, fill="both")
        packet_info_scrollbar = tk.Scrollbar(packet_info_frame, command=self.packet_info_text.yview)
        self.packet_info_text.config(yscrollcommand=packet_info_scrollbar.set)
        packet_info_scrollbar.pack(side="right", fill="y")

        # Digital Signatures and HMAC Panel
        digital_signatures_frame = tk.LabelFrame(main_frame, text="Digital Signatures and HMAC", bg="#34495E", fg="white", font=("Helvetica", 12), width=500, height=400)
        digital_signatures_frame.grid(row=5, column=2, columnspan=2, pady=10, sticky="nsew")
        digital_signatures_frame.grid_propagate(False)
        self.digital_signatures_text = tk.Text(digital_signatures_frame, bg="#34495E", fg="white", font=("Helvetica", 10), wrap="word", state="disabled", height=20, width=60)
        self.digital_signatures_text.pack(expand=True, fill="both")
        digital_signatures_scrollbar = tk.Scrollbar(digital_signatures_frame, command=self.digital_signatures_text.yview)
        self.digital_signatures_text.config(yscrollcommand=digital_signatures_scrollbar.set)
        digital_signatures_scrollbar.pack(side="right", fill="y")

        self.scanner_backend = None
        
    def update_gui(self, data):
        """
        Updates the GUI with the latest data for the device ID.
        Args:
            data (dict): The data to update in the GUI.
        """
        for key, value in data.items():
            if key in self.value_entries:
                self.value_entries[key].config(state="normal")
                self.value_entries[key].delete(0, tk.END)
                self.value_entries[key].insert(0, str(value))  # Convert value to string
                self.value_entries[key].config(state="readonly")
            if key == "Digital Signature Matched":
                color = "green" if value == True else "red"
                self.value_entries[key].config(bg=color)

    def toggle_testing(self):
        """
        Toggles the testing state and updates the testing button accordingly.
        """
        try:
            if self.testing_button["text"] == "Start Testing":
                self.scanner_backend = PiSyncBackend(self.update_gui, self.update_button_text, self.update_notification, 
                                                     self.update_digital_signatures, device_id=self.device_id_entry.get())
                self.update_notification(f"Testing started for device ID: {self.device_id_entry.get()}")
                self.scanner_backend.start_monitoring()
                self.testing_button.config(text="Testing", bg="#FFA500")
                self.scanner_backend.toggle_scanning(True)
            else:
                self.testing_button.config(text="Start Testing", bg="#2ECC71")
                self.scanner_backend.toggle_scanning(False)
                self.update_notification("Testing stopped.")
        except Exception as e:
            self.update_notification(f"Error during testing: {e}")

    def update_button_text(self, text, bg):
        """
        Updates the text and background color of the testing button.
        Args:
            text (str): The new text for the button.
            bg (str): The new background color for the button.
        """
        self.testing_button.config(text=text, bg=bg)

    def update_notification(self, message):
        """
        Updates the packet information panel with a new message.
        Args:
            message (str): The message to be added to the panel.
        """
        self.packet_info_text.config(state="normal")
        self.packet_info_text.insert("end", message + "\n")
        self.packet_info_text.config(state="disabled")
        self.packet_info_text.see("end")

    def update_digital_signatures(self, message):
        """
        Updates the digital signatures and HMAC panel with a new message.
        Args:
            message (str): The message to be added to the panel.
        """
        self.digital_signatures_text.config(state="normal")
        self.digital_signatures_text.insert("end", message + "\n")
        self.digital_signatures_text.config(state="disabled")
        self.digital_signatures_text.see("end")

    def on_closing(self):
        """
        Cleans up resources and closes the application.
        """
        try:
            if self.scanner_backend:
                self.scanner_backend.closing_all()
            self.root.destroy()
        except Exception as e:
            self.update_notification(f"Error during closing: {e}")

    def reset_app(self):
        """
        Resets the application to its initial state.
        """
        if self.scanner_backend is not None:
            self.scanner_backend.closing_all()
            self.scanner_backend = None
        for label_text in self.labels:
            self.value_entries[label_text].config(state="normal")
            self.value_entries[label_text].delete(0, tk.END)
            self.value_entries[label_text].insert(0, "N/A")
            self.value_entries[label_text].config(state="readonly", bg="#D6DBDF")
        self.testing_button.config(text="Start Testing", bg="#2ECC71")
        self.update_notification("Application reset.")

# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = PiSyncApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Program interrupted by user. Exiting...")
        app.on_closing()
