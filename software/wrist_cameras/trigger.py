"""Camera-side software trigger; exits and restores pins when reader exits."""
import argparse,ctypes,os,signal,time
import wrist_camera_runtime as hw
p=argparse.ArgumentParser();p.add_argument('--bus',type=int,required=True);p.add_argument('--parent',type=int,required=True)
a=p.parse_args();hw.BUS=a.bus
stopping=False
def stop(*_):
 global stopping
 stopping=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
# PR_SET_PDEATHSIG. Recheck PPID to cover the setup race.
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0:
 raise OSError(ctypes.get_errno(),'prctl')
if os.getppid()!=a.parent:stopping=True
try:
 while not stopping:
  for address in hw.CAMERAS:hw.write(address,0x2d3,0x90)
  time.sleep(.005)
  for address in hw.CAMERAS:hw.write(address,0x2d3,0x80)
  time.sleep(.09)
finally:
 errors=[]
 for address in hw.CAMERAS:
  try:hw.write(address,0x2d3,0x84)
  except Exception as error:errors.append(str(error))
 if errors:raise RuntimeError('; '.join(errors))
