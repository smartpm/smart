import sys
sys.argv = ["./smart.py", "test"]
exec(open('./smart.py').read())

MAIN = "cooker-ciril"
CONTRIB = "contrib-ciril"

def main():
    for pkg in cache.getPackages():
        for loader in pkg.loaders:
            if loader.getChannel().getAlias() == MAIN:
                break
        else:
            continue
        firstreq = True
        for req in pkg.requires:
            foundmain = False
            foundcontrib = []
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    for loader in prvpkg.loaders:
                        name = loader.getChannel().getAlias()
                        if name == CONTRIB:
                            foundcontrib.append((prv, prvpkg))
                        elif name == MAIN:
                            foundmain = True
                            break
                    else:
                        continue
                    break
            if not foundmain:
                if firstreq:
                    firstreq = False
                    print(pkg)
                    print("  Requires:")
                print("   ", req)
                if foundcontrib:
                    print("      Contrib:")
                    for prv, prvpkg in foundcontrib:
                        print("       ", prvpkg)
        if not firstreq:
            print()

if __name__ == "__main__":
    main()
