import string

first = []
second = []
third = []

current = first
for line in open("NOMES"):
    line = line.strip()
    if not line:
        if not first:
            current = first
        elif not second:
            current = second
        elif not third:
            current = third
        else:
            raise ValueError, "Oops.. too many blank lines."
    else:
        current.append(line)

first.sort()
second.sort()
third.sort()

acronyms = {}

for s1 in first:
    for s2 in second:
        for s3 in third:
            name = " ".join([s1,s2,s3])
            acronym = "".join([x[0] for x in name.split()])
            acronyms.setdefault(acronym, []).append(name)

firstletter = dict.fromkeys([x[0] for x in second], True)
for s1 in string.uppercase:
    for s2 in second:
        for s3 in third:
            name = " ".join([s1,s2,s3])
            acronym = "".join([x[0] for x in name.split()])
            name = acronym+" "+" ".join(name.split()[1:])
            acronyms.setdefault(acronym, []).append(name)

items = acronyms.items()
items.sort()
for acronym, names in items:
    print acronym, "=", names[0]
    for name in names[1:]:
        print " "*(len(acronym)+2), name

