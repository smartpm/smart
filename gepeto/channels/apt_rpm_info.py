
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
