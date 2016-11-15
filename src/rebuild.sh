#!/usr/bin/env sh
opam upgrade -y tcpip
mirage configure -t unix --net=direct --http-port=8080 # This requires tun/tap interface above
rm -f main.native
make
