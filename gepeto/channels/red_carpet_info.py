
name = "Red Carpet Channel"

description = """
Channel for the Red Carpet package tool.
"""

fields = [("baseurl", "Base URL for packages",
           "URL where packages are found"),
          ("packageinfourl", "URL for packageinfo XML",
           "URL for packageinfo.xml.gz including filename "
           "(option may be ommitted if file is named packageinfo.xml.gz "
           "and is inside the base url)")]
