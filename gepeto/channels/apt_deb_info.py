
name = "APT-DEB Repository"

description = """
Repositories created for APT-DEB.
"""

fields = [("baseurl", "Base URL",
           "Base URL of repository, where dists/ is located."),
          ("distribution", "Distribution",
           "Distribution to use."),
          ("components", "Components",
           "Space separated list of components."),
          ("fingerprint", "Fingerprint",
           "GPG fingerprint of key signing the channel.")]
