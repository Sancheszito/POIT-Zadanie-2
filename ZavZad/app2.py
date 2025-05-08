import serial
ser=serial.Serial("/dev/ttyS0",9600)
while True:
	read_ser=ser.readline()
	print(read_ser.decode())
