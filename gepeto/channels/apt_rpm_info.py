
name = "APT-RPM Repository"

description = """
Repositories created for APT-RPM.
"""

fields = [("baseurl", "Base URL",
           "Base URL of APT-RPM repository, where base/ is located."),
          ("components", "Components",
           "Space separated list of components."),
          ("fingerprint", "Fingerprint",
           "GPG fingerprint of key signing the channel.")]

def detectLocalChannels(path, media):
    import os
    channels = []
    if os.path.isfile(os.path.join(path, "base/release")):
        components = {}
        for entry in os.listdir(os.path.join(path, "base")):
            if entry.startswith("pkglist."):
                entry = entry[8:]
                if entry.endswith(".bz2"):
                    entry = entry[:-4]
                elif entry.endswith(".gz"):
                    entry = entry[:-3]
                components[entry] = True
        for component in components.keys():
            if not os.path.isdir(os.path.join(path, "RPMS."+component)):
                del components[component]
        if components:
            if media:
                baseurl = "localmedia://"
                baseurl += path[len(media.getMountPoint()):]
            else:
                baseurl = "file://"
                baseurl += path
            components = " ".join(components.keys())
            channel = {"baseurl": baseurl, "components": components}
            if media:
                infofile = os.path.join(media.getMountPoint(), ".disk/info")
                if os.path.isfile(infofile):
                    file = open(infofile)
                    channel["name"] = file.read().strip()
                    file.close()
            channels.append(channel)
    return channels

