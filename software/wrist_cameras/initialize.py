"""Initialize only camera-side registers after both patched wrist probes finish."""
import fcntl,json,subprocess,time
from pathlib import Path
import wrist_camera_runtime as hw
from wrist_cameras import discover_devices,LOCK_PATH,READY_PATH

def main():
 with open(LOCK_PATH,'r+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  ready=Path(READY_PATH);ready.unlink(missing_ok=True)
  deadline=time.monotonic()+60
  while True:
   try:
    devices=discover_devices();hw.BUS=devices['wrist_a']['bus']
    assert hw.read(0x48,13)==0x94,'wrong deserializer'
    assert hw.read(0x48,1)&3==1,'driver did not configure 3Gbps'
    assert hw.read(0x48,0x13)&8,'GMSL link unlocked'
    for address in hw.CAMERAS:
     assert hw.read(address,13) in (0x91,0x93),'wrong serializer'
     assert hw.read(address,0)>>1==address,'wrong serializer alias'
    break
   except (RuntimeError,AssertionError,subprocess.SubprocessError) as error:
    if time.monotonic()>=deadline:raise RuntimeError('Wrist probes not ready: '+str(error))
    time.sleep(.5)
  if subprocess.run(['fuser',*(v['device'] for v in devices.values())],capture_output=True).returncode==0:
   raise RuntimeError('Refusing to initialize cameras in use')
  try:
   for address in hw.CAMERAS:
    for register,value in hw.VENDOR:hw.write(address,register,value)
    time.sleep(.765)
    for register,value in hw.VENDOR_RELEASE:hw.write(address,register,value)
    for register,value in hw.VIDEO[address]:hw.write(address,register,value)
   for register,value in hw.DESER:hw.write(0x48,register,value)
   time.sleep(.3)
   for address in hw.CAMERAS:
    for register,value in hw.VIDEO[address][-6:]:
     assert hw.read(address,register)==value,(address,register)
  finally:
   restore_errors=[]
   for address in hw.CAMERAS:
    try:hw.write(address,0x2d3,0x84)
    except Exception as error:restore_errors.append(str(error))
   if restore_errors:raise RuntimeError('; '.join(restore_errors))
  data={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'devices':devices,'initialized_at_unix':time.time(),'trigger':'on demand via WristCameras API'}
  ready.parent.mkdir(parents=True,exist_ok=True)
  temporary=ready.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2));temporary.replace(ready)
  print(json.dumps(data,indent=2))
if __name__=='__main__':main()
