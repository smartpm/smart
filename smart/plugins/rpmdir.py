
from smart import *

if sysconf.has("rpm-dir"):

    from smart.channels.rpm_dir import RPMDirChannel

    def createRPMDirChannel():
        channel = RPMDirChannel(sysconf.get("rpm-dir"),
                                "rpm-dir",
                                "rpm-dir-option",
                                "Dynamic RPM Directory",
                                True, False, 0) 
        return [channel]
    
    hooks.register("rebuild-dynamic-channels", createRPMDirChannel)
