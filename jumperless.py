import os
import json
import time
import re
from serial.serialwin32 import Serial as Serial
import serial.tools.list_ports


# Constants
JUMPERLESS_HWID = 'USB VID:PID=1D50:ACAB SER=0'
CLEAR = '::bridgelist[]'.encode()
FLASH_MODE = "::bridgelist[116-70,117-71]".encode()
RE_INCREMENT_EXPRESSION = re.compile(r'^(\d+)\+\+\(([A-Za-z0-9]+(?:( ?+, ?+)[A-Za-z0-9]+)*)\)$')
RE_SERIES_EXPRESSION = re.compile(r'\b[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+\b')


# Global variables
netlist = set()
current_file = ""


def save_netlist(filename: str) -> None:
    global current_file
    with open(f'{filename}.json', 'w') as f:
        json.dump(list(netlist), f)
    current_file = filename
    print(f"Saved: {filename}")


def load_netlist(filename: str) -> None:
    global current_file
    if os.path.exists(f'{filename}.json'):
        with open(f'{filename}.json', 'r') as f:
            netlist.update(json.load(f))
        print(f"Opened: {filename}")
        current_file = filename
        apply_netlist()
    else:
        print(f"File {filename}.json not found")


def apply_netlist() -> None:
    command = f"::bridgelist[{','.join(netlist)}]"
    ser.write(command.encode())
    resp = ser.read_all().decode()
    # if 'ok' not in resp:
    #     print(f"Error: {resp}")


def array_expression_to_netlist(array_list: str) -> [str]:
    connections = []
    match = RE_INCREMENT_EXPRESSION.match(array_list)
    start_pin = int(match.group(1))
    connections_to = [s.strip() for s in match.group(2).split(',')]
    print(connections_to)
    if len(connections_to) == 0:
        return []
    for connect_to in connections_to:
        if connect_to.strip() != "x":
            c = f"{start_pin}-{connect_to.strip()}"
            connections.append(c)
        start_pin += 1
        
    return connections


def series_expression_to_netlist(series: str) -> [str]:
    connections = []
    connections_to = [s.strip() for s in series.split('-')]
    for (i,c) in enumerate(connections_to[:-1]):
        cf = f"{c}-{connections_to[i+1]}"
        connections.append(cf)
    return connections


def split_custom_expanded(s):
    """
    Split the string by commas, correctly handling nested parentheses and additional patterns.
    """
    items = []
    current = []
    depth = 0
    for char in s:
        if char == ',' and depth == 0:
            items.append(''.join(current).strip())
            current = []
        else:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            current.append(char)
    if current:
        items.append(''.join(current).strip())  # Add the last item
    return items


def get_jumperless_port() -> str:
    candidates = [device for device in list(serial.tools.list_ports.comports()) if device.hwid == JUMPERLESS_HWID]
    if len(candidates) == 0 :
        print("No Jumperless found")
        return None
    elif len(candidates) > 1:
        print("Multiple Jumperless found")
        for (i,candidate) in enumerate(candidates):
            print(f"[{i}] {candidate.description} at {candidate.name}")
        index = input("Please select one: ")
        if not index.isdigit() or int(index) < 0 or int(index) >= len(candidates):
            print("Invalid selection")
            return None
        return candidates[int(index)].name
    else:
        return candidates[0].name


###--- Main ---###

jumperless_port_name = get_jumperless_port()
if jumperless_port_name is None:
    exit(1)

ser = Serial(jumperless_port_name, 115200, timeout=5)

print("-"*50)
intro = """
1)  Connect two rails: 5-30
2)  Connect a series of rails: VCC-1-2-3-4
3)  Remove a rail from a net: -30
4)  Separate multiple commands with commas:
        5-30,-20,20-40
    Is saying: connect 5->30, disconnect 20, connect 20->40
5) Series expansion:
        1++(10,20,x,40)
    Produces: 1-10, 2-20, 4-40 (skips 3)
6) Special commands:
    'clear' to reset the board.
    `flash` to put Arduino into flashing mode.
    'save <filename>' to save current netlist.
    'load <filename>' to load netlist from file.
"""
print(intro)
print("-"*50)


while True:
    user_input = input(f"[{current_file}] >> ").lower().strip()
    if user_input == 'clear':
        ser.write(CLEAR)
        netlist.clear()
        current_file = ""
        continue
    elif user_input == 'flash':
        ser.write(FLASH_MODE)
        ser.close() # Release the port to allow external programs to flash
        input("Upload sketch to Arduino and press any key when done")
        ser.open()
        time.sleep(1)
        apply_netlist()
        continue
    elif user_input.startswith('save'):
        if len(netlist) == 0:
            print("No connections to save")
            continue
        arguments = user_input.split(' ')
        if len(arguments) == 1:
            if current_file == "": # There is no current file
                current_file = "default"
            else:   # There is a current file
                current_file = current_file
        else:
            current_file = arguments[1]
        save_netlist(current_file)
        continue
    elif user_input.startswith('load'):
        arguments = user_input.split(' ')
        filename = arguments[1].strip() if len(arguments) > 1 else input("Please specify file:\n").strip()
        if len(filename) > 0:
            load_netlist(filename)
        continue
    user_input = re.sub('vcc', '5v', user_input, re.IGNORECASE)
    connections = [c.strip() for c in split_custom_expanded(user_input)]
    ok = True
    for connection in connections:
        if connection.startswith('-'):
            node = connection[1:]
            # If 1->2 and 2->3, then 1->3
            # After we remove 2, we have to (re)connect 1->3
            net = set() # get all the nodes connected to the removed node
            for c in netlist.copy():
                (a,b) = c.split('-')
                if a == node:
                    net.add(b)
                    netlist.remove(c)
                elif b == node:
                    net.add(a)
                    netlist.remove(c)
            net = list(net)
            for (i,c) in enumerate(net[:-1]):
                netlist.add(f"{c}-{net[i+1]}")
        elif re.match(r'^\w+-\w+$', connection):
            netlist.add(connection)
        elif RE_INCREMENT_EXPRESSION.match(connection):
            _netlist = array_expression_to_netlist(connection)
            if len(_netlist) > 0:
                print(" | ".join(_netlist))
                netlist.update(_netlist)
            else:
                print("No valid connections in array", connection)
                ok = False
        elif RE_SERIES_EXPRESSION.match(connection):
            _netlist = series_expression_to_netlist(connection)
            if len(_netlist) > 0:
                print(" | ".join(_netlist))
                netlist.update(_netlist)
            else:
                print("No valid connections in array", connection)
                ok = False               
        else:
            print("Invalid connection: ", connection)
            ok = False
    if not ok:
        continue
    apply_netlist()