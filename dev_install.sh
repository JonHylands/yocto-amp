#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

rm -rf dist/
rm -rf *.egg-info/
python setup.py sdist
cd dist/
tar -xvzf $(ls | grep fxos-powertool)
rm *.tar.gz
cd ../
sudo python setup.py install
