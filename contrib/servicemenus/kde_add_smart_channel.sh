#!/bin/sh

path="$1"

rpmpkgs=$(ls -l $path | grep \.rpm | wc -l)
debpkgs=$(ls -l $path | grep \.deb | wc -l)

if [ $rpmpkgs -gt 0 ] && [ $debpkgs -gt 0 ]; then
  type=$(kdialog --title "Add Smart channel" --combobox "RPM and DEB files found. Which should I add?" "Both" "RPM" "DEB")
  if [ "$?" -ne 0 ]; then exit $?; fi
elif [ $rpmpkgs -gt 0 ]; then
  type="RPM"
else
  type="DEB"
fi

dirname=$(echo $path | awk -F'/' '{ print $(NF-1)"-"$NF }')
addrpm="smart --gui channel --add rpm-dir-$dirname type=rpm-dir name=rpm-dir-$dirname path=$path -y"
adddeb="smart --gui channel --add deb-dir-$dirname type=deb-dir name=deb-dir-$dirname path=$path -y"

case $type in
  Both)
    $addrpm
    $adddeb
    ;;
  RPM)
    $addrpm
    ;;
  DEB)
    $adddeb
    ;;
esac

error=$?

if [ "$error" -ne 0 ]; then
  kdialog --error "Error from Smart! ($error)"
else
  kdialog --msgbox "Smart channel added."
fi
