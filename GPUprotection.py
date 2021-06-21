from subprocess import Popen, PIPE, STDOUT
import threading
from copy import copy, deepcopy
import serial
import serial.threaded
import os, time

DieTemp = 75
heat_to_power_map = {
    b'2':45,
    b'3':47,
    # b'4':38,
    # b'5':40,
    # b'6':42,
    # b'7':44,
    # b'8':46,
    b'9':50
}
debug = False
debug_temp_counter = 0
arduino_port = "/dev/ttyUSB0"

def main():
    print("Main: Creating Threads")
    thread_dict = {
    'proc_protection': threading.Thread(target=threadwrap,args=[process_monitor], name='proc_protection'),
    'arduino_control': threading.Thread(target=threadwrap,args=[arduino_fan_control], name='arduino_control')
    }
    print("Main: Starting Threads")
    for t in thread_dict.values():
        t.start()
    for t in thread_dict.values():
        t.join()



def threadwrap(threadfunc):
    while True:
        try:
            threadfunc()
        except BaseException as e:
            print('{!r}; restarting thread'.format(e))
        else:
            print('exited normally, bad thread; restarting')
        time.sleep(1)
  

def parse_nvidia_smi():
    nvidia_smi_query_all = ["nvidia-smi", "-q", "-a"]
    attribute_exceptions = ["HW Slowdown"]
    p = Popen(nvidia_smi_query_all,stdout=PIPE,stderr=STDOUT,close_fds=True)
    info = p.stdout.read()
    ret_hash = {}
    for line in info.decode("utf-8").split('\n'):
        if not line or line.startswith("="):
            continue
        indent_lvl = (len(line) - len(line.lstrip()))/4
        has_value = False
        key = line.strip()
        if " : " in line:
            key,value = line.split(" : ")
            key = key.strip()
            value = value.strip()
            has_value = True
        for ex in attribute_exceptions:
            if ex in key:
                has_value = False
        pid_val = None
        if "Process ID" in key:
            pid_val = value
            has_value = False
        if indent_lvl == 0 :
            if has_value:
                ret_hash[key] = value
            else:
                top_key = key
                ret_hash[top_key] = {}
            continue
        if indent_lvl == 1 :
            if has_value:
                ret_hash[top_key][key] = value
            else:
                second_key = key
                ret_hash[top_key][second_key] = {}
            continue
        if indent_lvl == 2 :
            if has_value:
                ret_hash[top_key][second_key][key] = value
            else:
                if pid_val:
                    third_key = key + " " + pid_val
                    pid_val = None
                else:
                    third_key = key
                ret_hash[top_key][second_key][third_key] = {}
            continue
        if indent_lvl == 3 :
            if has_value:
                ret_hash[top_key][second_key][third_key][key] = value
            else:
                fourth_key = key
                ret_hash[top_key][second_key][third_key][fourth_key] = {}
            continue
        if indent_lvl == 4 :
            if has_value:
                ret_hash[top_key][second_key][third_key][fourth_key][key] = value
            continue
    return ret_hash


def get_process_ids(nvidia_smi_hash,filter_pnames=["Xorg"]):
    pids = []
    for key, value in nvidia_smi_hash.items():   # iter on both keys and values
        if key.startswith('GPU'):
            for pkey,pval in nvidia_smi_hash[key]["Processes"].items():
                if pkey.startswith("Process ID"):
                    skip_me = False
                    for filter_pname in filter_pnames:
                        if filter_pname in nvidia_smi_hash[key]["Processes"][pkey]["Name"]:
                            skip_me = True
                    if not skip_me:
                        pids.append(pkey.split()[2])
            continue
    return pids

def get_gpu_max_temp(nvidia_smi_hash=None):
    global debug_temp_counter
    if not nvidia_smi_hash:
        nvidia_smi_hash = parse_nvidia_smi()
    temps = []
    for key, value in nvidia_smi_hash.items():   # iter on both keys and values
        if key.startswith('GPU'):
            temps.append(int(nvidia_smi_hash[key]["Temperature"]["GPU Current Temp"].split()[0]))
            continue
    if debug:
        temps = [int(debug_temp_counter%(DieTemp+15))]
        debug_temp_counter += 1
    if not temps:
        return None
    return max(temps)



def process_monitor():
    # cmd = '''nvidia-smi -q -a | grep "GPU Current Temp" | awk -F" " '{print $5}' '''
    # while True:
    #     p = Popen(cmd,stdout=PIPE,stderr=STDOUT,close_fds=True)
    #     temperture = p.stdout.read()
    #     if temperture > DieTemp:
    while True:
        nvidia_smi_info = parse_nvidia_smi()
        temp = get_gpu_max_temp(nvidia_smi_info)
        if not temp:
            print("process_monitor: No temperture found?")
            time.sleep(3)
            continue
        print("process_monitor: Temp: " + str(temp))
        
        if temp > DieTemp:
            os.system("shutdown /s /t 1")
        time.sleep(3)

def arduino_fan_control():
    # cmd = '''nvidia-smi -q -a | grep "GPU Current Temp" | awk -F" " '{print $5}' '''
    # while True:
    #     p = Popen(cmd,stdout=PIPE,stderr=STDOUT,close_fds=True)
    #     temperture = p.stdout.read()
    #     if temperture > DieTemp:
    arduino = serial.Serial(arduino_port, 9600,timeout=1)
    print("Asking arduino to Turn Fan ON MAX power")
    arduino.write(b'255-')
    while True:
        #fan_on = False
        nvidia_smi_info = parse_nvidia_smi()
        temp = get_gpu_max_temp(nvidia_smi_info)
        if not temp:
            print("arduino_fan_control: No temperture found?")
            time.sleep(0.5)
            continue
        print("arduino_fan_control: Temps: " + str(temp))
        power = temp - 35
        power = max(0,power)
        power = power * power
        power = 76 + int(power * (255.0/400))
        power = str(min(255, power)).rjust(3,'0') + '-'
        print("Sending to arduino " + power,end='')

        arduino.write(power.encode())
        print(" .")
        respons = arduino.read_until()
        print("Arduino responded with: " + str(respons))
        # for power in sorted(heat_to_power_map.keys()):
        #     if temp < heat_to_power_map[power]:
        #         print("setting power to " + str((int(power)+1)*10) + " Sending to arduino: " + str(int(power)))
        #         arduino.write(power)
        #         fan_on = True
        #         respons = arduino.read_until()
        #         print("Arduino responded with: " + str(respons))
        #         break
        # if not fan_on:
        #     print("Asking arduino to Turn Fan ON MAX power")
        #     arduino.write(b'9')
        time.sleep(0.2)



if __name__ == "__main__":
    main()