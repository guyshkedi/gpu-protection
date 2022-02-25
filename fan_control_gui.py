from functools import update_wrapper
import subprocess

from PySimpleGUI.PySimpleGUI import Button
from GPUprotection import get_gpu_max_temp
import PySimpleGUI as sg
import serial
from pystemd.systemd1 import Unit

arduino_port = "/dev/ttyUSB0"

def main():
    fcg = FanControlGui()
    fcg.start_loop()


class FanControlGui():

    
    #window config
    title="FanControlGui"
    x=80
    y=70
    down_text = "    v     "
    up_text = "    ^     "
    turn_on_service = "Turn On Service"
    stop_service = "Stop Service"
    connect_arduino = "Connect To Serial Port @Arduino"
    disconnect_arduino = "Disconnect"
    get_speed = "Get Fan Speed"
    update_speed = "Update Speed"
    
    def __init__(self):

        self.speed_value_text = sg.Text("-1",size=(5,1))
        self.arduino_connection_button = sg.Button(self.connect_arduino)
        self.arduino = None
        self.arduino_connected = False
        self.new_power = 255
        self.down_button = sg.Button(self.down_text,disabled=True)
        self.up_button = sg.Button(self.up_text,disabled=True)
        self.speed_button = sg.Button(self.get_speed)
        
        self.set_new_speed_input = sg.Input(size=(6,1))
        status = get_GPUprotection_status()
        print("-D- gpu-proteciton status: " + str(status))
        if status:
            self.GPUprotection_status_colored = sg.Text("O",background_color="green")
            self.GPUprotection_status_text = sg.Text("Running")
            self.GPUprotection_button = sg.Button(self.stop_service)
        else:
            self.GPUprotection_status_colored = sg.Text("X",background_color="red")
            self.GPUprotection_status_text = sg.Text("Not Running" )
            self.GPUprotection_button = sg.Button(self.turn_on_service)
        
        
        self.gpu_temp_value = sg.Text(str(get_gpu_max_temp()))



        layout = [
            [
                sg.Text("GPU Temp:"),
                self.gpu_temp_value
            ],
            [
                sg.Text("GPUprotection service\nstatus:"),
                self.GPUprotection_status_colored,
                self.GPUprotection_status_text,
                self.GPUprotection_button
            ], 
            [
                self.arduino_connection_button
            ],
            [
                sg.Text("Current Speed(0-255):"),
                self.speed_value_text,
                self.speed_button
            ],
            [            
                self.up_button,
                sg.Text("Up")
            ],
            [
                self.down_button,
                sg.Text("Down")
            ],
            [
                sg.Text("Set Speed:"),
                self.set_new_speed_input,
                sg.Button(self.update_speed)
            ]
            ]

        self.window = sg.Window(title=self.title, layout=layout, margins=(self.x, self.y))

    def start_loop(self):
        unit = Unit(b'gpu-protection.service')
        while True:
            event, value = self.window.read(timeout=1000)
            if event in (None,'Quit'):
                break
            self.update_GPUprotection()
            self.update_gpu_temp()
            if self.arduino_connected:
                try:
                    self.arduino.write(str(self.new_power).encode())
                except Exception as e:
                    print(e)
                    if not get_GPUprotection_status():
                        unit.load()
                        unit.Start(b'replace')
                 
            if event == self.up_text or event == self.down_text:
                self.change_fan_power(event)
            elif event == self.turn_on_service:
                unit.load()
                try:
                    unit.Start(b'replace')
                except Exception as e:
                    print(e)
                    sg.popup_error('-E- Unable to Start Service! (do you have permission?)')
            elif event == self.stop_service:
                unit.load()
                try:
                    unit.Stop(b'replace')
                except Exception as e:
                    print(e)
                    sg.popup_error('-E- Unable to Stop Service! (do you have permission?)')
            elif event == self.connect_arduino or event == self.disconnect_arduino:
                self.invoke_arduino_connection(event)
            elif event == self.get_speed:
                self.update_fan_speed()
            elif event == self.update_speed:
                self.change_fan_power(new_power=int(self.set_new_speed_input.get()))
            
    def change_fan_power(self,direction=None,new_power=None):
        try:
            if not new_power:
                fan_speed = int(self.speed_value_text.get())
                print("Fan Speed: " + str(fan_speed))
        except Exception as e:
            print(e)
            self.arduino_disconnected()
            sg.popup_error("Failed to get current speed!\nCant update speed without beeing connected to arduino")
            return
        try:
            if direction == self.up_text:
                new_power = fan_speed + 1
                if new_power > 255:
                    new_power = 255
            elif direction == self.down_text:
                new_power = fan_speed - 1
                if new_power < 76:
                    new_power = 76
            self.new_power = str(new_power).rjust(3,'0')+"-"
            print("-D- Writting to arduino: " + self.new_power)
            self.arduino.write(self.new_power.encode())
            respons = self.arduino.read_until()
            print("Arduino responded with: " + str(respons))
        except Exception as e:
            print(e)
            self.arduino_disconnected()
            sg.popup_error("Failed to write to arduino!")

    def invoke_arduino_connection(self,action):
        if action == self.connect_arduino:
            try:
                self.serial_connect_arduino()
                self.arduino_connected = True
                self.arduino_connection_button.update(self.disconnect_arduino)
                self.up_button.update(disabled=False)
                self.down_button.update(disabled=False)
            except Exception as e:
                self.arduino_connected = False
                print(e)
                sg.popup_error("Failed to connect to arduino")
        elif action == self.disconnect_arduino:
            print("Disconnecting")
            try:
                self.arduino_disconnected()
                self.arduino
            except Exception as e:
                print(e)
                self.arduino_connected = False
                sg.popup_error("Failed to close connection to arduino")
        
    def arduino_disconnected(self):
        self.arduino_connected = False
        self.arduino_connection_button.update(self.connect_arduino)
        self.up_button.update(disabled=True)
        self.down_button.update(disabled=True)

    def update_GPUprotection(self):
        status = get_GPUprotection_status()
        if status:
            self.GPUprotection_status_colored.update("O",background_color="green")
            self.GPUprotection_status_text.update("Running")
            self.GPUprotection_button.update("Stop Service")
        else:     
            self.GPUprotection_status_colored.update("X",background_color="red")
            self.GPUprotection_status_text.update("Stopped")
            self.GPUprotection_button.update("Turn On Service")

    def update_gpu_temp(self):
        self.gpu_temp_value.update(str(get_gpu_max_temp()))
        pass
    
    def update_fan_speed(self):
        self.new_power = get_fan_speed(self.arduino)
        self.speed_value_text.update(str(self.new_power))
        

    def serial_connect_arduino(self):
        self.arduino = serial.Serial(arduino_port, 9600,timeout=1)

def get_fan_speed(arduino):
    try:
        fan_speed = arduino.read_until()
        print("Got fan_speed from arduino: ",end='')
        print(fan_speed)
        fan_speed.decode("utf-8")
    except Exception as e:
        print(e)
        fan_speed = -1
    if not fan_speed:
        fan_speed = -1
    return int(fan_speed)


def get_GPUprotection_status():
    unit = Unit(b'gpu-protection.service')
    unit.load()
    if unit.ActiveState == b"active":
        return True
    return False


main()